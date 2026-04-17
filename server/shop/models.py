from decimal import Decimal

from django.db import models

from shop.enums import OrderStatusEnum, OrderPaymentStatusEnum, OrderDeliveryStatusEnum, PaymentMethodEnum
from shop.validators import validate_image_extension


# Create your models here.

class Catalog(models.Model):
    title = models.CharField(max_length=255, verbose_name='Назва')
    photo = models.FileField(upload_to='catalog_photos/', verbose_name='Фото (На списку каталогів)', blank=True, null=True, validators=[validate_image_extension])
    photo_banner = models.FileField(upload_to='catalog_photos/', verbose_name='Фото (Всередині каталогу)', blank=True, null=True, validators=[validate_image_extension])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True, verbose_name='Активний')
    priority = models.PositiveIntegerField(default=1, verbose_name='Пріоритет')

    class Meta:
        verbose_name = 'Каталог'
        verbose_name_plural = 'Каталоги'

    def save(self, *args, **kwargs):
        if not self.pk:
            last_catalog= Catalog.objects.order_by('-priority').first()
            self.priority = (last_catalog.priority + 1) if last_catalog else 1
        super(Catalog, self).save(*args, **kwargs)

    def __str__(self):
        return self.title


class Product(models.Model):
    title = models.CharField(max_length=255, verbose_name='Назва')
    article = models.CharField(max_length=255, blank=True, verbose_name='Артикул')
    description = models.TextField(verbose_name='Опис')
    promotional_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Ціна зі знижкою')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Ціна')
    photo = models.FileField(
        upload_to='product_photos/',
        verbose_name='Фото',
        validators=[validate_image_extension],
        blank=True,
        null=True,
    )
    catalog = models.ForeignKey(Catalog, related_name='products', on_delete=models.CASCADE, verbose_name='Каталог')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    property_title = models.CharField(max_length=255, blank=True, null=True, verbose_name='Назва типу товару')
    active = models.BooleanField(default=True, verbose_name='Активний')
    priority = models.PositiveIntegerField(default=1, verbose_name='Пріоритет')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товари'

    def save(self, *args, **kwargs):
        if not self.pk:
            last_product= Product.objects.filter(catalog=self.catalog).order_by('-priority').first()
            self.priority = (last_product.priority + 1) if last_product else 1
        super(Product, self).save(*args, **kwargs)

    def __str__(self):
        return self.title


class ProductView(models.Model):
    product = models.ForeignKey(Product, related_name='product_views', on_delete=models.CASCADE)
    user_id = models.BigIntegerField()
    viewed_at = models.DateTimeField(blank=True, null=True)


class ProductProperty(models.Model):
    title = models.CharField(max_length=255, verbose_name='Назва')
    photo = models.FileField(upload_to='product_property_photos/', blank=True, null=True, verbose_name='Фото', validators=[validate_image_extension])
    product = models.ForeignKey(Product, related_name='product_properties', on_delete=models.CASCADE, verbose_name='Продукт')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True, verbose_name='Активний')

    class Meta:
        verbose_name = 'Тип товару'
        verbose_name_plural = 'Типи товарів'

    def __str__(self):
        return self.title


class Order(models.Model):
    status = models.CharField(
        max_length=20,
        choices=[(status.value, status.name) for status in OrderStatusEnum],
        default=OrderStatusEnum.PENDING.value, verbose_name='Статус'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=[(status.value, status.name) for status in OrderPaymentStatusEnum],
        default=OrderPaymentStatusEnum.PENDING.value, verbose_name='Статус оплати'
    )
    delivery_status = models.CharField(
        max_length=20,
        choices=[(status.value, status.name) for status in OrderDeliveryStatusEnum],
        default=OrderDeliveryStatusEnum.PENDING.value, verbose_name='Статус доставки'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Загальна сума')
    promotion_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name='Знижка')
    promocode_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name='Знижка по промокоду')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата створення')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата оновлення')
    invoice_url = models.CharField(max_length=1024, blank=True, null=True)
    user_id = models.BigIntegerField()
    full_name = models.CharField(max_length=1024, verbose_name='Замовник')
    city = models.CharField(max_length=1024, verbose_name='Місто доставки')
    warehouse = models.CharField(max_length=1024, verbose_name='Відділення')
    phone_number = models.CharField(max_length=1024, verbose_name='Номер телефону')
    payment_method = models.CharField(
        max_length=20,
        choices=[(status.value, status.name) for status in PaymentMethodEnum], verbose_name='Оплата'
    )

    class Meta:
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'

    def __str__(self):
        return 'Замовлення №{self.id}'.format(self=self)


class OrderItem(models.Model):
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE, verbose_name='Товар')
    product_property = models.ForeignKey(ProductProperty, related_name='order_items', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Тип товару')
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, verbose_name='Кількість')

    class Meta:
        verbose_name = 'Товар в замовленні'
        verbose_name_plural = 'Товари'

    def __str__(self):
        return ''


class BasketItem(models.Model):
    product = models.ForeignKey(Product, related_name='basket_items', on_delete=models.CASCADE)
    product_property = models.ForeignKey(ProductProperty, related_name='basket_items', on_delete=models.CASCADE, blank=True, null=True)
    quantity = models.IntegerField(default=1)
    user_id = models.BigIntegerField()


class Promocode(models.Model):
    discount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Знижка %')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сума замовлення')
    active = models.BooleanField(default=True, verbose_name='Активний')
    value = models.CharField(max_length=1024, verbose_name='Промокод')

    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоди'

    def __str__(self):
        return self.value


class Banner(models.Model):
   photo = models.FileField(upload_to='banner_photos/', verbose_name='Баннер', validators=[validate_image_extension], null=True, blank=True)

   class Meta:
       verbose_name = 'Баннер'
       verbose_name_plural = 'Баннер'

   def __str__(self):
       return 'Баннер'
