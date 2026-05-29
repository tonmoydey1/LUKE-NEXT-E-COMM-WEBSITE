import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=15, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    premium_badge = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class OTPVerification(models.Model):
    PURPOSE_SIGNUP = "signup"
    PURPOSE_PASSWORD_RESET = "password_reset"
    PURPOSE_CHOICES = [(PURPOSE_SIGNUP, "Signup"), (PURPOSE_PASSWORD_RESET, "Password reset")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def issue(cls, user, purpose):
        return cls.objects.create(
            user=user,
            purpose=purpose,
            code=f"{secrets.randbelow(900000) + 100000}",
            expires_at=timezone.now() + timedelta(minutes=10),
        )

    @property
    def is_valid(self):
        return not self.is_used and self.expires_at >= timezone.now()


class Address(models.Model):
    HOME = "home"
    WORK = "work"
    OTHER = "other"
    ADDRESS_TYPES = [(HOME, "Home"), (WORK, "Work"), (OTHER, "Other")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    pincode = models.CharField(max_length=6)
    address_type = models.CharField(max_length=15, choices=ADDRESS_TYPES, default=HOME)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.full_name}, {self.city} - {self.pincode}"


class PremiumMembership(models.Model):
    PLAN_MONTHLY = "monthly"
    PLAN_YEARLY = "yearly"
    PLAN_CHOICES = [(PLAN_MONTHLY, "Monthly"), (PLAN_YEARLY, "Yearly")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def currently_active(self):
        return self.is_active and self.expires_at >= timezone.now()


class PremiumPayment(models.Model):
    INITIATED = "initiated"
    SUCCESS = "success"
    FAILED = "failed"
    STATUS_CHOICES = [(INITIATED, "Initiated"), (SUCCESS, "Success"), (FAILED, "Failed")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="premium_payments")
    plan = models.CharField(max_length=20, choices=PremiumMembership.PLAN_CHOICES)
    method = models.CharField(max_length=20, default="upi")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=80, unique=True, default=uuid.uuid4)
    provider_order_id = models.CharField(max_length=100, blank=True)
    provider_payment_id = models.CharField(max_length=100, blank=True)
    signature = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=INITIATED)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.plan} - {self.status}"
