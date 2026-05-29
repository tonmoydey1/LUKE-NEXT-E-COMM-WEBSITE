from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import Address
from apps.catalog.models import Coupon, Product, ProductVariant

from .forms import CouponForm
from .invoices import render_invoice_pdf
from .models import Cart, CartItem, Order
from .services import create_order_from_cart, is_serviceable_pincode, send_luxe_email, send_order_invoice_email, update_order_status


def _cart(user):
    return Cart.objects.get_or_create(user=user)[0]


@login_required
def cart_view(request):
    cart = _cart(request.user)
    return render(request, "orders/cart.html", {"cart": cart, "coupon_form": CouponForm()})


@login_required
def add_to_cart_view(request):
    product = get_object_or_404(Product, id=request.POST.get("product_id"), is_active=True)
    variant = ProductVariant.objects.filter(id=request.POST.get("variant_id"), product=product).first()
    item, created = CartItem.objects.get_or_create(cart=_cart(request.user), product=product, variant=variant)
    item.quantity = item.quantity + int(request.POST.get("quantity", 1)) if not created else int(request.POST.get("quantity", 1))
    item.saved_for_later = False
    item.save()
    messages.success(request, "Added to cart.")
    return redirect("orders:cart")


@login_required
def update_cart_item_view(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.quantity = max(1, min(10, int(request.POST.get("quantity", item.quantity))))
    item.saved_for_later = request.POST.get("saved_for_later") == "on"
    item.save()
    return redirect("orders:cart")


@login_required
def remove_cart_item_view(request, item_id):
    get_object_or_404(CartItem, id=item_id, cart__user=request.user).delete()
    messages.info(request, "Item removed.")
    return redirect("orders:cart")


@login_required
def apply_coupon_view(request):
    cart = _cart(request.user)
    coupon = Coupon.objects.filter(code__iexact=request.POST.get("code"), is_active=True).first()
    if coupon:
        cart.coupon = coupon
        cart.save(update_fields=["coupon", "updated_at"])
        messages.success(request, "Coupon applied.")
    else:
        messages.error(request, "Invalid coupon.")
    return redirect("orders:cart")


def check_delivery_view(request):
    pincode = request.GET.get("pincode", "")
    serviceable = is_serviceable_pincode(pincode)
    eta = None
    if serviceable:
        from .services import estimate_delivery_for_pincode

        eta = estimate_delivery_for_pincode(pincode)
    return JsonResponse(
        {
            "serviceable": serviceable,
            "eta": eta.isoformat() if eta else None,
            "message": "Delivery available" if serviceable else "Not serviceable",
        }
    )


def delivery_checker_view(request):
    return render(request, "orders/delivery_checker.html")


@login_required
def checkout_view(request):
    cart = _cart(request.user)
    addresses = request.user.addresses.all()
    if not cart.items.filter(saved_for_later=False).exists():
        messages.error(request, "Your cart is empty.")
        return redirect("orders:cart")
    if request.method == "POST":
        address_id = request.POST.get("address")
        if not address_id:
            messages.error(request, "Please add a delivery address before placing your order.")
            return redirect("accounts:addresses")
        address = Address.objects.filter(id=address_id, user=request.user).first()
        if not address:
            messages.error(request, "Please choose a valid delivery address.")
            return redirect("orders:checkout")
        if not is_serviceable_pincode(address.pincode):
            messages.error(request, "Selected pincode is not serviceable.")
            return redirect("orders:checkout")
        order = create_order_from_cart(request.user, address, request.POST.get("payment_method", "razorpay"))
        if order.payment_method == "cod":
            send_luxe_email("Your LuxeNest order is confirmed", request.user.email, "emails/order_confirmation.html", {"order": order})
            send_order_invoice_email(order, "LuxeNest COD invoice")
            return redirect("orders:success", order.order_id)
        request.session["pending_order_id"] = order.id
        return redirect("payments:payment_page")
    return render(request, "orders/checkout.html", {"cart": cart, "addresses": addresses})


@login_required
def order_success_view(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    return render(request, "orders/success.html", {"order": order})


@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items")
    return render(request, "orders/history.html", {"orders": orders})


@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related("items"), order_id=order_id, user=request.user)
    return render(request, "orders/detail.html", {"order": order})


@login_required
def track_order_view(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related("tracking_events"), order_id=order_id, user=request.user)
    steps = [status for status, _ in Order.STATUS_CHOICES[:6]]
    current_index = steps.index(order.status) if order.status in steps else 0
    progress = int((current_index / (len(steps) - 1)) * 100) if len(steps) > 1 else 0
    return render(request, "orders/tracking.html", {"order": order, "status_steps": Order.STATUS_CHOICES[:6], "progress": progress})


@login_required
def invoice_view(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related("items"), order_id=order_id, user=request.user)
    if request.GET.get("download") == "pdf":
        pdf = render_invoice_pdf(order)
        if request.GET.get("email") == "1":
            sent = send_order_invoice_email(order, "Your LuxeNest invoice")
            if not sent:
                messages.error(request, "PDF downloaded, but email could not be sent. Add EMAIL_HOST_PASSWORD in .env.")
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{order.order_id}-invoice.pdf"'
        response["Content-Length"] = str(len(pdf))
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "no-store"
        return response
    return render(request, "orders/invoice.html", {"order": order})


@login_required
def send_invoice_view(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related("items"), order_id=order_id, user=request.user)
    sent = send_order_invoice_email(order, "Your LuxeNest invoice")
    if sent:
        messages.success(request, f"Invoice sent to {order.user.email}.")
    else:
        messages.error(request, "Invoice PDF was generated, but email could not be sent. Add EMAIL_HOST_PASSWORD in .env.")
    return redirect("orders:invoice", order.order_id)


@login_required
def cancel_order_view(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    if order.status in [Order.PLACED, Order.CONFIRMED]:
        update_order_status(order, Order.CANCELLED, note="Cancelled by customer.")
        messages.success(request, "Order cancelled.")
    else:
        messages.error(request, "This order can no longer be cancelled online.")
    return redirect("orders:detail", order.order_id)
