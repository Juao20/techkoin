from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from trust import services as trust

from .models import Shop, User


def _link(kind: str, pk: int, has_file: bool, label: str):
    if not has_file:
        return "-"
    return format_html(
        '<a href="/api/private-files/{}/{}/" target="_blank">{}</a>', kind, pk, label
    )


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "first_name", "account_type", "identity_status", "is_moderator")
    list_filter = ("identity_status", "account_type", "is_moderator", "is_staff")
    readonly_fields = ("identity_document", "identity_selfie", "identity_files")
    actions = ["approve_identity", "reject_identity"]
    fieldsets = (
        *UserAdmin.fieldsets,
        (
            "TechKoin",
            {
                "fields": (
                    "phone",
                    "whatsapp_number",
                    "account_type",
                    "city",
                    "quartier",
                    "is_moderator",
                    "identity_status",
                    "identity_files",
                )
            },
        ),
    )

    @admin.display(description="Pièces d'identité")
    def identity_files(self, obj):
        return format_html(
            "{} · {}",
            _link("identity", obj.pk, bool(obj.identity_document), "pièce"),
            _link("selfie", obj.pk, bool(obj.identity_selfie), "selfie"),
        )

    @admin.action(description="Valider l'identité (badge « Identité vérifiée »)")
    def approve_identity(self, request, queryset):
        for user in queryset.filter(identity_status="pending"):
            trust.decide_identity(user, True)

    @admin.action(description="Refuser la vérification d'identité")
    def reject_identity(self, request, queryset):
        for user in queryset.filter(identity_status="pending"):
            trust.decide_identity(user, False)


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "verification_status", "plan")
    list_filter = ("verification_status", "plan", "city")
    search_fields = ("name", "slug")
    readonly_fields = ("verification_document", "dossier")
    actions = ["approve_shop", "reject_shop"]

    @admin.display(description="Dossier")
    def dossier(self, obj):
        return _link("shop-document", obj.pk, bool(obj.verification_document), "document")

    @admin.action(description="Valider la boutique (badge « Boutique vérifiée »)")
    def approve_shop(self, request, queryset):
        for shop in queryset.filter(verification_status="pending"):
            trust.decide_shop(shop, True)

    @admin.action(description="Refuser la vérification de la boutique")
    def reject_shop(self, request, queryset):
        for shop in queryset.filter(verification_status="pending"):
            trust.decide_shop(shop, False)
