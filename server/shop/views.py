# views.py
import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal
import time

from django.utils import timezone

from rest_framework import generics

from shop.catalog_import import run_product_sync

from .enums import OrderPaymentStatusEnum, PaymentMethodEnum
from .models import Catalog, Product, ProductView, BasketItem, ProductProperty, Order, OrderItem, Promocode, Banner
from .serializers import (
    CatalogSerializer,
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
from django.db.models import Sum

from .telegram import TelegramAdmin
from .wayforpayadmin import secret_key, WayForPayAdmin


class UserViewedProductsView(generics.ListCreateAPIView):
    model = Product
    serializer_class = ProductSerializer

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return Product.objects.filter(
            product_views__user_id=user_id,
            active=True,
        ).order_by(
            '-product_views__viewed_at'
        ).distinct()


class UserBasketItemsView(generics.ListCreateAPIView):
    model = BasketItem
    serializer_class = BasketItemSerializer

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return BasketItem.objects.filter(user_id=user_id)


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
    queryset = Product.objects.filter(
        active=True,
        promotional_price__isnull=False,  # Ensures promotional price is not null
        promotional_price__gt=0                       # Ensures price is greater than zero
    ).order_by("-priority", "-id")
    serializer_class = ProductSerializer


class ProductDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.filter(active=True)
    serializer_class = ProductSerializer

    def get(self, request, *args, **kwargs):
        # Retrieve the product instance
        product = self.get_object()

        # Retrieve user_id from query parameters
        user_id = request.query_params.get('userId')
        print(f"Product get: {product.id}, User ID: {user_id}")

        if user_id:
            product_view, created = ProductView.objects.get_or_create(
                product=product,
                user_id=user_id,
                defaults={'viewed_at': timezone.now()}
            )
            if not created:
                product_view.viewed_at = timezone.now()
                product_view.save(update_fields=['viewed_at'])


        # Use the default GET behavior to return the response
        return super().get(request, *args, **kwargs)

class CatalogList(generics.ListAPIView):
    queryset = Catalog.objects.filter(active=True).order_by("-priority", "-id")
    serializer_class = CatalogSerializer



# This view handles the 'show' action, retrieving a single catalog item by its ID
class CatalogDetail(generics.RetrieveAPIView):
    queryset = Catalog.objects.filter(active=True)
    serializer_class = CatalogSerializer


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
            if item.product.promotional_price is not None and item.product.promotional_price > 0:
                promotion_amount += (item.quantity * (item.product.price - item.product.promotional_price))
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
            TelegramAdmin.create_order_message(order.id, user_id, total_amount, promotion_amount, promocode_amount, order.payment_method)
        except:
            pass

        try:
            TelegramAdmin.create_order_client_message(order.id, user_id, total_amount, promotion_amount, promocode_amount, order.payment_method)
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
