from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("", views.payment_page_view, name="payment_page"),
    path("verify/", views.payment_verify_view, name="verify"),
    path("failure/", views.payment_failure_view, name="failure"),
]
