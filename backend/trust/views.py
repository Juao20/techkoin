from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Shop, User

from .imei import hash_identifier, normalize
from .models import StolenDeviceReport

MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
ALLOWED_DOCUMENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


def error(code: str, message: str, http=status.HTTP_400_BAD_REQUEST, fields=None):
    body = {"code": code, "message": message}
    if fields:
        body["fields"] = fields
    return Response(body, status=http)


def check_document(upload) -> str | None:
    if upload is None:
        return "Ajoutez le document demandé."
    if upload.size > MAX_DOCUMENT_BYTES:
        return "Ce fichier dépasse 8 Mo."
    if upload.content_type not in ALLOWED_DOCUMENT_TYPES:
        return "Envoyez une photo (JPEG, PNG, WebP) ou un PDF."
    return None


class StolenReportSerializer(serializers.Serializer):
    imei_or_serial = serializers.CharField(max_length=40)
    description = serializers.CharField(max_length=2000)
    police_reference = serializers.CharField(max_length=80, required=False, allow_blank=True)

    def validate_imei_or_serial(self, value):
        if len(normalize(value)) < 6:
            raise serializers.ValidationError("Saisissez l'IMEI ou le numéro de série complet.")
        return value


class StolenReportView(APIView):
    """Public declaration. It only counts once a moderator confirms it."""

    permission_classes = [AllowAny]
    throttle_scope = "report"

    def post(self, request):
        s = StolenReportSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        StolenDeviceReport.objects.create(
            imei_or_serial_hash=hash_identifier(d["imei_or_serial"]),
            reporter=request.user if request.user.is_authenticated else None,
            description=d["description"],
            police_reference=d.get("police_reference", ""),
        )
        return Response(
            {"message": "Merci. Notre équipe vérifie votre déclaration."},
            status=status.HTTP_201_CREATED,
        )


class IdentityVerificationView(APIView):
    """ID document and selfie, reviewed by a moderator (spec 8.1)."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "upload"

    def post(self, request):
        user = request.user
        if user.identity_status == User.VerificationStatus.VERIFIED:
            return error("already_verified", "Votre identité est déjà vérifiée.")
        problems = {}
        for field in ("document", "selfie"):
            message = check_document(request.FILES.get(field))
            if message:
                problems[field] = message
        if problems:
            return error("invalid_documents", "Documents incomplets.", fields=problems)
        user.identity_document = request.FILES["document"]
        user.identity_selfie = request.FILES["selfie"]
        user.identity_status = User.VerificationStatus.PENDING
        user.identity_decided_at = None
        user.save()
        return Response({"identity_status": user.identity_status}, status=status.HTTP_201_CREATED)


class ShopVerificationView(APIView):
    """IFU, RCCM and address, reviewed by a moderator."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "upload"

    def post(self, request):
        shop = Shop.objects.filter(owner=request.user).first()
        if shop is None:
            return error("no_shop", "Ce compte n'a pas de boutique.", status.HTTP_404_NOT_FOUND)
        if shop.is_verified:
            return error("already_verified", "Votre boutique est déjà vérifiée.")
        ifu = str(request.data.get("ifu", "")).strip()
        rccm = str(request.data.get("rccm", "")).strip()
        address = str(request.data.get("address", shop.address)).strip()
        problems = {}
        if not ifu:
            problems["ifu"] = "Indiquez le numéro IFU."
        if not rccm:
            problems["rccm"] = "Indiquez le numéro RCCM."
        if not address:
            problems["address"] = "Indiquez l'adresse de la boutique."
        message = check_document(request.FILES.get("document"))
        if message:
            problems["document"] = message
        if problems:
            return error("invalid_documents", "Dossier incomplet.", fields=problems)
        shop.ifu, shop.rccm, shop.address = ifu, rccm, address
        shop.verification_document = request.FILES["document"]
        shop.verification_status = User.VerificationStatus.PENDING
        shop.verification_decided_at = None
        shop.save()
        return Response(
            {"verification_status": shop.verification_status}, status=status.HTTP_201_CREATED
        )


PRIVATE_FIELDS = {
    "identity": (User, "identity_document"),
    "selfie": (User, "identity_selfie"),
    "shop-document": (Shop, "verification_document"),
}


def private_file(request, kind: str, pk: int):
    """Moderators only: private documents are never reachable through the media URL."""
    if not (request.user.is_authenticated and (request.user.is_moderator or request.user.is_staff)):
        raise Http404
    if kind not in PRIVATE_FIELDS:
        raise Http404
    model, field = PRIVATE_FIELDS[kind]
    file = getattr(get_object_or_404(model, pk=pk), field)
    if not file:
        raise Http404
    return FileResponse(file.open("rb"))
