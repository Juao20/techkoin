from django.urls import path

from . import views

urlpatterns = [
    path("ai/status/", views.AIStatus.as_view()),
    path("ai/search/", views.SearchView.as_view()),
    path("ai/describe/", views.DescribeView.as_view()),
    path("ai/assistant/", views.AssistantView.as_view()),
    path("ai/voice/", views.VoiceView.as_view()),
]
