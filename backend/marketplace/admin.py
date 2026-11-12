from django.contrib import admin

from .models import Favorite, Listing, ListingPhoto


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


admin.site.register(Favorite)
