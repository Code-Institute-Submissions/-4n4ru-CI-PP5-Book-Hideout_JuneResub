# Generated by Django 3.2 on 2022-06-26 10:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sale', '0003_auto_20220626_0029'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='sale_name',
            field=models.CharField(default='sale', max_length=254),
            preserve_default=False,
        ),
    ]
