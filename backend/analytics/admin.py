from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("type", "created_at", "listing", "shop", "query_text")
    list_filter = ("type",)
