import requests
from django.conf import settings
from django.utils import timezone

from . import models


def send_otp_sms(phone_number, code):
    # request to kavehnegar api for send otp sms and resturn response
    body = {
        'receptor': f'+98{phone_number}',
        'token': code,
        'template': settings.KavenegarTemplate,
    }
    url = f'https://api.kavenegar.com/v1/{settings.KavenegarAPIKey}/verify/lookup.json'
    response = requests.post(url, params=body)
    return response


def check_otp_cooldown(phone_number):
    # checks phonenumber last sent otp for cooldown
    valid_otps = models.Otp.objects.filter(receiver=phone_number, expiration_time__gte=timezone.now())

    otp = valid_otps.last()

    if not otp:
        return None

    return otp.id
    