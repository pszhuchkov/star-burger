import requests

from collections import defaultdict
from environs import Env
from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from geopy import distance

from foodcartapp.models import Product, Restaurant, Order, RestaurantMenuItem


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


def serialize_order(order, restaurants_ids_with_products_ids):
    available_restaurants_ids = get_available_restaurants(
        restaurants_ids_with_products_ids, get_product_ids_for_order(order)
    )

    available_restaurants = Restaurant.objects.filter(
        id__in=available_restaurants_ids
    )

    serialized_available_restaurants = [serialize_restaurant(restaurant, order.address)
                                        for restaurant in available_restaurants]
    available_restaurants_sorted_by_distance = sorted(
        serialized_available_restaurants,
        key=lambda restaurant: restaurant['distance_to_order']
    )

    return {
        'id': order.id,
        'status': order.get_status_display(),
        'payment': order.get_payment_display(),
        'restaurants': available_restaurants_sorted_by_distance,
        'price': order.order_price,
        'firstname': order.firstname,
        'lastname': order.lastname,
        'phonenumber': order.phonenumber,
        'address': order.address,
        'comment': order.comment
    }


def serialize_restaurant(restaurant, order_address):
    env = Env()
    env.read_env()
    apikey = env("YANDEX_API_KEY")

    order_coordinates = fetch_coordinates(apikey, order_address)
    restaurant_coordinates = fetch_coordinates(apikey, restaurant.address)
    return {
        'id': restaurant.id,
        'name': restaurant.name,
        'address': restaurant.address,
        'distance_to_order': round(distance.distance(order_coordinates,
                                               restaurant_coordinates).km, 3)

    }


def get_available_restaurants(restaurants_ids_with_products_ids, product_ids):
    available_restaurants_ids = []
    for restaurant_id, available_products_ids in restaurants_ids_with_products_ids.items():
        if product_ids.issubset(available_products_ids):
            available_restaurants_ids.append(restaurant_id)
    return available_restaurants_ids


def get_product_ids_for_order(order):
    order_items = order.order_items
    product_ids = set(order_items.values_list('product', flat=True))
    return product_ids


def fetch_coordinates(apikey, place):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    params = {"geocode": place, "apikey": apikey, "format": "json"}
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']
    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lon, lat


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):

    restaurant_menu_items = RestaurantMenuItem.objects.\
        filter(availability=True).\
        values_list('restaurant', 'product')

    restaurants_ids_with_products_ids = defaultdict(set)
    for restaurant_menu_item in restaurant_menu_items:
        restaurants_ids_with_products_ids[restaurant_menu_item[0]].add(restaurant_menu_item[1])

    orders = Order.objects.fetch_with_order_price().order_by('id')

    serialized_orders = [serialize_order(order, restaurants_ids_with_products_ids) for order in orders]

    return render(request, template_name='order_items.html', context={
        'orders': serialized_orders
    })
