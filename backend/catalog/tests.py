from django.core.management import call_command
from django.test import TestCase

from .models import DeviceModel


class CatalogApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalog", verbosity=0)

    def test_catalog_size_and_idempotence(self):
        count = DeviceModel.objects.count()
        self.assertGreaterEqual(count, 150)
        self.assertLessEqual(count, 200)
        call_command("seed_catalog", verbosity=0)
        self.assertEqual(DeviceModel.objects.count(), count)

    def test_autocomplete_matches_aliases(self):
        r = self.client.get("/api/catalog/models/?q=ip13")
        slugs = [m["slug"] for m in r.json()]
        self.assertIn("apple-iphone-13", slugs)

    def test_autocomplete_limited_to_ten(self):
        r = self.client.get("/api/catalog/models/?q=galaxy")
        self.assertLessEqual(len(r.json()), 10)

    def test_detail_has_default_specs(self):
        data = self.client.get("/api/catalog/models/apple-iphone-13/").json()
        self.assertEqual(data["default_processor"]["name"], "Apple A15 Bionic")
        self.assertIn(128, data["storage_options_gb"])

    def test_brands_filtered_by_category(self):
        names = [b["name"] for b in self.client.get("/api/catalog/brands/?category=tablet").json()]
        self.assertIn("Apple", names)
        self.assertNotIn("Tecno", names)

    def test_cities(self):
        names = [c["name"] for c in self.client.get("/api/catalog/cities/").json()]
        self.assertEqual(names[0], "Cotonou")
        self.assertEqual(len(names), 12)
