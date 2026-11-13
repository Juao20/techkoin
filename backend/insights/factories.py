"""Small builders shared by the phase 5 tests (shops, listings, simulated events)."""

from datetime import timedelta

from django.utils import timezone

from accounts.models import Shop, User
from analytics.models import Event
from catalog.models import DeviceModel
from marketplace import services
from marketplace.models import Listing


def make_shop(n=1, plan="pro", city="Cotonou"):
    owner = User.objects.create_user(
        username=f"shop{n}",
        email=f"shop{n}@t.test",
        password="x-y-z-12345",
        account_type="boutique",
        city=city,
    )
    return Shop.objects.create(
        owner=owner, name=f"Boutique {n}", slug=f"boutique-{n}", plan=plan, city=city
    )


def add_listing(shop, model_slug="apple-iphone-13", price=300_000, **extra):
    model = DeviceModel.objects.get(slug=model_slug)
    n = Listing.objects.count()
    fields = dict(
        seller=shop.owner,
        shop=shop,
        device_model=model,
        category=model.category,
        brand=model.brand,
        condition_type="used",
        grade="B",
        price_fcfa=price,
        storage_gb=128,
        city=shop.city,
        status="active",
        title=f"{model.name} {n}",
        slug=f"annonce-{n}",
        published_at=timezone.now() - timedelta(days=extra.pop("days_online", 5)),
    )
    fields.update(extra)
    listing = Listing.objects.create(**fields)
    services.refresh_search_text(listing)  # what the real search matches against
    listing.save(update_fields=["search_text"])
    return listing


def add_events(kind, n, days_ago=1, **fields):
    """n events of a type, all dated `days_ago` days back."""
    when = timezone.now() - timedelta(days=days_ago)
    events = [Event(type=kind, **fields) for _ in range(n)]
    created = Event.objects.bulk_create(events)
    Event.objects.filter(pk__in=[e.pk for e in created]).update(created_at=when)
    return created
