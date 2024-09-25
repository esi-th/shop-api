from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.test import TestCase

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from unittest.mock import patch

from orders.models import Order
from payments.models import PaymentRequest
from .serializers import CreatePaymentGateway, Gateway


#################################################
#                                               #
#                                               #
#              Views Test Cases                 #
#                                               #
#                                               #
#################################################


class GatewayListViewTests(APITestCase):

    def setUp(self):
        # Initial setup for each test
        self.user = get_user_model().objects.create_user(
            username='testuser', 
            password='password123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('gateways_list')
        self.gateway1 = Gateway.objects.create(
            name='Gateway 1', is_active=True, 
            description='test gateway', logo='https://picsum.photos/200/300'
        )
        self.gateway2 = Gateway.objects.create(
            name='Gateway 2', is_active=True, 
            description='test gateway', logo='https://picsum.photos/200/300'
        )
        self.gateway_inactive = Gateway.objects.create(
            name='Gateway Inactive', is_active=False,
            description='inactive gateway', logo='https://picsum.photos/200/300'
        )

    def test_get_active_gateways(self):
        # Test Case for active gateways list
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['name'], self.gateway1.name)
        self.assertEqual(response.data[1]['name'], self.gateway2.name)


class PaymentProcessViewTests(APITestCase):

    def setUp(self):
        # Initial setup for each test
        self.user = get_user_model().objects.create_user(
            username='testuser', 
            password='password123'
        )
        self.order = Order.objects.create(user=self.user, total_price=1000)
        self.gateway = Gateway.objects.create(
            name='Gateway 1', is_active=True, 
            description='test gateway', logo='https://picsum.photos/200/300'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('payment_process')

    def test_order_not_found(self):
        # Test case for when the specified order is not found
        data = {
            'order_id': 999,
            'gateway_id': self.gateway.id
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'gateway or order not found.')

    def test_gateway_not_found(self):
        # Test case for when the specified order is not found
        data = {
            'order_id': self.order.id,
            'gateway_id': 999
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'gateway or order not found.')

    def test_create_payment_request_success(self):
        # Test case for successfully creating a payment request
        data = {
            'order_id': self.order.id,
            'gateway_id': self.gateway.id
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('paylink', response.data)
        self.assertTrue(PaymentRequest.objects.filter(user=self.user, order=self.order).exists())

    def test_create_payment_request_too_many_requests(self):
        # Test case for making too many payment requests within 60 minutes
        PaymentRequest.objects.create(
            user=self.user, order=self.order,
            gateway=self.gateway,
            timestamp=timezone.now()
        )

        data = {
            'order_id': self.order.id,
            'gateway_id': self.gateway.id
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data['message'], 'you can only make a payment request for each order once every 60 minutes.')

    def test_create_payment_request_already_paid(self):
        # Test case for creating a payment request for an already paid order
        self.order.is_paid = True
        self.order.save()

        data = {
            'order_id': self.order.id,
            'gateway_id': self.gateway.id
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data['message'], 'your order has already been paid.')

    def test_create_payment_request_gateway_not_active(self):
        # Test case for inactive gateway
        self.gateway.is_active = False
        self.gateway.save()
        data = {
            'order_id': self.order.id,
            'gateway_id': self.gateway.id
        }
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'gateway is not active.')

    def test_create_payment_request_internal_server_error(self):
        # Test Case for gateway not respond
        # Mocking the gateway response to simulate an error
        with patch('payments.utils.oxapay_create_payment_gateway_request') as mock:
            mock.return_value = {'code': 500}
            data = {
                'order_id': self.order.id,
                'gateway_id': self.gateway.id
            }
            response = self.client.post(self.url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertEqual(response.data['message'], 'something is wrong. please call website support.')


class PaymentCallbackViewTests(APITestCase):

    def setUp(self):
        # Initial setup for each test
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='testuser', 
            password='password123'
        )
        self.client.force_authenticate(user=self.user)
        self.track_id = '12345678'
        self.invalid_track_id = '234123'
        self.gateway = Gateway.objects.create(
            name='Gateway 1', is_active=True,
            description='test gateway', logo='https://picsum.photos/200/300'
        )
        self.order = Order.objects.create(
            user=self.user, total_price=1000, 
            is_paid=False, gateway_track_id=self.track_id
        )
        self.url = f'http://127.0.0.1:8000/payment/callback/?trackId=&status=1'

    def test_payment_callback_success(self):
        # This test checks for a successful payment callback.
        with patch('payments.utils.oxapay_payment_callback_handler') as mock:
            mock.return_value = {'code': 200}
            response = self.client.get(self.url, {'trackId': self.track_id})
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['message'], 'transaction success.')

    def test_payment_callback_order_not_found(self):
        # This test checks for a scenario where the order is not found.
        response = self.client.get(self.url, {'trackId': self.invalid_track_id})
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data['message'], 'something is wrong.')

    def test_payment_callback_order_already_paid(self):
        # This test checks for a scenario where the order is already paid.
        self.order.is_paid = True
        self.order.save()
        response = self.client.get(self.url, {'trackId': self.track_id})
        
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data['message'], 'your order has already been paid.')

    def test_payment_callback_transaction_failed(self):
        # This test checks for a failed transaction.
        with patch('payments.utils.oxapay_payment_callback_handler') as mock:
            mock.return_value = {'code': 400}
            response = self.client.get(self.url, {'trackId': self.track_id})
            
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data['message'], 'transaction failed.')
        

