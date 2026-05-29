from .models import Category


def navigation(request):
    return {"nav_categories": Category.objects.filter(parent__isnull=True)[:8]}
