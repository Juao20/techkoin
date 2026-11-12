from django.contrib import admin, messages

from . import services
from .models import ModerationDecision, ModerationQueueItem, StolenDeviceReport

Action = ModerationDecision.Action


@admin.register(ModerationQueueItem)
class ModerationQueueAdmin(admin.ModelAdmin):
    """Moderation queue: riskiest first, one-click decisions."""

    list_display = (
        "title",
        "seller",
        "price_fcfa",
        "risk_score",
        "priority",
        "rules",
        "imei_status",
    )
    list_display_links = ("title",)
    list_filter = ("category", "imei_status")
    search_fields = ("title", "slug", "seller__email")
    readonly_fields = (
        "risk_score",
        "moderation_flags",
        "imei_status",
        "estimate_low",
        "estimate_mid",
        "estimate_high",
        "price_badge",
    )
    fields = (
        "title",
        "seller",
        "price_fcfa",
        "description",
        "risk_score",
        "moderation_flags",
        "imei_status",
        "estimate_low",
        "estimate_mid",
        "estimate_high",
        "price_badge",
        "rejection_reason",
    )
    actions = ["approve", "reject", "request_changes"]

    def get_queryset(self, request):
        qs = super().get_queryset(request).filter(status="pending_review")
        return qs.order_by("-risk_score", "created_at")

    @admin.display(boolean=True, description="Prioritaire")
    def priority(self, obj):
        return bool(obj.moderation_flags.get("priority"))

    @admin.display(description="Règles déclenchées")
    def rules(self, obj):
        rules = obj.moderation_flags.get("risk_rules", {})
        return ", ".join(f"{name} (+{points})" for name, points in rules.items()) or "-"

    def _apply(self, request, queryset, action):
        done = 0
        for listing in queryset:
            try:
                services.decide(listing, request.user, action, listing.rejection_reason)
                done += 1
            except ValueError as exc:
                self.message_user(request, f"{listing.title} : {exc}", level=messages.ERROR)
        self.message_user(request, f"{done} annonce(s) traitée(s).")

    @admin.action(description="Approuver les annonces sélectionnées")
    def approve(self, request, queryset):
        self._apply(request, queryset, Action.APPROVE)

    @admin.action(description="Refuser (motif : champ « motif de refus » de l'annonce)")
    def reject(self, request, queryset):
        self._apply(request, queryset, Action.REJECT)

    @admin.action(description="Demander des modifications au vendeur")
    def request_changes(self, request, queryset):
        self._apply(request, queryset, Action.REQUEST_CHANGES)

    def has_add_permission(self, request):
        return False


@admin.register(StolenDeviceReport)
class StolenDeviceReportAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "police_reference", "created_at")
    list_filter = ("status",)
    readonly_fields = ("imei_or_serial_hash",)
    actions = ["confirm", "dismiss"]

    @admin.action(description="Confirmer et retirer les annonces concernées")
    def confirm(self, request, queryset):
        pulled = sum(services.confirm_stolen_report(r) for r in queryset)
        self.message_user(request, f"{pulled} annonce(s) retirée(s) de la vente.")

    @admin.action(description="Rejeter la déclaration")
    def dismiss(self, request, queryset):
        queryset.update(status=StolenDeviceReport.Status.DISMISSED)


@admin.register(ModerationDecision)
class ModerationDecisionAdmin(admin.ModelAdmin):
    list_display = ("listing", "moderator", "action", "created_at")
    list_filter = ("action",)

    def has_change_permission(self, request, obj=None):
        return False  # decisions are an audit trail

    def has_add_permission(self, request):
        return False
