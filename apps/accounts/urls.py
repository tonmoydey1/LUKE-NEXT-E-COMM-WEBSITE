from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("reset-password/<int:user_id>/<str:token>/", views.reset_password_view, name="reset_password"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile/", views.profile_view, name="profile"),
    path("addresses/", views.addresses_view, name="addresses"),
    path("premium/", views.premium_view, name="premium"),
    path("premium/details/", views.premium_details_view, name="premium_details"),
    path("premium/cancel/", views.premium_cancel_view, name="premium_cancel"),
    path("premium/invoice/<int:payment_id>/", views.premium_invoice_view, name="premium_invoice"),
    path("premium/invoice/<int:payment_id>/send/", views.send_premium_invoice_view, name="send_premium_invoice"),
    path("premium/payment/<int:payment_id>/", views.premium_payment_view, name="premium_payment"),
    path("premium/verify/", views.premium_verify_view, name="premium_verify"),
]
