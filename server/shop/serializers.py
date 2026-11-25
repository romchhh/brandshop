# serializers.py

from collections.abc import Iterable

from django.conf import settings
from django.db.models import Q

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


def catalog_cover_photos_by_id(catalog_ids: Iterable[int]) -> dict[int, str | None]:
    """Перше фото активного товару в категорії (як у списку `/catalog/:id`)."""
    ids = list(dict.fromkeys(int(x) for x in catalog_ids))
    if not ids:
        return {}
    rows = (
        Product.objects.filter(catalog_id__in=ids, active=True)
        .exclude(Q(photo="") | Q(photo__isnull=True))
        .order_by("catalog_id", "-updated_at", "-priority", "-id")
        .distinct("catalog_id")
        .only("catalog_id", "photo")
    )
    return {p.catalog_id: _absolute_media_url(p.photo) for p in rows}


class ProductPropertySerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()

    class Meta:
        model = ProductProperty
        fields = ['id', 'title', 'photo']

    def get_photo(self, obj):
        return _absolute_media_url(obj.photo)


class ProductCardSerializer(serializers.ModelSerializer):
    """Коротка картка для головної: без опису і без фото кожного розміру."""

    photo = serializers.SerializerMethodField()
    catalog_title = serializers.SerializerMethodField()
    product_properties = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "title", "photo", "price", "promotional_price", "catalog_title", "product_properties"]

    def get_catalog_title(self, obj):
        catalog = getattr(obj, "catalog", None)
        return catalog.title if catalog is not None else ""

    def get_photo(self, obj):
        return _absolute_media_url(obj.photo)

    def get_product_properties(self, obj):
        cached = getattr(obj, "_prefetched_objects_cache", {}).get("product_properties")
        props = cached if cached is not None else obj.product_properties.filter(active=True)
        return [{"id": p.id, "title": p.title} for p in props if getattr(p, "active", True)]


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
        cached = getattr(obj, "_prefetched_objects_cache", {}).get("product_properties")
        if cached is not None:
            active_properties = [p for p in cached if getattr(p, "active", True)]
        else:
            active_properties = obj.product_properties.filter(active=True)
        return ProductPropertySerializer(active_properties, many=True).data


class CatalogSummarySerializer(serializers.ModelSerializer):
    """Список категорій без товарів — для меню «Каталог» / Redux."""

    photo = serializers.SerializerMethodField()
    photo_banner = serializers.SerializerMethodField()
    products_count = serializers.IntegerField(read_only=True, default=0)
    products = serializers.SerializerMethodField()

    class Meta:
        model = Catalog
        fields = ["id", "title", "photo", "photo_banner", "products_count", "products"]

    def get_photo(self, obj):
        own = _absolute_media_url(obj.photo)
        if own:
            return own
        covers = self.context.get("cover_photos") or {}
        return covers.get(obj.id)

    def get_photo_banner(self, obj):
        return _absolute_media_url(obj.photo_banner)

    def get_products(self, obj):
        covers = self.context.get("cover_photos") or {}
        url = _absolute_media_url(obj.photo) or covers.get(obj.id)
        return [{"photo": url}] if url else []


class CatalogSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()
    photo_banner = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()

    class Meta:
        model = Catalog
        fields = ['id', 'title', 'photo', 'products', 'photo_banner']

    def get_photo(self, obj):
        return _absolute_media_url(obj.photo)

    def get_photo_banner(self, obj):
        return _absolute_media_url(obj.photo_banner)

    def get_products(self, obj):
        override = self.context.get("catalog_products_queryset")
        card_mode = self.context.get("light_products", False)
        ser = ProductCardSerializer if card_mode else ProductSerializer
        if override is not None:
            return ser(override, many=True).data
        active_products = obj.products.filter(active=True).order_by("-updated_at", "-priority", "-id")
        return ser(active_products, many=True).data


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
