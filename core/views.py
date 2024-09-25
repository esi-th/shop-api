from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils import timezone


from datetime import timedelta
import random
import string


from . import serializers
from . import utils
from . import models


class RegisterView(APIView):
    """ 
    Handles the user signup process, including OTP generation and validation, 
    and ensures the user doesn't already exist.
    """
    http_method_names = ['post', ]

    @swagger_auto_schema(
        operation_id='UserRegister',
        request_body=serializers.SignUpSerializer,
        responses={
            200: openapi.Response('Success', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=200),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='success.'),
                    'cooldown': openapi.Schema(type=openapi.TYPE_STRING, example='120')
                }
            )),
            400: openapi.Response('Bad Request', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=400),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='something is wrong. please contact support.')
                }
            )),
            405: openapi.Response('Method Not Allowed', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=405),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='user has already registered.')
                }
            )),
            429: openapi.Response('Too Many Requests', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=429),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='please wait before requesting a new OTP.'),
                    'remaining_time': openapi.Schema(type=openapi.TYPE_INTEGER, example=120)
                }
            ))
        }
    )
    def post(self, request):
        serializer = serializers.SignUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        password = serializer.validated_data['password']

        try:
            user = get_user_model().objects.get(phone_number=phone_number)
            return Response(
                {
                    'code': 405,
                    'message': 'user has already registerd.'
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        except get_user_model().DoesNotExist:
            cooldown = utils.check_otp_cooldown(phone_number)
            if cooldown is not None:
                otp = models.Otp.objects.get(id=cooldown)
                reamining_time = otp.expiration_time - timezone.now()
                return Response(
                    {
                        'code': 429,
                        'message': 'please wait before requesting a new OTP.',
                        'remaining_time': int(reamining_time.total_seconds())
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            code = ''.join(random.choices(string.digits, k=4))
            response = utils.send_otp_sms(phone_number, code)

            if response.status_code == 200:
                models.Otp.objects.create(
                    receiver=phone_number,
                    token=code,
                    expiration_time=timezone.now() + timedelta(minutes=2),
                    password=password
                )
                return Response(
                    {
                        'code': 200,
                        'message': 'success.',
                        'cooldown': '120',
                    }, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'code': 400,
                        'message': 'something is wrong. please contact support.'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            

class LoginView(APIView):
    """
    Manages user login, including authentication, token generation, 
    and verifying if the user exists and the credentials are correct.
    """
    http_method_names = ['post', ]

    @swagger_auto_schema(
        operation_id='UserLogin',
        request_body=serializers.LoginSerializer,
        responses={
            200: openapi.Response('Success', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=200),
                    'expire': openapi.Schema(type=openapi.TYPE_STRING, example='2024-07-04T18:14:30.647Z'),
                    'refresh': openapi.Schema(type=openapi.TYPE_STRING, example='refresh_token_example'),
                    'access': openapi.Schema(type=openapi.TYPE_STRING, example='access_token_example')
                }
            )),
            400: openapi.Response('Bad Request', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=400),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='invalid phone number or password.')
                }
            ))
        }
    )
    def post(self, request):
        serializer = serializers.LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        password = serializer.validated_data['password']

        try:
            user = get_user_model().objects.get(phone_number=phone_number)
            if user.check_password(password):
                refresh = RefreshToken.for_user(user)
                return Response(
                    {
                        'code': 200,
                        'expire': timezone.now() + timedelta(minutes=60),
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'code': 400,
                        'message': 'invalid phone number or password.'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
        except get_user_model().DoesNotExist:
            return Response(
                {
                    'code': 400,
                }, status=status.HTTP_400_BAD_REQUEST
            )


class VerifyAccessTokenView(APIView):
    """
    Handles the process of obtaining an access token using a phone number 
    and OTP, including user creation if needed (signup).
    """
    http_method_names = ['post', ]

    @swagger_auto_schema(
        operation_id='VerifyUserAfterRegisteration',
        request_body=serializers.ObtainAccessTokenSerializer,
        responses={
            200: openapi.Response('Success', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=200),
                    'expire': openapi.Schema(type=openapi.TYPE_STRING, example='2024-07-04T18:14:30.647Z'),
                    'refresh': openapi.Schema(type=openapi.TYPE_STRING, example='refresh_token_example'),
                    'access': openapi.Schema(type=openapi.TYPE_STRING, example='access_token_example')
                }
            )),
            400: openapi.Response('Bad Request', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=400),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='invalid phone number or token.')
                }
            ))
        }
    )
    def post(self, request):
        serializer = serializers.ObtainAccessTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        token = serializer.validated_data['token']

        try:
            otp = models.Otp.objects.get(receiver=phone_number, token=token)

            if otp.expiration_time > timezone.now():
                try:
                    user = get_user_model().objects.get(phone_number=phone_number)

                except get_user_model().DoesNotExist:

                    hashed_password = make_password(otp.password)

                    user = get_user_model().objects.create(
                        username=phone_number,
                        email=f'email{phone_number}@sigloy.com',
                        password=hashed_password,
                        phone_number=phone_number,
                    )

                refresh = RefreshToken.for_user(user)
                otp.delete()
                return Response(
                    {
                        'code': 200,
                        'expire': timezone.now() + timedelta(minutes=60),
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }, status=status.HTTP_200_OK
                )
            else:
                otp.delete()
                return Response(
                    {
                        'code': 400,
                        'message': 'token has expired.'
                    }, status=status.HTTP_400_BAD_REQUEST
                )

        except models.Otp.DoesNotExist:
            return Response(
                {
                    'code': 400,
                    'message': 'invalid phone number or token.'
                }, status=status.HTTP_400_BAD_REQUEST
            )


