from django.db import models


# class ProductType(models.Model):
#     title = models.CharField("Title", max_length=255)


# class ProductAttribute(models.Model):
#     title = models.CharField('Title', max_length=255)
#     product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE, verbose_name='Product Type')
#     attribute_type = models.CharField()
    

class Product(models.Model):
    title = models.CharField('Title', max_length=255)
    # type = models.ForeignKey(ProductType, on_delete=models.PROTECT)
    price = models.IntegerField('Price')
    offprice = models.IntegerField('Off Price', default=0)
    exclusive = models.BooleanField('Exclusive', default=False)
    features = models.JSONField('Features', blank=True, null=True)
    thumbnail = models.ImageField('Thumbnail', upload_to='products/product_thumbnails/', blank=True)

    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_modified = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title
