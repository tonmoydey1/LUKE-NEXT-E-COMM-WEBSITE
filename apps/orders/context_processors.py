from .models import Cart


def cart_counter(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return {"cart_count": cart.items.filter(saved_for_later=False).count()}
    return {"cart_count": 0}
