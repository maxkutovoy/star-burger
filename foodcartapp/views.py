import json

import phonenumbers
from django.db import transaction
from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.serializers import Serializer, ModelSerializer
from rest_framework.serializers import ValidationError
from rest_framework.serializers import CharField, IntegerField
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from .models import Product
from .models import Order
from .models import ProductInOrder
from .models import RestaurantMenuItem


class ProductInOrderSerializer(Serializer):
    product = IntegerField()
    quantity = IntegerField()

    def validate_product(self, value):
        if not value:
            return 'Error'
        return value


class OrderSerializer(ModelSerializer):
    products = ProductInOrderSerializer(many=True, write_only=True)

    def validate_products(self, value):
        if not value:
            raise ValidationError(
                'error: products: Список продуктов не может быть пустым.'
            )
        elif not any(
            Product.objects.filter(pk=product['product']) for product in value
        ):
            raise ValidationError(
                'error: products: Недопустимый первичный ключ.'
            )
        return value

    class Meta:
        model = Order
        fields = [
            'id',
            'status',
            'payment_form',
            'firstname',
            'lastname',
            'phonenumber',
            'address',
            'comment'
            'products',
        ]

        def validate_phone_number(self, value):
            if not phonenumbers.is_valid_number(value):
                raise ValidationError(
                    'error: phonenumber: Введен некорректный номер телефона.'
                )
            return value


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


@transaction.atomic
@api_view(['POST'])
def register_order(request):
    new_order_data = request.data

    serializer = OrderSerializer(data=new_order_data)
    serializer.is_valid(raise_exception=True)

    new_order = Order.objects.create(
        firstname=serializer.validated_data['firstname'],
        lastname=serializer.validated_data['lastname'],
        phonenumber=serializer.validated_data['phonenumber'],
        address=serializer.validated_data['address'],
    )

    for product in serializer.validated_data['products']:
        product_in_order = Product.objects.get(pk=product['product'])
        ProductInOrder.objects.create(
            order=new_order,
            product=product_in_order,
            quantity=product['quantity'],
            products_price=product_in_order.price * product['quantity']
        )

    serializer = OrderSerializer(new_order)
    return Response(serializer.data)