class ForgetPasswordView(APIView):
    """
    Initiates the password reset process by sending an OTP to the user's phone number if the user exists.
    """
    http_method_names = ['post', ]

    @swagger_auto_schema(
        operation_id='SendOtpForResetPassword',
        request_body=serializers.ForgetPasswordSerializer,
        responses={
            200: openapi.Response('Success', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=200),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='success.'),
                    'cooldown': openapi.Schema(type=openapi.TYPE_STRING, example='120')
                }
            )),
            400: openapi.Response('Bad Request', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=400)
                }
            )),
            429: openapi.Response('Too Many Requests', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='please wait before requesting a new OTP.'),
                    'remaining_time': openapi.Schema(type=openapi.TYPE_INTEGER, example=120)
                }
            ))
        }
    )
    def post(self, request):
        serializer = serializers.ForgetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        phone_number = serializer.validated_data['phone_number']

        try : 
            user = get_user_model().objects.get(phone_number=phone_number)
            cooldown = utils.check_otp_cooldown(phone_number)
            if cooldown is not None:
                otp = models.Otp.objects.get(id=cooldown)
                reamining_time = otp.expiration_time - timezone.now()
                return Response(
                    {
                        'message': 'please wait before requesting a new OTP.',
                        'remaining_time': int(reamining_time.total_seconds())
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            code = ''.join(random.choices(string.digits, k=4))
            response = utils.send_otp_sms(phone_number, code)

            if response.status_code == 200:
                models.Otp.objects.create(
                    receiver=phone_number,
                    token=code,
                    expiration_time=timezone.now() + timedelta(minutes=2),
                )
                return Response(
                    {
                        'code': 200,
                        'message': 'success.',
                        'cooldown': '120'
                    },
                    status=status.HTTP_200_OK
                )

        except get_user_model().DoesNotExist:
            return Response(
                {
                    'code': 400
                }, status=status.HTTP_400_BAD_REQUEST
            )


class ForgetPasswordVerifyView(APIView):
    """
    Verifies the OTP sent for password reset and generates a temporary token for resetting the password.
    """
    http_method_names = ['post', ]

    @swagger_auto_schema(
        operation_id='CreateResetPasswordToken',
        request_body=serializers.ForgetPasswordVerifySerializer,
        responses={
            200: openapi.Response('Success', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=200),
                    'token': openapi.Schema(type=openapi.TYPE_STRING, example='temporary_token_example'),
                    'expire': openapi.Schema(type=openapi.TYPE_STRING, example='2024-07-04T18:14:30.647Z')
                }
            )),
            400: openapi.Response('Bad Request', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=400),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='token has expired or invalid phone number or token.')
                }
            ))
        }
    )
    def post(self, request):
        serializer = serializers.ForgetPasswordVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        token = serializer.validated_data['token']

        try:
            otp = models.Otp.objects.get(receiver=phone_number, token=token)

            if otp.expiration_time > timezone.now():
                forget_password_token = models.ForgetPasswordToken.objects.create(
                    phone_number=phone_number,
                    expiration_time = timezone.now() + timedelta(hours=2)
                )
                return Response(
                    {
                        'code': 200,
                        'token': str(forget_password_token.id),
                        'expire': timezone.now() + timedelta(hours=2)
                    }, status=status.HTTP_200_OK
                )
            else:
                otp.delete()
                return Response(
                    {
                        'code': 400,
                        'message': 'token has expired.'
                    }, status=status.HTTP_400_BAD_REQUEST
                )

        except models.Otp.DoesNotExist:
            return Response(
                {
                    'code': 400,
                    'message': 'invalid phone number or token.'
                }, status=status.HTTP_400_BAD_REQUEST
            )
        

class PasswordResetView(APIView):
    """
    Resets the user's password using the temporary token and new password provided.
    """
    http_method_names = ['post', ]

    @swagger_auto_schema(
        operation_id='UserPasswordReset',
        request_body=serializers.PasswordResetSerializer,
        responses={
            200: openapi.Response('Success', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=200),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='success.')
                }
            )),
            400: openapi.Response('Bad Request', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=400),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='token has expired or invalid token.')
                }
            ))
        }
    )
    def post(self, request):
        serializer = serializers.PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        password = serializer.validated_data['password']

        try:
            forget_password_token = models.ForgetPasswordToken.objects.get(id=token)

            if forget_password_token.expiration_time > timezone.now():
                user = get_user_model().objects.get(phone_number=forget_password_token.phone_number)
                user.password = make_password(password)
                user.save()
                forget_password_token.delete()
                return Response(
                    {
                        'code': 200,
                        'message': 'success.'
                    }, status=status.HTTP_200_OK
                )
            else:
                forget_password_token.delete()
                return Response(
                    {
                        'code': 400,
                        'message': 'token has expired.'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
        
        except models.ForgetPasswordToken.DoesNotExist:
            return Response(
                {
                    'code': 400,
                    'message': 'invalid token.',
                }, status=status.HTTP_400_BAD_REQUEST
            )


class LogoutView(APIView):
    """
    Logs out the user by blacklisting the provided refresh token, ensuring it can no longer be used.
    """
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(operation_id='UserLogout')
    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        