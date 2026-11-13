"""Scheduled every 15 minutes: escrow releases, expired unpaid orders, ended Pro subscriptions."""

from django.core.management.base import BaseCommand

from payments.services import release_due_orders
from payments.subscriptions import expire_due


class Command(BaseCommand):
    help = "Release escrow funds whose delay has passed, cancel unpaid orders, end Pro periods."

    def handle(self, *args, **options):
        result = release_due_orders()
        ended = expire_due()
        self.stdout.write(
            f"{result['released']} libérée(s), {result['expired']} expirée(s), "
            f"{ended} abonnement(s) terminé(s)."
        )
