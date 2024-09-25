from django.conf import settings
from django.db import models

from orders.models import Order


class Gateway(models.Model):
    name = models.CharField('Name', max_length=255)
    is_active = models.BooleanField('Is Active', default=False)
    description = models.CharField('Description', max_length=255)
    logo = models.ImageField('Logo', upload_to='gateways/logos/')

    def __str__(self):
        return self.name


class PaymentRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    gateway = models.ForeignKey(Gateway, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.timestamp}'
