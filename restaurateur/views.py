import requests
import os

from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from geopy import distance
from requests.exceptions import RequestException

from foodcartapp.models import Product, Restaurant, Order, RestaurantMenuItem, Place


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


def serialize_order(order, restaurants_with_products_ids):
    available_restaurants = get_available_restaurants(
        restaurants_with_products_ids, get_product_ids_for_order(order)
    )

    formalized_available_restaurants = [formalize_restaurant(restaurant, order.address)
                                        for restaurant in available_restaurants.values()]
    available_restaurants_sorted_by_distance = sorted(
        formalized_available_restaurants,
        key=lambda restaurant: (restaurant['distance_to_order'] is None,
                                restaurant['distance_to_order'])
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


def formalize_restaurant(restaurant, order_address):
    try:
        distance_to_order = get_distance_between_two_addresses(
            restaurant['address'], order_address
        )
    except RequestException:
        distance_to_order = None

    return {
        'name': restaurant['name'],
        'address': restaurant['address'],
        'distance_to_order': distance_to_order
    }


def get_distance_between_two_addresses(address1, address2):
    apikey = os.environ['YANDEX_API_KEY']

    coords = []
    for address in [address1, address2]:
        try:
            place = Place.objects.get(address=address)
        except Place.DoesNotExist:
            lon, lat = fetch_coordinates(apikey, address)
            place = Place.objects.create(address=address, lon=lon, lat=lat)
            place.save()
        coords.append((place.lon, place.lat))
    distance_between_two_addresses = distance.distance(coords[0], coords[1]).km
    return round(distance_between_two_addresses, 3)


def get_available_restaurants(restaurants_with_products_ids, product_ids):
    available_restaurants = {}
    for restaurant_id, restaurant_properties in restaurants_with_products_ids.items():
        if product_ids.issubset(restaurant_properties['products']):
            available_restaurants[restaurant_id] = restaurant_properties
    return available_restaurants


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
        values_list('restaurant', 'restaurant__name', 'restaurant__address', 'product')

    restaurants_with_products_ids = {}
    for menu_item in restaurant_menu_items:
        restaurant_id, restaurant_name, restaurant_address, product_id = menu_item
        if restaurant_id in restaurants_with_products_ids:
            restaurants_with_products_ids[restaurant_id]['products'].add(product_id)
        else:
            restaurants_with_products_ids[restaurant_id] = {
                'name': restaurant_name,
                'address': restaurant_address,
                'products': {product_id}
            }

    orders = Order.objects.fetch_with_order_price().order_by('id')

    serialized_orders = [serialize_order(order, restaurants_with_products_ids)
                         for order in orders]

    return render(request, template_name='order_items.html', context={
        'orders': serialized_orders
    })
