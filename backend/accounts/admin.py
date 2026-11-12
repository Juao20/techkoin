from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Shop, User

admin.site.register(User, UserAdmin)


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "verification_status", "plan")
    list_filter = ("verification_status", "plan", "city")
    search_fields = ("name", "slug")
