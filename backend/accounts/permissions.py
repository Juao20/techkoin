from rest_framework.permissions import BasePermission

from .models import Shop


def shop_of(user) -> Shop | None:
    if not user or not user.is_authenticated:
        return None
    return Shop.objects.filter(owner=user).first()


class HasShop(BasePermission):
    message = "Cette fonction est réservée aux comptes boutique."

    def has_permission(self, request, view):
        shop = shop_of(request.user)
        request.shop = shop
        return shop is not None


class IsProShop(HasShop):
    """The only gate to the Pro endpoints: the front end displays, it never decides (spec 11)."""

    message = "Cette fonction fait partie de l'offre Pro. Abonnez-vous pour y accéder."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.shop.is_pro
