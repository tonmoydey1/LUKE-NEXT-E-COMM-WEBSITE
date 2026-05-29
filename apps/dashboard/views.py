from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.shortcuts import render

from apps.catalog.models import Product
from apps.orders.models import Order
from apps.payments.models import Payment


@staff_member_required
def admin_dashboard_view(request):
    orders = Order.objects.all()
    context = {
        "revenue": orders.exclude(status=Order.CANCELLED).aggregate(total=Sum("total"))["total"] or 0,
        "order_count": orders.count(),
        "customer_count": orders.values("user").distinct().count(),
        "low_stock": Product.objects.filter(stock__lte=5).count(),
        "recent_orders": orders.select_related("user")[:8],
        "status_breakdown": orders.values("status").annotate(count=Count("id")),
        "payments": Payment.objects.select_related("order")[:8],
    }
    return render(request, "dashboard/admin_dashboard.html", context)
