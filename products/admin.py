from django.contrib import admin


from . import models


@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'price', 'offprice', 'exclusive', 'datetime_created', 'datetime_modified', ]
    list_display_links = ['title', ]
    search_fields = ['title', ]
