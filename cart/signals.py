from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import Cart

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_cart(sender, instance, created, **kwargs):
    """
    This signal listens for the creation of new user instances.
    When a new user is created, it automatically creates a cart for that user.
    """
    if created:
        Cart.objects.create(user=instance)
