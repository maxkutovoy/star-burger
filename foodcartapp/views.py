import json
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.http import JsonResponse
from django.templatetags.static import static


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
    try:
        new_order_data = request.data
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

    except ValueError:
        return JsonResponse({
            'error': 'Error',
        })
    return Response(new_order_data)

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
