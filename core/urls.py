from django.urls import path

from . import views


urlpatterns = [
     path('register/', views.RegisterView.as_view(), name='register'),
     path('login/', views.LoginView.as_view(), name='login'),
     path('logout/', views.LogoutView.as_view(), name='logout'),
     path('forget/', views.ForgetPasswordView.as_view(), name='forget_password'),
     path('forget/verify/', views.ForgetPasswordVerifyView.as_view(), name='forget_password_verify'),
     path('password/reset/', views.PasswordResetView.as_view(), name='reset_password'),
     path('verify/', views.VerifyAccessTokenView.as_view(), name='verify_access_token'),
]
