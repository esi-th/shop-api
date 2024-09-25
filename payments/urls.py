from django.urls import path

from . import views


urlpatterns = [
    path('process/', views.PaymentProcessView.as_view(), name='payment_process'),
    path('callback/', views.PeymentCallbackView.as_view(), name='callback'),
    path('gateways/all/', views.GatewayListView.as_view(), name='gateways_list'),
]
