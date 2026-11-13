import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image

from insights.factories import add_listing, make_shop
from marketplace.models import ListingPhoto
from marketplace.photos import process_upload

pytestmark = pytest.mark.django_db

INDEX = """<!doctype html>
<html lang="fr"><head>
<title>TechKoin — Appareils</title>
<meta
  name="description"
  content="Générique"
/>
</head><body><div id="root"></div></body></html>
"""


@pytest.fixture
def dist(settings, tmp_path):
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    settings.FRONTEND_DIST = str(tmp_path)
    settings.SITE_URL = "https://techkoin.example"
    call_command("seed_catalog", verbosity=0)
    return tmp_path


def photo_for(listing):
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), (200, 190, 170)).save(buf, "PNG")
    image, thumb, phash = process_upload(SimpleUploadedFile("a.png", buf.getvalue(), "image/png"))
    photo = ListingPhoto(listing=listing, phash=phash)
    photo.image.save("p.webp", image, save=False)
    photo.thumb.save("t.webp", thumb, save=False)
    photo.save()


def test_a_listing_page_carries_title_price_city_and_photo(client, dist):
    listing = add_listing(make_shop(city="Cotonou"), price=185_000)
    photo_for(listing)
    html = client.get(f"/annonce/{listing.slug}").content.decode()
    assert '<meta property="og:title" content="' in html and listing.title in html
    assert "185 000 FCFA" in html and "Cotonou" in html
    assert 'property="og:image" content="https://techkoin.example/media/' in html
    assert 'property="og:url" content="https://techkoin.example/annonce/' in html
    assert "<title>" + listing.title in html
    assert "Générique" not in html and '<div id="root">' in html


def test_a_shop_page_carries_its_name_and_description(client, dist):
    shop = make_shop(city="Parakou")
    shop.description = "Le spécialiste du portable <b>reconditionné</b>"
    shop.save()
    html = client.get(f"/boutique/{shop.slug}/").content.decode()
    assert f"<title>{shop.name} | TechKoin</title>" in html
    assert "&lt;b&gt;reconditionné" in html and "<b>" not in html  # escaped


def test_unknown_pages_and_other_routes_get_the_plain_app(client, dist):
    for path in ("/annonce/inconnue", "/boutique/inconnue", "/recherche", "/"):
        html = client.get(path).content.decode()
        assert "Générique" in html and "og:title" not in html


def test_drafts_never_leak_into_previews(client, dist):
    listing = add_listing(make_shop(), status="draft")
    assert "og:title" not in client.get(f"/annonce/{listing.slug}").content.decode()


def test_api_and_admin_routes_are_untouched(client, dist):
    assert client.get("/api/health/").json() == {"status": "ok"}
    assert client.get("/api/inconnu/").status_code == 404
    assert client.get("/admin/login/").status_code == 200


def test_without_a_build_the_page_says_how_to_make_one(client, settings, tmp_path):
    settings.FRONTEND_DIST = str(tmp_path / "absent")
    assert client.get("/annonce/x").status_code == 404
