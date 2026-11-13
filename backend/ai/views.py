from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.models import Event
from analytics.tracking import track

from . import client, search
from .throttles import FeatureThrottle


class SearchView(APIView):
    """F1, « Recherche intelligente »."""

    permission_classes = [AllowAny]
    throttle_classes = [FeatureThrottle]
    ai_feature = "search"

    def post(self, request):
        query = str(request.data.get("query", "")).strip()
        if len(query) < 2:
            return Response(
                {"code": "empty_query", "message": "Décrivez ce que vous cherchez."}, status=400
            )
        user = request.user if request.user.is_authenticated else None
        result = search.run(query, user=user)
        track(
            Event.Type.AI_SEARCH,
            request,
            query_text=result["query"],
            filters=result["filters"],
        )
        return Response(result)


class AIStatus(APIView):
    """Tells the front end which features run on the model and which on fallbacks."""

    permission_classes = [AllowAny]

    def get(self, request):
        live = client.has_key()
        return Response({"model_available": live, "voice_available": live})
