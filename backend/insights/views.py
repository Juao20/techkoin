"""Endpoints of the shop analysis (spec 13, « Pro »).

P1 to P3 are open to every shop but a Free shop only receives the first element of each module
(a real, limited preview). P4 to P7 are Pro only: `IsProShop` answers 403 to anyone else. The
front end displays what it gets; it never decides who may see what.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import HasShop, IsProShop
from ai.throttles import FeatureThrottle
from marketplace import services
from marketplace.models import Listing
from pricing.estimate import round_price
from pricing.services import recompute_listing

from . import bulk, chat, competition, demand, dormant, pricing_advice, reports
from .models import WeeklyReport


def error(code: str, message: str, http=status.HTTP_400_BAD_REQUEST, fields=None):
    body = {"code": code, "message": message}
    if fields:
        body["fields"] = fields
    return Response(body, status=http)


def limited(shop, rows: list) -> tuple[list, dict]:
    """Pro: everything. Free: the first element only, and how much is hidden."""
    if shop.is_pro:
        return rows, {"preview": False, "total": len(rows), "hidden": 0}
    return rows[:1], {"preview": True, "total": len(rows), "hidden": max(len(rows) - 1, 0)}


def period_arg(request, allowed=(7, 30), default=7) -> int:
    try:
        value = int(request.query_params.get("period", default))
    except ValueError:
        return default
    return value if value in allowed else default


class InsightView(APIView):
    permission_classes = [HasShop]
    throttle_classes = [FeatureThrottle]
    ai_feature = "insights"


class Demand(InsightView):
    """P1."""

    def get(self, request):
        shop = request.shop
        days = period_arg(request)
        result = demand.radar(shop, days)
        rows, meta = limited(shop, result["rows"])
        body = {"period": days, "min_searches": result["min_searches"], "rows": rows, **meta}
        if shop.is_pro:
            body["recommendations"], body["used_ai"] = demand.recommendations(shop, result["rows"])
        return Response(body)


class Pricing(InsightView):
    """P2."""

    def get(self, request):
        shop = request.shop
        items = pricing_advice.rows(shop)
        if shop.is_pro:
            items, used_ai = pricing_advice.with_notes(shop, items)
            rows, meta = items, {"preview": False, "total": len(items), "hidden": 0}
        else:
            rows, meta = limited(shop, items)
            for row in rows:
                row["note"] = pricing_advice._fallback_note(row)
            used_ai = False
        return Response({"rows": rows, "used_ai": used_ai, **meta})


class Dormant(InsightView):
    """P3."""

    def get(self, request):
        shop = request.shop
        pro = shop.is_pro
        result = dormant.diagnose(shop, 30, with_fixes=pro, use_model=pro)
        rows, meta = limited(shop, result["rows"])
        return Response(
            {"min_days": result["min_days"], "rows": rows, "used_ai": result["used_ai"], **meta}
        )


class ApplyListing(APIView):
    """« Appliquer ce prix » / « Appliquer » on a correction: price, title and description."""

    permission_classes = [IsProShop]

    def post(self, request, listing_id):
        listing = get_object_or_404(
            Listing, pk=listing_id, shop=request.shop, status=Listing.Status.ACTIVE
        )
        changed = []
        if "price_fcfa" in request.data:
            try:
                price = int(request.data["price_fcfa"])
            except (TypeError, ValueError):
                price = 0
            if price <= 0 or price > 100_000_000:
                return error(
                    "invalid_price", "Prix invalide.", fields={"price_fcfa": "Prix invalide."}
                )
            price = round_price(price)
            if price != listing.price_fcfa:
                listing.price_fcfa = price
                listing.last_price_change_at = timezone.now()
                changed.append("price")
        if "title" in request.data:
            title = str(request.data["title"]).strip()
            if not title or len(title) > 120:
                return error(
                    "invalid_title", "Titre invalide.", fields={"title": "1 à 120 caractères."}
                )
            listing.title = title
            listing.moderation_flags = {**listing.moderation_flags, "auto_title": False}
            changed.append("title")
        if "description" in request.data:
            listing.description = str(request.data["description"]).strip()
            changed.append("description")
        if not changed:
            return error("nothing_to_apply", "Rien à appliquer.")
        recompute_listing(listing, save=False)
        services.refresh_search_text(listing)
        listing.save()
        return Response({"id": listing.pk, "price_fcfa": listing.price_fcfa, "changed": changed})


class ReportList(APIView):
    """P4: the weekly reports, newest first."""

    permission_classes = [IsProShop]

    def get(self, request):
        items = WeeklyReport.objects.filter(shop=request.shop)[:26]
        return Response(
            {
                "results": [
                    {
                        "id": r.pk,
                        "period_start": r.period_start,
                        "period_end": r.period_end,
                        "summary": r.summary,
                        "emailed_at": r.emailed_at,
                    }
                    for r in items
                ]
            }
        )

    def post(self, request):
        """« Générer le rapport maintenant »: same content as Monday's, without the e-mail."""
        report = reports.build(request.shop)
        return Response(report_body(report), status=status.HTTP_201_CREATED)


def report_body(report: WeeklyReport) -> dict:
    return {
        "id": report.pk,
        "period_start": report.period_start,
        "period_end": report.period_end,
        "summary": report.summary,
        "actions": report.actions,
        "figures": report.figures,
        "used_ai": report.used_ai,
        "emailed_at": report.emailed_at,
    }


class ReportDetail(APIView):
    permission_classes = [IsProShop]

    def get(self, request, pk):
        return Response(report_body(get_object_or_404(WeeklyReport, pk=pk, shop=request.shop)))


class Chat(APIView):
    """P5."""

    permission_classes = [IsProShop]
    throttle_classes = [FeatureThrottle]
    ai_feature = "insights_chat"

    def post(self, request):
        question = str(request.data.get("question", "")).strip()
        if len(question) < 3:
            return error("empty_question", "Posez votre question.")
        return Response(chat.answer(request.shop, question))


class BulkOptimize(APIView):
    """P6, step 1: proposals only, nothing is written."""

    permission_classes = [IsProShop]
    throttle_classes = [FeatureThrottle]
    ai_feature = "insights_bulk"

    def post(self, request):
        try:
            return Response({"items": bulk.propose(request.shop, request.data.get("listing_ids"))})
        except bulk.BulkError as exc:
            return error("invalid_selection", str(exc))


class BulkApply(APIView):
    """P6, step 2: writes the proposals the shop accepted."""

    permission_classes = [IsProShop]

    def post(self, request):
        try:
            done = bulk.apply(request.shop, request.data.get("items"))
        except bulk.BulkError as exc:
            return error("invalid_selection", str(exc))
        return Response({"applied": done})


class Competition(APIView):
    """P7."""

    permission_classes = [IsProShop]
    throttle_classes = [FeatureThrottle]
    ai_feature = "insights"

    def get(self, request, listing_id):
        listing = get_object_or_404(
            Listing.objects.select_related("shop", "device_model").prefetch_related("photos"),
            pk=listing_id,
            shop=request.shop,
            status=Listing.Status.ACTIVE,
        )
        return Response(competition.analyse(request.shop, listing))
