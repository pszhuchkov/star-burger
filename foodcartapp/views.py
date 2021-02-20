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

    if 'products' not in received_order or not received_order['products'] or not isinstance(received_order['products'], list):
        return Response({'error': 'products key is not presented or not list'},
                        status=status.HTTP_400_BAD_REQUEST)
    if 'firstname' not in received_order or not received_order['firstname'] or not isinstance(received_order['firstname'], str):
        return Response({'error': 'firstname key is not presented or not str'},
                        status=status.HTTP_400_BAD_REQUEST)
    if 'lastname' not in received_order or not received_order['lastname'] or not isinstance(received_order['lastname'], str):
        return Response({'error': 'lastname key is not presented or not str'},
                        status=status.HTTP_400_BAD_REQUEST)
    if 'phonenumber' not in received_order or not received_order['phonenumber'] or not isinstance(received_order['phonenumber'], str):
        return Response({'error': 'phonenumber key is not presented or not str'},
                        status=status.HTTP_400_BAD_REQUEST)
    if 'address' not in received_order or not received_order['address'] or not isinstance(received_order['address'], str):
        return Response({'error': 'address key is not presented or not str'},
                        status=status.HTTP_400_BAD_REQUEST)

    order = Order.objects.create(firstname=received_order['firstname'],
                                 lastname=received_order['lastname'],
                                 phonenumber=received_order['phonenumber'],
                                 address=received_order['address'])

    order_products = received_order['products']

    for order_product in order_products:
        if 'product' not in order_product or not isinstance(order_product['product'], int):
            return Response({'error': 'product is not presented or is not int'},
                            status=status.HTTP_400_BAD_REQUEST)
        product = Product.objects.get(id=order_product['product'])
        if not product:
            return Response({'error': 'product doesnt exist'},
                            status=status.HTTP_400_BAD_REQUEST)
        OrderItem.objects.create(order=order,
                                 product=product,
                                 quantity=order_product['quantity'])
    return Response({'ok': True})
