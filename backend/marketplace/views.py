from urllib.parse import quote

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.models import Event
from analytics.tracking import track

from . import services
from .models import Favorite, Listing, ListingPhoto
from .photos import InvalidPhoto, process_upload
from .search import PAGE_SIZE, search_listings
from .serializers import (
    ListingCardSerializer,
    ListingDetailSerializer,
    ListingWriteSerializer,
    PhotoSerializer,
)


class ListingPagination(PageNumberPagination):
    page_size = PAGE_SIZE


def error(code: str, message: str, http=status.HTTP_400_BAD_REQUEST, fields=None):
    body = {"code": code, "message": message}
    if fields:
        body["fields"] = fields
    return Response(body, status=http)


def favorite_ids(request) -> set[int]:
    if request.user.is_authenticated:
        return set(Favorite.objects.filter(user=request.user).values_list("listing_id", flat=True))
    return set()


def ctx(request):
    return {"request": request, "favorite_ids": favorite_ids(request)}


def own_listing(request, pk) -> Listing:
    return get_object_or_404(Listing, pk=pk, seller=request.user)


class ListingList(APIView):
    """GET: public search. POST: create a draft."""

    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "POST" else [AllowAny()]

    def get(self, request):
        qs = search_listings(request.query_params)
        paginator = ListingPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        data = ListingCardSerializer(page, many=True, context=ctx(request)).data
        searched = {k for k in request.query_params if k not in {"page", "sort"}}
        if searched and request.query_params.get("page", "1") == "1":
            kind = (
                Event.Type.SEARCH if paginator.page.paginator.count else Event.Type.SEARCH_NO_RESULT
            )
            track(
                kind,
                request,
                query_text=request.query_params.get("q", "")[:200],
                filters={k: v for k, v in request.query_params.items() if k != "page"},
                results_count=paginator.page.paginator.count,
                city=request.query_params.get("city", ""),
            )
        return paginator.get_paginated_response(data)

    def post(self, request):
        serializer = ListingWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        shop = getattr(user, "shop", None)
        listing = serializer.save(
            seller=user,
            shop=shop,
            city=serializer.validated_data.get("city") or user.city,
            quartier=serializer.validated_data.get("quartier") or user.quartier,
        )
        _finalize(listing)
        return Response(ListingDetailSerializer(listing, context=ctx(request)).data, status=201)


def _finalize(listing: Listing) -> None:
    """Keep derived fields (title, slug, search text, invoice flag) in sync after a save."""
    if not listing.title or listing.moderation_flags.get("auto_title", True):
        listing.title = services.build_title(listing) or listing.title
    listing.has_invoice = "invoice" in (listing.accessories or [])
    from pricing.services import recompute_listing
    from trust.imei import hash_identifier

    listing.imei_hash = hash_identifier(listing.imei_or_serial)
    recompute_listing(listing, save=False)
    services.refresh_search_text(listing)
    listing.slug = services.unique_slug(listing)
    listing.save()


