from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response


from drf_yasg.utils import swagger_auto_schema


from . import models
from . import serializers


class ProductListView(APIView):
    http_method_names = ['get', ]
    
    @swagger_auto_schema(
        operation_id='ProductsList',
        responses={
            200: serializers.ProductSerilizer(many=True),
            400: 'Bad Request'
        }
    )
    def get(self, request):
        queryset = models.Product.objects.all()
        serializer = serializers.ProductSerilizer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductDetailView(APIView):
    http_method_names = ['get', ]
    
    @swagger_auto_schema(
        operation_id='ProductDetail',
        responses={
            200: serializers.ProductSerilizer(),
            404: 'Not Found'
        }
    )
    def get(self, request, pk):
        product = get_object_or_404(models.Product, pk=pk)
        serializer = serializers.ProductSerilizer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)
    