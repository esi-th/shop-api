from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth.hashers import check_password, make_password
from unittest.mock import patch
from . import models


# Constants for the test
TEST_PHONE_NUMBER = '+989170001111'  
TEST_PASSWORD = 'testpassword'  
USER_CREATION_USERNAME = '09170001111'  


class LoginViewTestCase(TestCase):
    def setUp(self):
        # Initial setup for each test
        self.client = APIClient()
        self.url = reverse('login')  
        self.user_data = {
            'phone_number': TEST_PHONE_NUMBER,
            'password': TEST_PASSWORD
        }
        # Create a user for testing
        self.user = get_user_model().objects.create_user(
            phone_number=TEST_PHONE_NUMBER,
            username=USER_CREATION_USERNAME, 
            password=TEST_PASSWORD
        )
    
    def test_login_success(self):
        """
        Test successful login with correct credentials.
        """
        response = self.client.post(self.url, self.user_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertIn('expire', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('access', response.data)
    
    def test_login_invalid_password(self):
        """
        Test login with an incorrect password.
        """
        invalid_data = self.user_data.copy()
        invalid_data['password'] = 'wrongpassword'  # Set an incorrect password
        response = self.client.post(self.url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'invalid phone number or password.')
    
    def test_login_user_does_not_exist(self):
        """
        Test login with a non-existent phone number.
        """
        non_existent_user_data = {
            'phone_number': '+989170004433',  # Non-existent phone number
            'password': TEST_PASSWORD
        }
        response = self.client.post(self.url, non_existent_user_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutViewTestCase(TestCase):
    def setUp(self):
        # Initial setup for each test
        self.client = APIClient()
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.user_data = {
            'phone_number': TEST_PHONE_NUMBER,
            'password': TEST_PASSWORD
        }
        # Create a user for testing
        self.user = get_user_model().objects.create_user(
            phone_number=TEST_PHONE_NUMBER, 
            username=USER_CREATION_USERNAME, 
            password=TEST_PASSWORD
        )

    def test_logout_user(self):
        """
        Test that a user can successfully log out.
        """
        response = self.client.post(
            self.login_url,
            self.user_data, 
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        refresh = response.data['refresh']
        access = response.data['access']
        
        self.client.credentials(HTTP_AUTHORIZATION=f'JWT {access}')
        response = self.client.post(
            self.logout_url,
            {'refresh_token': refresh},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
    

class RegisterViewTestCase(TestCase):
    def setUp(self):
        # Initial setup for each test
        self.client = APIClient()
        self.register_url = reverse('register')  
        self.phone_number = TEST_PHONE_NUMBER
        self.password = TEST_PASSWORD
        self.user_data = {
            'phone_number': self.phone_number,
            'password': self.password
        }

    def test_register_user_already_exists(self):
        """
        Test registration with a phone number that is already registered.
        """
        # Create a user with the phone number to simulate that it already exists
        get_user_model().objects.create_user(
            phone_number=self.phone_number, 
            username=USER_CREATION_USERNAME, 
            password=self.password
            )
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data['code'], 405)
        self.assertEqual(response.data['message'], 'user has already registerd.')

    @patch('core.utils.check_otp_cooldown')
    def test_register_too_many_requests(self, mock_check_otp_cooldown):
        """
        Test registration when too many OTP requests have been made.
        """
        # Create an OTP object to simulate existing OTP data
        otp_expiration_time = timezone.now() + timedelta(seconds=120)
        otp = models.Otp.objects.create(
            receiver=self.phone_number,
            token='1234',
            expiration_time=otp_expiration_time,
            password=self.password
        )
        mock_check_otp_cooldown.return_value = otp.id

        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data['code'], 429)
        self.assertEqual(response.data['message'], 'please wait before requesting a new OTP.')


    @patch('core.utils.send_otp_sms')
    def test_register_success(self, mock_send_otp_sms):
        """
        Test successful registration and OTP sending.
        """
        # Mock the send OTP function to simulate a successful send
        mock_send_otp_sms.return_value.status_code = 200
        
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['message'], 'success.')

        
        otp = models.Otp.objects.get(receiver=self.phone_number)
        self.assertIsNotNone(otp)
        self.assertEqual(otp.receiver, self.phone_number)

    @patch('core.utils.send_otp_sms')
    def test_register_otp_send_failure(self, mock_send_otp_sms):
        """
        Test registration when OTP sending fails.
        """
        # Mock the send OTP function to simulate a failure
        mock_send_otp_sms.return_value.status_code = 400
        
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)
        self.assertEqual(response.data['message'], 'something is wrong. please contact support.')


class VerifyAccessTokenViewTestCase(TestCase):
    def setUp(self):
        # Initial setup for each test
        self.client = APIClient()
        self.verify_url = reverse('verify_access_token')  
        self.phone_number = TEST_PHONE_NUMBER
        self.token = '1234'
        self.password = TEST_PASSWORD
        self.otp = models.Otp.objects.create(
            receiver=self.phone_number,
            token=self.token,
            expiration_time=timezone.now() + timedelta(minutes=2),
            password=self.password
        )

    def test_verify_access_token_success(self):
        """
        Test successful verification of the access token.
        """
        # Data to be sent in the verification request
        data = {
            'phone_number': self.phone_number,
            'token': self.token
        }
        response = self.client.post(self.verify_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertIn('expire', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('access', response.data)

    def test_verify_access_token_expired(self):
        """
        Test verification of an expired access token.
        """
        # Expire the OTP by setting its expiration time to the past
        self.otp.expiration_time = timezone.now() - timedelta(minutes=1)
        self.otp.save()
        data = {
            'phone_number': self.phone_number,
            'token': self.token
        }
        response = self.client.post(self.verify_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)
        self.assertEqual(response.data['message'], 'token has expired.')

    def test_verify_access_token_invalid(self):
        """
        Test verification of an invalid access token.
        """
        # Data to be sent in the verification request with an invalid token
        data = {
            'phone_number': self.phone_number,
            'token': '0000'
        }
        response = self.client.post(self.verify_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)
        self.assertEqual(response.data['message'], 'invalid phone number or token.')
    

class ForgetPasswordViewTestCase(TestCase):
    def setUp(self):
        # Initial setup for each test
        self.client = APIClient()
        self.url = reverse('forget_password') 
        self.phone_number = TEST_PHONE_NUMBER
        self.password = TEST_PASSWORD
        self.user = get_user_model().objects.create_user(
            phone_number=self.phone_number, 
            username=USER_CREATION_USERNAME, 
            password=self.password
            )
    
    @patch('core.utils.send_otp_sms')
    def test_forget_password_success(self, mock_send_otp_sms):
        """
        Test successful forget password request where OTP is sent.
        """
        # Mock the send OTP function to simulate a successful send
        mock_send_otp_sms.return_value.status_code = 200
        
        data = {'phone_number': self.phone_number}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['message'], 'success.')

    def test_forget_password_user_not_exist(self):
        """
        Test forget password request with a phone number that is not registered.
        """
        data = {'phone_number': '+989170002222'}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)

    @patch('core.utils.check_otp_cooldown')
    def test_forget_password_too_many_requests(self, mock_check_otp_cooldown):
        """
        Test forget password request when too many OTP requests have been made.
        """
        otp_expiration_time = timezone.now() + timedelta(seconds=120)
        otp = models.Otp.objects.create(
            receiver=self.phone_number,
            token='1234',
            expiration_time=otp_expiration_time
        )
        mock_check_otp_cooldown.return_value = otp.id

        data = {'phone_number': self.phone_number}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data['message'], 'please wait before requesting a new OTP.')


