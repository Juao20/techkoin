from django.urls import path

from . import views

urlpatterns = [
    path("ai/status/", views.AIStatus.as_view()),
]
