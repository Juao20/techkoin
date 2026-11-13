from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.models import Event
from analytics.tracking import track
from marketplace.models import Listing

from . import client, describe, search, voice
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


class DescribeView(APIView):
    """F2, « Rédaction assistée »: the seller reviews the text before using it."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [FeatureThrottle]
    ai_feature = "describe"

    def post(self, request):
        listing = get_object_or_404(
            Listing, pk=request.data.get("listing_id") or 0, seller=request.user
        )
        return Response(describe.run(listing, user=request.user))


class VoiceView(APIView):
    """F3, « Dictée »: audio up to 60 s, deleted once transcribed."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [FeatureThrottle]
    parser_classes = [MultiPartParser]
    ai_feature = "voice"

    def post(self, request):
        upload = request.FILES.get("audio")
        if upload is None:
            return Response({"code": "missing_audio", "message": "Aucun enregistrement reçu."}, 400)
        if upload.size > voice.MAX_BYTES or float(request.data.get("duration", 0) or 0) > (
            voice.MAX_SECONDS + 1
        ):
            return Response(
                {"code": "too_long", "message": "L'enregistrement dure 60 secondes au maximum."},
                400,
            )
        if not (upload.content_type or "").startswith(("audio/", "video/webm")):
            return Response({"code": "invalid_audio", "message": "Format audio non reconnu."}, 400)
        data = upload.read()
        return Response(
            voice.run(data, upload.name or "audio.webm", upload.content_type, user=request.user)
        )


class AIStatus(APIView):
    """Tells the front end which features run on the model and which on fallbacks."""

    permission_classes = [AllowAny]

    def get(self, request):
        live = client.has_key()
        return Response({"model_available": live, "voice_available": live})
