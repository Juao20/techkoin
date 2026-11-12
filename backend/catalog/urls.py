from django.urls import path

from . import views

urlpatterns = [
    path("catalog/models/", views.DeviceModelList.as_view()),
    path("catalog/models/<slug:slug>/", views.DeviceModelDetail.as_view()),
    path("catalog/brands/", views.BrandList.as_view()),
    path("catalog/processors/", views.ProcessorList.as_view()),
    path("catalog/gpus/", views.GpuList.as_view()),
    path("catalog/cities/", views.CityList.as_view()),
]
