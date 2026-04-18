# serializers.py

from django.conf import settings

from rest_framework import serializers
from .models import Catalog, Product, ProductProperty, BasketItem, Order, OrderItem, Promocode


def _absolute_media_url(file_field) -> str | None:
    if not file_field:
        return None
    path = file_field.url
    if not path:
        return None
    base = getattr(settings, 'PUBLIC_BASE_URL', '') or ''
    if base:
        return f"{base}{path}" if path.startswith('/') else f"{base}/{path}"
    return path


class ProductPropertySerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()

    class Meta:
        model = ProductProperty
        fields = ['id', 'title', 'photo']

    def get_photo(self, obj):
        return _absolute_media_url(obj.photo)


class ProductSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()
    catalog_title = serializers.SerializerMethodField()  # Add catalog_title field
    product_properties = serializers.SerializerMethodField()  # Use a method field

    class Meta:
        model = Product
        fields = ['id', 'title', 'description', 'photo', 'price', 'promotional_price', 'catalog_title', 'catalog_id',
                  'product_properties', 'property_title']

    def get_catalog_title(self, obj):
        return obj.catalog.title

    def get_photo(self, obj):
        return _absolute_media_url(obj.photo)

    def get_product_properties(self, obj):
        active_properties = obj.product_properties.filter(active=True)
        return ProductPropertySerializer(active_properties, many=True).data


class CatalogSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()
    photo_banner = serializers.SerializerMethodField()
    #products = ProductSerializer(many=True, read_only=True)  # Nested serializer to display products in catalog
    products = serializers.SerializerMethodField()

    class Meta:
        model = Catalog
        fields = ['id', 'title', 'photo', 'products', 'photo_banner']

    def get_photo(self, obj):
        return _absolute_media_url(obj.photo)

    def get_photo_banner(self, obj):
        return _absolute_media_url(obj.photo_banner)

    def get_products(self, obj):
        # Спочатку щойно оновлені/нові (sync), далі за priority — порядок каталогів не змінюється (CatalogList.order_by('priority')).
        active_products = obj.products.filter(active=True).order_by("-updated_at", "-priority", "-id")
        return ProductSerializer(active_products, many=True).data


class BasketItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(many=False, read_only=True)
    product_property = ProductPropertySerializer(many=False, read_only=True)

    class Meta:
        model = BasketItem
        fields = ['id', 'product', 'user_id', 'quantity', 'product_property']

    def validate_quantity(self, value):
        if not isinstance(value, int):
            raise serializers.ValidationError("Quantity must be an integer.")
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(many=False, read_only=True)
    product_property = ProductPropertySerializer(many=False, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_property']


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'status', 'payment_status', 'delivery_status', 'total_amount', 'promotion_amount',
                  'promocode_amount', 'order_items', 'invoice_url']


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['full_name', 'city', 'warehouse', 'phone_number', 'payment_method']


class PromocodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promocode
        fields = ['id', 'discount']
