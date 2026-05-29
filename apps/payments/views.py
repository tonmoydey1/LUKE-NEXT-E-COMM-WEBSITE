from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.orders.invoices import render_invoice_pdf
from apps.orders.models import Order
from apps.orders.services import send_luxe_email, send_order_invoice_email, update_order_status

from .models import Payment
from django.conf import settings

from .services import create_razorpay_order, has_real_razorpay_keys, verify_razorpay_signature


@login_required
def payment_page_view(request):
    order = get_object_or_404(Order, id=request.session.get("pending_order_id"), user=request.user)
    payment, razorpay_order = create_razorpay_order(order)
    return render(
        request,
        "payments/payment.html",
        {
            "order": order,
            "payment": payment,
            "razorpay_order": razorpay_order,
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "gateway_ready": has_real_razorpay_keys() and not razorpay_order.get("demo"),
        },
    )


@login_required
def payment_verify_view(request):
    order = get_object_or_404(Order, id=request.session.get("pending_order_id"), user=request.user)
    payment = get_object_or_404(Payment, order=order)
    payload = {
        "razorpay_order_id": request.POST.get("razorpay_order_id", payment.provider_order_id),
        "razorpay_payment_id": request.POST.get("razorpay_payment_id", ""),
        "razorpay_signature": request.POST.get("razorpay_signature", ""),
        "payment_mode": request.POST.get("payment_mode", "card"),
    }
    try:
        verify_razorpay_signature(payload)
        payment.status = Payment.SUCCESS
        payment.provider_payment_id = payload["razorpay_payment_id"] or f"demo_{payload['payment_mode']}_{payment.transaction_id}"
        payment.signature = payload["razorpay_signature"]
        payment.raw_response = payload
        payment.save()
        update_order_status(order, Order.CONFIRMED, note="Payment received successfully.")
        send_luxe_email("LuxeNest payment confirmed", request.user.email, "emails/payment_confirmation.html", {"order": order, "payment": payment})
        send_order_invoice_email(order, "LuxeNest payment invoice")
        request.session.pop("pending_order_id", None)
        return redirect("orders:success", order.order_id)
    except Exception:
        payment.status = Payment.FAILED
        payment.save(update_fields=["status", "updated_at"])
        messages.error(request, "Payment verification failed.")
        return redirect("payments:failure")


@login_required
def payment_failure_view(request):
    return render(request, "payments/failure.html")
