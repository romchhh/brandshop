from django.urls import path
from .views import CatalogList, CatalogDetail, UserViewedProductsView, ProductDetail, PromotionalProductList, \
    UserBasketItemsView, BasketItemUpdateView, UserOrdersView, WayForPayHookView, PromocodeDetail, UserMetaDataView, \
    BotStatisticsView, BotSyncProductsView

urlpatterns = [
    path('catalogs/', CatalogList.as_view(), name='catalog-list'),  # Index endpoint
    path('catalogs/<int:pk>/', CatalogDetail.as_view(), name='catalog-detail'),  # Show endpoint
    path('user/<int:user_id>/viewed-products/', UserViewedProductsView.as_view(), name='user_viewed_products'),
    path('user/<int:user_id>/basket-items/', UserBasketItemsView.as_view(), name='user_basket_items'),
    path('promotional-products/', PromotionalProductList.as_view(), name='promotional-product-list'),
    path('products/<int:pk>/', ProductDetail.as_view(), name='product-detail'),
    path('user/<int:user_id>/basket-items/<int:basket_id>/', BasketItemUpdateView.as_view(),name='basket-item'),
    path('user/<int:user_id>/orders/', UserOrdersView.as_view(), name='user-orders'),
    path('wayforpay_hook', WayForPayHookView.as_view(), name='wayforpay_hook'),
    path('promocode', PromocodeDetail.as_view(), name='promocode'),
    path('user-metadata/', UserMetaDataView.as_view(), name='user-metadata'),
    path('bot/statistics/', BotStatisticsView.as_view(), name='bot-statistics'),
    path('bot/sync-products/', BotSyncProductsView.as_view(), name='bot-sync-products'),
]