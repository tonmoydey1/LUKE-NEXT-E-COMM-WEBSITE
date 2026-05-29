from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.orders.models import Order

from apps.orders.services import is_console_email_backend, send_luxe_email
from apps.payments.services import create_razorpay_amount_order, has_real_razorpay_keys, verify_razorpay_signature

from .forms import AddressForm, LuxeLoginForm, LuxeRegisterForm, OTPForm, ProfileForm
from .invoices import premium_invoice_number, render_premium_invoice_pdf, send_premium_invoice_email
from .models import OTPVerification, PremiumMembership, PremiumPayment


PREMIUM_PLANS = {
    "monthly": {"code": "monthly", "name": "Luxe Plus Monthly", "amount": 299, "duration": 30},
    "yearly": {"code": "yearly", "name": "Luxe Black Annual", "amount": 2499, "duration": 365},
}


def register_view(request):
    form = LuxeRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = form.save()
        except IntegrityError:
            form.add_error("username", "This username or email is already registered. Please login or use different details.")
            return render(request, "accounts/register.html", {"form": form})
        otp = OTPVerification.issue(user, OTPVerification.PURPOSE_SIGNUP)
        sent = send_luxe_email("Verify your LuxeNest account", user.email, "emails/otp.html", {"user": user, "otp": otp})
        request.session["otp_user_id"] = user.id
        if sent and not is_console_email_backend():
            messages.success(request, "We sent a verification OTP to your email.")
        else:
            messages.warning(request, f"SMTP is not configured. Local demo OTP: {otp.code}")
        return redirect("accounts:verify_otp")
    return render(request, "accounts/register.html", {"form": form})


def verify_otp_view(request):
    user = get_object_or_404(User, id=request.session.get("otp_user_id"))
    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        otp = (
            OTPVerification.objects.filter(user=user, code=form.cleaned_data["code"], purpose=OTPVerification.PURPOSE_SIGNUP)
            .order_by("-created_at")
            .first()
        )
        if otp and otp.is_valid:
            otp.is_used = True
            otp.save(update_fields=["is_used"])
            user.profile.is_email_verified = True
            user.profile.save(update_fields=["is_email_verified"])
            login(request, user)
            send_luxe_email("Welcome to LuxeNest", user.email, "emails/welcome.html", {"user": user})
            messages.success(request, "Your account is verified. Welcome to LuxeNest.")
            return redirect("accounts:dashboard")
        messages.error(request, "Invalid or expired OTP.")
    return render(request, "accounts/otp.html", {"form": form, "user": user})


def login_view(request):
    data = request.POST.copy() if request.method == "POST" else None
    if data:
        identifier = data.get("username", "").strip()
        if "@" in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
            if user:
                data["username"] = user.username
    form = LuxeLoginForm(request, data=data)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "Welcome back.")
        return redirect(request.GET.get("next") or "accounts:dashboard")
    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("catalog:home")


def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        user = User.objects.filter(email__iexact=email).first()
        if user:
            otp = OTPVerification.issue(user, OTPVerification.PURPOSE_PASSWORD_RESET)
            link = request.build_absolute_uri(reverse("accounts:reset_password", args=[user.id, otp.code]))
            sent = send_luxe_email("Reset your LuxeNest password", user.email, "emails/password_reset.html", {"user": user, "link": link})
            if not sent or is_console_email_backend():
                messages.warning(request, f"SMTP is not configured. Local reset code: {otp.code}")
        messages.success(request, "If the email exists, a password reset link has been sent.")
        return redirect("accounts:login")
    return render(request, "accounts/forgot_password.html")


def reset_password_view(request, user_id, token):
    user = get_object_or_404(User, id=user_id)
    otp = OTPVerification.objects.filter(user=user, code=token, purpose=OTPVerification.PURPOSE_PASSWORD_RESET).first()
    if not otp or not otp.is_valid:
        messages.error(request, "Password reset link is invalid or expired.")
        return redirect("accounts:forgot_password")
    if request.method == "POST":
        password = request.POST.get("password")
        user.set_password(password)
        user.save(update_fields=["password"])
        otp.is_used = True
        otp.save(update_fields=["is_used"])
        messages.success(request, "Password updated. Please login.")
        return redirect("accounts:login")
    return render(request, "accounts/reset_password.html")


