from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Banner, Catalog, Order, OrderItem, Product, ProductProperty, Promocode

admin.site.site_header = "BrandShop777 — адмінка"
admin.site.site_title = "BrandShop777"
admin.site.index_title = "Магазин: товари, замовлення, акції"
admin.site.site_url = None


def _thumb(file_field, size: int = 48):
    if not file_field:
        return "—"
    try:
        url = file_field.url
    except ValueError:
        return "—"
    return format_html(
        '<img src="{}" alt="" style="width:{}px;height:{}px;object-fit:cover;'
        'border-radius:6px;background:#f0f0f0;" />',
        url,
        size,
        size,
    )


class ProductPropertyInline(admin.TabularInline):
    model = ProductProperty
    extra = 0
    fields = ("title", "active", "photo")
    show_change_link = True


@admin.register(Catalog)
class CatalogAdmin(admin.ModelAdmin):
    list_display = ("thumb", "title", "active", "priority", "id")
    list_display_links = ("thumb", "title")
    list_editable = ("active", "priority")
    list_filter = ("active",)
    search_fields = ("title",)
    ordering = ("priority", "title")
    list_per_page = 40
    fieldsets = (
        (None, {"fields": ("title", "active", "priority")}),
        ("Фото", {"fields": ("photo", "photo_banner")}),
    )

    @admin.display(description="Фото")
    def thumb(self, obj):
        return _thumb(obj.photo or obj.photo_banner)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return (
                (None, {"fields": ("title", "active")}),
                ("Фото", {"fields": ("photo", "photo_banner")}),
            )
        return self.fieldsets


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    change_list_template = "admin/shop/product/change_list.html"

    def changelist_view(self, request, extra_context=None):
        from django.utils import timezone
        from django.utils.formats import date_format

        from shop.models import CatalogSyncState
        from shop.sync_schedule import get_sync_state, next_sync_at, schedule_label

        extra_context = extra_context or {}
        state = get_sync_state()
        labels = {
            CatalogSyncState.STATUS_OK: "успішно",
            CatalogSyncState.STATUS_ERROR: "з помилками",
            CatalogSyncState.STATUS_RUNNING: "зараз виконується",
            CatalogSyncState.STATUS_IDLE: "ще не запускалось",
        }

        def _fmt(dt):
            if not dt:
                return ""
            local = timezone.localtime(dt)
            return date_format(local, "d.m.Y H:i")

        extra_context["catalog_sync"] = {
            "schedule": schedule_label(),
            "finished": _fmt(state.finished_at),
            "next": _fmt(next_sync_at()),
            "status_label": labels.get(state.status, state.status),
            "rows": state.rows_ok or "",
            "message": (state.message or "")[:240],
            "running": state.status == CatalogSyncState.STATUS_RUNNING,
        }
        return super().changelist_view(request, extra_context=extra_context)
    list_display = (
        "thumb",
        "title",
        "article",
        "catalog",
        "price",
        "promotional_price",
        "active",
        "priority",
    )
    list_display_links = ("thumb", "title")
    list_editable = ("active", "priority", "promotional_price")
    list_filter = ("active", "catalog")
    search_fields = ("title", "article")
    autocomplete_fields = ("catalog",)
    list_select_related = ("catalog",)
    list_per_page = 40
    ordering = ("-updated_at",)
    inlines = [ProductPropertyInline]
    readonly_fields = ("photo_import_source", "created_at", "updated_at", "photo_preview")
    fieldsets = (
        (
            "Основне",
            {
                "fields": (
                    "title",
                    "article",
                    "catalog",
                    "active",
                    "priority",
                    "description",
                )
            },
        ),
        ("Ціни", {"fields": ("price", "promotional_price")}),
        ("Фото", {"fields": ("photo_preview", "photo", "photo_import_source")}),
        ("Службове", {"classes": ("collapse",), "fields": ("property_title", "created_at", "updated_at")}),
    )

    @admin.display(description="Фото")
    def thumb(self, obj):
        return _thumb(obj.photo)

    @admin.display(description="Перегляд")
    def photo_preview(self, obj):
        return _thumb(obj.photo, size=160)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return (
                (
                    "Основне",
                    {"fields": ("title", "article", "catalog", "active", "description")},
                ),
                ("Ціни", {"fields": ("price", "promotional_price")}),
                ("Фото", {"fields": ("photo",)}),
            )
        return self.fieldsets


@admin.register(ProductProperty)
class ProductPropertyAdmin(admin.ModelAdmin):
    list_display = ("title", "product", "active", "thumb")
    list_filter = ("active",)
    search_fields = ("title", "product__title", "product__article")
    autocomplete_fields = ("product",)
    list_select_related = ("product",)
    list_per_page = 50
    list_editable = ("active",)

    @admin.display(description="Фото")
    def thumb(self, obj):
        return _thumb(obj.photo)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("product", "product_property", "quantity")
    readonly_fields = ("product", "product_property", "quantity")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
    list_display = (
        "id",
        "created_at",
        "full_name",
        "phone_number",
        "total_amount",
        "status",
        "payment_status",
        "delivery_status",
        "payment_method",
    )
    list_filter = ("status", "payment_status", "delivery_status", "payment_method", "created_at")
    search_fields = ("id", "full_name", "phone_number", "city", "warehouse")
    list_editable = ("status", "payment_status", "delivery_status")
    list_per_page = 30
    ordering = ("-created_at",)
    readonly_fields = (
        "user_id",
        "full_name",
        "phone_number",
        "city",
        "warehouse",
        "payment_method",
        "total_amount",
        "promotion_amount",
        "promocode_amount",
        "invoice_url",
        "created_at",
        "updated_at",
        "money_summary",
    )
    fieldsets = (
        (
            "Статуси (редагуйте тут)",
            {"fields": ("status", "payment_status", "delivery_status")},
        ),
        (
            "Клієнт і доставка",
            {"fields": ("full_name", "phone_number", "city", "warehouse", "payment_method", "user_id")},
        ),
        ("Суми", {"fields": ("money_summary", "total_amount", "promotion_amount", "promocode_amount", "invoice_url")}),
        ("Дати", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Підсумок")
    def money_summary(self, obj):
        return mark_safe(
            f"<b>{obj.total_amount} грн</b>"
            f"<br/>знижка товару: {obj.promotion_amount}"
            f"<br/>промокод: {obj.promocode_amount}"
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Promocode)
class PromocodeAdmin(admin.ModelAdmin):
    list_display = ("value", "discount", "total_amount", "active")
    list_editable = ("active", "discount", "total_amount")
    list_filter = ("active",)
    search_fields = ("value",)
    list_per_page = 40


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("id", "thumb", "photo")
    readonly_fields = ("thumb",)

    @admin.display(description="Перегляд")
    def thumb(self, obj):
        return _thumb(getattr(obj, "photo", None), size=120)

    def has_delete_permission(self, request, obj=None):
        return False
