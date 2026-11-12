"""Load the starter catalog (cities, processors, GPUs, device models). Idempotent."""

import re

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from catalog.models import Brand, City, DeviceModel, GraphicsCard, Processor
from seed.data import devices, hardware

CATEGORY_BY_KIND = {"phone": "smartphone", "tablet": "tablet"}


def aliases_for(brand: str, name: str) -> list[str]:
    full = f"{brand} {name}".lower()
    aliases = {full.replace(" ", ""), name.lower().replace(" ", "")}
    if brand == "Apple" and name.startswith("iPhone"):
        aliases.add("ip" + name[6:].strip().lower().replace(" ", ""))
    if brand == "Samsung":
        aliases.add(name.replace("Galaxy ", "").lower().replace(" ", ""))
    aliases.add(re.sub(r"[^a-z0-9]", "", full))
    return sorted(a for a in aliases if a)


class Command(BaseCommand):
    help = "Create or update the starter catalog."

    @transaction.atomic
    def handle(self, *args, **options):
        cities = {}
        for i, name in enumerate(hardware.CITIES):
            cities[name], _ = City.objects.update_or_create(
                slug=slugify(name), defaults={"name": name, "position": i}
            )
        for a, b in hardware.NEARBY:
            cities[a].nearby.add(cities[b])

        cpus = {}
        for name, vendor, family, gen, cores, segment, year, score in hardware.PROCESSORS:
            cpus[name], _ = Processor.objects.update_or_create(
                name=name,
                defaults=dict(
                    vendor=vendor,
                    family=family,
                    generation=gen,
                    cores=cores,
                    segment=segment,
                    release_year=year,
                    perf_score=score,
                ),
            )
        gpus = {}
        for name, vendor, vram, dedicated, score in hardware.GPUS:
            gpus[name], _ = GraphicsCard.objects.update_or_create(
                name=name,
                defaults=dict(vendor=vendor, vram_gb=vram, dedicated=dedicated, perf_score=score),
            )

        brands: dict[str, set[str]] = {}
        count = 0

        def save(
            category, brand, name, year, price_k, cpu, gpu, ram, storage, screen, res, os_, **flags
        ):
            nonlocal count
            brands.setdefault(brand, set()).add(category)
            b, _ = Brand.objects.get_or_create(
                slug=slugify(brand), defaults={"name": brand, "categories": []}
            )
            DeviceModel.objects.update_or_create(
                slug=slugify(f"{brand} {name}"),
                defaults=dict(
                    category=category,
                    brand=b,
                    name=name,
                    release_year=year,
                    aliases=aliases_for(brand, name),
                    reference_price_new_fcfa=price_k * 1000,
                    default_processor=cpus[cpu],
                    default_gpu=gpus[gpu] if gpu else None,
                    ram_options_gb=ram,
                    storage_options_gb=storage,
                    screen_size_in=screen,
                    screen_resolution=res,
                    os=os_,
                    **flags,
                ),
            )
            count += 1

        for brand, name, year, price, cpu, ram, storage, screen, f in devices.PHONES:
            os_ = "iOS" if brand == "Apple" else "Android"
            save(
                "smartphone",
                brand,
                name,
                year,
                price,
                cpu,
                None,
                ram,
                storage,
                screen,
                "",
                os_,
                has_5g="5" in f,
                dual_sim="d" in f,
                esim="e" in f,
            )
        for brand, name, year, price, cpu, ram, storage, screen, f in devices.TABLETS:
            os_ = "iPadOS" if brand == "Apple" else "Android"
            save(
                "tablet",
                brand,
                name,
                year,
                price,
                cpu,
                None,
                ram,
                storage,
                screen,
                "",
                os_,
                cellular_option="5" in f,
                stylus_support="s" in f,
            )
        for (
            cat,
            brand,
            name,
            year,
            price,
            cpu,
            gpu,
            ram,
            storage,
            screen,
            res,
            os_,
        ) in devices.COMPUTERS:
            save(cat, brand, name, year, price, cpu, gpu, ram, storage, screen, res, os_)

        for brand, cats in brands.items():
            Brand.objects.filter(slug=slugify(brand)).update(categories=sorted(cats))

        self.stdout.write(
            self.style.SUCCESS(
                f"Catalogue prêt : {count} modèles, {len(cpus)} processeurs, "
                f"{len(gpus)} cartes graphiques, {len(cities)} villes."
            )
        )
