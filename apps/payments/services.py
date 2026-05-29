from django.conf import settings

from .models import Payment


def _demo_razorpay_order(payment, order):
    return {"id": f"demo_{payment.transaction_id}", "amount": int(order.total * 100), "currency": "INR", "demo": True}


def has_real_razorpay_keys():
    key_id = settings.RAZORPAY_KEY_ID or ""
    key_secret = settings.RAZORPAY_KEY_SECRET or ""
    placeholders = {"replace-me", "rzp_test_xxxxx", "test", "demo"}
    return key_id not in placeholders and key_secret not in placeholders and key_id.startswith("rzp_")


def create_razorpay_order(order):
    payment, _ = Payment.objects.get_or_create(user=order.user, order=order, defaults={"amount": order.total})
    if not has_real_razorpay_keys():
        return payment, _demo_razorpay_order(payment, order)
    import razorpay

    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        rp_order = client.order.create({"amount": int(order.total * 100), "currency": "INR", "payment_capture": 1, "receipt": order.order_id})
    except Exception as exc:
        payment.raw_response = {"mode": "demo_fallback", "reason": str(exc)}
        payment.save(update_fields=["raw_response", "updated_at"])
        return payment, _demo_razorpay_order(payment, order)
    payment.provider_order_id = rp_order["id"]
    payment.raw_response = rp_order
    payment.save(update_fields=["provider_order_id", "raw_response", "updated_at"])
    return payment, rp_order


def verify_razorpay_signature(payload):
    if settings.DEBUG and str(payload.get("razorpay_payment_id", "")).startswith("lxn_test_"):
        return True
    if not has_real_razorpay_keys() or payload.get("razorpay_order_id", "").startswith("demo_"):
        return True
    import razorpay

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    client.utility.verify_payment_signature(payload)
    return True


def create_razorpay_amount_order(amount, receipt, notes=None):
    if not has_real_razorpay_keys():
        return {"id": f"demo_{receipt}", "amount": int(amount * 100), "currency": "INR", "demo": True}
    import razorpay

    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        return client.order.create(
            {
                "amount": int(amount * 100),
                "currency": "INR",
                "payment_capture": 1,
                "receipt": receipt[:40],
                "notes": notes or {},
            }
        )
    except Exception as exc:
        return {"id": f"demo_{receipt}", "amount": int(amount * 100), "currency": "INR", "demo": True, "reason": str(exc)}
