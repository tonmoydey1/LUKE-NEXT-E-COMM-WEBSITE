import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.models import Address
from apps.catalog.models import Coupon, Product, ProductVariant


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.select_related("product", "variant"))

    @property
    def discount(self):
        if not self.coupon or not self.coupon.is_active or self.subtotal < self.coupon.minimum_order_value:
            return Decimal("0.00")
        raw = self.subtotal * Decimal(self.coupon.discount_percent) / Decimal("100")
        return min(raw, self.coupon.max_discount)

    @property
    def tax(self):
        return self.subtotal * Decimal("0.18")

    @property
    def shipping(self):
        return Decimal("0.00") if self.subtotal >= 1499 else Decimal("79.00")

    @property
    def total(self):
        return self.subtotal + self.tax + self.shipping - self.discount


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    saved_for_later = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["cart", "product", "variant"]

    @property
    def unit_price(self):
        return self.product.price + (self.variant.price_delta if self.variant else 0)

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class Order(models.Model):
    PLACED = "placed"
    CONFIRMED = "confirmed"
    PACKED = "packed"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    STATUS_CHOICES = [
        (PLACED, "Order Placed"),
        (CONFIRMED, "Confirmed"),
        (PACKED, "Packed"),
        (SHIPPED, "Shipped"),
        (OUT_FOR_DELIVERY, "Out for Delivery"),
        (DELIVERED, "Delivered"),
        (CANCELLED, "Cancelled"),
        (RETURNED, "Returned"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    order_id = models.CharField(max_length=24, unique=True, editable=False)
    address = models.ForeignKey(Address, on_delete=models.PROTECT)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax = models.DecimalField(max_digits=12, decimal_places=2)
    shipping = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=40, default="razorpay")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=PLACED)
    estimated_delivery = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"LXN{timezone.now():%y%m%d}{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_id


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    product_name = models.CharField(max_length=180)
    variant_label = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18)

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class ShippingStatus(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tracking_events")
    status = models.CharField(max_length=30, choices=Order.STATUS_CHOICES)
    location = models.CharField(max_length=120, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
