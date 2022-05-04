from operator import itemgetter

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum, F
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MinValueValidator
from django.utils import timezone
from geopy import distance
from phonenumber_field.modelfields import PhoneNumberField

from .coordinates_utils import fetch_coordinates
from places.models import Place
from django.conf import settings


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
                .filter(availability=True)
                .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name='ресторан',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class OrderQuerySet(models.QuerySet):
    def calculate_order_price(self):
        order_price = self.annotate(
            total_order_price=Sum(
                F('products_in_order__products_price'),
            ),
        )
        return order_price

    def get_available_restaurants_with_distance(self):
        orders = self.prefetch_related('products_in_order')
        for order in orders:
            products_in_order = order.products_in_order.all()
            available_restaurants = []
            restaurants_with_distance = []

            for product_in_order in products_in_order:
                restaurants = []
                restaurant_menu_items = RestaurantMenuItem.objects. \
                    select_related('restaurant', 'product'). \
                    filter(product=product_in_order.product)

                for restaurant in restaurant_menu_items:
                    restaurants.append(restaurant.restaurant)

                if not available_restaurants:
                    available_restaurants = set(restaurants)
                else:
                    available_restaurants = available_restaurants.intersection(
                        set(restaurants)
                    )
                    if not available_restaurants:
                        return None

            for restaurant in available_restaurants:
                try:
                    restaurant_coordinates = Place.objects.get(
                        address=restaurant.address
                    )
                except Place.DoesNotExist:
                    rest_lon, rest_lat = fetch_coordinates(
                        apikey=settings.YANDEX_API_KEY,
                        address=restaurant.address,
                    )
                    restaurant_coordinates = Place.objects.create(
                        address=restaurant.address,
                        lat=rest_lat,
                        lon=rest_lon
                    )

                try:
                    client_coordinates = Place.objects.get(address=order.address)
                except Place.DoesNotExist:
                    client_lon, client_lat = fetch_coordinates(
                        apikey=settings.YANDEX_API_KEY,
                        address=order.address,
                    )

                    client_coordinates = Place.objects.create(
                        address=order.address,
                        lat=client_lat,
                        lon=client_lon,
                    )

                delivery_distance = round(distance.distance(
                    (restaurant_coordinates.lat, restaurant_coordinates.lon),
                    (client_coordinates.lat, client_coordinates.lon),
                ).km, 2)

                restaurants_with_distance.append(
                    (restaurant.name, delivery_distance)
                )
            order.restaurants = sorted(restaurants_with_distance,
                                       key=itemgetter(1))

        return orders


class Order(models.Model):
    order_statuses = [
        ('new_order', 'в работе'),
        ('completed_order', 'завершен'),
    ]

    payment_forms = [
        ('cash', 'наличными курьеру'),
        ('card', 'картой курьеру'),
        ('site', 'сразу на сайте'),
    ]

    firstname = models.CharField(
        'имя клиента',
        max_length=200,
    )

    lastname = models.CharField(
        'фамилия клиента',
        max_length=200,
        default='',
    )

    phonenumber = PhoneNumberField(
        'номер клиента',
        db_index=True,
    )

    address = models.CharField(
        'адрес доставки',
        max_length=200,
    )

    restaurant = models.ForeignKey(
        Restaurant,
        verbose_name='ресторан доставки',
        related_name='orders',
        on_delete=models.DO_NOTHING,
    )

    status = models.CharField(
        'статус заказа',
        max_length=50,
        choices=order_statuses,
        default='new_order',
        db_index=True,
    )

    payment_form = models.CharField(
        'форма оплаты',
        max_length=50,
        choices=payment_forms,
        null=True,
        db_index=True,
    )

    comment = models.TextField(
        'комментарий к заказу',
        default='',
    )

    order_time = models.DateTimeField(
        'время создания заказа',
        default=timezone.now,
        db_index=True,
    )

    call_time = models.DateTimeField(
        'время звонка',
        null=True,
        blank=True,
        db_index=True,
    )

    delivery_time = models.DateTimeField(
        'время доставки',
        null=True,
        blank=True,
        db_index=True,
    )

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return f"Заказ: {self.pk} от {self.order_time}"


class ProductInOrder(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='products_in_order',
        verbose_name='заказ'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.DO_NOTHING,
        related_name='products_in_order',
        verbose_name='продукт в заказе'
    )

    quantity = models.PositiveSmallIntegerField(
        'количество',
        validators=[MinValueValidator(1)],
    )

    products_price = models.DecimalField(
        decimal_places=2,
        max_digits=5,
        verbose_name='общая стоимость блюд',
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = 'продукт в заказе'
        verbose_name_plural = 'продукты в заказе'

    def __str__(self):
        return self.product.name
