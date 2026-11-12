from django.urls import path

from .views import csrf, health

urlpatterns = [
    path("health/", health, name="health"),
    path("auth/csrf/", csrf, name="csrf"),
]
