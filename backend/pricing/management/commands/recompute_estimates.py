"""Recompute estimates, price badges and usage scores of every live listing (run nightly)."""

from django.core.management.base import BaseCommand

from marketplace.models import Listing
from pricing.services import recompute_listing


class Command(BaseCommand):
    help = "Recompute estimates, price badges and usage scores of active listings."

    def handle(self, *args, **options):
        live = Listing.objects.filter(status__in=["active", "reserved", "pending_review"])
        count = 0
        for listing in live.select_related("device_model", "processor", "gpu").iterator():
            recompute_listing(listing)
            count += 1
        self.stdout.write(f"{count} annonces recalculées.")
