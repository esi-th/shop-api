# Generated by Django 5.0.6 on 2024-07-17 10:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gateway',
            name='logo',
            field=models.ImageField(upload_to='gateways/logos/', verbose_name='Logo'),
        ),
    ]
