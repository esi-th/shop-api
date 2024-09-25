from rest_framework import serializers


from . import models


class ProductSerilizer(serializers.ModelSerializer):
    class Meta:
        model = models.Product
        fields = ['id', 'thumbnail', 'title', 'features', 'price', 'offprice', 'exclusive']
    