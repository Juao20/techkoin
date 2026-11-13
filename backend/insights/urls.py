from django.urls import path

from . import views

urlpatterns = [
    path("insights/demand/", views.Demand.as_view()),
    path("insights/pricing/", views.Pricing.as_view()),
    path("insights/dormant/", views.Dormant.as_view()),
    path("insights/reports/", views.ReportList.as_view()),
    path("insights/reports/<int:pk>/", views.ReportDetail.as_view()),
    path("insights/chat/", views.Chat.as_view()),
    path("insights/bulk-optimize/", views.BulkOptimize.as_view()),
    path("insights/bulk-optimize/apply/", views.BulkApply.as_view()),
    path("insights/competition/<int:listing_id>/", views.Competition.as_view()),
    path("insights/listings/<int:listing_id>/apply/", views.ApplyListing.as_view()),
]
