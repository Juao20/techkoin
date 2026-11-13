from django.urls import include, path

from .views import csrf, health

urlpatterns = [
    path("", include("accounts.urls")),
    path("", include("catalog.urls")),
    path("", include("analytics.urls")),
    path("", include("marketplace.urls")),
    path("", include("pricing.urls")),
    path("", include("trust.urls")),
    path("", include("ai.urls")),
    path("", include("payments.urls")),
    path("health/", health, name="health"),
    path("auth/csrf/", csrf, name="csrf"),
]
