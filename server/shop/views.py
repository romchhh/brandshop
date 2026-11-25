# views.py
import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal
import time

from django.core.cache import cache
from django.utils import timezone

from rest_framework import generics
from rest_framework.pagination import PageNumberPagination

from shop.api_json_cache import api_json_cache_ttl_seconds
from shop.catalog_import import run_product_sync
from shop.promotional_rules import effective_promotional_price, promo_excluded_catalog_titles

from .enums import OrderPaymentStatusEnum, PaymentMethodEnum
from .models import Catalog, Product, ProductView, BasketItem, ProductProperty, Order, OrderItem, Promocode, Banner
from .serializers import (
    CatalogSerializer,
    CatalogSummarySerializer,
    catalog_cover_photos_by_id,
    ProductCardSerializer,
    ProductSerializer,
    BasketItemSerializer,
    OrderSerializer,
    OrderCreateSerializer,
    PromocodeSerializer,
    _absolute_media_url,
)
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from rest_framework.views import APIView
from django.db.models import Count, Q, Sum, Case, When, IntegerField

from .telegram import TelegramAdmin
from .wayforpayadmin import secret_key, WayForPayAdmin


class PublicProductPagination(PageNumberPagination):
    """Публічний список товарів — порціями по 10 (скрол)."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class UserViewedProductsView(generics.ListCreateAPIView):
    model = Product
    serializer_class = ProductCardSerializer
    pagination_class = PublicProductPagination

    def get_queryset(self):
        from django.db.models import Prefetch

        user_id = self.kwargs['user_id']
        return (
            Product.objects.filter(product_views__user_id=user_id, active=True)
            .select_related("catalog")
            .prefetch_related(
                Prefetch(
                    "product_properties",
                    queryset=ProductProperty.objects.filter(active=True).only(
                        "id", "title", "product_id", "active"
                    ),
                )
            )
            .order_by("-product_views__viewed_at")
            .distinct()
        )

    def list(self, request, *args, **kwargs):
        user_id = self.kwargs.get("user_id")
        page = str(request.query_params.get("page", "1"))
        ps = str(request.query_params.get("page_size") or PublicProductPagination.page_size)
        cache_key = f"api:v1:viewed:{user_id}:p{page}:ps{ps}"
        hit = cache.get(cache_key)
        if hit is not None:
            return Response(hit)
        response = super().list(request, *args, **kwargs)
        if response.status_code == 200:
            cache.set(cache_key, response.data, timeout=min(120, api_json_cache_ttl_seconds()))
        return response


class UserBasketItemsView(generics.ListCreateAPIView):
    model = BasketItem
    serializer_class = BasketItemSerializer

    def get_queryset(self):
        from django.db.models import Prefetch

        user_id = self.kwargs['user_id']
        return (
            BasketItem.objects.filter(user_id=user_id)
            .select_related("product__catalog", "product_property")
            .prefetch_related(
                Prefetch(
                    "product__product_properties",
                    queryset=ProductProperty.objects.filter(active=True).only(
                        "id", "title", "photo", "product_id", "active"
                    ),
                )
            )
        )


    def post(self, request, user_id):
        params = request.data.get('params')
        serializer = BasketItemSerializer(data=params, partial=True)

        # If the data is not valid, return a 400 Bad Request with errors
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        product_id = params.get('product_id')
        product_property_id = params.get('product_property_id')

        try:
            Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            if product_property_id is not None:
                ProductProperty.objects.get(id=product_property_id, product_id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product property not found"}, status=status.HTTP_404_NOT_FOUND)

        basket_item, created = BasketItem.objects.get_or_create(product_id=product_id, user_id=user_id, product_property_id=product_property_id)

        # Return the basket item data
        serializer = BasketItemSerializer(basket_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class WayForPayHookView(generics.CreateAPIView):
    def post(self, request):
        params = json.loads(list(request.data.keys())[0])
        orderReference = params.get('orderReference')
        transactionStatus = params.get('transactionStatus')

        print(transactionStatus)
        print(orderReference)

        time = int(timezone.now().timestamp())
        body_status = 'accept'
        into = "{0};{1};{2}".format(orderReference, body_status, time)
        signature = hmac.new(bytearray(secret_key, encoding='utf-8'), bytearray(into, encoding="utf-8"),
                             digestmod=hashlib.md5).hexdigest()
        body = {
            "orderReference": orderReference,
            "status": body_status,
            "time": time,
            "signature": signature
        }

        if transactionStatus == 'Approved':
            try:
                order = Order.objects.get(id=orderReference)
                order.payment_status = OrderPaymentStatusEnum.PAYED.value
                order.save()
            except Order.DoesNotExist:
                pass

        return Response(body, status=status.HTTP_201_CREATED)


class BasketItemUpdateView(generics.UpdateAPIView):
    def update(self, request, user_id, basket_id):
        try:
            # Ensure the basket item exists for the given user_id and basket_id
            basket_item = BasketItem.objects.get(id=basket_id, user_id=user_id)
        except BasketItem.DoesNotExist:
            return Response({"error": "BasketItem not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = BasketItemSerializer(data=request.data.get('params'), partial=True)

        # If the data is not valid, return a 400 Bad Request with errors
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # Extract quantity from the request data
        quantity = request.data.get('params').get('quantity')

        # Assign the new quantity and save the basket item
        basket_item.quantity = quantity
        basket_item.save()

        # Serialize and return the updated basket item
        serializer = BasketItemSerializer(basket_item)
        return Response(serializer.data, status=status.HTTP_200_OK)


    def delete(self, request, user_id, basket_id):
        try:
            # Ensure the basket item exists for the given user_id and basket_id
            basket_item = BasketItem.objects.get(id=basket_id, user_id=user_id)
        except BasketItem.DoesNotExist:
            return Response({"error": "BasketItem not found"}, status=status.HTTP_404_NOT_FOUND)

        # Delete the basket item
        basket_item.delete()

        # Return a success message
        return Response(status=status.HTTP_204_NO_CONTENT)


class PromotionalProductList(generics.ListCreateAPIView):
    serializer_class = ProductCardSerializer
    pagination_class = PublicProductPagination

    def get_queryset(self):
        from django.db.models import Prefetch

        return (
            Product.objects.filter(
                active=True,
                promotional_price__isnull=False,
                promotional_price__gt=0,
            )
            .exclude(catalog__title__in=promo_excluded_catalog_titles())
            .select_related("catalog")
            .prefetch_related(
                Prefetch(
                    "product_properties",
                    queryset=ProductProperty.objects.filter(active=True).only(
                        "id", "title", "product_id", "active"
                    ),
                )
            )
            .order_by("-updated_at", "-priority", "-id")
        )

    def list(self, request, *args, **kwargs):
        page = str(request.query_params.get("page", "1"))
        ps = str(
            request.query_params.get("page_size")
            or getattr(self.pagination_class, "page_size", 20)
        )
        cache_key = f"api:v1:promotional:page:{page}:ps:{ps}"
        hit = cache.get(cache_key)
        if hit is not None:
            return Response(hit)
        response = super().list(request, *args, **kwargs)
        if response.status_code == 200:
            cache.set(cache_key, response.data, timeout=api_json_cache_ttl_seconds())
        return response


class ProductDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        from django.db.models import Prefetch

        return (
            Product.objects.filter(active=True)
            .select_related("catalog")
            .prefetch_related(
                Prefetch(
                    "product_properties",
                    queryset=ProductProperty.objects.filter(active=True).only(
                        "id", "title", "photo", "product_id", "active"
                    ),
                )
            )
        )

    def get(self, request, *args, **kwargs):
        product = self.get_object()
        cache_key = f"api:v1:product:{product.pk}"
        hit = cache.get(cache_key)

        user_id = request.query_params.get("userId")
        if user_id:
            product_view, created = ProductView.objects.get_or_create(
                product=product,
                user_id=user_id,
                defaults={"viewed_at": timezone.now()},
            )
            if not created:
                product_view.viewed_at = timezone.now()
                product_view.save(update_fields=["viewed_at"])

        if hit is not None:
            return Response(hit)

        data = self.get_serializer(product).data
        cache.set(cache_key, data, timeout=api_json_cache_ttl_seconds())
        return Response(data)


def _home_product_qs():
    from django.db.models import Prefetch

    return (
        Product.objects.filter(active=True)
        .select_related("catalog")
        .prefetch_related(
            Prefetch(
                "product_properties",
                queryset=ProductProperty.objects.filter(active=True).only("id", "title", "product_id", "active"),
            )
        )
    )


class HomeFeedView(APIView):
    """Легкий payload головної: категорії без товарів + кілька карток."""

    def get(self, request):
        cache_key = "api:v2:home"
        hit = cache.get(cache_key)
        if hit is not None:
            return Response(hit)

        catalogs = (
            Catalog.objects.filter(active=True, products__active=True)
            .distinct()
            .annotate(products_count=Count("products", filter=Q(products__active=True)))
            .order_by("priority")
            .only("id", "title", "photo", "priority")
        )
        catalog_list = list(catalogs)
        cover_photos = catalog_cover_photos_by_id(c.id for c in catalog_list)
        cards = _home_product_qs()
        data = {
            "catalogs": [
                {
                    "id": c.id,
                    "title": c.title,
                    "photo": _absolute_media_url(c.photo) or cover_photos.get(c.id),
                    "products_count": c.products_count,
                    "products": (
                        [{"photo": cover_photos.get(c.id)}]
                        if not _absolute_media_url(c.photo) and cover_photos.get(c.id)
                        else []
                    ),
                }
                for c in catalog_list
            ],
            "new_products": ProductCardSerializer(list(cards.order_by("-created_at", "-id")[:4]), many=True).data,
            "promotional_products": ProductCardSerializer(
                list(
                    cards.filter(promotional_price__gt=0)
                    .exclude(catalog__title__in=promo_excluded_catalog_titles())
                    .order_by("-updated_at", "-id")[:4]
                ),
                many=True,
            ).data,
            "products": ProductCardSerializer(
                list(cards.order_by("-updated_at", "-priority", "-id")[:12]),
                many=True,
            ).data,
        }
        cache.set(cache_key, data, timeout=api_json_cache_ttl_seconds())
        return Response(data)


class ProductSearchView(APIView):
    """Пошук по назві без вивантаження всього каталогу на клієнт."""

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()[:80]
        if len(q) < 2:
            return Response([])
        qs = _home_product_qs().filter(title__icontains=q).order_by("-updated_at")[:24]
        return Response(ProductCardSerializer(qs, many=True).data)


class NewProductsFeedView(APIView):
    """Новинки — сторінками по 10."""

    def get(self, request):
        try:
            page = max(1, int(request.query_params.get("page", 1) or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = max(1, min(50, int(request.query_params.get("page_size", 10) or 10)))
        except (TypeError, ValueError):
            page_size = 10
        cache_key = f"api:v1:new-products:p{page_size}:page{page}"
        hit = cache.get(cache_key)
        if hit is not None:
            return Response(hit)
        qs = _home_product_qs().order_by("-created_at", "-id")
        total = qs.count()
        start = (page - 1) * page_size
        chunk = list(qs[start : start + page_size])
        body = {
            "results": ProductCardSerializer(chunk, many=True).data,
            "count": total,
            "page": page,
            "page_size": page_size,
            "next": start + page_size < total,
        }
        cache.set(cache_key, body, timeout=api_json_cache_ttl_seconds())
        return Response(body)


class ProductsByIdsView(APIView):
    """Картки обраного: порція id (типово 10 при скролі)."""

    def get(self, request):
        raw = (request.query_params.get("ids") or "").strip()
        if not raw:
            return Response({"results": [], "next": False, "count": 0})
        id_list: list[int] = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                id_list.append(int(part))
            if len(id_list) >= 200:
                break
        try:
            offset = max(0, int(request.query_params.get("offset", 0) or 0))
        except (TypeError, ValueError):
            offset = 0
        try:
            limit = max(1, min(50, int(request.query_params.get("limit", 10) or 10)))
        except (TypeError, ValueError):
            limit = 10
        if not id_list:
            return Response({"results": [], "next": False, "count": 0})
        chunk_ids = id_list[offset : offset + limit]
        cache_key = (
            f"api:v1:products:ids:{hashlib.sha256(raw.encode()).hexdigest()[:24]}:"
            f"o{offset}:l{limit}"
        )
        hit = cache.get(cache_key)
        if hit is not None:
            return Response(hit)
        order = Case(
            *[When(pk=pk, then=pos) for pos, pk in enumerate(chunk_ids)],
            output_field=IntegerField(),
        )
        qs = _home_product_qs().filter(pk__in=chunk_ids).order_by(order)
        body = {
            "results": ProductCardSerializer(qs, many=True).data,
            "count": len(id_list),
            "offset": offset,
            "limit": limit,
            "next": offset + limit < len(id_list),
        }
        cache.set(cache_key, body, timeout=api_json_cache_ttl_seconds())
        return Response(body)


class CatalogList(generics.ListAPIView):
    queryset = Catalog.objects.filter(active=True, products__active=True).distinct().order_by("priority")

    def get_queryset(self):
        qs = super().get_queryset()
        summary = self.request.query_params.get("summary", "1").lower() not in ("0", "false", "full")
        if summary:
            return qs.annotate(products_count=Count("products", filter=Q(products__active=True))).only(
                "id", "title", "photo", "photo_banner", "priority", "active"
            )
        return qs

    def list(self, request, *args, **kwargs):
        summary = request.query_params.get("summary", "1").lower() not in ("0", "false", "full")
        try:
            page = max(1, int(request.query_params.get("page", 1) or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = max(1, min(50, int(request.query_params.get("page_size", 10) or 10)))
        except (TypeError, ValueError):
            page_size = 10
        cache_key = f"api:v2:catalogs:summary={int(summary)}:p{page_size}:page{page}"
        hit = cache.get(cache_key)
        if hit is not None:
            return Response(hit)
        qs = self.filter_queryset(self.get_queryset())
        total = qs.count()
        start = (page - 1) * page_size
        chunk = list(qs[start : start + page_size])
        if summary:
            cover_ctx = {
                "cover_photos": catalog_cover_photos_by_id(c.id for c in chunk),
            }
            results = CatalogSummarySerializer(chunk, many=True, context=cover_ctx).data
        else:
            results = CatalogSerializer(chunk, many=True).data
        body = {
            "results": results,
            "count": total,
            "page": page,
            "page_size": page_size,
            "next": start + page_size < total,
        }
        cache.set(cache_key, body, timeout=api_json_cache_ttl_seconds())
        return Response(body)



# This view handles the 'show' action, retrieving a single catalog item by its ID
class CatalogDetail(generics.RetrieveAPIView):
    queryset = Catalog.objects.filter(active=True)
    serializer_class = CatalogSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        paginated = str(request.query_params.get("paginated", "")).lower() in ("1", "true", "yes", "on")
        if not paginated:
            serializer = self.get_serializer(instance)
            return Response(serializer.data)

        try:
            page = max(1, int(request.query_params.get("page", 1) or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = max(1, min(50, int(request.query_params.get("page_size", 10) or 10)))
        except (TypeError, ValueError):
            page_size = 20

        cache_key = f"api:v1:catalog:{instance.pk}:pag:{page}:ps:{page_size}"
        hit = cache.get(cache_key)
        if hit is not None:
            return Response(hit)

        qs = instance.products.filter(active=True).order_by("-updated_at", "-priority", "-id")
        total = qs.count()
        start = (page - 1) * page_size
        page_slice = list(qs[start : start + page_size])
        serializer = self.get_serializer(
            instance,
            context={
                **self.get_serializer_context(),
                "catalog_products_queryset": page_slice,
                "light_products": True,
            },
        )
        data = dict(serializer.data)
        data["products_count"] = total
        data["products_page"] = page
        data["products_page_size"] = page_size
        data["products_has_next"] = start + page_size < total
        cache.set(cache_key, data, timeout=api_json_cache_ttl_seconds())
        return Response(data)


class UserOrdersView(generics.ListCreateAPIView):
    model = Order
    serializer_class = OrderSerializer

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        status = self.request.query_params.getlist('status[]')
        return Order.objects.filter(user_id=user_id, status__in=status).order_by('-created_at')


    def post(self, request, user_id):
        params = request.data.get('params')
        serializer = OrderCreateSerializer(data=params, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        promocode_id = params.get('promocode_id')

        if promocode_id:
            try:
                promocode = Promocode.objects.get(id=promocode_id, active=True)
            except Product.DoesNotExist:
                return Response({"error": "Promocode not found"}, status=status.HTTP_404_NOT_FOUND)

        basket_items = BasketItem.objects.filter(user_id=user_id)

        total_amount = Decimal(0)
        promotion_amount = Decimal(0)
        for item in basket_items:
            total_amount += item.product.price * item.quantity
            promo = effective_promotional_price(item.product)
            if promo is not None:
                promotion_amount += item.quantity * (item.product.price - promo)
        total = total_amount - promotion_amount

        if promocode_id:
            promocode_amount = total * (promocode.discount/100)
        else:
            promocode_amount = 0

        if not basket_items.exists():
            return Response({"detail": "No items in the basket."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        with transaction.atomic():
            payment_status = OrderPaymentStatusEnum.IMPOSED_PAYMENT.value if params.get('payment_method') == PaymentMethodEnum.IMPOSED_PAYMENT.value else OrderPaymentStatusEnum.PENDING.value
            order = Order.objects.create(
                user_id=user_id,
                total_amount=total_amount,
                city=params.get('city'),
                warehouse=params.get('warehouse'),
                phone_number=params.get('phone_number'),
                payment_method=params.get('payment_method'),
                full_name=params.get('full_name'),
                promotion_amount=promotion_amount,
                promocode_amount=promocode_amount,
                payment_status=payment_status
            )

            for basket_item in basket_items:
                OrderItem.objects.create(
                    product=basket_item.product,
                    product_property=basket_item.product_property,
                    order=order,
                    quantity=basket_item.quantity
                )

            basket_items.delete()

        # if order.payment_method == PaymentMethodEnum.ONLINE.value:
        #    invoice_url = WayForPayAdmin.create_invoice(str(order.id), str(total_amount - promotion_amount - promocode_amount))
        #    if invoice_url:
        #        order.invoice_url = invoice_url
        #        order.save()

        try:
            TelegramAdmin.create_order_message(order)
        except:
            pass

        try:
            TelegramAdmin.create_order_client_message(order)
        except:
            pass

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PromocodeDetail(generics.RetrieveAPIView):
    serializer_class = PromocodeSerializer

    def get_object(self):
        promocode = self.request.query_params.get('promocode')
        userId = float(self.request.query_params.get('userId'))

        basket_items = BasketItem.objects.filter(user_id=userId)

        total_amount = Decimal(0)
        for item in basket_items:
            total_amount += item.product.price * item.quantity

        return Promocode.objects.filter(value=promocode, active=True, total_amount__lte=total_amount).first()


class UserMetaDataView(APIView):
    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('userId')

        if not user_id:
            return Response({'error': 'user_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Query to sum the quantity of all OrderItems related to the user_id
        total_order_items = BasketItem.objects.filter(user_id=user_id).aggregate(total_quantity=Sum('quantity'))[
                                'total_quantity'] or 0
        banner = Banner.objects.first()
        # Create a metadata response
        metadata = {
            'order_item_total': total_order_items,
            'banner': _absolute_media_url(banner.photo) if banner and banner.photo else None,
        }

        return Response(metadata, status=status.HTTP_200_OK)


class BotStatisticsView(APIView):
    """
    Агрегована статистика магазину для Telegram-бота.
    Закрийте /api/bot/ ззовні (firewall/nginx), якщо API доступне з інтернету.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)

        users_pv = set(ProductView.objects.values_list("user_id", flat=True).distinct())
        users_basket = set(BasketItem.objects.values_list("user_id", flat=True).distinct())
        users_orders_set = set(Order.objects.values_list("user_id", flat=True).distinct())
        unique_shop = users_pv | users_basket | users_orders_set

        users_with_orders_count = len(users_orders_set)
        only_browsing = len(users_pv - users_orders_set)

        orders_total = Order.objects.count()
        orders_today = Order.objects.filter(created_at__gte=today_start).count()
        orders_week = Order.objects.filter(created_at__gte=week_start).count()
        orders_month = Order.objects.filter(created_at__gte=month_start).count()

        active_today_ids = set(
            ProductView.objects.filter(viewed_at__gte=today_start).values_list("user_id", flat=True)
        ) | set(Order.objects.filter(created_at__gte=today_start).values_list("user_id", flat=True))

        active_week_ids = set(
            ProductView.objects.filter(viewed_at__gte=week_start).values_list("user_id", flat=True)
        ) | set(Order.objects.filter(created_at__gte=week_start).values_list("user_id", flat=True))

        return Response(
            {
                "ok": True,
                "unique_shop_users": len(unique_shop),
                "users_with_orders": users_with_orders_count,
                "users_only_browsing": only_browsing,
                "orders_total": orders_total,
                "orders_today": orders_today,
                "orders_week": orders_week,
                "orders_month": orders_month,
                "active_shop_users_today": len(active_today_ids),
                "active_shop_users_week": len(active_week_ids),
            },
            status=status.HTTP_200_OK,
        )


class BotSyncProductsView(APIView):
    """
    Повне оновлення каталогу з Google Таблиць (те саме, що manage.py update_products).
    Не відкривайте цей URL публічно без захисту на рівні мережі/nginx.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        try:
            run_product_sync(log=lambda m: None)
        except Exception as e:
            return Response(
                {"ok": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"ok": True}, status=status.HTTP_200_OK)
