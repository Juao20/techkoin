"""Scheduled every 15 minutes: tell users about new listings that match their saved searches."""

from django.core.management.base import BaseCommand

from marketplace.alerts import run_alerts


class Command(BaseCommand):
    help = "Send the notifications and e-mails of the search alerts."

    def handle(self, *args, **options):
        result = run_alerts()
        self.stdout.write(
            f"{result['alerts']} alerte(s) examinee(s), {result['notified']} notifiee(s)."
        )
