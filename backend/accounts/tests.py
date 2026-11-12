from django.test import TestCase

from .models import Shop, User
from .phone import normalize_phone


class PhoneTests(TestCase):
    def test_normalizes_common_formats(self):
        for raw in (
            "+229 01 97 00 00 00",
            "0197000000",
            "229 0197000000",
            "97000000",
            "00229 01 97 00 00 00",
        ):
            self.assertEqual(normalize_phone(raw), "+2290197000000", raw)

    def test_rejects_invalid(self):
        for raw in ("", "123", "+33 6 12 34 56 78", "0297000000"):
            self.assertIsNone(normalize_phone(raw), raw)


class AuthApiTests(TestCase):
    payload = {
        "email": "awa@example.com",
        "phone": "01 97 00 00 01",
        "password": "Un-mot-de-passe-solide-42",
        "first_name": "Awa",
        "account_type": "particulier",
        "city": "Cotonou",
    }

    def test_register_logs_in_and_stores_e164(self):
        r = self.client.post("/api/auth/register/", self.payload, content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(User.objects.get().phone, "+2290197000001")
        me = self.client.get("/api/auth/me/").json()
        self.assertEqual(me["user"]["email"], "awa@example.com")

    def test_boutique_registration_creates_shop(self):
        data = {**self.payload, "account_type": "boutique", "shop_name": "Tech Calavi"}
        r = self.client.post("/api/auth/register/", data, content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Shop.objects.get().slug, "tech-calavi")

    def test_boutique_requires_shop_name(self):
        data = {**self.payload, "account_type": "boutique"}
        r = self.client.post("/api/auth/register/", data, content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_login_with_email_or_phone(self):
        self.client.post("/api/auth/register/", self.payload, content_type="application/json")
        self.client.post("/api/auth/logout/")
        for identifier in ("awa@example.com", "0197000001"):
            r = self.client.post(
                "/api/auth/login/",
                {"identifier": identifier, "password": self.payload["password"]},
                content_type="application/json",
            )
            self.assertEqual(r.status_code, 200, identifier)
            self.client.post("/api/auth/logout/")

    def test_wrong_password_is_rejected(self):
        self.client.post("/api/auth/register/", self.payload, content_type="application/json")
        self.client.post("/api/auth/logout/")
        r = self.client.post(
            "/api/auth/login/",
            {"identifier": "awa@example.com", "password": "mauvais"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "invalid_credentials")

    def test_duplicate_email_rejected(self):
        self.client.post("/api/auth/register/", self.payload, content_type="application/json")
        r = self.client.post(
            "/api/auth/register/",
            {**self.payload, "phone": "01 97 00 00 02"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
