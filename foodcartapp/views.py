import json

from django.http import JsonResponse
from django.templatetags.static import static

from .models import Order
from .models import OrderItem
from .models import Product

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            },
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


@api_view(['POST'])
def register_order(request):
    received_order = request.data
    if 'products' not in received_order:
        return Response({'error': 'products key is not presented or not list'},
                        status=status.HTTP_400_BAD_REQUEST)
    products = received_order['products']
    if isinstance(products, list) and products:
        order = Order.objects.create(firstname=received_order['firstname'],
                                     lastname=received_order['lastname'],
                                     phonenumber=received_order['phonenumber'],
                                     address=received_order['address'])
        for order_item in products:
            product = Product.objects.get(id=order_item['product'])
            OrderItem.objects.create(order=order,
                                     product=product,
                                     quantity=order_item['quantity'])
        return Response({'ok': True})
    else:
        return Response({'error': 'products key is not presented or not list'},
                        status=status.HTTP_400_BAD_REQUEST)
