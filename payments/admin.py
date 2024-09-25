from django.contrib import admin

from .models import Gateway


@admin.register(Gateway)
class GatewayAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'id']
