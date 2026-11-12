from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import DeviceModel

from .estimate import estimate, price_badge


class EstimateRequest(serializers.Serializer):
    device_model = serializers.SlugRelatedField(
        slug_field="slug", queryset=DeviceModel.objects.filter(is_active=True)
    )
    storage_gb = serializers.IntegerField(required=False, allow_null=True)
    ram_gb = serializers.IntegerField(required=False, allow_null=True)
    condition_type = serializers.CharField(required=False, default="used")
    grade = serializers.CharField(required=False, allow_blank=True, default="")
    battery_health_pct = serializers.IntegerField(required=False, allow_null=True)
    replaced_parts = serializers.ListField(child=serializers.CharField(), required=False)
    city = serializers.CharField(required=False, allow_blank=True, default="")
    price_fcfa = serializers.IntegerField(required=False, min_value=0, default=0)


class EstimateView(APIView):
    """Live estimate shown while publishing. Public: it reveals no listing, only aggregates."""

    permission_classes = [AllowAny]
    throttle_scope = "estimate"

    def post(self, request):
        s = EstimateRequest(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        est = estimate(
            d["device_model"],
            storage_gb=d.get("storage_gb"),
            ram_gb=d.get("ram_gb"),
            condition_type=d["condition_type"],
            grade=d["grade"],
            battery_health_pct=d.get("battery_health_pct"),
            replaced_parts=d.get("replaced_parts"),
            city=d["city"],
        )
        if est is None:
            return Response({"available": False})
        return Response(
            {
                "available": True,
                "low": est.low,
                "mid": est.mid,
                "high": est.high,
                "sample_size": est.sample_size,
                "indicative": est.indicative,
                "badge": price_badge(d["price_fcfa"], est),
            }
        )
