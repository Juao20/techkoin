from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.phone import normalize_phone
from marketplace.models import Listing

from . import services
from .models import Order, Transaction
from .providers import get_provider
from .providers.base import InvalidSignature
from .services import InvalidTransition, OrderError


def error(code: str, message: str, http=status.HTTP_400_BAD_REQUEST, fields=None):
    body = {"code": code, "message": message}
    if fields:
        body["fields"] = fields
    return Response(body, status=http)


def user_orders(user):
    return Order.objects.filter(Q(buyer=user) | Q(seller=user))


def can_view(user, order: Order) -> bool:
    return user.id in (order.buyer_id, order.seller_id) or getattr(user, "is_moderator", False)


class OrderSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    listing = serializers.SerializerMethodField()
    history = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    checkout_url = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()
    provider = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    commission_fcfa = serializers.SerializerMethodField()
    seller_payout_fcfa = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "status_label",
            "role",
            "listing",
            "amount_fcfa",
            "commission_fcfa",
            "seller_payout_fcfa",
            "delivery_mode",
            "meetup_note",
            "payment_expires_at",
            "handed_over_at",
            "buyer_confirmed_at",
            "auto_release_at",
            "dispute_reason",
            "is_sandbox",
            "created_at",
            "history",
            "checkout_url",
            "actions",
            "provider",
            "seller_name",
        ]

    def _user(self):
        return self.context["request"].user

    def get_role(self, obj):
        user = self._user()
        if user.id == obj.buyer_id:
            return "buyer"
        return "seller" if user.id == obj.seller_id else "moderator"

    def get_listing(self, obj):
        thumb = None
        photo = obj.listing.photos.first()
        if photo:
            thumb = self.context["request"].build_absolute_uri(photo.thumb.url)
        return {
            "id": obj.listing_id,
            "slug": obj.listing.slug,
            "title": obj.listing.title,
            "thumb": thumb,
            "city": obj.listing.city,
        }

    def get_history(self, obj):
        return [
            {"from": e.from_status, "to": e.to_status, "note": e.note, "at": e.created_at}
            for e in obj.history.all()
        ]

    def get_checkout_url(self, obj):
        tx = obj.transactions.filter(direction="in", status="pending").first()
        return (tx.raw_payload or {}).get("checkout_url", "") if tx else ""

    def get_provider(self, obj):
        return settings.PAYMENT_PROVIDER

    def get_seller_name(self, obj):
        shop = getattr(obj.seller, "shop", None)
        return shop.name if shop else obj.seller.first_name or "Vendeur"

    # Commission and payout are the seller's business: hidden from the buyer.
    def get_commission_fcfa(self, obj):
        return obj.commission_fcfa if self.get_role(obj) != "buyer" else None

    def get_seller_payout_fcfa(self, obj):
        return obj.seller_payout_fcfa if self.get_role(obj) != "buyer" else None

    def get_actions(self, obj):
        role = self.get_role(obj)
        s = Order.Status
        buyer, seller = role == "buyer", role == "seller"
        return {
            "edit": buyer and obj.status == s.CREATED,
            "pay": buyer and obj.status == s.CREATED,
            "cancel": buyer and obj.status in (s.CREATED, s.PAYMENT_PENDING),
            "hand_over": seller and obj.status == s.PAID_HELD,
            "confirm": buyer and obj.status == s.HANDED_OVER,
            "dispute": buyer and obj.status in (s.PAID_HELD, s.HANDED_OVER),
        }


def respond(order: Order, request, http=status.HTTP_200_OK):
    order = Order.objects.select_related("listing", "buyer", "seller").get(pk=order.pk)
    return Response(OrderSerializer(order, context={"request": request}).data, status=http)


def guarded(fn):
    """Turns business rule errors into clear 4xx answers."""

    def wrapper(self, request, *args, **kwargs):
        try:
            return fn(self, request, *args, **kwargs)
        except InvalidTransition as exc:
            return error("invalid_state", str(exc), status.HTTP_409_CONFLICT)
        except OrderError as exc:
            return error("order_error", str(exc))

    return wrapper


