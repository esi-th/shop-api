# Generated by Django 5.0.6 on 2024-07-12 17:06

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('orders', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Gateway',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
                ('is_active', models.BooleanField(default=False, verbose_name='Is Active')),
                ('description', models.CharField(max_length=255, verbose_name='Description')),
                ('logo', models.ImageField(upload_to='', verbose_name='Logo')),
            ],
        ),
        migrations.CreateModel(
            name='PaymentRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('gateway', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='payments.gateway')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.order')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]