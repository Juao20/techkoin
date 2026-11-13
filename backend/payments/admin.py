from django.contrib import admin, messages

from . import services
from .models import Order, OrderEvent, Transaction


class EventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    readonly_fields = ("from_status", "to_status", "actor", "note", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    fields = ("direction", "provider", "operator", "amount_fcfa", "status", "provider_reference")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Disputes first: a moderator decides who gets the money held in escrow."""

    list_display = ("id", "listing", "buyer", "seller", "amount_fcfa", "status", "created_at")
    list_filter = ("status", "delivery_mode")
    search_fields = ("listing__title", "buyer__email", "seller__email")
    readonly_fields = [f.name for f in Order._meta.fields]
    inlines = [EventInline, TransactionInline]
    actions = ["release_to_seller", "refund_buyer"]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _resolve(self, request, queryset, outcome):
        done = 0
        for order in queryset.filter(status=Order.Status.DISPUTED):
            try:
                services.resolve_dispute(order, request.user, outcome)
                done += 1
            except services.OrderError as exc:
                self.message_user(request, f"Commande {order.pk} : {exc}", level=messages.ERROR)
        self.message_user(request, f"{done} litige(s) tranché(s).")

    @admin.action(description="Litige : verser les fonds au vendeur")
    def release_to_seller(self, request, queryset):
        self._resolve(request, queryset, "release")

    @admin.action(description="Litige : rembourser l'acheteur")
    def refund_buyer(self, request, queryset):
        self._resolve(request, queryset, "refund")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "direction", "provider", "status", "amount_fcfa", "created_at")
    list_filter = ("direction", "provider", "status")
    readonly_fields = [f.name for f in Transaction._meta.fields]

    def has_add_permission(self, request):
        return False
