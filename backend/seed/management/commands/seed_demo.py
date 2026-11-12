"""Demo data: shops, individuals, listings with generated photos, 90 days of events.

Everything created here belongs to users whose e-mail ends with DEMO_DOMAIN, so the command can
be run again safely (it skips when the data exists) and `--reset` removes it before recreating.
Photos are neutral generated placeholders, never real product images.
"""

import io
import random
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image, ImageDraw

from accounts.models import Shop, User
from analytics.models import Event
from catalog.models import City, DeviceModel
from marketplace import services
from marketplace.models import Favorite, Listing, ListingPhoto
from marketplace.photos import process_upload

DEMO_DOMAIN = "@demo.techkoin.test"
DEMO_PASSWORD = "Demo2026!"

SHOPS = [
    ("Cotonou Tech", "Cotonou", "Haie Vive", "pro", True),
    ("Dantokpa Mobile", "Cotonou", "Dantokpa", "free", True),
    ("Akpakpa Informatique", "Cotonou", "Akpakpa", "free", False),
    ("Porto-Novo Digital", "Porto-Novo", "Ouando", "free", True),
    ("Parakou Électro", "Parakou", "Banikanni", "free", False),
    ("Bohicon Phones", "Bohicon", "Centre", "free", False),
    ("Ganhi Computers", "Cotonou", "Ganhi", "pro", True),
    ("Calavi Store", "Abomey-Calavi", "Godomey", "free", False),
]

FIRST_NAMES = [
    "Koffi",
    "Afi",
    "Sènami",
    "Codjo",
    "Fatou",
    "Ibrahim",
    "Mariam",
    "Rodrigue",
    "Ginette",
    "Gildas",
    "Prisca",
    "Armand",
    "Nadège",
    "Judicaël",
    "Carine",
    "Fabrice",
    "Estelle",
    "Wilfried",
    "Rosine",
    "Hervé",
    "Mireille",
    "Séraphin",
    "Aïcha",
    "Dieudonné",
    "Léa",
]
LAST_NAMES = ["Adjovi", "Dossou", "Houngbo", "Agbodjan", "Tossou", "Gbaguidi", "Zannou", "Sossa"]

QUARTIERS = ["Fidjrossè", "Cadjehoun", "Akpakpa", "Gbégamey", "Vèdoko", "Agla", "Zogbo", "Togoudo"]
COLORS = ["Noir", "Blanc", "Gris", "Bleu", "Argent", "Or", "Vert"]
SEARCHES = [
    "iphone 13",
    "iphone 11",
    "samsung a54",
    "macbook",
    "pc portable hp",
    "dell latitude",
    "tecno spark",
    "infinix hot",
    "ipad",
    "thinkpad",
    "pc gamer",
    "redmi note",
    "galaxy s22",
    "ordinateur pas cher",
    "tablette samsung",
]
NO_RESULT_SEARCHES = ["rtx 4060", "macbook m3", "iphone 16 pro max", "ps5", "surface pro"]
DEFAULT_NEW_PRICE = {
    "smartphone": 180_000,
    "tablet": 220_000,
    "laptop": 450_000,
    "desktop": 350_000,
}


def placeholder_photo(label: str, kind: str, seed: int) -> SimpleUploadedFile:
    """Flat, neutral image with the device name: no gradient, no stock imagery."""
    rng = random.Random(seed)
    tone = rng.randint(226, 240)
    img = Image.new("RGB", (1200, 900), (tone, tone - 3, tone - 9))
    draw = ImageDraw.Draw(img)
    landscape = kind != "front" or rng.random() < 0.5
    w, h = (620, 400) if landscape else (330, 640)
    x, y = (1200 - w) // 2, (900 - h) // 2
    body = (40, 40, 44) if kind != "back" else (170 + rng.randint(0, 40),) * 3
    draw.rounded_rectangle((x, y, x + w, y + h), radius=28, fill=body)
    if kind in {"front", "screen_on"}:
        pad = 22
        screen = (230, 236, 232) if kind == "screen_on" else (18, 18, 20)
        draw.rounded_rectangle((x + pad, y + pad, x + w - pad, y + h - pad), radius=14, fill=screen)
    draw.text((40, 40), f"{label} · {kind}", fill=(90, 85, 76))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    data = buf.getvalue()
    return SimpleUploadedFile(f"{kind}.jpg", data, content_type="image/jpeg")


