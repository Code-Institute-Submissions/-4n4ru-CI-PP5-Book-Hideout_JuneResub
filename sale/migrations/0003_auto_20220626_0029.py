# Generated by Django 3.2 on 2022-06-25 23:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0007_alter_product_isbn13'),
        ('sale', '0002_rename_genre_sale_books'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sale',
            name='books',
        ),
        migrations.AddField(
            model_name='sale',
            name='books',
            field=models.ManyToManyField(to='products.Product'),
        ),
    ]
