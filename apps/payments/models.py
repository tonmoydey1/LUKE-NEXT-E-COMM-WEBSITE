import uuid

from django.conf import settings
from django.db import models

from apps.orders.models import Order


class Payment(models.Model):
    INITIATED = "initiated"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"
    STATUS_CHOICES = [(INITIATED, "Initiated"), (SUCCESS, "Success"), (FAILED, "Failed"), (REFUNDED, "Refunded")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments")
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    provider = models.CharField(max_length=40, default="razorpay")
    transaction_id = models.CharField(max_length=80, unique=True, default=uuid.uuid4)
    provider_order_id = models.CharField(max_length=100, blank=True)
    provider_payment_id = models.CharField(max_length=100, blank=True)
    signature = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=INITIATED)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order.order_id} - {self.status}"
