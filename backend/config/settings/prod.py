from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False
if not SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured("DJANGO_SECRET_KEY is required in production.")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
