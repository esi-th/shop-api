from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers


from .models import Order, OrderItem
from products.models import Product
from cart.models import Cart, CartItem


class OrderItemProductSerializer(serializers.ModelSerializer):
    """
    Serializer for the Product model, used within OrderItemSerializer.
    Serializes the 'id', 'title', and 'thumbnail' fields of the Product.
    """
    class Meta:
        model = Product
        fields = ['id', 'title', 'thumbnail', ]


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for the OrderItem model.
    Includes the nested OrderItemProductSerializer to serialize the product details.
    """
    product = OrderItemProductSerializer()
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'price', ]


class OrderSerailizer(serializers.ModelSerializer):
    """
    Serializer for the Order model.
    Includes the nested OrderItemSerializer to serialize order items details.
    """
    items = OrderItemSerializer(many=True)
    class Meta:
        model = Order
        fields = ['id', 'total_price',  'status', 'gateway_track_id', 'datetime_created', 'items', ]


class OrderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating an Order from user`s cart.
    Validates the cart ID and creates an Order and associated OrderItems.
    """
    cart_id = serializers.UUIDField()

    # validate method to check the validity of cart_id
    def validate_cart_id(self, cart_id):
        try:
            if Cart.objects.prefetch_related('items').get(id=cart_id).items.count() == 0:
                raise serializers.ValidationError('your cart is empty.')
        except Cart.DoesNotExist:
            raise serializers.ValidationError('there is no cart with this cart id.')
        return cart_id
    
    # save method to create an order from the cart
    def save(self, **kwargs):
        cart_id = self.validated_data['cart_id']
        user_id = self.context['user_id']
        user = get_user_model().objects.get(id=user_id)

        with transaction.atomic():
            order = Order()
            order.user = user
            order.save()

            cart_items = CartItem.objects.filter(cart_id=cart_id)
            order.total_price = sum([item.product.price for item in cart_items])
            order.save()
            # Create a list of order items based on the cart items
            order_items = [
                OrderItem(
                    order=order,
                    product=cart_item.product,
                    price=cart_item.product.price,
                ) for cart_item in cart_items
            ]

            OrderItem.objects.bulk_create(order_items)

            # empty user`s cart
            for item in cart_items:
                item.delete()

            return order
        