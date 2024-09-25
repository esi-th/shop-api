from django.shortcuts import get_object_or_404
from django.db import transaction
from django.conf import settings

import requests
import json

from orders.models import Order
from .models import PaymentRequest, Gateway


#################################################
#                                               #
#                                               #
#                Oxapay Gateway                 #
#                                               #
#                                               #
#################################################


def oxapay_create_payment_gateway_request(order: Order, gateway: Gateway, user):
    """
    This function initiates a payment request to the Oxapay payment gateway for a given order.
    It constructs the necessary data payload and sends a POST request to the Oxapay API.
    If the API response indicates success, it updates the order with the track ID, sets the order status to pending,
    and creates a PaymentRequest record. If the API response indicates failure, it returns an error message.
    """
    url = 'https://api.oxapay.com/merchants/request'
    data = {
        'merchant': settings.OXAPAY_MERCHANT_API_KEY,
        'amount': order.total_price,
        'lifeTime': 60,
        'feePaidByPayer': 1,
        'returnUrl': 'http://127.0.0.1:8000/payment/callback/',
        'description': f'User: {order.user} for order: {order.id}',
        'orderId': order.id
    }

    response = requests.post(url, data=json.dumps(data))
    response = response.json()
    
    if response['result'] == 100 and response['message'] == 'success':
        with transaction.atomic():
            order.gateway_track_id = response['trackId']
            order.gateway = Order.OXAPAY_GATEWAY
            order.status = Order.ORDER_STATUS_PENDING
            order.save()
            PaymentRequest.objects.create(
                user=user,
                gateway=gateway,
                order=order
            )
            return {
                    'code': 201,
                    'paylink': response['payLink']
            }
    else:
        return {
                'code': 400,
                'message': 'someting is wrong. please call website support.'
            }
    
def oxapay_payment_callback_handler(track_id):
    """
    This function handles the callback from the Oxapay payment gateway.
    It sends a POST request to the Oxapay API to inquire about the payment status of the given track ID.
    Depending on the response, it updates the order status to paid or unpaid, saves the gateway response if the payment is successful,
    and returns an appropriate message indicating the result of the transaction.
    """
    url = 'https://api.oxapay.com/merchants/inquiry'
    data = {
        'merchant': settings.OXAPAY_MERCHANT_API_KEY,
        'trackId': track_id
    }

    response = requests.post(url, data=json.dumps(data))
    response = response.json()

    order = get_object_or_404(Order, gateway_track_id=track_id)
    
    if response['result'] == 100 and response['status'] == 'Paid':
        with transaction.atomic():
            order.is_paid = True
            order.status = Order.ORDER_STATUS_PAID
            order.gateway_response = response
            order.save()
        return {
            'code': 200,
            'message': 'transaction success.',
            'track_id': track_id
        }
    else:
        with transaction.atomic():
            order.status = Order.ORDER_STATUS_UNPAID
            order.save()
        return {
            'code': 400,
            'message': 'transaction failed.',
            'track_id': track_id
        }
    