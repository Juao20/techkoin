from django.contrib.auth import authenticate, login, logout
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Shop
from .serializers import RegisterSerializer, ShopSerializer, UserSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user, backend="accounts.backends.EmailOrPhoneBackend")
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        identifier = request.data.get("identifier", "")
        password = request.data.get("password", "")
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            return Response(
                {
                    "code": "invalid_credentials",
                    "message": (
                        "Identifiants incorrects. "
                        "Vérifiez votre e-mail ou numéro et votre mot de passe."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """GET: current user or null. PATCH: update own profile."""

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"user": None})
        return Response({"user": UserSerializer(request.user).data})

    def patch(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"code": "not_authenticated", "message": "Connectez-vous pour continuer."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"user": serializer.data})


class ShopView(APIView):
    """GET/PATCH the shop of the logged-in boutique account."""

    permission_classes = [IsAuthenticated]

    def _shop(self, request):
        return Shop.objects.filter(owner=request.user).first()

    def get(self, request):
        shop = self._shop(request)
        if not shop:
            return Response(
                {"code": "no_shop", "message": "Ce compte n'a pas de boutique."}, status=404
            )
        return Response(ShopSerializer(shop).data)

    def patch(self, request):
        shop = self._shop(request)
        if not shop:
            return Response(
                {"code": "no_shop", "message": "Ce compte n'a pas de boutique."}, status=404
            )
        serializer = ShopSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
