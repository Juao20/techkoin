from django.contrib import admin

from .models import AIRequestLog


@admin.register(AIRequestLog)
class AIRequestLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "feature",
        "model",
        "success",
        "fallback_used",
        "cache_hit",
        "latency_ms",
        "input_tokens",
        "output_tokens",
    )
    list_filter = ("feature", "success", "fallback_used")
    readonly_fields = [f.name for f in AIRequestLog._meta.fields]

    def has_add_permission(self, request):
        return False
