# Generated by Django 3.2 on 2022-06-25 00:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0006_alter_product_isbn13'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='isbn13',
            field=models.CharField(max_length=13),
        ),
    ]
