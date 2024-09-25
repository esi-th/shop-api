from django.urls import path
from rest_framework.routers import DefaultRouter


from . import views


router = DefaultRouter()
router.register('', views.OrderViewSet, basename='orders')


urlpatterns = router.urls
