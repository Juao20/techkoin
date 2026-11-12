"""Base settings shared by every environment. Secrets come from the environment."""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BASE_DIR.parent

load_dotenv(REPO_ROOT / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
SITE_URL = os.environ.get("SITE_URL", "http://localhost:5173")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "accounts",
    "catalog",
    "marketplace",
    "trust",
    "payments",
    "analytics",
    "ai",
    "pricing",
    "seed",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=60,
    )
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Porto-Novo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "300/hour", "user": "1000/hour"},
}

# Sessions and CSRF: the SPA and the API share the same origin (Vite proxy in dev).
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # the SPA reads the token from the cookie
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", SITE_URL)

# Encryption of IMEI at rest (used from phase 2).
FIELD_ENCRYPTION_KEY = os.environ.get("FIELD_ENCRYPTION_KEY", "")

# Pricing, escrow, plans (used from later phases).
ESCROW_COMMISSION_PCT = float(os.environ.get("ESCROW_COMMISSION_PCT", "3"))
ESCROW_COMMISSION_MIN_FCFA = int(os.environ.get("ESCROW_COMMISSION_MIN_FCFA", "500"))
ESCROW_AUTO_RELEASE_HOURS = int(os.environ.get("ESCROW_AUTO_RELEASE_HOURS", "48"))
PRO_PLAN_PRICE_FCFA = int(os.environ.get("PRO_PLAN_PRICE_FCFA", "10000"))
PAYMENT_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "simulator")

# AI (Groq). Without a key, every feature runs in deterministic fallback mode.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL_SMART = os.environ.get("GROQ_MODEL_SMART", "llama-3.3-70b-versatile")
GROQ_MODEL_FAST = os.environ.get("GROQ_MODEL_FAST", "llama-3.1-8b-instant")
GROQ_MODEL_STT = os.environ.get("GROQ_MODEL_STT", "whisper-large-v3")
AI_TIMEOUT_SECONDS = int(os.environ.get("AI_TIMEOUT_SECONDS", "15"))

EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "TechKoin <no-reply@techkoin.bj>")