#################################################
#                                               #
#                                               #
#            Serializers Test Cases             #
#                                               #
#                                               #
#################################################


class CreatePaymentGatewaySerializerTest(APITestCase):

    def test_valid_data(self):
        # Test case for valid data input
        data = {
            'order_id': 1,
            'gateway_id': 1,
        }
        serializer = CreatePaymentGateway(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_missing_order_id(self):
        # Test case for missing order_id field
        data = {
            'gateway_id': 1,
        }
        serializer = CreatePaymentGateway(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('order_id', serializer.errors)
        self.assertEqual(serializer.errors['order_id'][0], 'This field is required.')
    
    def test_missing_gateway_id(self):
        # Test case for missing gateway_id field
        data = {
            'order_id': 1,
        }
        serializer = CreatePaymentGateway(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('gateway_id', serializer.errors)
        self.assertEqual(serializer.errors['gateway_id'][0], 'This field is required.')

    def test_invalid_order_id(self):
        # Test case for invalid order_id field (e.g., a string instead of integer)
        data = {'order_id': 'invalid'}
        serializer = CreatePaymentGateway(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('order_id', serializer.errors)
        self.assertEqual(serializer.errors['order_id'][0], 'A valid integer is required.')


#################################################
#                                               #
#                                               #
#              Models Test Cases                #
#                                               #
#                                               #
#################################################


class PaymentRequestModelTest(TestCase):

    def setUp(self):
        # Initial setup for each test
        self.user = get_user_model().objects.create_user(
            username='testuser', 
            password='password123'
        )
        self.track_id = '12345678'
        self.gateway = Gateway.objects.create(
            name='Gateway 1', is_active=True, 
            description='test gateway', logo='https://picsum.photos/200/300'
        )
        self.order = Order.objects.create(
            user=self.user, total_price=1000, 
            is_paid=False, gateway_track_id=self.track_id
        )
        self.payment_request = PaymentRequest.objects.create(
            user=self.user,
            order=self.order,
            gateway=self.gateway,
            timestamp=timezone.now()
        )

    def test_payment_request_creation(self):
        # Test case for creating a PaymentRequest instance
        self.assertEqual(self.payment_request.user, self.user)
        self.assertEqual(self.payment_request.order, self.order)
        self.assertIsNotNone(self.payment_request.timestamp)
        self.assertTrue(isinstance(self.payment_request, PaymentRequest))

    def test_payment_request_str(self):
        # Test case for the __str__ method of PaymentRequest model
        expected_str = f'{self.user.username} - {self.payment_request.timestamp}'
        self.assertEqual(str(self.payment_request), expected_str)
