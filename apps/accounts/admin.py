from django.contrib import admin

from .models import Address, OTPVerification, PremiumMembership, PremiumPayment, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "phone", "is_email_verified", "premium_badge", "created_at"]
    search_fields = ["user__username", "user__email", "phone"]


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ["user", "purpose", "code", "is_used", "expires_at", "created_at"]
    list_filter = ["purpose", "is_used"]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["user", "full_name", "city", "state", "pincode", "is_default"]
    search_fields = ["user__username", "pincode", "city", "phone"]


@admin.register(PremiumMembership)
class PremiumMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "amount", "starts_at", "expires_at", "is_active"]
    list_filter = ["plan", "is_active"]


@admin.register(PremiumPayment)
class PremiumPaymentAdmin(admin.ModelAdmin):
    list_display = ["transaction_id", "user", "plan", "method", "amount", "status", "created_at"]
    list_filter = ["method", "status", "plan"]
    search_fields = ["transaction_id", "provider_order_id", "provider_payment_id", "user__email"]
