from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["transaction_id", "order", "provider", "amount", "status", "created_at"]
    list_filter = ["provider", "status"]
    search_fields = ["transaction_id", "provider_order_id", "provider_payment_id", "order__order_id"]
