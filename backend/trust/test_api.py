from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone

from accounts.models import Shop, User
from marketplace.models import ListingReport

from .imei import hash_identifier
from .models import StolenDeviceReport
from .services import decide_identity, decide_shop, purge_old_documents
from .tests import GOOD_IMEI, make_listing, make_moderator, make_seller


@pytest.fixture(autouse=True)
def private_media(settings, tmp_path):
    settings.PRIVATE_MEDIA_ROOT = tmp_path / "private"


def doc(name="id.jpg", content_type="image/jpeg", size=2000):
    return SimpleUploadedFile(name, b"x" * size, content_type=content_type)


def test_three_different_reporters_send_a_listing_back_to_moderation(db, client):
    call_command("seed_catalog", verbosity=0)
    listing = make_listing(make_seller(1), status="active")
    for n in range(2, 5):
        client.force_login(make_seller(n))
        r = client.post(
            f"/api/listings/{listing.pk}/report/",
            {"reason": "scam", "details": "Prix suspect"},
            content_type="application/json",
        )
        assert r.status_code == 201
        listing.refresh_from_db()
        assert listing.status == ("pending_review" if n == 4 else "active")
    assert listing.moderation_flags["reported"] == 3


def test_report_rules(db, client):
    call_command("seed_catalog", verbosity=0)
    seller = make_seller(1)
    listing = make_listing(seller, status="active")
    post = lambda body: client.post(  # noqa: E731
        f"/api/listings/{listing.pk}/report/", body, content_type="application/json"
    )
    assert post({"reason": "scam"}).status_code in (401, 403)  # login required
    client.force_login(seller)
    assert post({"reason": "scam"}).status_code == 400  # not your own listing
    client.force_login(make_seller(2))
    assert post({"reason": "nope"}).status_code == 400
    assert post({"reason": "scam"}).status_code == 201
    assert post({"reason": "scam"}).status_code == 200  # same user twice counts once
    assert ListingReport.objects.count() == 1


def test_stolen_report_is_public_and_stores_only_a_hash(db, client):
    r = client.post(
        "/api/stolen-reports/",
        {"imei_or_serial": GOOD_IMEI, "description": "Volé hier", "police_reference": "PV-1"},
        content_type="application/json",
    )
    assert r.status_code == 201
    report = StolenDeviceReport.objects.get()
    assert report.status == "pending"
    assert report.imei_or_serial_hash == hash_identifier(GOOD_IMEI)
    assert GOOD_IMEI not in str(report.__dict__)
    bad = client.post(
        "/api/stolen-reports/",
        {"imei_or_serial": "12", "description": "x"},
        content_type="application/json",
    )
    assert bad.status_code == 400


def test_identity_verification_flow(db, client):
    user = make_seller(1)
    client.force_login(user)
    incomplete = client.post("/api/me/identity/", {"document": doc()})
    assert incomplete.status_code == 400 and "selfie" in incomplete.json()["fields"]
    wrong = client.post(
        "/api/me/identity/", {"document": doc(), "selfie": doc("s.exe", "application/x-msdownload")}
    )
    assert wrong.status_code == 400
    ok = client.post("/api/me/identity/", {"document": doc(), "selfie": doc("s.jpg")})
    assert ok.status_code == 201
    user.refresh_from_db()
    assert user.identity_status == "pending"
    decide_identity(user, True)
    user.refresh_from_db()
    assert user.identity_status == "verified" and user.identity_decided_at


def test_documents_are_private(db, client, settings):
    user = make_seller(1)
    client.force_login(user)
    client.post("/api/me/identity/", {"document": doc(), "selfie": doc("s.jpg")})
    user.refresh_from_db()
    assert not user.identity_document.storage.base_url  # no public URL
    assert not (settings.MEDIA_ROOT / user.identity_document.name).exists()  # not under /media
    assert (settings.PRIVATE_MEDIA_ROOT / user.identity_document.name).exists()
    # An ordinary user cannot read the file, a moderator can.
    assert client.get(f"/api/private-files/identity/{user.pk}/").status_code == 404
    client.force_login(make_moderator())
    r = client.get(f"/api/private-files/identity/{user.pk}/")
    assert r.status_code == 200 and b"".join(r.streaming_content).startswith(b"xxx")


def test_shop_verification_flow(db, client):
    owner = User.objects.create_user(
        username="o", email="o@example.com", password="x-y-z-12345", account_type="boutique"
    )
    shop = Shop.objects.create(owner=owner, name="Boutique Test", slug="boutique-test")
    client.force_login(owner)
    missing = client.post("/api/shop/verification/", {"ifu": "123"})
    assert missing.status_code == 400
    assert {"rccm", "address", "document"} <= set(missing.json()["fields"])
    ok = client.post(
        "/api/shop/verification/",
        {
            "ifu": "3202012345678",
            "rccm": "RB/COT/20 B 1234",
            "address": "Haie Vive",
            "document": doc(),
        },
    )
    assert ok.status_code == 201
    shop.refresh_from_db()
    assert shop.verification_status == "pending" and not shop.is_verified
    decide_shop(shop, True)
    shop.refresh_from_db()
    assert shop.is_verified


def test_documents_are_deleted_90_days_after_the_decision(db, client):
    user = make_seller(1)
    client.force_login(user)
    client.post("/api/me/identity/", {"document": doc(), "selfie": doc("s.jpg")})
    user.refresh_from_db()
    decide_identity(user, True)
    assert purge_old_documents() == 0  # too recent
    User.objects.filter(pk=user.pk).update(identity_decided_at=timezone.now() - timedelta(days=91))
    assert purge_old_documents() == 1
    user.refresh_from_db()
    assert not user.identity_document and not user.identity_selfie
    assert user.identity_status == "verified"  # the decision is kept
