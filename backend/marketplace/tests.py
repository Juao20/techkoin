import io
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from accounts.models import Shop, User
from analytics.models import Event

from .models import Favorite, Listing, ListingPhoto

IMEI = "490154203237518"


def png(size=(800, 600), color=(200, 30, 30)) -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return SimpleUploadedFile("p.png", buf.getvalue(), content_type="image/png")


def make_user(email="u@example.com", phone="+2290197000010", **extra) -> User:
    return User.objects.create_user(
        username=email, email=email, phone=phone, password="x-y-z-12345", first_name="Awa", **extra
    )


@override_settings(MEDIA_ROOT="/tmp/techkoin-test-media")
class ListingFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalog", verbosity=0)

    def setUp(self):
        self.user = make_user(city="Cotonou")
        self.client.force_login(self.user)

    def draft(self, **extra):
        data = {
            "device_model": "apple-iphone-13",
            "condition_type": "used",
            "grade": "B",
            "price_fcfa": 350000,
            "storage_gb": 128,
            "battery_health_pct": 86,
            "account_removed": True,
            "imei_or_serial": IMEI,
            **extra,
        }
        r = self.client.post("/api/listings/", data, content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()

    def add_photos(self, listing_id, kinds=("front", "back", "screen_on", "other")):
        for kind in kinds:
            r = self.client.post(
                f"/api/listings/{listing_id}/photos/", {"image": png(), "kind": kind}
            )
            self.assertEqual(r.status_code, 201, r.content)

    def test_create_prefills_from_catalog_and_builds_title(self):
        d = self.draft()
        self.assertEqual(d["title"], "Apple iPhone 13 128 Go")
        self.assertEqual(d["category"], "smartphone")
        self.assertEqual(d["status"], "draft")
        self.assertEqual(d["city"], "Cotonou")

    def test_imei_is_never_exposed_and_encrypted_in_db(self):
        d = self.draft()
        self.assertNotIn(IMEI, json.dumps(d))
        self.assertTrue(d["has_imei"])
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute("SELECT imei_or_serial FROM marketplace_listing")
            raw = cur.fetchone()[0]
        self.assertNotIn(IMEI, raw)
        self.assertEqual(Listing.objects.get().imei_or_serial, IMEI)

    def test_publish_requires_photos(self):
        d = self.draft()
        r = self.client.post(f"/api/listings/{d['id']}/publish/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("photos", r.json()["fields"])

    def test_publish_requires_screen_on_photo(self):
        d = self.draft()
        self.add_photos(d["id"], ("front", "back", "other", "other"))
        r = self.client.post(f"/api/listings/{d['id']}/publish/")
        self.assertIn("écran allumé", r.json()["fields"]["photos"])

    def test_grade_c_requires_defect_photo(self):
        d = self.draft(grade="C")
        self.add_photos(d["id"])
        r = self.client.post(f"/api/listings/{d['id']}/publish/")
        self.assertIn("défaut", r.json()["fields"]["photos"])
        self.add_photos(d["id"], ("defect",))
        self.assertEqual(self.client.post(f"/api/listings/{d['id']}/publish/").status_code, 200)

    def test_icloud_locked_device_is_refused(self):
        d = self.draft(account_removed=False)
        self.add_photos(d["id"])
        r = self.client.post(f"/api/listings/{d['id']}/publish/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("iCloud", r.json()["fields"]["account_removed"])

    def test_publish_goes_active_for_catalog_model(self):
        d = self.draft()
        self.add_photos(d["id"])
        r = self.client.post(f"/api/listings/{d['id']}/publish/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["status"], "active")

    def test_custom_model_goes_to_review(self):
        brand = "tecno"
        d = self.draft(
            device_model=None, brand=brand, custom_model_name="Zoom 9", category="smartphone"
        )
        self.add_photos(d["id"])
        r = self.client.post(f"/api/listings/{d['id']}/publish/")
        self.assertEqual(r.json()["status"], "pending_review")

    def test_particulier_limited_to_five_active(self):
        for _ in range(5):
            d = self.draft()
            self.add_photos(d["id"])
            self.assertEqual(self.client.post(f"/api/listings/{d['id']}/publish/").status_code, 200)
        d = self.draft()
        self.add_photos(d["id"])
        r = self.client.post(f"/api/listings/{d['id']}/publish/")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["code"], "limit_reached")

    def test_shop_has_no_limit(self):
        boutique = make_user(
            "b@example.com", "+2290197000011", account_type="boutique", city="Cotonou"
        )
        Shop.objects.create(owner=boutique, name="Boutique", slug="boutique")
        self.client.force_login(boutique)
        for _ in range(6):
            d = self.draft()
            self.add_photos(d["id"])
            self.assertEqual(self.client.post(f"/api/listings/{d['id']}/publish/").status_code, 200)

    def test_cannot_edit_someone_elses_listing(self):
        d = self.draft()
        other = make_user("o@example.com", "+2290197000012")
        self.client.force_login(other)
        r = self.client.patch(
            f"/api/listings/{d['id']}/", {"price_fcfa": 1}, content_type="application/json"
        )
        self.assertEqual(r.status_code, 404)

    def test_photo_pipeline_outputs_webp_and_limits_size(self):
        d = self.draft()
        self.add_photos(d["id"], ("front",))
        photo = ListingPhoto.objects.get()
        with Image.open(photo.image.path) as img:
            self.assertEqual(img.format, "WEBP")
        big = png(size=(3000, 2000))
        r = self.client.post(f"/api/listings/{d['id']}/photos/", {"image": big, "kind": "back"})
        self.assertEqual(r.status_code, 201)
        with Image.open(ListingPhoto.objects.get(kind="back").image.path) as img:
            self.assertLessEqual(max(img.size), 1600)
        self.assertTrue(ListingPhoto.objects.first().phash)

    def test_non_image_upload_rejected(self):
        d = self.draft()
        bad = SimpleUploadedFile("x.png", b"not an image", content_type="image/png")
        r = self.client.post(f"/api/listings/{d['id']}/photos/", {"image": bad, "kind": "front"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "invalid_photo")


@override_settings(MEDIA_ROOT="/tmp/techkoin-test-media")
class SearchAndContactTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalog", verbosity=0)
        cls.seller = make_user("s@example.com", "+2290197000020", city="Cotonou")
        cls.shop_user = make_user("sh@example.com", "+2290197000021", account_type="boutique")
        cls.shop = Shop.objects.create(
            owner=cls.shop_user,
            name="Tech Shop",
            slug="tech-shop",
            verification_status="verified",
            whatsapp_number="+2290197000099",
        )
        from catalog.models import DeviceModel

        def listing(slug, model, price, city="Cotonou", seller=None, shop=None, **kw):
            dm = DeviceModel.objects.get(slug=model)
            created = Listing.objects.create(
                seller=seller or cls.seller,
                shop=shop,
                device_model=dm,
                brand=dm.brand,
                category=dm.category,
                title=dm.name,
                slug=slug,
                price_fcfa=price,
                city=city,
                status="active",
                condition_type="used",
                grade="B",
                processor=dm.default_processor,
                search_text=f"{dm.brand.name} {dm.name} {' '.join(dm.aliases)}".lower(),
                **kw,
            )
            return created

        cls.a = listing("iphone-13-a", "apple-iphone-13", 350000, storage_gb=128, warranty_months=0)
        cls.b = listing(
            "iphone-12-b",
            "apple-iphone-12",
            250000,
            city="Abomey-Calavi",
            storage_gb=64,
            warranty_months=6,
            has_invoice=True,
        )
        cls.c = listing(
            "thinkpad-c",
            "lenovo-thinkpad-t14-gen-2",
            450000,
            city="Parakou",
            seller=cls.shop_user,
            shop=cls.shop,
            ram_gb=16,
            storage_gb=512,
            storage_type="ssd",
            keyboard_layout="azerty",
        )

    def ids(self, query):
        r = self.client.get(f"/api/listings/?{query}")
        self.assertEqual(r.status_code, 200)
        return {x["slug"] for x in r.json()["results"]}

    def test_text_search_with_alias(self):
        self.assertEqual(self.ids("q=ip13"), {"iphone-13-a"})

    def test_filters(self):
        self.assertEqual(self.ids("category=laptop"), {"thinkpad-c"})
        self.assertEqual(self.ids("price_max=300000"), {"iphone-12-b"})
        self.assertEqual(self.ids("price_min=300000&price_max=400000"), {"iphone-13-a"})
        self.assertEqual(self.ids("warranty=1"), {"iphone-12-b"})
        self.assertEqual(self.ids("invoice=1"), {"iphone-12-b"})
        self.assertEqual(self.ids("seller_type=shop"), {"thinkpad-c"})
        self.assertEqual(self.ids("seller_type=individual"), {"iphone-13-a", "iphone-12-b"})
        self.assertEqual(self.ids("verified=1"), {"thinkpad-c"})
        self.assertEqual(self.ids("storage_min=256&storage_type=ssd"), {"thinkpad-c"})
        self.assertEqual(self.ids("ram_min=16&keyboard=azerty"), {"thinkpad-c"})
        self.assertEqual(self.ids("brand=lenovo"), {"thinkpad-c"})
        self.assertEqual(self.ids("condition=new_sealed"), set())
        self.assertEqual(self.ids("grade=a,b"), {"iphone-13-a", "iphone-12-b", "thinkpad-c"})

    def test_combined_filters(self):
        self.assertEqual(
            self.ids("category=smartphone&price_max=300000&warranty=1"), {"iphone-12-b"}
        )

    def test_city_shows_chosen_city_first_then_nearby(self):
        r = self.client.get("/api/listings/?city=cotonou&sort=recent").json()["results"]
        self.assertEqual([x["slug"] for x in r], ["iphone-13-a", "iphone-12-b"])
        self.assertNotIn("thinkpad-c", [x["slug"] for x in r])

    def test_sorts(self):
        r = self.client.get("/api/listings/?sort=price_asc").json()["results"]
        self.assertEqual([x["price_fcfa"] for x in r], [250000, 350000, 450000])
        r = self.client.get("/api/listings/?sort=price_desc").json()["results"]
        self.assertEqual([x["price_fcfa"] for x in r], [450000, 350000, 250000])

    def test_best_deal_only_lists_reliable_estimates(self):
        Listing.objects.filter(slug="iphone-13-a").update(
            estimate_mid=400000, price_badge="good_deal"
        )
        Listing.objects.filter(slug="iphone-12-b").update(estimate_mid=260000, price_badge="fair")
        r = self.client.get("/api/listings/?sort=best_deal").json()["results"]
        self.assertEqual([x["slug"] for x in r], ["iphone-13-a", "iphone-12-b"])

    def test_pagination_size(self):
        r = self.client.get("/api/listings/").json()
        self.assertEqual(r["count"], 3)

    def test_search_events_recorded(self):
        self.client.get("/api/listings/?q=iphone")
        self.client.get("/api/listings/?q=zzzzzz")
        self.assertEqual(Event.objects.filter(type="search").count(), 1)
        self.assertEqual(Event.objects.filter(type="search_no_result").count(), 1)

    def test_no_event_without_query(self):
        self.client.get("/api/listings/")
        self.assertEqual(Event.objects.count(), 0)

    def test_public_payload_never_contains_private_data(self):
        body = json.dumps(self.client.get("/api/listings/iphone-13-a/").json())
        for forbidden in ("imei_or_serial", IMEI, "+2290197000020", "s@example.com"):
            self.assertNotIn(forbidden, body.lower())

    def test_view_counted_once_per_session_window(self):
        self.client.get("/api/listings/iphone-13-a/")
        self.client.get("/api/listings/iphone-13-a/")
        self.assertEqual(Listing.objects.get(slug="iphone-13-a").views_count, 1)
        self.assertEqual(Event.objects.filter(type="listing_view").count(), 1)

    def test_phone_reveal_requires_login_and_is_recorded(self):
        pk = self.c.pk
        self.assertEqual(self.client.post(f"/api/listings/{pk}/reveal-phone/").status_code, 403)
        buyer = make_user("buyer@example.com", "+2290197000030")
        self.client.force_login(buyer)
        r = self.client.post(f"/api/listings/{pk}/reveal-phone/")
        self.assertEqual(r.json()["phone"], "+2290197000099")
        self.assertEqual(Event.objects.filter(type="phone_reveal").count(), 1)
        self.assertEqual(Listing.objects.get(pk=pk).contacts_count, 1)

    def test_whatsapp_link(self):
        buyer = make_user("buyer@example.com", "+2290197000030")
        self.client.force_login(buyer)
        r = self.client.post(f"/api/listings/{self.c.pk}/whatsapp/")
        self.assertTrue(r.json()["url"].startswith("https://wa.me/2290197000099?text="))

    def test_favorites(self):
        buyer = make_user("buyer@example.com", "+2290197000030")
        self.client.force_login(buyer)
        pk = self.a.pk
        self.assertEqual(self.client.post(f"/api/listings/{pk}/favorite/").status_code, 201)
        self.client.post(f"/api/listings/{pk}/favorite/")
        self.assertEqual(Favorite.objects.count(), 1)
        self.assertEqual(Listing.objects.get(pk=pk).favorites_count, 1)
        self.assertEqual(len(self.client.get("/api/me/favorites/").json()), 1)
        flagged = self.client.get("/api/listings/").json()["results"]
        self.assertTrue(next(x for x in flagged if x["id"] == pk)["favorited"])
        self.assertEqual(self.client.delete(f"/api/listings/{pk}/favorite/").status_code, 204)
        self.assertEqual(Listing.objects.get(pk=pk).favorites_count, 0)

    def test_shop_storefront(self):
        d = self.client.get("/api/shops/tech-shop/").json()
        self.assertTrue(d["verified"])
        self.assertEqual(d["active_listings"], 1)
        r = self.client.get("/api/shops/tech-shop/listings/").json()
        self.assertEqual([x["slug"] for x in r["results"]], ["thinkpad-c"])

    def test_similar_excludes_self_and_respects_price_band(self):
        r = self.client.get("/api/listings/iphone-13-a/similar/").json()
        self.assertEqual(r, [])
        Listing.objects.filter(slug="iphone-12-b").update(price_fcfa=330000)
        r = self.client.get("/api/listings/iphone-13-a/similar/").json()
        self.assertEqual([x["slug"] for x in r], ["iphone-12-b"])
