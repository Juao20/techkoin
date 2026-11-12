from django.contrib import admin

from .models import Brand, City, DeviceModel, GraphicsCard, Processor

admin.site.register(Brand)
admin.site.register(Processor)
admin.site.register(GraphicsCard)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "position")
    filter_horizontal = ("nearby",)


@admin.register(DeviceModel)
class DeviceModelAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "category", "release_year", "is_active")
    list_filter = ("category", "brand", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
