from collections import defaultdict
from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from foodcartapp.models import Product, Restaurant, Order, RestaurantMenuItem, OrderItem


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    default_availability = {restaurant.id: False for restaurant in restaurants}
    products_with_restaurants = []
    for product in products:

        availability = {
            **default_availability,
            **{item.restaurant_id: item.availability for item in product.menu_items.all()},
        }
        orderer_availability = [availability[restaurant.id] for restaurant in restaurants]

        products_with_restaurants.append(
            (product, orderer_availability)
        )

    return render(request, template_name="products_list.html", context={
        'products_with_restaurants': products_with_restaurants,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


def serialize_order(order, restaurants_with_products):
    return {
        'id': order.id,
        'status': order.get_status_display(),
        'payment': order.get_payment_display(),
        'restaurants': get_available_restaurants(restaurants_with_products,
                                                 get_product_ids(order)),
        'price': order.order_price,
        'firstname': order.firstname,
        'lastname': order.lastname,
        'phonenumber': order.phonenumber,
        'address': order.address,
        'comment': order.comment
    }


def get_available_restaurants(restaurants_with_products, product_ids):
    available_restaurants = []
    for restaurant_name, available_products_ids in restaurants_with_products.items():
        if product_ids.issubset(available_products_ids):
            available_restaurants.append(restaurant_name)
    return available_restaurants


def get_product_ids(order):
    order_items = order.order_items
    product_ids = set(order_items.values_list('product_id', flat=True))
    return product_ids


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):

    restaurant_menu_items = RestaurantMenuItem.objects.\
        filter(availability=True).\
        values_list('restaurant__name', 'product')

    restaurants_with_products = defaultdict(set)
    for restaurant_menu_item in restaurant_menu_items:
        restaurants_with_products[restaurant_menu_item[0]].add(restaurant_menu_item[1])

    orders = Order.objects.fetch_with_order_price().order_by('id')

    serialized_orders = [serialize_order(order, restaurants_with_products) for order in orders]

    return render(request, template_name='order_items.html', context={
        'orders': serialized_orders
    })
