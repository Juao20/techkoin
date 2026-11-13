from django.urls import path

from .views import EventView, ShopStatsView

urlpatterns = [
    path("events/", EventView.as_view(), name="events"),
    path("shop/stats/", ShopStatsView.as_view(), name="shop-stats"),
]
