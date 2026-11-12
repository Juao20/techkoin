from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from accounts.models import User
from catalog.models import DeviceModel
from marketplace import services
from marketplace.models import Listing, ListingPhoto

from . import risk
from .imei import hash_identifier, luhn_valid, validate_identifier
from .models import StolenDeviceReport

GOOD_IMEI = "490154203237518"
OTHER_IMEI = "356938035643809"


@pytest.fixture
def catalog(db):
    call_command("seed_catalog", verbosity=0)


def make_seller(n=1, old=True):
    user = User.objects.create_user(
        username=f"s{n}", email=f"s{n}@example.com", password="x-y-z-12345", city="Cotonou"
    )
    if old:
        User.objects.filter(pk=user.pk).update(date_joined=timezone.now() - timedelta(days=90))
    return User.objects.get(pk=user.pk)


def make_listing(seller, imei=GOOD_IMEI, **extra):
    model = DeviceModel.objects.get(slug="apple-iphone-13")
    fields = dict(
        seller=seller,
        device_model=model,
        category="smartphone",
        brand=model.brand,
        condition_type="used",
        grade="B",
        price_fcfa=300_000,
        storage_gb=128,
        city="Cotonou",
        account_removed=True,
        imei_or_serial=imei,
        imei_hash=hash_identifier(imei),
        status="draft",
        slug=f"l-{Listing.objects.count()}",
        title="Apple iPhone 13 128 Go",
    )
    fields.update(extra)
    return Listing.objects.create(**fields)


def add_comparables(n=6, price=300_000):
    seller = make_seller(99)
    for i in range(n):
        make_listing(seller, imei=f"35{i:013d}", status="active", price_fcfa=price)


def test_luhn_and_identifier_validation():
    assert luhn_valid(GOOD_IMEI)
    assert not luhn_valid("490154203237519")
    assert validate_identifier(GOOD_IMEI, "smartphone") is None
    assert validate_identifier("490 154 203 237 518", "smartphone") is None
    assert "invalide" in validate_identifier("490154203237519", "smartphone")
    assert "15 chiffres" in validate_identifier("12345", "smartphone")
    assert validate_identifier("", "smartphone")
    # Laptops and tablets accept a serial number in the brand's format.
    assert validate_identifier("C02XL0ABJGH5", "laptop", "apple") is None
    assert validate_identifier("12", "laptop", "apple")
    assert validate_identifier("ABC1234", "laptop", "dell") is None


def test_hash_ignores_formatting(db):
    assert hash_identifier("490 154-203237518") == hash_identifier(GOOD_IMEI)
    assert hash_identifier("") == ""


def test_text_rules():
    assert risk.has_contact_info("Appelez le 01 97 55 44 33")
    assert risk.has_contact_info("ecrivez moi sur wa.me/22997554433")
    assert risk.has_contact_info("mon mail: vendeur@example.com")
    assert not risk.has_contact_info("iPhone 13 128 Go, 16 Go de RAM, batterie 86 %")
    assert risk.has_risky_phrase("Envoyez d'abord un acompte")
    assert risk.has_risky_phrase("PAIEMENT AVANT la remise")  # case insensitive
    assert risk.has_risky_phrase("frais de réservation à payer")  # accent insensitive
    assert not risk.has_risky_phrase("Appareil en bon état, rencontre possible à Cotonou")


def test_clean_listing_goes_online(catalog):
    add_comparables()
    listing = make_listing(make_seller(1))
    services.publish(listing)
    listing.refresh_from_db()
    assert listing.status == "active"
    assert listing.risk_score == 0
    assert listing.imei_status == "ok"
    assert listing.estimate_mid == 300_000 and listing.price_badge == "fair"


def test_price_far_below_market_adds_35_points(catalog):
    add_comparables()
    listing = make_listing(make_seller(1), price_fcfa=120_000)
    services.publish(listing)
    listing.refresh_from_db()
    assert listing.moderation_flags["risk_rules"] == {"price_too_low": 35}
    assert listing.status == "active"  # 35 alone stays under the review threshold


def test_scam_text_and_contact_send_to_moderation(catalog):
    listing = make_listing(
        make_seller(1), description="Envoie d'abord l'argent. Appelle le 01 97 55 44 33"
    )
    services.publish(listing)
    listing.refresh_from_db()
    assert listing.status == "pending_review"
    assert listing.risk_score == 50
    assert set(listing.moderation_flags["risk_rules"]) == {"risky_phrase", "contact_in_text"}


def test_duplicate_imei_from_another_seller_goes_to_review(catalog):
    first = make_listing(make_seller(1))
    services.publish(first)
    second = make_listing(make_seller(2))
    services.publish(second)
    second.refresh_from_db()
    assert second.imei_status == "duplicate"
    assert second.status == "pending_review"
    assert second.moderation_flags["risk_rules"]["duplicate_imei"] == 40


def test_same_imei_by_the_same_seller_is_not_a_duplicate(catalog):
    seller = make_seller(1)
    services.publish(make_listing(seller))
    again = make_listing(seller)
    services.publish(again)
    again.refresh_from_db()
    assert again.imei_status == "ok"


def test_confirmed_stolen_device_is_never_visible(catalog):
    StolenDeviceReport.objects.create(
        imei_or_serial_hash=hash_identifier(GOOD_IMEI),
        description="Volé",
        status=StolenDeviceReport.Status.CONFIRMED,
    )
    listing = make_listing(make_seller(1))
    services.publish(listing)
    listing.refresh_from_db()
    assert listing.imei_status == "reported_stolen"
    assert listing.status == "pending_review"
    assert listing.risk_score == 100 and listing.moderation_flags["priority"] is True


def test_pending_stolen_report_does_not_block(catalog):
    StolenDeviceReport.objects.create(
        imei_or_serial_hash=hash_identifier(GOOD_IMEI), description="Peut-être volé"
    )
    listing = make_listing(make_seller(1))
    services.publish(listing)
    listing.refresh_from_db()
    assert listing.status == "active"


def test_same_photo_as_another_seller_adds_40_points(catalog):
    other = make_listing(make_seller(1), imei=OTHER_IMEI, status="active")
    ListingPhoto.objects.create(listing=other, image="a.webp", thumb="a.webp", phash="ab12cd34")
    mine = make_listing(make_seller(2))
    ListingPhoto.objects.create(listing=mine, image="b.webp", thumb="b.webp", phash="ab12cd34")
    services.publish(mine)
    mine.refresh_from_db()
    assert mine.moderation_flags["risk_rules"]["duplicate_photo"] == 40
    assert mine.status == "pending_review"


def test_new_account_with_three_listings_adds_15_points(catalog):
    seller = make_seller(1, old=False)
    for i in range(2):
        make_listing(seller, imei=f"35{i:013d}", status="active")
    listing = make_listing(seller)
    services.publish(listing)
    listing.refresh_from_db()
    assert listing.moderation_flags["risk_rules"] == {"new_account_many_listings": 15}


def test_custom_model_always_waits_for_review(catalog):
    seller = make_seller(1)
    listing = make_listing(seller)
    Listing.objects.filter(pk=listing.pk).update(device_model=None, custom_model_name="Spark Go")
    listing.refresh_from_db()
    services.publish(listing)
    listing.refresh_from_db()
    assert listing.status == "pending_review"
    assert listing.moderation_flags["risk_rules"] == {"custom_model": 10}


def test_invalid_imei_blocks_publication_with_a_field_error(catalog):
    listing = make_listing(make_seller(1), imei="490154203237519")
    assert "imei_or_serial" in services.validate_for_publish(listing)
