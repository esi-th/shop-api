from django.urls import reverse
from django.test import TestCase
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

from products.models import Product
from orders.models import Order, OrderItem

from .models import CartItem
from . import serializers


#################################################
#                                               #
#                                               #
#              Views Test Cases                 #
#                                               #
#                                               #
#################################################


class CartViewTests(TestCase):
    def setUp(self):
        """
        Set up initial data for tests.
        """
        self.cart_url = reverse('cart')
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.client.force_authenticate(user=self.user)
        self.cart = self.user.cart
        self.product_1 = Product.objects.create(
            title='Test Product 1', 
            price=10, 
            thumbnail='https://picsum.photos/200/300'
            )
        
    def test_get_cart(self):
        """
        Test getting the current user's cart.
        """
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.cart.id))
        self.assertIn('items', response.data)
        self.assertEqual(response.data['total_price'], 0)
    
    def test_add_product_to_cart(self):
        """
        Test adding a product to the current user's cart.
        """
        data = {
            'product': self.product_1.id
        }
        response = self.client.post(self.cart_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['code'], 201)
        self.assertEqual(response.data['message'], 'product added to your cart.')

    def test_add_existing_product_to_cart(self):
        """
        Test adding an already existing product to the current user's cart.
        """
        CartItem.objects.create(cart=self.cart, product=self.product_1)
        data = {
            'product': self.product_1.id
        }
        response = self.client.post(self.cart_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data['code'], 405)
        self.assertEqual(response.data['message'], 'product is already in your cart.')

    def test_add_purchased_product_to_cart(self):
        """
        Test adding a product that has already been purchased by the user to the cart.
        """
        order = Order.objects.create(user=self.user, total_price=10)
        OrderItem.objects.create(order=order, product=self.product_1, price=10)
        data = {
            'product': self.product_1.id
        }
        response = self.client.post(self.cart_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)
        self.assertEqual(response.data['message'], 'you have already purchased this product.')

    def test_remove_product_from_cart(self):
        """
        Test removing a product from the current user's cart.
        """
        cart_item = CartItem.objects.create(cart=self.cart, product=self.product_1)
        data = {
            'product': self.product_1.id
        }
        response = self.client.patch(self.cart_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CartItem.objects.filter(id=cart_item.id).exists())

    def test_remove_nonexistent_product_from_cart(self):
        """
        Test removing a product that is not in the current user's cart.
        """
        data = {
            'product': self.product_1.id
        }
        response = self.client.patch(self.cart_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['message'], 'product not found in your cart.')


#################################################
#                                               #
#                                               #
#            Serializers Test Cases             #
#                                               #
#                                               #
#################################################


class CartSerializerTests(TestCase):
    def setUp(self):
        """
        Set up initial data for tests.
        """
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.client.force_authenticate(user=self.user)
        self.cart = self.user.cart
        self.product = Product.objects.create(
            title='Test Product 1', 
            price=10, 
            thumbnail='https://picsum.photos/200/300'
            )
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.product)

    def test_cart_item_serializer(self):
        serializer = serializers.CartItemSerializer(self.cart_item)
        self.assertEqual(serializer.data['product']['title'], self.product.title)
        self.assertEqual(serializer.data['product']['price'], self.product.price)

    def test_cart_serializer(self):
        serializer = serializers.CartSerializer(self.cart)
        self.assertEqual(len(serializer.data['items']), 1)
        self.assertEqual(serializer.data['total_price'], self.product.price)

    def test_add_cart_item_serializer(self):
        data = {
            'product': self.product.id
        }
        serializer = serializers.AddCartItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_remove_cart_item_serializer(self):
        data = {
            'product': self.product.id
        }
        serializer = serializers.RemoveCartItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())


#################################################
#                                               #
#                                               #
#              Models Test Cases                #
#                                               #
#                                               #
#################################################


class CartModelTests(TestCase):
    def setUp(self):
        """
        Set up initial data for tests.
        """
        self.cart_url = reverse('cart')
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.client.force_authenticate(user=self.user)
        self.cart = self.user.cart
        self.product_1 = Product.objects.create(
            title='Test Product 1', 
            price=10, 
            thumbnail='https://picsum.photos/200/300'
            )
        self.product_2 = Product.objects.create(
            title='Test Product 2', 
            price=20, 
            thumbnail='https://picsum.photos/200/300'
            )

    def test_create_cart(self):
        self.assertEqual(self.cart, self.user.cart)

    def test_add_cart_item(self):
        cart_item = CartItem.objects.create(cart=self.cart , product=self.product_1)
        self.assertEqual(cart_item.cart, self.cart)
        self.assertEqual(cart_item.product, self.product_1)

    def test_cart_item_unique_constraint(self):
        CartItem.objects.create(cart=self.cart , product=self.product_1)
        with self.assertRaises(Exception):
            CartItem.objects.create(cart=self.cart , product=self.product_1)

    def test_cart_total_price(self):
        CartItem.objects.create(cart=self.cart , product=self.product_1)
        CartItem.objects.create(cart=self.cart , product=self.product_2)
        total_price = sum(item.product.price for item in self.cart .items.all())
        self.assertEqual(total_price, 30)
