"""Serves the built front end (`index.html`) and injects Open Graph tags for the pages people share.

`/annonce/<slug>` and `/boutique/<slug>` get the title, price, city and first photo in their
`<meta>` tags, so WhatsApp shows a proper preview (spec 14). Every other route returns the plain
`index.html` and the React router takes over. In development Vite serves the pages instead.
"""

from __future__ import annotations

import re
from functools import lru_cache
from html import escape
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse

from accounts.models import Shop
from marketplace.models import Listing
from marketplace.services import specs_line

LISTING_RE = re.compile(r"^annonce/(?P<slug>[\w-]+)/?$")
SHOP_RE = re.compile(r"^boutique/(?P<slug>[\w-]+)/?$")
NBSP = " "


def fcfa(value: int) -> str:
    return f"{value:,}".replace(",", NBSP) + f"{NBSP}FCFA"


def absolute(url: str) -> str:
    return url if url.startswith("http") else f"{settings.SITE_URL}{url}"


@lru_cache(maxsize=4)
def _read(path: str, mtime: float) -> str:
    return Path(path).read_text(encoding="utf-8")


def index_html() -> str:
    path = Path(settings.FRONTEND_DIST) / "index.html"
    if not path.exists():
        raise Http404("Le front n'est pas construit : lancez `npm run build` dans frontend/.")
    return _read(str(path), path.stat().st_mtime)


def tags(title: str, description: str, url: str, image: str = "", kind: str = "website") -> str:
    rows = [
        ("property", "og:type", kind),
        ("property", "og:site_name", "TechKoin"),
        ("property", "og:title", title),
        ("property", "og:description", description),
        ("property", "og:url", absolute(url)),
        ("property", "og:locale", "fr_FR"),
        ("name", "twitter:card", "summary_large_image" if image else "summary"),
        ("name", "twitter:title", title),
        ("name", "twitter:description", description),
    ]
    if image:
        rows += [("property", "og:image", image), ("name", "twitter:image", image)]
    return "\n    ".join(
        f'<meta {k}="{escape(n)}" content="{escape(v, quote=True)}" />' for k, n, v in rows
    )


def listing_meta(slug: str) -> tuple[str, str] | None:
    listing = (
        Listing.objects.filter(
            slug=slug,
            status__in=[Listing.Status.ACTIVE, Listing.Status.RESERVED, Listing.Status.SOLD],
        )
        .select_related("device_model", "brand", "processor")
        .prefetch_related("photos")
        .first()
    )
    if not listing:
        return None
    photo = listing.photos.first()
    image = absolute(photo.image.url) if photo else ""
    bits = [fcfa(listing.price_fcfa), listing.city, specs_line(listing)]
    description = " · ".join(b for b in bits if b)
    title = f"{listing.title} · {fcfa(listing.price_fcfa)} | TechKoin"
    return title, tags(title, description, f"/annonce/{listing.slug}", image, "product")


def shop_meta(slug: str) -> tuple[str, str] | None:
    shop = Shop.objects.filter(slug=slug).first()
    if not shop:
        return None
    count = Listing.objects.filter(shop=shop, status=Listing.Status.ACTIVE).count()
    where = f"{shop.city}. " if shop.city else ""
    description = (shop.description or "").strip()[:160] or f"{where}{count} annonce(s) en ligne."
    title = f"{shop.name} | TechKoin"
    image = absolute(shop.logo.url) if shop.logo else ""
    return title, tags(title, description, f"/boutique/{shop.slug}", image)


def render(path: str) -> str:
    html = index_html()
    found = None
    if m := LISTING_RE.match(path):
        found = listing_meta(m["slug"])
    elif m := SHOP_RE.match(path):
        found = shop_meta(m["slug"])
    if not found:
        return html
    title, meta = found
    html = re.sub(
        r"<title>.*?</title>", lambda _: f"<title>{escape(title)}</title>", html, flags=re.S
    )
    # the generic description of the page is replaced by the specific one
    html = re.sub(r'\s*<meta\s+name="description"[^>]*?/>', "", html, flags=re.S)
    return html.replace("</head>", f"    {meta}\n  </head>", 1)


def spa_with_meta(request, path: str = ""):
    return HttpResponse(render(path), content_type="text/html; charset=utf-8")
