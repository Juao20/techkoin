from django.urls import path

from . import views

urlpatterns = [
    path("listings/", views.ListingList.as_view()),
    path("listings/facets/", views.ListingFacets.as_view()),
    path("listings/<int:pk>/", views.ListingById.as_view()),
    path("listings/<int:pk>/photos/", views.PhotoUpload.as_view()),
    path("listings/<int:pk>/photos/<int:photo_id>/", views.PhotoDelete.as_view()),
    path("listings/<int:pk>/publish/", views.Publish.as_view()),
    path("listings/<int:pk>/mark-sold/", views.MarkSold.as_view()),
    path("listings/<int:pk>/archive/", views.Archive.as_view()),
    path("listings/<int:pk>/reveal-phone/", views.RevealPhone.as_view()),
    path("listings/<int:pk>/whatsapp/", views.WhatsAppLink.as_view()),
    path("listings/<int:pk>/favorite/", views.FavoriteToggle.as_view()),
    path("listings/<int:pk>/report/", views.ReportListing.as_view()),
    path("listings/<slug:slug>/similar/", views.Similar.as_view()),
    path("listings/<slug:slug>/", views.ListingBySlug.as_view()),
    path("me/listings/", views.MyListings.as_view()),
    path("me/alerts/", views.MyAlerts.as_view()),
    path("me/alerts/<int:pk>/", views.MyAlert.as_view()),
    path("me/notifications/", views.MyNotifications.as_view()),
    path("me/favorites/", views.MyFavorites.as_view()),
    path("shops/<slug:slug>/", views.ShopDetail.as_view()),
    path("shops/<slug:slug>/listings/", views.ShopListings.as_view()),
]