class ListingBySlug(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        listing = get_object_or_404(
            Listing.objects.select_related("brand", "shop", "seller", "processor", "gpu"),
            slug=slug,
            status__in=[Listing.Status.ACTIVE, Listing.Status.RESERVED, Listing.Status.SOLD],
        )
        event = track(Event.Type.LISTING_VIEW, request, listing=listing)
        if event:
            Listing.objects.filter(pk=listing.pk).update(views_count=F("views_count") + 1)
            listing.views_count += 1
        return Response(ListingDetailSerializer(listing, context=ctx(request)).data)


class ListingById(APIView):
    """Owner access by id: read (any status), update."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        return Response(
            ListingDetailSerializer(own_listing(request, pk), context=ctx(request)).data
        )

    def patch(self, request, pk):
        listing = own_listing(request, pk)
        if listing.status in (Listing.Status.SOLD, Listing.Status.RESERVED):
            return error(
                "locked", "Cette annonce ne peut plus être modifiée.", status.HTTP_409_CONFLICT
            )
        old_price = listing.price_fcfa
        serializer = ListingWriteSerializer(listing, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        listing = serializer.save()
        if "title" in request.data:
            listing.moderation_flags = {**listing.moderation_flags, "auto_title": False}
        if listing.price_fcfa != old_price and listing.status != Listing.Status.DRAFT:
            listing.last_price_change_at = timezone.now()
        _finalize(listing)
        return Response(ListingDetailSerializer(listing, context=ctx(request)).data)


class PhotoUpload(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = "upload"

    def post(self, request, pk):
        listing = own_listing(request, pk)
        upload = request.FILES.get("image")
        if upload is None:
            return error("missing_image", "Choisissez une photo à envoyer.")
        if listing.photos.count() >= services.MAX_PHOTOS:
            return error(
                "too_many_photos", f"Vous pouvez ajouter {services.MAX_PHOTOS} photos au maximum."
            )
        kind = request.data.get("kind", ListingPhoto.Kind.OTHER)
        if kind not in ListingPhoto.Kind.values:
            return error("invalid_kind", "Type de photo inconnu.")
        try:
            image, thumb, phash = process_upload(upload)
        except InvalidPhoto as exc:
            return error("invalid_photo", str(exc))
        photo = ListingPhoto(
            listing=listing, kind=kind, phash=phash, position=listing.photos.count()
        )
        photo.image.save(f"{listing.pk}.webp", image, save=False)
        photo.thumb.save(f"{listing.pk}.webp", thumb, save=False)
        photo.save()
        return Response(PhotoSerializer(photo, context={"request": request}).data, status=201)


class PhotoDelete(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, photo_id):
        listing = own_listing(request, pk)
        photo = get_object_or_404(ListingPhoto, pk=photo_id, listing=listing)
        photo.image.delete(save=False)
        photo.thumb.delete(save=False)
        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class Publish(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "publish"

    @transaction.atomic
    def post(self, request, pk):
        listing = own_listing(request, pk)
        if listing.status not in (
            Listing.Status.DRAFT,
            Listing.Status.REJECTED,
            Listing.Status.ARCHIVED,
        ):
            return error("not_draft", "Cette annonce est déjà publiée.", status.HTTP_409_CONFLICT)
        errors = services.validate_for_publish(listing)
        if errors:
            return error("invalid_listing", "L'annonce est incomplète.", fields=errors)
        is_particulier = listing.shop_id is None
        if (
            is_particulier
            and services.active_count(request.user) >= services.ACTIVE_LIMIT_PARTICULIER
        ):
            return error(
                "limit_reached",
                f"Vous avez déjà {services.ACTIVE_LIMIT_PARTICULIER} annonces actives. "
                "Archivez ou marquez une annonce comme vendue pour en publier une nouvelle.",
                status.HTTP_403_FORBIDDEN,
            )
        listing = services.publish(listing)
        return Response(ListingDetailSerializer(listing, context=ctx(request)).data)


class MarkSold(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        listing = own_listing(request, pk)
        listing.status = Listing.Status.SOLD
        listing.sold_at = timezone.now()
        listing.save(update_fields=["status", "sold_at", "updated_at"])
        return Response(ListingDetailSerializer(listing, context=ctx(request)).data)


class Archive(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        listing = own_listing(request, pk)
        listing.status = Listing.Status.ARCHIVED
        listing.save(update_fields=["status", "updated_at"])
        return Response(ListingDetailSerializer(listing, context=ctx(request)).data)


def contact_number(listing: Listing) -> str:
    if listing.shop and listing.shop.whatsapp_number:
        return listing.shop.whatsapp_number
    return listing.seller.whatsapp_number or listing.seller.phone or ""


class RevealPhone(APIView):
    """The number is only returned after an authenticated click, and every reveal is recorded."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "reveal"

    def post(self, request, pk):
        listing = get_object_or_404(Listing, pk=pk, status=Listing.Status.ACTIVE)
        track(Event.Type.PHONE_REVEAL, request, listing=listing)
        Listing.objects.filter(pk=listing.pk).update(contacts_count=F("contacts_count") + 1)
        return Response({"phone": contact_number(listing)})


class WhatsAppLink(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "reveal"

    def post(self, request, pk):
        listing = get_object_or_404(Listing, pk=pk, status=Listing.Status.ACTIVE)
        number = contact_number(listing).lstrip("+")
        message = (
            f"Bonjour, votre annonce « {listing.title} » sur TechKoin "
            "est-elle toujours disponible ?"
        )
        track(Event.Type.WHATSAPP_CLICK, request, listing=listing)
        Listing.objects.filter(pk=listing.pk).update(contacts_count=F("contacts_count") + 1)
        return Response({"url": f"https://wa.me/{number}?text={quote(message)}"})


class FavoriteToggle(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        listing = get_object_or_404(Listing, pk=pk, status=Listing.Status.ACTIVE)
        _, created = Favorite.objects.get_or_create(user=request.user, listing=listing)
        if created:
            Listing.objects.filter(pk=pk).update(favorites_count=F("favorites_count") + 1)
            track(Event.Type.FAVORITE_ADD, request, listing=listing)
        return Response({"favorited": True}, status=status.HTTP_201_CREATED if created else 200)

    def delete(self, request, pk):
        deleted, _ = Favorite.objects.filter(user=request.user, listing_id=pk).delete()
        if deleted:
            Listing.objects.filter(pk=pk, favorites_count__gt=0).update(
                favorites_count=F("favorites_count") - 1
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class Similar(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        base = get_object_or_404(Listing, slug=slug)
        qs = (
            Listing.objects.filter(
                status=Listing.Status.ACTIVE,
                category=base.category,
                price_fcfa__gte=int(base.price_fcfa * 0.8),
                price_fcfa__lte=int(base.price_fcfa * 1.2),
            )
            .exclude(pk=base.pk)
            .select_related("brand", "shop", "seller", "processor")
            .prefetch_related("photos")
            .order_by("-published_at")[:6]
        )
        return Response(ListingCardSerializer(qs, many=True, context=ctx(request)).data)


class MyListings(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            Listing.objects.filter(seller=request.user)
            .select_related("brand", "shop", "seller", "processor")
            .prefetch_related("photos")
            .order_by("-updated_at")
        )
        return Response(ListingCardSerializer(qs, many=True, context=ctx(request)).data)


class MyFavorites(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            Listing.objects.filter(favorited_by__user=request.user)
            .select_related("brand", "shop", "seller", "processor")
            .prefetch_related("photos")
            .order_by("-favorited_by__created_at")
        )
        return Response(ListingCardSerializer(qs, many=True, context=ctx(request)).data)


class ShopDetail(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        from accounts.models import Shop

        shop = get_object_or_404(Shop, slug=slug)
        return Response(
            {
                "name": shop.name,
                "slug": shop.slug,
                "logo": request.build_absolute_uri(shop.logo.url) if shop.logo else None,
                "description": shop.description,
                "address": shop.address,
                "city": shop.city,
                "quartier": shop.quartier,
                "opening_hours": shop.opening_hours,
                "verified": shop.is_verified,
                "member_since": shop.created_at.date().isoformat(),
                "active_listings": shop.listings.filter(status=Listing.Status.ACTIVE).count(),
                "sold_count": shop.listings.filter(status=Listing.Status.SOLD).count(),
            }
        )


class ShopListings(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        params = request.query_params.copy()
        qs = search_listings(params).filter(shop__slug=slug)
        paginator = ListingPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            ListingCardSerializer(page, many=True, context=ctx(request)).data
        )
