from django.urls import path

from .views import EstimateView

urlpatterns = [path("pricing/estimate/", EstimateView.as_view())]