class Command(BaseCommand):
    help = "Create demo shops, individuals, listings, photos and 90 days of events."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo data first.")
        parser.add_argument("--listings", type=int, default=150)
        parser.add_argument("--days", type=int, default=90)
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **opts):
        demo_users = User.objects.filter(email__endswith=DEMO_DOMAIN)
        if opts["reset"]:
            self.reset(demo_users)
        elif demo_users.exists():
            self.stdout.write(
                "Données de démonstration déjà présentes. Utilisez --reset pour recréer."
            )
            return
        if not DeviceModel.objects.exists():
            call_command("seed_catalog")

        self.rng = random.Random(opts["seed"])
        self.models = list(DeviceModel.objects.filter(is_active=True).select_related("brand"))
        self.cities = list(City.objects.all())

        with transaction.atomic():
            shops, individuals = self.create_accounts()
        listings = self.create_listings(shops, individuals, opts["listings"])
        self.create_events(listings, individuals, opts["days"])
        self.print_accounts()

    # ---------------------------------------------------------------- reset

    def reset(self, demo_users):
        for photo in ListingPhoto.objects.filter(listing__seller__in=demo_users):
            photo.image.delete(save=False)
            photo.thumb.delete(save=False)
        Event.objects.filter(user__in=demo_users).delete()
        Event.objects.filter(session_id__startswith="demo").delete()
        demo_users.delete()
        self.stdout.write("Données de démonstration supprimées.")

    # ------------------------------------------------------------- accounts

    def phone(self, n: int) -> str:
        return f"+2290197{n:06d}"

    def make_user(self, email_local, first, last, n, **extra) -> User:
        user = User(
            username=f"{email_local}{DEMO_DOMAIN}",
            email=f"{email_local}{DEMO_DOMAIN}",
            first_name=first,
            last_name=last,
            phone=self.phone(n),
            whatsapp_number=self.phone(n),
            **extra,
        )
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user

    def create_accounts(self):
        admin = self.make_user("admin", "Admin", "TechKoin", 1, city="Cotonou")
        admin.is_staff = admin.is_superuser = True
        admin.save()
        mod = self.make_user("moderateur", "Modérateur", "TechKoin", 2, city="Cotonou")
        mod.is_moderator = mod.is_staff = True
        mod.save()

        shops: list[Shop] = []
        owner_locals = {0: "boutique.pro", 1: "boutique.gratuite"}
        for i, (name, city, quartier, plan, verified) in enumerate(SHOPS):
            local = owner_locals.get(i, f"boutique{i + 1}")
            owner = self.make_user(
                local,
                name.split()[0],
                "Gérant",
                10 + i,
                account_type=User.AccountType.BOUTIQUE,
                city=city,
            )
            shops.append(
                Shop.objects.create(
                    owner=owner,
                    name=name,
                    slug=slugify(name),
                    city=city,
                    quartier=quartier,
                    address=f"{quartier}, {city}",
                    description=f"{name} vend des appareils neufs et reconditionnés.",
                    whatsapp_number=owner.phone,
                    plan=plan,
                    verification_status="verified" if verified else "none",
                    opening_hours={
                        "mon": "8h - 19h",
                        "tue": "8h - 19h",
                        "wed": "8h - 19h",
                        "thu": "8h - 19h",
                        "fri": "8h - 19h",
                        "sat": "9h - 17h",
                    },
                )
            )

        individuals = [
            self.make_user(
                "particulier" if i == 0 else f"particulier{i + 1}",
                FIRST_NAMES[i % len(FIRST_NAMES)],
                self.rng.choice(LAST_NAMES),
                100 + i,
                city=self.rng.choice(self.cities).name,
                quartier=self.rng.choice(QUARTIERS),
            )
            for i in range(25)
        ]
        return shops, individuals

    # ------------------------------------------------------------- listings

    def create_listings(self, shops, individuals, total):
        rng = self.rng
        listings: list[Listing] = []
        per_individual = {u.pk: 0 for u in individuals}
        for i in range(total):
            by_shop = i % 100 < 55
            if by_shop:
                shop = rng.choice(shops)
                seller = shop.owner
            else:
                shop = None
                free = [u for u in individuals if per_individual[u.pk] < 4]
                seller = rng.choice(free)
                per_individual[seller.pk] += 1
            listings.append(self.create_listing(seller, shop, i))
            if (i + 1) % 25 == 0:
                self.stdout.write(f"  {i + 1}/{total} annonces")
        return listings

    def create_listing(self, seller, shop, index) -> Listing:
        rng = self.rng
        m = rng.choice(self.models)
        new = shop is not None and rng.random() < 0.35
        condition = (
            "new_sealed"
            if new
            else rng.choices(["used", "refurbished", "new_open"], [70, 22, 8])[0]
        )
        is_new = condition.startswith("new")
        grade = "" if is_new else rng.choices(["A", "B", "C"], [35, 50, 15])[0]
        ref = m.reference_price_new_fcfa or DEFAULT_NEW_PRICE[m.category]
        age = max(0, timezone.now().year - (m.release_year or timezone.now().year))
        factor = (
            1.0 if is_new else max(0.25, 0.85 - 0.12 * age) * {"A": 1.0, "B": 0.9, "C": 0.75}[grade]
        )
        price = int(round(ref * factor * rng.uniform(0.92, 1.1), -3))
        city = shop.city if shop else seller.city
        published = timezone.now() - timedelta(days=rng.randint(0, 85), hours=rng.randint(0, 23))
        status = rng.choices(["active", "sold", "archived", "pending_review"], [86, 8, 3, 3])[0]

        listing = Listing(
            seller=seller,
            shop=shop,
            device_model=m,
            category=m.category,
            brand=m.brand,
            condition_type=condition,
            grade=grade,
            price_fcfa=max(price, 15_000),
            negotiable=rng.random() < 0.5,
            city=city,
            quartier=shop.quartier if shop else seller.quartier,
            accessories=rng.sample(
                ["charger", "box", "cable", "case", "earphones"], rng.randint(0, 4)
            )
            + (["invoice"] if shop else []),
            warranty_months=rng.choice([3, 6, 12]) if shop or is_new else rng.choice([0, 0, 1]),
            provenance=rng.choice(["local", "europe", "usa", "dubai"]),
            imei_or_serial=f"35{rng.randint(10**12, 10**13 - 1)}",
            color=rng.choice(COLORS),
            status=status,
            published_at=published,
            sold_at=published + timedelta(days=rng.randint(1, 10)) if status == "sold" else None,
            ram_gb=rng.choice(m.ram_options_gb) if m.ram_options_gb else None,
            storage_gb=rng.choice(m.storage_options_gb) if m.storage_options_gb else None,
            screen_size_in=m.screen_size_in,
            screen_resolution=m.screen_resolution,
            refresh_rate_hz=m.refresh_rate_hz,
            os=m.os,
            price_badge=rng.choices(
                ["good_deal", "fair", "above_market", "unknown"], [20, 55, 15, 10]
            )[0],
        )
        if m.category in ("laptop", "desktop"):
            listing.processor = m.default_processor
            listing.gpu = m.default_gpu
            listing.gpu_dedicated = bool(m.default_gpu and m.default_gpu.dedicated)
            listing.storage_type = "ssd" if rng.random() < 0.85 else "hdd"
            listing.keyboard_layout = rng.choices(["azerty", "qwerty"], [60, 40])[0]
            listing.battery_cycles = None if is_new else rng.randint(40, 600)
        else:
            listing.storage_type = ""
            listing.network_5g = m.has_5g
            listing.dual_sim = m.dual_sim
            listing.esim = m.esim
            listing.account_removed = True
            listing.battery_health_pct = None if is_new else rng.randint(74, 100)
            listing.cellular = m.cellular_option and rng.random() < 0.5
            listing.stylus_included = m.stylus_support and rng.random() < 0.4
        listing.title = services.build_title(listing)
        listing.has_invoice = "invoice" in listing.accessories
        services.refresh_search_text(listing)
        listing.slug = services.unique_slug(listing)
        listing.save()

        kinds = ["front", "back", "screen_on"] + (["defect"] if grade == "C" else []) + ["other"]
        for position, kind in enumerate(kinds):
            image, thumb, phash = process_upload(
                placeholder_photo(listing.title, kind, listing.pk * 10 + position)
            )
            photo = ListingPhoto(listing=listing, kind=kind, phash=phash, position=position)
            photo.image.save(f"{listing.pk}.webp", image, save=False)
            photo.thumb.save(f"{listing.pk}.webp", thumb, save=False)
            photo.save()
        return listing

    # --------------------------------------------------------------- events

    def create_events(self, listings, individuals, days):
        rng = self.rng
        live = [x for x in listings if x.status == "active"]
        if not live:
            return
        now = timezone.now()
        total = 0
        for offset in range(days, -1, -1):
            day = now - timedelta(days=offset)
            volume = int(60 + (days - offset) * 1.2 + rng.randint(0, 40))
            batch: list[Event] = []
            for _ in range(volume):
                sid = f"demo{rng.getrandbits(48):012x}"
                city = rng.choice(self.cities).name
                if rng.random() < 0.35:
                    no_result = rng.random() < 0.12
                    query = rng.choice(NO_RESULT_SEARCHES if no_result else SEARCHES)
                    batch.append(
                        Event(
                            type="search_no_result" if no_result else "search",
                            session_id=sid,
                            query_text=query,
                            filters={"q": query},
                            city=city,
                            results_count=0 if no_result else rng.randint(3, 40),
                        )
                    )
                    continue
                listing = rng.choice(live)
                batch.append(
                    Event(
                        type="listing_view",
                        session_id=sid,
                        listing=listing,
                        shop=listing.shop,
                        city=city,
                    )
                )
                roll = rng.random()
                if roll < 0.12:
                    batch.append(
                        Event(
                            type="whatsapp_click",
                            session_id=sid,
                            listing=listing,
                            shop=listing.shop,
                            city=city,
                        )
                    )
                elif roll < 0.18:
                    batch.append(
                        Event(
                            type="phone_reveal",
                            session_id=sid,
                            listing=listing,
                            shop=listing.shop,
                            city=city,
                        )
                    )
                elif roll < 0.30:
                    batch.append(
                        Event(
                            type="favorite_add",
                            session_id=sid,
                            listing=listing,
                            shop=listing.shop,
                            city=city,
                        )
                    )
            created = Event.objects.bulk_create(batch)
            moment = day.replace(hour=12, minute=0, second=0, microsecond=0)
            ids = [e.pk for e in created]
            if ids:
                Event.objects.filter(pk__in=ids).update(created_at=moment, updated_at=moment)
            total += len(batch)

        for listing in live:
            counts = {
                t: Event.objects.filter(listing=listing, type=t).count()
                for t in ("listing_view", "whatsapp_click", "phone_reveal", "favorite_add")
            }
            Listing.objects.filter(pk=listing.pk).update(
                views_count=counts["listing_view"],
                contacts_count=counts["whatsapp_click"] + counts["phone_reveal"],
                favorites_count=counts["favorite_add"],
            )
        self.stdout.write(f"  {total} événements sur {days} jours")

        fan = individuals[0]
        for listing in rng.sample(live, min(5, len(live))):
            if listing.seller_id != fan.pk:
                Favorite.objects.get_or_create(user=fan, listing=listing)
                Listing.objects.filter(pk=listing.pk).update(
                    favorites_count=F("favorites_count") + 1
                )

    def print_accounts(self):
        self.stdout.write(self.style.SUCCESS("Données de démonstration créées."))
        self.stdout.write(f"Mot de passe de tous les comptes : {DEMO_PASSWORD}")
        for local in ("admin", "moderateur", "boutique.pro", "boutique.gratuite", "particulier"):
            self.stdout.write(f"  {local}{DEMO_DOMAIN}")
