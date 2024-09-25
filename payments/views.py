from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from datetime import timedelta

from .models import PaymentRequest, Gateway
from orders.models import Order
from . import serializers
from . import utils


class GatewayListView(APIView):
    """
    View for list of active gateways
    """
    http_method_names = ['get', ]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve a list of active payment gateways.",
        responses={200: serializers.GatewaySerializer(many=True)}
    )

    def get(self, request):
        gateways = Gateway.objects.filter(is_active=True).all()
        serializer = serializers.GatewaySerializer(gateways, many=True)
        return Response(serializer.data)


class PaymentProcessView(APIView):
    """
    View for processing the payment.
    This view handles the creation of a payment request to the payment gateway.
    """
    http_method_names = ['post', ]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create a payment request to the payment gateway.",
        request_body=serializers.CreatePaymentGateway,
        responses={
           201: openapi.Response('Created', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Payment gateway created successfully.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=201),
                    'paylink': openapi.Schema(type=openapi.TYPE_STRING, example='https://paymentgateway.com/paylink')
                }
            )),
            400: openapi.Response('Bad Request', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Gateway is not active.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=400),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='gateway is not active.')
                }
            )),
            404: openapi.Response('Not Found', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Gateway or order not found.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=404),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='gateway or order not found.')
                }
            )),
            405: openapi.Response('Method Not Allowed', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Order has already been paid.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=405),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='your order has already been paid.')
                }
            )),
            429: openapi.Response('Too Many Requests', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Payment request cooldown.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=429),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='you can only make a payment request for each order once every 60 minutes.')
                }
            )),
            500: openapi.Response('Internal Server Error', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Gateway service has problem.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=500),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='something is wrong. please call website support.')
                }
            ))
        }
    )
    def post(self, request):
        serializer = serializers.CreatePaymentGateway(data=request.data)
        serializer.is_valid(raise_exception=True)
        order_id = serializer.validated_data['order_id']
        gateway_id = serializer.validated_data['gateway_id']
        
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            gateway = Gateway.objects.get(id=gateway_id)
        except Order.DoesNotExist:
            return Response(
                {
                    'code': 404,
                    'message': 'gateway or order not found.'
                }, status=status.HTTP_404_NOT_FOUND
            )
        except Gateway.DoesNotExist:
            return Response(
                {
                    'code': 404,
                    'message': 'gateway or order not found.'
                }, status=status.HTTP_404_NOT_FOUND
            )
        
        if not gateway.is_active:
            return Response(
                {
                    'code': 400,
                    'message': 'gateway is not active.'
                }, status=status.HTTP_400_BAD_REQUEST
            )
        
        if order.is_paid:
            return Response(
                {
                    'code': 405,
                    'message': 'your order has already been paid.'
                }, status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        sixty_minutes_ago = timezone.now() - timedelta(minutes=60)
        last_request = PaymentRequest.objects.filter(
            user=request.user, 
            timestamp__gte=sixty_minutes_ago,
            gateway=gateway,
            order=order
        ).first()

        if last_request:
            return Response(
                {
                    'code': 429,
                    'message': 'you can only make a payment request for each order once every 60 minutes.'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        gateway_response = utils.oxapay_create_payment_gateway_request(
            order=order, 
            user=request.user,
            gateway=gateway,
        )
        if gateway_response['code'] == 201:
            return Response(
                {
                    'code': 201,
                    'paylink': gateway_response['paylink']
                }, status=status.HTTP_201_CREATED
            )
        else:
            return Response(
            {
                'code': 500,
                'message': 'something is wrong. please call website support.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
             
    
class PeymentCallbackView(APIView):
    """
    View for handling payment callback.
    This view processes the callback from the payment gateway to update order status.
    """
    http_method_names = ['get', ]

    @swagger_auto_schema(
        operation_description="Handle payment callback from the payment gateway.",
        manual_parameters=[
            openapi.Parameter('trackId', openapi.IN_QUERY, description="Track ID from the payment gateway", type=openapi.TYPE_STRING)
        ],
        responses={
            200: openapi.Response('Ok', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Transaction success.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=200),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='transaction success.'),
                    'track_id': openapi.Schema(type=openapi.TYPE_STRING, example='95357016')
                }
            )),
            204: openapi.Response('No Content', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Wong track id or payment track id not found.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=204),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='something is wrong.')
                }
            )),
            400: openapi.Response('Bad Request', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Transaction failed.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=400),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='transaction failed.'),
                    'track_id': openapi.Schema(type=openapi.TYPE_STRING, example='95357016')
                }
            )),
            405: openapi.Response('Method Not Allowed', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Order has already been paid.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=405),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='your order has already been paid.')
                }
            ))
        }
    )
    def get(self, request):
        with transaction.atomic():
            try:
                track_id = request.GET.get('trackId')
                order = get_object_or_404(Order, gateway_track_id=track_id)
            except:
                return Response(
                    {
                        'code': 204,
                        'message': 'something is wrong.'
                    }, status=status.HTTP_204_NO_CONTENT
                )
            
            if order.is_paid:
                return Response(
                    {
                        'code': 405,
                        'message': 'your order has already been paid.'
                    }, status=status.HTTP_405_METHOD_NOT_ALLOWED
                )
            
            gateway_response = utils.oxapay_payment_callback_handler(order.gateway_track_id)

            if gateway_response['code'] == 200:
                return Response(
                    {
                        'code': 200,
                        'message': 'transaction success.',
                        'track_id': track_id
                    }, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'code': 400,
                        'message': 'transaction failed.',
                        'track_id': track_id
                    }, status=status.HTTP_400_BAD_REQUEST
                )
