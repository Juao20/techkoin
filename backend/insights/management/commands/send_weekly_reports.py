"""Every Monday at 8:00 (Africa/Porto-Novo): build and e-mail the weekly report of each Pro shop."""

from django.core.management.base import BaseCommand

from insights.reports import run_weekly


class Command(BaseCommand):
    help = "Build the weekly report of every Pro shop and e-mail it to its owner."

    def handle(self, *args, **options):
        result = run_weekly()
        self.stdout.write(
            f"{result['reports']} rapport(s), {result['emails']} e-mail(s) envoyé(s)."
        )
