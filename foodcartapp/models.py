from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum, F
from django.core.validators import MinValueValidator


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
        verbose_name="ресторан",
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
    def order_price(self):
        order_price = self.annotate(
            total_order_price=Sum(
                F('products_in_order__products_price'),
            ),
        )
        return order_price


class Order(models.Model):
    order_statuses = [
        ('new_order', 'в работе'),
        ('completed_order', 'завершен'),
    ]

    firstname = models.CharField(
        'имя клиента',
        max_length=200,
    )

    lastname = models.CharField(
        'фамилия клиента',
        max_length=200,
        blank=True,
        null=True,
    )

    phonenumber = PhoneNumberField(
        'номер клиента',
    )

    address = models.CharField(
        'адрес доставки',
        max_length=200,
    )

    order_time = models.DateTimeField(
        'время создания заказа',
        auto_now_add=True,
    )

    status = models.CharField(
        'статус заказа',
        max_length=200,
        choices=order_statuses,
        default='new_order'
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
        related_name='orders_with_product',
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
