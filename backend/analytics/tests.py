from django.test import TestCase

from .models import Event
from .tracking import track


class TrackingTests(TestCase):
    def test_bot_is_ignored(self):
        r = self.client.get("/api/health/", HTTP_USER_AGENT="Googlebot/2.1")
        self.assertIsNone(track("search", r.wsgi_request))
        self.assertEqual(Event.objects.count(), 0)

    def test_session_cookie_is_set_once(self):
        r = self.client.get("/api/health/")
        self.assertIn("tk_sid", r.cookies)
        r2 = self.client.get("/api/health/")
        self.assertNotIn("tk_sid", r2.cookies)

    def test_front_cannot_report_server_side_events(self):
        r = self.client.post(
            "/api/events/", {"type": "order_paid"}, content_type="application/json"
        )
        self.assertEqual(r.status_code, 400)

    def test_front_can_report_whatsapp_click(self):
        r = self.client.post(
            "/api/events/", {"type": "whatsapp_click"}, content_type="application/json"
        )
        self.assertEqual(r.status_code, 204)
        self.assertEqual(Event.objects.filter(type="whatsapp_click").count(), 1)
