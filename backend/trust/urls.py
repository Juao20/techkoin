from django.urls import path

from . import views

urlpatterns = [
    path("stolen-reports/", views.StolenReportView.as_view()),
    path("me/identity/", views.IdentityVerificationView.as_view()),
    path("shop/verification/", views.ShopVerificationView.as_view()),
    path("private-files/<str:kind>/<int:pk>/", views.private_file),
]
