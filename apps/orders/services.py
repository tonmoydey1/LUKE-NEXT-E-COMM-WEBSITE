from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Order, OrderItem, ShippingStatus


def send_luxe_email(subject, to_email, template, context, attachments=None):
    html = render_to_string(template, context)
    email = EmailMessage(subject=subject, body=html, from_email=settings.DEFAULT_FROM_EMAIL, to=[to_email])
    email.content_subtype = "html"
    for attachment in attachments or []:
        email.attach(*attachment)
    try:
        email.send(fail_silently=False)
        return True
    except Exception:
        return False


def is_console_email_backend():
    return settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend"


def send_order_invoice_email(order, subject="Your LuxeNest invoice"):
    from .invoices import render_invoice_pdf

    invoice = render_invoice_pdf(order)
    return send_luxe_email(
        subject,
        order.user.email,
        "emails/invoice.html",
        {"order": order},
        attachments=[(f"{order.order_id}-invoice.pdf", invoice, "application/pdf")],
    )


def estimate_delivery_for_pincode(pincode):
    if not pincode or len(pincode) != 6:
        return None
    days = 2 if pincode[:2] in {"11", "40", "56", "60", "70"} else 5
    return timezone.localdate() + timedelta(days=days)


def is_serviceable_pincode(pincode):
    return bool(pincode and pincode.isdigit() and len(pincode) == 6 and pincode[0] != "0")


def create_order_from_cart(user, address, payment_method="razorpay"):
    cart = user.cart
    order = Order.objects.create(
        user=user,
        address=address,
        subtotal=cart.subtotal,
        tax=cart.tax,
        shipping=cart.shipping,
        discount=cart.discount,
        total=cart.total,
        payment_method=payment_method,
        estimated_delivery=estimate_delivery_for_pincode(address.pincode),
    )
    for item in cart.items.filter(saved_for_later=False).select_related("product", "variant"):
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product.name,
            variant_label=f"{item.variant.name}: {item.variant.value}" if item.variant else "",
            quantity=item.quantity,
            unit_price=item.unit_price,
            gst_rate=item.product.gst_rate,
        )
    ShippingStatus.objects.create(order=order, status=Order.PLACED, location=address.city, note="Your order has been placed.")
    cart.items.filter(saved_for_later=False).delete()
    cart.coupon = None
    cart.save(update_fields=["coupon", "updated_at"])
    return order


def update_order_status(order, status, location="", note=""):
    order.status = status
    order.save(update_fields=["status", "updated_at"])
    event = ShippingStatus.objects.create(order=order, status=status, location=location, note=note)
    send_luxe_email(
        f"LuxeNest order {order.order_id}: {order.get_status_display()}",
        order.user.email,
        "emails/order_status.html",
        {"order": order, "event": event},
    )
    return event
