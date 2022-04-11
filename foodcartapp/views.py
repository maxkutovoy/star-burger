import json

import phonenumbers
from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Product
from .models import Order
from .models import ProductInOrder


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
            } if product.category else None,
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
    new_order_data = request.data

    for param in ['products', 'firstname', 'lastname',
                  'phonenumber', 'address']:
        if param not in (new_order_data.keys()):
            content = f'error: {param}: Обязательное поле.'
            return Response(content, status=status.HTTP_406_NOT_ACCEPTABLE)
        elif not new_order_data[param] and param is not 'lastname':
            content = f'error: {param}: Поле не может быть пустым.'
            return Response(content, status=status.HTTP_406_NOT_ACCEPTABLE)

    if not isinstance(new_order_data['products'], list):
        content = 'error: products: Ожидался list со значениями'
        return Response(content, status=status.HTTP_406_NOT_ACCEPTABLE)

    elif not phonenumbers.is_valid_number(new_order_data['phonenumber']):
        content = 'error: phonenumber: Введен некорректный номер телефона.'
        return Response(content, status=status.HTTP_406_NOT_ACCEPTABLE)

    elif not isinstance(new_order_data['firstname'], str):
        content = 'error: firstname: Это поле должно быть str.'
        return Response(content, status=status.HTTP_406_NOT_ACCEPTABLE)

    for product in new_order_data['products']:
        if not Product.objects.filter(pk=product['product']):
            content = 'error: products: Нет продукта с таким индексом.'
            return Response(content, status=status.HTTP_406_NOT_ACCEPTABLE)

    new_order, _ = Order.objects.get_or_create(
        customer_first_name=new_order_data['firstname'],
        customer_last_name=new_order_data['lastname'],
        phone_number=new_order_data['phonenumber'],
        address=new_order_data['address'],
    )
    for product in new_order_data['products']:
        product_in_order = Product.objects.get(pk=product['product'])
        ProductInOrder.objects.create(
            order=new_order,
            product=product_in_order,
            quantity=product['quantity']
        )

# {
# 'products': [
#   {
#       'product': 2,
#       'quantity': 1
#   },
#   {
#       'product': 3,
#       'quantity': 1
#    }
# ],
# 'firstname': 'Максим',
# 'lastname': 'К',
# 'phonenumber': '+7 999 666 55 44',
# 'address': 'Омск'}
