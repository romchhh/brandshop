# myapp/admin.py

from django.contrib import admin

from .models import Catalog, Product, ProductProperty, Order, OrderItem, Promocode, Banner

admin.site.index_title = 'Керування товарами і замовленнями'
admin.site.site_header = 'Панель адміністрування Give Me Vape'
admin.site.site_title = 'Give Me Vape'
admin.site.site_url = None


# Define a custom admin class for the Catalog model
class CatalogAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'priority')  # Fields to display in the admin list view
    search_fields = ('title',)  # Fields to search in the admin interface
    list_filter = ('title', 'priority')  # Fields to filter by in the admin interface

    def has_delete_permission(self, request, obj=None):
        return False

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)  # Get the default fields
        if obj is None:
            fields.remove('priority')
        return fields


class ProductAdmin(admin.ModelAdmin):
    change_list_template = "admin/shop/product/change_list.html"
    list_display = (
    'title', 'article', 'price', 'promotional_price', 'catalog', 'priority')  # Fields to display in the admin list view
    search_fields = ('title', 'article', 'description')  # Fields to search in the admin interface
    list_filter = ('catalog', 'priority')

    def has_delete_permission(self, request, obj=None):
        return False

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)  # Get the default fields
        if obj is None:
            fields.remove('priority')
        return fields


class ProductPropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'product')  # Fields to display in the admin list view
    search_fields = ('title',)  # Fields to search in the admin interface
    list_filter = ('product',)

    def has_delete_permission(self, request, obj=None):
        return False


class OrderItemInline(admin.TabularInline):  # You can also use StackedInline for a different layout
    model = OrderItem

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['quantity', 'product', 'product_property']
        return []

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = (
        'id', 'user_id', 'full_name', 'city', 'warehouse', 'phone_number', 'delivery_status', 'status',
        'payment_status',
        'created_at', 'updated_at')
    list_filter = (
        'payment_method', 'status', 'payment_status', 'delivery_status', 'created_at', 'full_name', 'city', 'warehouse',
        'phone_number')
    list_editable = ('status', 'payment_status', 'delivery_status')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['total_amount', 'promotion_amount', 'promocode_amount', 'invoice_url', 'user_id', 'full_name',
                    'city', 'warehouse', 'phone_number', 'payment_method']
        return []

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


class PromocodeAdmin(admin.ModelAdmin):
    list_display = ('value', 'discount', 'total_amount', 'active')  # Fields to display in the admin list view
    search_fields = ('value',)  # Fields to search in the admin interface
    list_filter = ('value', 'discount', 'total_amount', 'active')


class BannerAdmin(admin.ModelAdmin):
    model = Banner

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


# Register the Catalog model with the custom admin class
admin.site.register(Catalog, CatalogAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductProperty, ProductPropertyAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Promocode, PromocodeAdmin)
admin.site.register(Banner, BannerAdmin)