class ForgetPasswordVerifyViewTestCase(TestCase):
    def setUp(self):
        # Initial setup for each test
        self.client = APIClient()
        self.url = reverse('forget_password_verify')  # مسیر URL صحیح را وارد کنید
        self.phone_number = '+989170001111'
        self.token = '1234'
        self.otp = models.Otp.objects.create(
            receiver=self.phone_number,
            token=self.token,
            expiration_time=timezone.now() + timedelta(minutes=2)
        )

    def test_forget_password_verify_success(self):
        """
        Test successful verification of the forget password OTP token.
        """
        data = {
            'phone_number': self.phone_number,
            'token': self.token
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertIn('token', response.data)
        self.assertIn('expire', response.data)

    def test_forget_password_verify_expired_token(self):
        """
        Test verification of an expired OTP token.
        """
        self.otp.expiration_time = timezone.now() - timedelta(minutes=1)
        self.otp.save()
        data = {
            'phone_number': self.phone_number,
            'token': self.token
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)
        self.assertEqual(response.data['message'], 'token has expired.')

    def test_forget_password_verify_invalid_token(self):
        """
        Test verification of an invalid OTP token.
        """
        data = {
            'phone_number': self.phone_number,
            'token': '0000'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)
        self.assertEqual(response.data['message'], 'invalid phone number or token.')


class PasswordResetViewTestCase(TestCase):
    def setUp(self):
        # Initial setup for each test
        self.client = APIClient()
        self.url = reverse('reset_password')  
        self.phone_number = TEST_PHONE_NUMBER
        self.user = get_user_model().objects.create_user(
            phone_number=self.phone_number, 
            username=USER_CREATION_USERNAME, 
            password='oldpassword'
            )
        self.token = models.ForgetPasswordToken.objects.create(
            phone_number=self.phone_number,
            expiration_time=timezone.now() + timedelta(hours=2)
        )
        self.new_password = 'newpassword123'

    def test_password_reset_success(self):
        """
        Test successful password reset with a valid token.
        """
        data = {
            'token': str(self.token.id),
            'password': self.new_password
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['message'], 'success.')

        # Check if password was updated
        self.user.refresh_from_db()
        self.assertTrue(check_password(self.new_password, self.user.password))

    def test_password_reset_expired_token(self):
        """
        Test password reset with an expired token.
        """
        self.token.expiration_time = timezone.now() - timedelta(hours=1)
        self.token.save()
        data = {
            'token': str(self.token.id),
            'password': self.new_password
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)
        self.assertEqual(response.data['message'], 'token has expired.')

    def test_password_reset_invalid_token(self):
        """
        Test password reset with an invalid token.
        """
        data = {
            'token': 'ea61fa6d-fa8b-4f3f-aab6-ad4b360ab6ff',
            'password': self.new_password
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)
        self.assertEqual(response.data['message'], 'invalid token.')
