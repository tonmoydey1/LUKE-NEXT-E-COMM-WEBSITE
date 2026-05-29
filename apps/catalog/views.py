from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ProductSearchForm, ReviewForm
from .models import Category, Product, Wishlist


def _filtered_products(request, category=None):
    qs = Product.objects.filter(is_active=True).select_related("category").prefetch_related("images")
    form = ProductSearchForm(request.GET)
    if category:
        qs = qs.filter(Q(category=category) | Q(category__parent=category))
    if form.is_valid():
        q = form.cleaned_data.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(brand__icontains=q) | Q(description__icontains=q))
        if form.cleaned_data.get("min_price") is not None:
            qs = qs.filter(price__gte=form.cleaned_data["min_price"])
        if form.cleaned_data.get("max_price") is not None:
            qs = qs.filter(price__lte=form.cleaned_data["max_price"])
        if form.cleaned_data.get("rating") is not None:
            qs = qs.filter(rating__gte=form.cleaned_data["rating"])
        sort_map = {
            "popular": "-review_count",
            "newest": "-created_at",
            "price_low": "price",
            "price_high": "-price",
            "best_rated": "-rating",
        }
        qs = qs.order_by(sort_map.get(form.cleaned_data.get("sort"), "-created_at"))
    return qs, form


def home_view(request):
    featured = Product.objects.filter(is_active=True, is_featured=True).prefetch_related("images")[:12]
    trending = Product.objects.filter(is_active=True, is_trending=True).prefetch_related("images")[:12]
    categories = Category.objects.filter(is_featured=True)[:10]
    return render(request, "catalog/home.html", {"featured": featured, "trending": trending, "categories": categories})


def product_list_view(request):
    products, form = _filtered_products(request)
    return render(request, "catalog/product_list.html", {"products": products, "form": form, "title": "All Products"})


def category_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products, form = _filtered_products(request, category)
    return render(request, "catalog/product_list.html", {"products": products, "form": form, "title": category.name, "category": category})


def product_detail_view(request, slug):
    product = get_object_or_404(Product.objects.prefetch_related("images", "variants", "reviews"), slug=slug, is_active=True)
    if request.method == "POST" and request.user.is_authenticated:
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Review submitted.")
            return redirect(product.get_absolute_url())
    related = Product.objects.filter(category=product.category, is_active=True).exclude(id=product.id)[:4]
    return render(request, "catalog/product_detail.html", {"product": product, "related": related, "review_form": ReviewForm()})


def search_suggest_view(request):
    q = request.GET.get("q", "")
    data = list(Product.objects.filter(name__icontains=q, is_active=True).values("name", "slug")[:8])
    return JsonResponse({"results": data})


@require_POST
def ai_help_chat_view(request):
    message = request.POST.get("message", "").strip()
    if not message:
        return JsonResponse({"reply": "Ask Tonmoy AI can help with products, delivery, payment, invoices, premium membership, or orders."})

    text = message.lower()
    reply = _chat_reply(text)
    products = _chat_product_suggestions(message)
    return JsonResponse({"reply": reply, "products": products})


def _chat_reply(text):
    knowledge = [
        (
            ("delivery", "pincode", "location", "eta", "shipping"),
            "You can check delivery from the Delivery option in the navbar. Enter a 6-digit Indian pincode or use current location to preview ETA and serviceability before checkout.",
        ),
        (
            ("payment", "upi", "card", "razorpay", "cod", "cash"),
            "LuxeNest supports Card, UPI, and Cash on Delivery flows. For live Razorpay checkout, use valid Razorpay API keys in .env; for project demos, the LuxeNest sandbox keeps the flow interview-safe.",
        ),
        (
            ("invoice", "pdf", "bill", "gst", "email"),
            "Invoices are generated after successful orders with GST, shipping, discount, payment status, and LuxeNest branding. Use View Invoice or Download PDF on the order success page.",
        ),
        (
            ("premium", "membership", "subscription", "cancel", "member"),
            "Premium members get priority delivery, premium badges, early offers, and invoice priority. You can manage plan status, invoices, and cancellation from Premium Details.",
        ),
        (
            ("cart", "coupon", "checkout", "order"),
            "Add products to cart, apply a coupon like LUXE10 when eligible, choose delivery address, then select Card/UPI or Cash on Delivery at checkout.",
        ),
        (
            ("return", "refund", "cancel"),
            "Orders can be cancelled before they are shipped. Return and refund requests are available from the order lifecycle structure once the order is delivered.",
        ),
        (
            ("login", "register", "otp", "account", "password"),
            "Use Account to login or register. Email OTP verification, password reset, profile, address book, wishlist, and order history are part of the customer dashboard.",
        ),
    ]
    for keywords, answer in knowledge:
        if any(keyword in text for keyword in keywords):
            return answer
    return (
        "I can help you find products, check delivery, explain payments, invoices, premium membership, cart, checkout, and order tracking. "
        "Tell me what you want to buy or what step is stuck."
    )


def _chat_product_suggestions(message):
    terms = [term for term in re_split_words(message) if len(term) > 2]
    query = Q()
    for term in terms[:5]:
        query |= Q(name__icontains=term) | Q(brand__icontains=term) | Q(category__name__icontains=term)
    if query:
        products = Product.objects.filter(query, is_active=True).select_related("category").prefetch_related("images")[:3]
    else:
        products = Product.objects.filter(is_active=True, is_featured=True).prefetch_related("images")[:3]
    return [
        {
            "name": product.name,
            "price": f"Rs. {product.price}",
            "image": product.hero_image,
            "url": product.get_absolute_url(),
        }
        for product in products
    ]


def re_split_words(value):
    return [part.strip() for part in value.replace("/", " ").replace("-", " ").replace(",", " ").split()]


@login_required
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user).select_related("product").prefetch_related("product__images")
    return render(request, "catalog/wishlist.html", {"items": items})


@login_required
def toggle_wishlist_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.delete()
        messages.info(request, "Removed from wishlist.")
    else:
        messages.success(request, "Added to wishlist.")
    return redirect(request.META.get("HTTP_REFERER") or product.get_absolute_url())


def about_view(request):
    return render(request, "content/about.html")


def contact_view(request):
    return render(request, "content/contact.html")


def faq_view(request):
    return render(request, "content/faq.html")
