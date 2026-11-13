from django.urls import path

from . import views

urlpatterns = [
    path("ai/status/", views.AIStatus.as_view()),
    path("ai/search/", views.SearchView.as_view()),
]
