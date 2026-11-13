from django.urls import path

from . import views

urlpatterns = [
    path("orders/", views.OrderCreate.as_view()),
    path("orders/<int:pk>/", views.OrderDetail.as_view()),
    path("orders/<int:pk>/pay/", views.OrderPay.as_view()),
    path("orders/<int:pk>/handed-over/", views.OrderHandedOver.as_view()),
    path("orders/<int:pk>/confirm/", views.OrderConfirm.as_view()),
    path("orders/<int:pk>/dispute/", views.OrderDispute.as_view()),
    path("orders/<int:pk>/cancel/", views.OrderCancel.as_view()),
    path("orders/<int:pk>/simulator-settle/", views.SimulatorSettle.as_view()),
    path("me/orders/", views.MyOrders.as_view()),
    path("shop/subscribe/", views.ShopSubscribe.as_view()),
    path("shop/subscription/", views.ShopSubscription.as_view()),
    path("shop/subscription/settle/", views.SubscriptionSettle.as_view()),
    path("payments/commission/", views.Commission.as_view()),
    path("payments/webhooks/<str:provider>/", views.Webhook.as_view()),
]