class OrderCreate(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "payments"

    @guarded
    def post(self, request):
        listing = get_object_or_404(Listing, pk=request.data.get("listing_id") or 0)
        order = services.create_order(
            request.user,
            listing,
            request.data.get("delivery_mode", "meetup"),
            str(request.data.get("meetup_note", "")),
        )
        return respond(order, request, status.HTTP_201_CREATED)


class OrderDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get_order(self, request, pk) -> Order:
        order = get_object_or_404(Order, pk=pk)
        if not can_view(request.user, order):
            from django.http import Http404

            raise Http404
        return order

    def get(self, request, pk):
        order = services.refresh_payment(self.get_order(request, pk))  # settles a delayed payment
        return respond(order, request)

    @guarded
    def patch(self, request, pk):
        order = self.get_order(request, pk)
        if order.buyer_id != request.user.id:
            return error("forbidden", "Action réservée à l'acheteur.", status.HTTP_403_FORBIDDEN)
        services.update_details(
            order,
            request.user,
            request.data.get("delivery_mode", order.delivery_mode),
            str(request.data.get("meetup_note", order.meetup_note)),
        )
        return respond(order, request)


class OrderAction(APIView):
    """Shared plumbing for the buyer and seller actions."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "payments"

    def order_for(self, request, pk) -> Order:
        order = get_object_or_404(Order, pk=pk)
        if not can_view(request.user, order):
            from django.http import Http404

            raise Http404
        return order


class OrderPay(OrderAction):
    @guarded
    def post(self, request, pk):
        order = self.order_for(request, pk)
        if order.buyer_id != request.user.id:
            return error("forbidden", "Seul l'acheteur peut payer.", status.HTTP_403_FORBIDDEN)
        phone = normalize_phone(str(request.data.get("phone", "")))
        if not phone:
            return error(
                "invalid_phone",
                "Numéro invalide.",
                fields={
                    "phone": "Saisissez un numéro béninois valide, par exemple 01 97 00 00 00."
                },
            )
        key = request.headers.get("Idempotency-Key")
        order = services.start_payment(order, str(request.data.get("operator", "")), phone, key)
        return respond(order, request)


class OrderHandedOver(OrderAction):
    @guarded
    def post(self, request, pk):
        return respond(
            services.mark_handed_over(self.order_for(request, pk), request.user), request
        )


class OrderConfirm(OrderAction):
    @guarded
    def post(self, request, pk):
        return respond(services.buyer_confirm(self.order_for(request, pk), request.user), request)


class OrderDispute(OrderAction):
    @guarded
    def post(self, request, pk):
        order = services.open_dispute(
            self.order_for(request, pk), request.user, str(request.data.get("reason", ""))
        )
        return respond(order, request)


class OrderCancel(OrderAction):
    @guarded
    def post(self, request, pk):
        return respond(services.cancel(self.order_for(request, pk), request.user), request)


class MyOrders(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = user_orders(request.user).select_related("listing", "buyer", "seller")
        return Response(OrderSerializer(orders, many=True, context={"request": request}).data)


class Commission(APIView):
    """Shown to the seller before publishing: what the escrow costs on a given price."""

    permission_classes = [AllowAny]

    def get(self, request):
        try:
            price = int(request.query_params.get("price", 0))
        except ValueError:
            price = 0
        if price <= 0:
            return Response(
                {"commission_fcfa": 0, "payout_fcfa": 0, "pct": settings.ESCROW_COMMISSION_PCT}
            )
        commission = services.commission_for(price)
        return Response(
            {
                "commission_fcfa": commission,
                "payout_fcfa": price - commission,
                "pct": settings.ESCROW_COMMISSION_PCT,
                "minimum_fcfa": settings.ESCROW_COMMISSION_MIN_FCFA,
            }
        )


class Webhook(APIView):
    """Provider notifications: signature checked, then applied once whatever the retries."""

    permission_classes = [AllowAny]
    authentication_classes: list = []  # no session, so no CSRF: the signature is the proof

    def post(self, request, provider):
        if provider != "fedapay":
            return error("unknown_provider", "Fournisseur inconnu.", status.HTTP_404_NOT_FOUND)
        try:
            event = get_provider("fedapay").parse_webhook(request.headers, request.body)
        except InvalidSignature:
            return error("invalid_signature", "Signature invalide.", status.HTTP_401_UNAUTHORIZED)
        if event is not None:
            services.handle_webhook(event)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SimulatorSettle(APIView):
    """Development only: settles a simulated payment that was left pending (numbers ending 99)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not (settings.DEBUG and settings.PAYMENT_PROVIDER == "simulator"):
            return error("not_available", "Indisponible.", status.HTTP_404_NOT_FOUND)
        order = get_object_or_404(Order, pk=pk)
        if not can_view(request.user, order):
            return error("forbidden", "Accès refusé.", status.HTTP_403_FORBIDDEN)
        for tx in order.transactions.filter(direction="in", status=Transaction.Status.PENDING):
            tx.raw_payload = {**tx.raw_payload, "settled": True}
            tx.save(update_fields=["raw_payload", "updated_at"])
        return respond(services.refresh_payment(order), request)
