from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from uuid import uuid4

from .models import Order, OrderItem
from products.models import Product
from cart.models import CartItem


#################################################
#                                               #
#                                               #
#              Views Test Cases                 #
#                                               #
#                                               #
#################################################


class OrderTests(TestCase):
    # Initial setup for each test
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username='testuser', password='password')
        self.client.force_authenticate(user=self.user)
        self.product = Product.objects.create(
            title='Test CopyTrader', price=100,
            thumbnail='https://picsum.photos/200/300'
        )
        self.cart = self.user.cart

    def test_create_order(self):
        # Test creating an order and verifying the response and database changes
        CartItem.objects.create(cart=self.cart, product=self.product)
        response = self.client.post('/orders/', {'cart_id': self.cart.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.total_price, 100)
        self.assertEqual(order.items.first().product, self.product)

    def test_list_orders(self):
        # Test listing orders and verifying the response data
        order = Order.objects.create(user=self.user, total_price=100)
        OrderItem.objects.create(order=order, product=self.product, price=100)
        
        response = self.client.get('/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['total_price'], 100)

    def test_empty_cart_validation(self):
        # Test validation when trying to create an order with an empty cart
        response = self.client.post('/orders/', {'cart_id': self.cart.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['cart_id'][0], 'your cart is empty.')

    def test_invalid_cart_id_validation(self):
        # Test validation when trying to create an order with an invalid cart ID
        invalid_cart_id = uuid4()
        response = self.client.post('/orders/', {'cart_id': invalid_cart_id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['cart_id'][0], 'there is no cart with this cart id.')


#################################################
#                                               #
#                                               #
#              Models Test Cases                #
#                                               #
#                                               #
#################################################


class OrderModelTest(TestCase):
    # Initial setup for each test
    def setUp(self):
        self.user = get_user_model().objects.create(
            username='testuser', 
            password='12345'
        )
        self.product = Product.objects.create(
            title='Test CopyTrader', price=100,
            thumbnail='https://picsum.photos/200/300'
        )

    def test_order_creation(self):
        # Test creating an order and verifying its attributes
        order = Order.objects.create(user=self.user, total_price=200)
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.total_price, 200)
        self.assertEqual(order.status, Order.ORDER_STATUS_UNPAID)
        self.assertFalse(order.is_paid)
        self.assertEqual(order.gateway, Order.OXAPAY_GATEWAY)

    def test_order_string_representation(self):
        # Test the string representation of the Order model
        order = Order.objects.create(user=self.user, total_price=200)
        self.assertEqual(str(order), f'#{order.id}')

    def test_order_item_creation(self):
        # Test creating an order item and verifying its attributes
        order = Order.objects.create(user=self.user)
        order_item = OrderItem.objects.create(order=order, product=self.product, price=100)
        self.assertEqual(order_item.order, order)
        self.assertEqual(order_item.product, self.product)
        self.assertEqual(order_item.price, 100)

    def test_order_item_unique_together_constraint(self):
        # Test the unique together constraint of the OrderItem model
        order = Order.objects.create(user=self.user)
        OrderItem.objects.create(order=order, product=self.product, price=100)
        with self.assertRaises(Exception):
            OrderItem.objects.create(order=order, product=self.product, price=100)


class OrderItemModelTest(TestCase):
    # Initial setup for each test
    def setUp(self):
        self.user = get_user_model().objects.create(
            username='testuser', 
            password='12345'
        )
        self.product = Product.objects.create(
            title='Test CopyTrader', price=100,
            thumbnail='https://picsum.photos/200/300'
        )
        self.order = Order.objects.create(user=self.user, total_price=200)

    def test_order_item_creation(self):
        # Test creating an order item and verifying its attributes
        order_item = OrderItem.objects.create(order=self.order, product=self.product, price=100)
        self.assertEqual(order_item.order, self.order)
        self.assertEqual(order_item.product, self.product)
        self.assertEqual(order_item.price, 100)
