from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from . import serializers
from . import models
from orders.models import OrderItem


class CartView(APIView):
    """
    API view to manage the authenticated user's shopping cart.
    
    This view allows the user to:
    - Retrieve the current state of their cart.
    - Add a product to their cart.
    - Remove a product from their cart.

    Requires the user to be authenticated.
    """
    http_method_names = ['get', 'patch', 'post', ]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: serializers.CartSerializer()},
        operation_description="Get the current user's cart details."
    )
    def get(self, request):
        """
        Retrieve the current state of the authenticated user's cart.

        This method fetches the user's cart, including all items and their associated products,
        and returns it in a serialized format.

        Returns:
            Response: Contains the serialized cart data with a status of 200.
        """
        cart_id = self.request.user.cart.id
        cart = get_object_or_404(
            models.Cart.objects.prefetch_related('items__product').all(),
            id=cart_id
        )
        serializer = serializers.CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Add product to cart.",
        request_body=serializers.AddCartItemSerializer,
        responses={
            201: openapi.Response('Created', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Product added to cart successfully.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=201),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='product added to your cart.')
                }
            )),
            405: openapi.Response('Method Not Allowed', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Product is already in your cart.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=405),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='product is already in your cart.')
                }
            )),
            400: openapi.Response('Bad Request', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='You have already purchased this product.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=400),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='you have already purchased this product.')
                }
            ))
        }
    )
    def post(self, request):
        """
        Add a product to the authenticated user's cart.

        This method validates the product data from the request and adds the product to the user's cart
        if it is not already present and has not been purchased before.

        Returns:
            Response: Contains a success message with a status of 201 if the product is added successfully,
                      or an error message with appropriate status codes (405 or 400) if the product is already
                      in the cart or has been purchased before.
        """
        serializer = serializers.AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart_id = self.request.user.cart.id
        product = serializer.validated_data['product']

        if models.CartItem.objects.filter(cart_id=cart_id, product_id=product.id).exists():
            return Response(
                {
                    'code': 405,
                    'message': 'product is already in your cart.'
                }, status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

        existing_order_item = OrderItem.objects.filter(
            order__user=request.user,
            product_id=product.id,
        ).exists()

        if existing_order_item:
            return Response(
                {
                    'code': 400,
                    'message': 'you have already purchased this product.'
                }, status=status.HTTP_400_BAD_REQUEST
            )
        
        models.CartItem.objects.create(cart_id=cart_id, product=product)

        return Response(
            {
                'code': 201,
                'message': 'product added to your cart.'
            }, status=status.HTTP_201_CREATED
        )
    
    @swagger_auto_schema(
        operation_description="Remove product from cart.",
        request_body=serializers.RemoveCartItemSerializer,
        responses={
            204: openapi.Response('No Content', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Product Removed from cart successfully.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=204),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='product removed from your cart.')
                }
            )),
            404: openapi.Response('Not Found', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Product not found in cart.',
                properties={
                    'code': openapi.Schema(type=openapi.TYPE_INTEGER, example=404),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='product not found in your cart.')
                }
            ))
        }
    )
    def patch(self, request):
        """
        Remove a product from the authenticated user's cart.

        This method validates the product data from the request and removes the product from the user's cart
        if it is present.

        Returns:
            Response: Contains a success message with a status of 204 if the product is removed successfully,
                      or an error message with a status of 404 if the product is not found in the cart.
        """
        serializer = serializers.RemoveCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cart_id = self.request.user.cart.id
        product = serializer.validated_data['product']

        try:
            cart_item = models.CartItem.objects.get(cart_id=cart_id, product_id=product.id)
            cart_item.delete()
            return Response(
                {
                    'code': 204,
                    'message': 'product removed from your cart'
                }, status = status.HTTP_204_NO_CONTENT
            )
        except models.CartItem.DoesNotExist:
            return Response(
                {
                    'code': 404,
                    'message': 'product not found in your cart.'
                }, status=status.HTTP_404_NOT_FOUND
            )
