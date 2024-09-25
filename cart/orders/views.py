from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status

from . import serializers
from . import models


class OrderViewSet(ModelViewSet):
    """
    ViewSet for managing Orders.
    Supports 'GET' to retrieve authenticatend user`s orders and 'POST' to create a new order from cart.
    """
    http_method_names = ['get', 'post', ]
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.OrderSerailizer
    
    def get_queryset(self):
        """
        Retrieves the queryset of Orders for the authenticated user.
        Prefetches related items and products for optimization.
        """
        queryset = models.Order.objects.prefetch_related(
            'items__product'
        ).filter(user_id=self.request.user)
        return queryset
    
    def get_serializer_class(self):
        """
        Returns the appropriate serializer class based on the request method.
        Uses OrderCreateSerializer for 'POST' requests and OrderSerailizer for 'GET' requests.
        """
        if self.request.method == 'POST':
            return serializers.OrderCreateSerializer
        return serializers.OrderSerailizer
    
    def get_serializer_context(self):
        """
        Provides additional context to the serializer, specifically the user ID.
        """
        return {'user_id': self.request.user.id}
    
    def create(self, request, *args, **kwargs):
        """
        Handles the creation of a new Order from a Cart.
        Validates the request data and saves the new order, returning the serialized order data.
        """
        create_order_serializer = serializers.OrderCreateSerializer(
            data=request.data, 
            context={'user_id': self.request.user.id}
        )
        create_order_serializer.is_valid(raise_exception=True)
        created_order = create_order_serializer.save()

        serializer = serializers.OrderSerailizer(created_order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
