from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/", views.add_to_cart_view, name="add_to_cart"),
    path("cart/update/<int:item_id>/", views.update_cart_item_view, name="update_cart_item"),
    path("cart/remove/<int:item_id>/", views.remove_cart_item_view, name="remove_cart_item"),
    path("cart/coupon/", views.apply_coupon_view, name="apply_coupon"),
    path("delivery/check/", views.check_delivery_view, name="check_delivery"),
    path("delivery/", views.delivery_checker_view, name="delivery_checker"),
    path("checkout/", views.checkout_view, name="checkout"),
    path("success/<str:order_id>/", views.order_success_view, name="success"),
    path("history/", views.order_history_view, name="history"),
    path("<str:order_id>/", views.order_detail_view, name="detail"),
    path("<str:order_id>/invoice/", views.invoice_view, name="invoice"),
    path("<str:order_id>/invoice/send/", views.send_invoice_view, name="send_invoice"),
    path("<str:order_id>/track/", views.track_order_view, name="track"),
    path("<str:order_id>/cancel/", views.cancel_order_view, name="cancel"),
]
