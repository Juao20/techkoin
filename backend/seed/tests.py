import pytest
from django.core.management import call_command

from accounts.models import Shop, User
from analytics.models import Event
from marketplace.models import Listing, ListingPhoto
from marketplace.services import validate_for_publish


@pytest.mark.django_db
def test_seed_demo_creates_publishable_listings_and_is_idempotent():
    call_command("seed_catalog")
    call_command("seed_demo", listings=12, days=3)

    assert Shop.objects.count() == 8
    assert User.objects.filter(email="boutique.pro@demo.techkoin.test").exists()
    assert Listing.objects.count() == 12 + 5  # plus the suspicious ones
    assert ListingPhoto.objects.count() >= 12 * 4
    assert Event.objects.exists()
    # Active listings respect the same rules as listings published through the API.
    for listing in Listing.objects.filter(status="active"):
        assert validate_for_publish(listing) == {}
    # The 5 suspicious listings wait in the moderation queue.
    queue = Listing.objects.filter(status="pending_review")
    assert queue.count() == 5
    stolen = queue.get(imei_status="reported_stolen")  # blocked and handled first
    assert stolen.moderation_flags["priority"] is True and stolen.risk_score == 100
    assert all(listing.risk_score >= 40 for listing in queue)

    users_before = User.objects.count()
    call_command("seed_demo", listings=12, days=3)
    assert User.objects.count() == users_before

    call_command("seed_demo", listings=12, days=3, reset=True)
    assert User.objects.count() == users_before
    assert Listing.objects.count() == 12 + 5  # plus the suspicious ones
