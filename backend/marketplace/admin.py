from django.contrib import admin

from .models import Favorite, Listing, ListingPhoto, ListingReport


class PhotoInline(admin.TabularInline):
    model = ListingPhoto
    extra = 0
    readonly_fields = ("phash",)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "category", "price_fcfa", "city", "status", "risk_score")
    list_filter = ("status", "category", "condition_type", "city")
    search_fields = ("title", "slug", "seller__email")
    exclude = ("imei_or_serial",)  # never shown in clear in the admin
    inlines = [PhotoInline]


@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):
    list_display = ("listing", "reason", "reporter", "status", "created_at")
    list_filter = ("status", "reason")
    actions = ["mark_handled", "mark_dismissed"]

    @admin.action(description="Marquer comme traités")
    def mark_handled(self, request, queryset):
        queryset.update(status=ListingReport.Status.HANDLED)

    @admin.action(description="Classer sans suite")
    def mark_dismissed(self, request, queryset):
        queryset.update(status=ListingReport.Status.DISMISSED)


admin.site.register(Favorite)
