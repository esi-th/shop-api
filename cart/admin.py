from django.contrib import admin

from . import models


class CartItemInlines(admin.TabularInline):
    model = models.CartItem
    fields = ['id', 'product', ]
    extra = 0


@admin.register(models.Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user']
    inlines = [CartItemInlines, ]
