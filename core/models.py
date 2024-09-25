from django.db import models
from django.contrib.auth.models import AbstractUser
from uuid import uuid4
from phonenumber_field.modelfields import PhoneNumberField


class CustomUser(AbstractUser):
    phone_number = PhoneNumberField(unique=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)


class Otp(models.Model):
    id = models.UUIDField('ID', default=uuid4, primary_key=True)
    receiver = PhoneNumberField()
    token = models.CharField('Token', max_length=6)
    expiration_time = models.DateTimeField('Expiration Time', null=True)
    password = models.CharField('Password' ,max_length=60, null=True)


class ForgetPasswordToken(models.Model):
    id = models.UUIDField('ID', default=uuid4, primary_key=True)
    phone_number = PhoneNumberField()
    expiration_time = models.DateTimeField('Expiration Time', null=True)
