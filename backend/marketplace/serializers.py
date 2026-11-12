from rest_framework import serializers

from catalog.models import Brand, Category, DeviceModel, GraphicsCard, Processor

from .models import Listing, ListingPhoto
from .services import specs_line


class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingPhoto
        fields = ["id", "image", "thumb", "kind", "position"]


def seller_info(listing: Listing) -> dict:
    shop = listing.shop
    if shop:
        return {
            "type": "shop",
            "name": shop.name,
            "slug": shop.slug,
            "verified": shop.is_verified,
            "city": shop.city,
            "member_since": shop.created_at.date().isoformat(),
        }
    user = listing.seller
    last = f" {user.last_name[:1]}." if user.last_name else ""
    return {
        "type": "individual",
        "name": f"{user.first_name}{last}".strip() or "Vendeur",
        "slug": None,
        "verified": user.identity_status == "verified",
        "city": user.city,
        "member_since": user.date_joined.date().isoformat(),
    }


class ListingCardSerializer(serializers.ModelSerializer):
    """Compact representation used in result grids. Never contains contact data or IMEI."""

    brand = serializers.CharField(source="brand.name", default="")
    specs = serializers.SerializerMethodField()
    thumb = serializers.SerializerMethodField()
    seller_verified = serializers.SerializerMethodField()
    shop_name = serializers.CharField(source="shop.name", default=None)
    favorited = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "slug",
            "title",
            "category",
            "brand",
            "price_fcfa",
            "negotiable",
            "price_badge",
            "condition_type",
            "grade",
            "city",
            "specs",
            "thumb",
            "keyboard_layout",
            "warranty_months",
            "has_invoice",
            "seller_verified",
            "shop_name",
            "published_at",
            "status",
            "favorited",
        ]

    def get_specs(self, obj):
        return specs_line(obj)

    def get_thumb(self, obj):
        photos = list(obj.photos.all())
        front = next((p for p in photos if p.kind == "front"), photos[0] if photos else None)
        if not front:
            return None
        request = self.context.get("request")
        url = front.thumb.url
        return request.build_absolute_uri(url) if request else url

    def get_seller_verified(self, obj):
        return seller_info(obj)["verified"]

    def get_favorited(self, obj):
        return obj.id in self.context.get("favorite_ids", set())


class ListingDetailSerializer(ListingCardSerializer):
    photos = PhotoSerializer(many=True, read_only=True)
    seller = serializers.SerializerMethodField()
    processor = serializers.SerializerMethodField()
    gpu = serializers.CharField(source="gpu.name", default=None)
    model_slug = serializers.CharField(source="device_model.slug", default=None)
    has_imei = serializers.SerializerMethodField()
    advised_usage = serializers.SerializerMethodField()
    estimate_indicative = serializers.SerializerMethodField()

    class Meta(ListingCardSerializer.Meta):
        fields = ListingCardSerializer.Meta.fields + [
            "photos",
            "seller",
            "description",
            "quartier",
            "accessories",
            "provenance",
            "model_slug",
            "has_imei",
            "ram_gb",
            "storage_gb",
            "storage_type",
            "color",
            "screen_size_in",
            "screen_resolution",
            "refresh_rate_hz",
            "processor",
            "gpu",
            "gpu_dedicated",
            "vram_gb",
            "touchscreen",
            "os",
            "keyboard_backlit",
            "battery_cycles",
            "battery_autonomy_h",
            "ports",
            "ram_upgradable",
            "battery_health_pct",
            "network_5g",
            "dual_sim",
            "esim",
            "carrier_unlocked",
            "account_removed",
            "biometrics_ok",
            "screen_original",
            "replaced_parts",
            "cellular",
            "stylus_included",
            "keyboard_included",
            "estimate_low",
            "estimate_mid",
            "estimate_high",
            "usage_scores",
            "advised_usage",
            "estimate_indicative",
            "views_count",
            "favorites_count",
            "rejection_reason",
        ]

    def get_seller(self, obj):
        return seller_info(obj)

    def get_processor(self, obj):
        p = obj.processor
        return {"name": p.name, "family": p.family, "generation": p.generation} if p else None

    def get_advised_usage(self, obj):
        from pricing.usage import advised_usage

        return advised_usage(obj.usage_scores)

    def get_estimate_indicative(self, obj):
        return bool(obj.moderation_flags.get("estimate_indicative", True))

    def get_has_imei(self, obj):
        return bool(obj.imei_or_serial)


class ListingWriteSerializer(serializers.ModelSerializer):
    device_model = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=DeviceModel.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    brand = serializers.SlugRelatedField(
        slug_field="slug", queryset=Brand.objects.all(), required=False, allow_null=True
    )
    processor = serializers.PrimaryKeyRelatedField(
        queryset=Processor.objects.all(), required=False, allow_null=True
    )
    gpu = serializers.PrimaryKeyRelatedField(
        queryset=GraphicsCard.objects.all(), required=False, allow_null=True
    )
    imei_or_serial = serializers.CharField(write_only=True, required=False, allow_blank=True)
    category = serializers.ChoiceField(choices=Category.choices, required=False)

    class Meta:
        model = Listing
        fields = [
            "category",
            "device_model",
            "custom_model_name",
            "brand",
            "title",
            "description",
            "condition_type",
            "grade",
            "price_fcfa",
            "negotiable",
            "city",
            "quartier",
            "accessories",
            "warranty_months",
            "provenance",
            "imei_or_serial",
            "ram_gb",
            "storage_gb",
            "storage_type",
            "color",
            "screen_size_in",
            "screen_resolution",
            "refresh_rate_hz",
            "processor",
            "gpu",
            "gpu_dedicated",
            "vram_gb",
            "touchscreen",
            "os",
            "keyboard_layout",
            "keyboard_backlit",
            "battery_cycles",
            "battery_autonomy_h",
            "ports",
            "ram_upgradable",
            "battery_health_pct",
            "network_5g",
            "dual_sim",
            "esim",
            "carrier_unlocked",
            "account_removed",
            "biometrics_ok",
            "screen_original",
            "replaced_parts",
            "cellular",
            "stylus_included",
            "keyboard_included",
        ]

    def validate_price_fcfa(self, value):
        if value > 100_000_000:
            raise serializers.ValidationError("Ce prix semble trop élevé. Vérifiez le montant.")
        return value

    def validate_warranty_months(self, value):
        if value not in (0, 1, 3, 6, 12):
            raise serializers.ValidationError("Choisissez 0, 1, 3, 6 ou 12 mois.")
        return value

    def validate_accessories(self, value):
        allowed = {"charger", "box", "cable", "case", "earphones", "invoice"}
        if not isinstance(value, list) or not set(value) <= allowed:
            raise serializers.ValidationError("Accessoire inconnu.")
        return value

    def validate_battery_health_pct(self, value):
        if value is not None and not 1 <= value <= 100:
            raise serializers.ValidationError("Indiquez un pourcentage entre 1 et 100.")
        return value

    def validate(self, attrs):
        grade = attrs.get("grade", getattr(self.instance, "grade", ""))
        condition = attrs.get("condition_type", getattr(self.instance, "condition_type", "used"))
        if condition in ("new_sealed", "new_open") and grade:
            attrs["grade"] = ""
        model = attrs.get("device_model")
        if model:
            attrs.setdefault("brand", model.brand)
            attrs["category"] = model.category
            attrs["custom_model_name"] = ""
        if self.instance is None and not attrs.get("category"):
            raise serializers.ValidationError(
                {"category": "Choisissez une catégorie ou un modèle du catalogue."}
            )
        return attrs
