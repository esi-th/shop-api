from rest_framework import serializers
from .models import Gateway

# Serializer to handle creation of Payment Gateway
# It takes `order_id` and `gateway_id` as input fields.
class CreatePaymentGateway(serializers.Serializer):
    order_id = serializers.IntegerField()
    gateway_id = serializers.IntegerField()

# Serializer for the `Gateway` model
# It serializes the `id`, `name`, `description`, and `logo` fields of the `Gateway` model.
class GatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gateway
        fields = ['id', 'name', 'description', 'logo']