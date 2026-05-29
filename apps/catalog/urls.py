from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("shop/", views.product_list_view, name="product_list"),
    path("shop/search/", views.product_list_view, name="search"),
    path("shop/suggest/", views.search_suggest_view, name="search_suggest"),
    path("shop/ai-help/", views.ai_help_chat_view, name="ai_help_chat"),
    path("shop/category/<slug:slug>/", views.category_view, name="category"),
    path("shop/product/<slug:slug>/", views.product_detail_view, name="product_detail"),
    path("shop/wishlist/", views.wishlist_view, name="wishlist"),
    path("shop/wishlist/toggle/<int:product_id>/", views.toggle_wishlist_view, name="toggle_wishlist"),
    path("about/", views.about_view, name="about"),
    path("contact/", views.contact_view, name="contact"),
    path("faq/", views.faq_view, name="faq"),
]
