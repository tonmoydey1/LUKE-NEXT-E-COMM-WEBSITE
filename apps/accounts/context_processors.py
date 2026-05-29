from django.utils import timezone

from .models import PremiumMembership


def premium_status(request):
    if not request.user.is_authenticated:
        return {"active_premium_membership": None}

    membership = (
        PremiumMembership.objects.filter(
            user=request.user,
            is_active=True,
            expires_at__gte=timezone.now(),
        )
        .order_by("-expires_at")
        .first()
    )
    return {"active_premium_membership": membership}
