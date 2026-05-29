from django.contrib import admin

from .models import Cart, CartItem, Order, OrderItem, ShippingStatus
from .services import update_order_status


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["user", "updated_at"]
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "product_name", "variant_label", "quantity", "unit_price", "gst_rate"]


class ShippingStatusInline(admin.TabularInline):
    model = ShippingStatus
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_id", "user", "total", "payment_method", "status", "estimated_delivery", "created_at"]
    list_filter = ["status", "payment_method", "created_at"]
    search_fields = ["order_id", "user__username", "user__email"]
    inlines = [OrderItemInline, ShippingStatusInline]
    readonly_fields = ["order_id", "subtotal", "tax", "shipping", "discount", "total"]

    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            old_status = Order.objects.get(pk=obj.pk).status
        super().save_model(request, obj, form, change)
        if old_status and old_status != obj.status:
            update_order_status(obj, obj.status, note="Status updated by LuxeNest operations team.")
