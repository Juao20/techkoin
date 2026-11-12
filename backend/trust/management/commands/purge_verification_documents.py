"""Delete identity and business documents 90 days after the verification decision."""

from django.core.management.base import BaseCommand

from trust.services import purge_old_documents


class Command(BaseCommand):
    help = "Delete verification documents whose decision is older than 90 days."

    def handle(self, *args, **options):
        self.stdout.write(f"{purge_old_documents()} dossier(s) purgé(s).")
