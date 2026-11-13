"""Automatic release after the buyer's silence, and expiry of unpaid orders (every 15 minutes)."""

from django.core.management.base import BaseCommand

from payments.services import release_due_orders


class Command(BaseCommand):
    help = "Release escrow funds whose delay has passed and cancel unpaid orders."

    def handle(self, *args, **options):
        result = release_due_orders()
        self.stdout.write(f"{result['released']} libérée(s), {result['expired']} expirée(s).")