@login_required
def dashboard_view(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items")[:6]
    active_membership = get_active_membership(request.user)
    return render(request, "accounts/dashboard.html", {"orders": orders, "active_membership": active_membership})


@login_required
def profile_view(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user.profile)
    if request.method == "POST" and form.is_valid():
        profile = form.save()
        request.user.first_name = form.cleaned_data["first_name"]
        request.user.last_name = form.cleaned_data["last_name"]
        request.user.email = form.cleaned_data["email"]
        request.user.save(update_fields=["first_name", "last_name", "email"])
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")
    form.initial.update(first_name=request.user.first_name, last_name=request.user.last_name, email=request.user.email)
    return render(request, "accounts/profile.html", {"form": form})


@login_required
def addresses_view(request):
    form = AddressForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        if address.is_default:
            request.user.addresses.update(is_default=False)
        address.save()
        messages.success(request, "Address saved.")
        return redirect("accounts:addresses")
    return render(request, "accounts/addresses.html", {"form": form, "addresses": request.user.addresses.all()})


@login_required
def premium_view(request):
    plans = list(PREMIUM_PLANS.values())
    if request.method == "POST":
        plan = PREMIUM_PLANS.get(request.POST.get("plan"))
        if not plan:
            messages.error(request, "Choose a valid Premium plan.")
            return redirect("accounts:premium")
        payment_method = request.POST.get("payment_method")
        if payment_method not in {"card", "upi"}:
            messages.error(request, "Choose Card or UPI to activate Premium.")
            return redirect("accounts:premium")
        premium_payment = PremiumPayment.objects.create(
            user=request.user,
            plan=plan["code"],
            method=payment_method,
            amount=plan["amount"],
        )
        return redirect("accounts:premium_payment", premium_payment.id)
    return render(request, "accounts/premium.html", {"plans": plans})


@login_required
def premium_payment_view(request, payment_id):
    premium_payment = get_object_or_404(PremiumPayment, id=payment_id, user=request.user)
    plan = PREMIUM_PLANS[premium_payment.plan]
    should_create_order = not premium_payment.provider_order_id or premium_payment.provider_order_id.startswith("demo_")
    if should_create_order:
        razorpay_order = create_razorpay_amount_order(
            premium_payment.amount,
            f"premium_{premium_payment.transaction_id}",
            {"type": "premium", "plan": plan["code"], "method": premium_payment.method},
        )
        premium_payment.provider_order_id = razorpay_order["id"]
        premium_payment.raw_response = razorpay_order
        premium_payment.save(update_fields=["provider_order_id", "raw_response", "updated_at"])
    else:
        razorpay_order = premium_payment.raw_response
    is_demo = not has_real_razorpay_keys() or razorpay_order.get("demo") or premium_payment.provider_order_id.startswith("demo_")
    if is_demo:
        messages.error(request, "Razorpay order could not be created. Check API key/secret and try again.")
    return render(
        request,
        "accounts/premium_payment.html",
        {
            "plan": plan,
            "payment": premium_payment,
            "razorpay_order": razorpay_order,
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "is_demo_payment": is_demo,
        },
    )


@login_required
def premium_verify_view(request):
    payment = get_object_or_404(PremiumPayment, id=request.POST.get("payment_id"), user=request.user)
    payload = {
        "razorpay_order_id": request.POST.get("razorpay_order_id", payment.provider_order_id),
        "razorpay_payment_id": request.POST.get("razorpay_payment_id", ""),
        "razorpay_signature": request.POST.get("razorpay_signature", ""),
    }
    try:
        verify_razorpay_signature(payload)
        plan = PREMIUM_PLANS[payment.plan]
        payment.status = PremiumPayment.SUCCESS
        payment.provider_payment_id = payload["razorpay_payment_id"] or f"demo_{payment.method}_{payment.transaction_id}"
        payment.signature = payload["razorpay_signature"]
        payment.raw_response = {**payment.raw_response, "verification": payload}
        payment.save()
        PremiumMembership.objects.filter(user=request.user, is_active=True).update(is_active=False)
        PremiumMembership.objects.create(
            user=request.user,
            plan=plan["code"],
            amount=plan["amount"],
            expires_at=timezone.now() + timedelta(days=plan["duration"]),
        )
        request.user.profile.premium_badge = True
        request.user.profile.save(update_fields=["premium_badge"])
        send_luxe_email(
            "Your LuxeNest Premium is active",
            request.user.email,
            "emails/premium.html",
            {"plan": plan, "user": request.user, "payment_method": payment.method.upper()},
        )
        sent_invoice = send_premium_invoice_email(payment)
        if not sent_invoice:
            messages.warning(request, "Premium activated. Invoice PDF is ready, but email needs SMTP credentials in .env.")
        messages.success(request, f"Premium membership activated via {payment.method.upper()}.")
        return redirect("accounts:dashboard")
    except Exception:
        payment.status = PremiumPayment.FAILED
        payment.save(update_fields=["status", "updated_at"])
        messages.error(request, "Premium payment verification failed. Please try again.")
        return redirect("accounts:premium")


def get_active_membership(user):
    return (
        PremiumMembership.objects.filter(user=user, is_active=True, expires_at__gte=timezone.now())
        .order_by("-expires_at")
        .first()
    )


@login_required
def premium_details_view(request):
    active_membership = get_active_membership(request.user)
    memberships = request.user.memberships.order_by("-created_at")
    payments = request.user.premium_payments.order_by("-created_at")[:8]
    return render(
        request,
        "accounts/premium_details.html",
        {
            "active_membership": active_membership,
            "memberships": memberships,
            "payments": payments,
        },
    )


@login_required
def premium_cancel_view(request):
    membership = get_active_membership(request.user)
    if not membership:
        messages.info(request, "No active Premium membership found.")
        return redirect("accounts:premium_details")

    if request.method != "POST":
        return render(request, "accounts/premium_cancel.html", {"membership": membership})

    if request.POST.get("confirm_cancel") != "yes":
        messages.info(request, "Premium cancellation was not completed.")
        return redirect("accounts:premium_details")

    cancelled_count = PremiumMembership.objects.filter(
        user=request.user,
        is_active=True,
        expires_at__gte=timezone.now(),
    ).update(is_active=False)
    request.user.profile.premium_badge = False
    request.user.profile.save(update_fields=["premium_badge"])

    messages.success(request, f"Premium membership cancelled. {cancelled_count} active subscription record(s) were closed.")
    return redirect("accounts:premium_details")


@login_required
def premium_invoice_view(request, payment_id):
    payment = get_object_or_404(PremiumPayment, id=payment_id, user=request.user, status=PremiumPayment.SUCCESS)
    if request.GET.get("download") == "pdf":
        pdf = render_premium_invoice_pdf(payment)
        if request.GET.get("email") == "1":
            sent = send_premium_invoice_email(payment)
            if not sent:
                messages.error(request, "PDF downloaded, but Premium invoice email could not be sent. Add EMAIL_HOST_PASSWORD in .env.")
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{premium_invoice_number(payment)}.pdf"'
        response["Content-Length"] = str(len(pdf))
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "no-store"
        return response
    return render(
        request,
        "accounts/premium_invoice.html",
        {"payment": payment, "invoice_no": premium_invoice_number(payment)},
    )


@login_required
def send_premium_invoice_view(request, payment_id):
    payment = get_object_or_404(PremiumPayment, id=payment_id, user=request.user, status=PremiumPayment.SUCCESS)
    sent = send_premium_invoice_email(payment)
    if sent:
        messages.success(request, f"Premium invoice sent to {request.user.email}.")
    else:
        messages.error(request, "Premium invoice PDF was generated, but email could not be sent. Add EMAIL_HOST_PASSWORD in .env.")
    return redirect("accounts:premium_invoice", payment.id)
