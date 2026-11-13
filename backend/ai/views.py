from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import client


class AIStatus(APIView):
    """Tells the front end which features run on the model and which on fallbacks."""

    permission_classes = [AllowAny]

    def get(self, request):
        live = client.has_key()
        return Response({"model_available": live, "voice_available": live})
