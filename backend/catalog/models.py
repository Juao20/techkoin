from django.db import models


class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(models.TextChoices):
    LAPTOP = "laptop", "PC portable"
    DESKTOP = "desktop", "PC fixe"
    SMARTPHONE = "smartphone", "Smartphone"
    TABLET = "tablet", "Tablette"


class City(Timestamped):
    """Administrable list of cities (section 6.4)."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    nearby = models.ManyToManyField("self", blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]
        verbose_name_plural = "cities"

    def __str__(self):
        return self.name


class Brand(Timestamped):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    categories = models.JSONField(default=list)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Processor(Timestamped):
    class Segment(models.TextChoices):
        LAPTOP = "laptop", "Portable"
        DESKTOP = "desktop", "Fixe"
        MOBILE = "mobile", "Mobile"

    name = models.CharField(max_length=120, unique=True)
    vendor = models.CharField(max_length=40)
    family = models.CharField(max_length=40)
    generation = models.CharField(max_length=20, blank=True)
    cores = models.PositiveSmallIntegerField(null=True, blank=True)
    segment = models.CharField(max_length=10, choices=Segment.choices)
    release_year = models.PositiveSmallIntegerField(null=True, blank=True)
    perf_score = models.PositiveSmallIntegerField(default=0)  # 0-100

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class GraphicsCard(Timestamped):
    name = models.CharField(max_length=120, unique=True)
    vendor = models.CharField(max_length=40)
    vram_gb = models.PositiveSmallIntegerField(default=0)
    dedicated = models.BooleanField(default=False)
    perf_score = models.PositiveSmallIntegerField(default=0)  # 0-100

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class DeviceModel(Timestamped):
    category = models.CharField(max_length=12, choices=Category.choices)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="models")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    release_year = models.PositiveSmallIntegerField(null=True, blank=True)
    aliases = models.JSONField(default=list, blank=True)
    reference_price_new_fcfa = models.PositiveIntegerField(null=True, blank=True)

    default_processor = models.ForeignKey(
        Processor, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    default_gpu = models.ForeignKey(
        GraphicsCard, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    ram_options_gb = models.JSONField(default=list, blank=True)
    storage_options_gb = models.JSONField(default=list, blank=True)
    screen_size_in = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    screen_resolution = models.CharField(max_length=20, blank=True)
    refresh_rate_hz = models.PositiveSmallIntegerField(null=True, blank=True)
    os = models.CharField(max_length=40, blank=True)
    has_5g = models.BooleanField(default=False)
    dual_sim = models.BooleanField(default=False)
    esim = models.BooleanField(default=False)
    stylus_support = models.BooleanField(default=False)
    cellular_option = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["brand__name", "-release_year", "name"]

    def __str__(self):
        return f"{self.brand.name} {self.name}"
