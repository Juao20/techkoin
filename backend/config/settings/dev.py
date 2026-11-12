from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = SECRET_KEY or "dev-only-insecure-key"  # noqa: F405

INSTALLED_APPS += ["corsheaders"]  # noqa: F405
MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")  # noqa: F405
CORS_ALLOWED_ORIGINS = [SITE_URL]  # noqa: F405
CORS_ALLOW_CREDENTIALS = True
