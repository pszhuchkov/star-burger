# Generated by Django 3.0.7 on 2021-02-25 12:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0043_auto_20210225_1450'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment',
            field=models.IntegerField(choices=[(0, 'Сразу'), (1, 'Электронно'), (2, 'Наличностью')], default=2, verbose_name='оплата'),
            preserve_default=False,
        ),
    ]
