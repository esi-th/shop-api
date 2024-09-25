from django.db import models
from django.conf import settings

from products.models import Product


class Order(models.Model):
    ORDER_STATUS_PAID = 'paid'
    ORDER_STATUS_UNPAID = 'unpaid'
    ORDER_STATUS_PENDING = 'pending'
    ORDER_STATUS = [
        (ORDER_STATUS_PAID, 'Paid'),
        (ORDER_STATUS_UNPAID, 'Unpaid'),
        (ORDER_STATUS_PENDING, 'Pending'),
    ]

    OXAPAY_GATEWAY = 'oxapay'
    GATEWAY_CHOICES = [
        (OXAPAY_GATEWAY, 'Oxapay'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders', verbose_name='User')
    total_price = models.IntegerField('Total Price', default=0)
    status = models.CharField('Status', max_length=7, choices=ORDER_STATUS, default=ORDER_STATUS_UNPAID)
    is_paid = models.BooleanField('Is Paid', default=False)

    gateway = models.CharField('Gateway', max_length=10, choices=GATEWAY_CHOICES, default=OXAPAY_GATEWAY)
    gateway_track_id = models.CharField('Gateway Track ID', max_length=255, blank=True, default='')
    gateway_response = models.TextField('Gateway Response', blank=True, null=True)

    datetime_created = models.DateTimeField('Created At', auto_now_add=True)

    def __str__(self):
        return f'#{self.id}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='items', verbose_name='Order')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items', verbose_name='Product')
    price = models.IntegerField('Price')

    class Meta:
        unique_together = [['order', 'product']]
    