from django.db import models
from django.db.models import Sum
from django.core.validators import MinValueValidator
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class Restaurant(models.Model):
    name = models.CharField('название', max_length=50)
    address = models.CharField('адрес', max_length=100, blank=True)
    contact_phone = models.CharField('контактный телефон', max_length=50, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'


class ProductQuerySet(models.QuerySet):
    def available(self):
        return self.distinct().filter(menu_items__availability=True)


class ProductCategory(models.Model):
    name = models.CharField('название', max_length=50)

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField('название', max_length=50)
    category = models.ForeignKey(ProductCategory, null=True, blank=True, on_delete=models.SET_NULL,
                                 verbose_name='категория', related_name='products')
    price = models.DecimalField('цена', max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField('картинка')
    special_status = models.BooleanField('спец.предложение', default=False, db_index=True)
    description = models.TextField('описание', max_length=200, blank=True)

    objects = ProductQuerySet.as_manager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items',
                                   verbose_name="ресторан")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='menu_items',
                                verbose_name='продукт')
    availability = models.BooleanField('в продаже', default=True, db_index=True)

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]


class OrderQuerySet(models.QuerySet):
    def fetch_with_order_price(self):
        orders_with_price = self.annotate(
            order_price=Sum('order_items__price')
        )
        return orders_with_price


class Order(models.Model):
    STATUS_CHOICES = [(0, 'Необработанный'), (1, 'Обработанный')]
    PAYMENT_CHOICES = [(0, 'Сразу'), (1, 'Электронно'), (2, 'Наличностью')]

    firstname = models.CharField('имя', max_length=25)
    lastname = models.CharField('фамилия', max_length=25)
    phonenumber = PhoneNumberField('телефон')
    address = models.CharField('адрес', max_length=200)
    status = models.IntegerField('статус', choices=STATUS_CHOICES, default=0)
    payment = models.IntegerField('оплата', choices=PAYMENT_CHOICES, null=True, blank=True)
    restaurant = models.ForeignKey('Restaurant', null=True, blank=True, on_delete=models.SET_NULL)
    comment = models.TextField('комментарий', blank=True)
    registered_at = models.DateTimeField('получен', default=timezone.now)
    called_at = models.DateTimeField('согласован', null=True, blank=True)
    delivered_at = models.DateTimeField('доставлен', null=True, blank=True)

    objects = OrderQuerySet.as_manager()

    def __str__(self):
        return f'{self.firstname} {self.lastname} {self.address}'

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'


class OrderItem(models.Model):
    order = models.ForeignKey('Order', verbose_name='заказ', related_name='order_items', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', verbose_name='товар', related_name='product_orders', null=True, on_delete=models.SET_NULL)
    quantity = models.IntegerField(verbose_name='количество', validators=[MinValueValidator(1)])
    price = models.DecimalField('цена', max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])

    def __str__(self):
        return f'{self.product} {self.order.firstname} {self.order.lastname} {self.order.address}'

    class Meta:
        verbose_name = 'элемент заказа'
        verbose_name_plural = 'элементы заказа'


class Place(models.Model):
    address = models.CharField('адрес', max_length=200)
    lon = models.FloatField('долгота', null=True, blank=True)
    lat = models.FloatField('широта', null=True, blank=True)

    def __str__(self):
        return f'{self.address} ({self.lon}, {self.lat})'

    class Meta:
        verbose_name = 'место'
        verbose_name_plural = 'места'
