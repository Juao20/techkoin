from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers

from .models import Shop
from .phone import normalize_phone

User = get_user_model()


def unique_shop_slug(name: str) -> str:
    base = slugify(name) or "boutique"
    slug, n = base, 2
    while Shop.objects.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class ShopSerializer(serializers.ModelSerializer):
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = Shop
        fields = [
            "name",
            "slug",
            "logo",
            "description",
            "address",
            "city",
            "quartier",
            "opening_hours",
            "whatsapp_number",
            "is_verified",
            "verification_status",
            "plan",
        ]
        read_only_fields = ["slug", "plan", "is_verified", "verification_status"]


class UserSerializer(serializers.ModelSerializer):
    shop = ShopSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "whatsapp_number",
            "first_name",
            "last_name",
            "account_type",
            "city",
            "quartier",
            "identity_status",
            "is_moderator",
            "shop",
        ]
        read_only_fields = ["id", "email", "account_type", "identity_status", "is_moderator"]

    def validate_phone(self, value):
        phone = normalize_phone(value)
        if not phone:
            raise serializers.ValidationError(
                "Saisissez un numéro béninois valide, par exemple 01 97 00 00 00."
            )
        if User.objects.filter(phone=phone).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Ce numéro est déjà utilisé.")
        return phone

    def validate_whatsapp_number(self, value):
        if not value:
            return ""
        phone = normalize_phone(value)
        if not phone:
            raise serializers.ValidationError("Saisissez un numéro WhatsApp béninois valide.")
        return phone


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=60)
    last_name = serializers.CharField(max_length=60, required=False, allow_blank=True)
    account_type = serializers.ChoiceField(choices=User.AccountType.choices)
    city = serializers.CharField(max_length=80, required=False, allow_blank=True)
    shop_name = serializers.CharField(max_length=120, required=False, allow_blank=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Cette adresse e-mail est déjà utilisée.")
        return value

    def validate_phone(self, value):
        phone = normalize_phone(value)
        if not phone:
            raise serializers.ValidationError(
                "Saisissez un numéro béninois valide, par exemple 01 97 00 00 00."
            )
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("Ce numéro est déjà utilisé.")
        return phone

    def validate_password(self, value):
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def validate(self, attrs):
        if attrs["account_type"] == User.AccountType.BOUTIQUE and not attrs.get("shop_name"):
            raise serializers.ValidationError(
                {"shop_name": "Indiquez le nom de votre boutique pour continuer."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated):
        shop_name = validated.pop("shop_name", "")
        password = validated.pop("password")
        user = User(username=validated["email"], **validated)
        user.whatsapp_number = user.phone
        user.set_password(password)
        user.save()
        if user.account_type == User.AccountType.BOUTIQUE:
            Shop.objects.create(
                owner=user,
                name=shop_name,
                slug=unique_shop_slug(shop_name),
                city=user.city,
                whatsapp_number=user.phone,
            )
        return user
