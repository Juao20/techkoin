from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import HasShop
from marketplace.models import Listing

from . import stats
from .models import Event
from .tracking import track

# Events the front end may report itself (the rest is recorded server side).
FRONT_EVENTS = {
    Event.Type.WHATSAPP_CLICK,
    Event.Type.COMPARE,
    Event.Type.CONTACT_CLICK,
    Event.Type.CHECKOUT_START,
}


class ShopStatsView(APIView):
    """GET shop/stats?period=7|30|90: open to every shop, Free or Pro (spec 11)."""

    permission_classes = [HasShop]

    def get(self, request):
        return Response(
            stats.shop_stats(request.shop, stats.parse_period(request.query_params.get("period")))
        )


class EventView(APIView):
    throttle_scope = "events"

    def post(self, request):
        etype = request.data.get("type")
        if etype not in FRONT_EVENTS:
            return Response(
                {"code": "invalid_event", "message": "Type d'événement non autorisé."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        listing = None
        if request.data.get("listing"):
            listing = Listing.objects.filter(pk=request.data["listing"]).first()
        track(etype, request, listing=listing, metadata=request.data.get("metadata") or {})
        return Response(status=status.HTTP_204_NO_CONTENT)
