from django.urls import path


from . import views


urlpatterns = [
    path('all/', views.ProductListView.as_view(), name='products_list'),
    path('<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
]
