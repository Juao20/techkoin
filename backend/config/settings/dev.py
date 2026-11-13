from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = SECRET_KEY or "dev-only-insecure-key"  # noqa: F405

INSTALLED_APPS += ["corsheaders"]  # noqa: F405
MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")  # noqa: F405
CORS_ALLOWED_ORIGINS = [SITE_URL]  # noqa: F405
CORS_ALLOW_CREDENTIALS = True

AI_LIMITS = {k: (v[0] * 100, v[1] * 100) for k, v in AI_LIMITS.items()}  # noqa: F405

# End-to-end tests and demo sessions come from one address: relax the limits in development only.
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {
        scope: f"{int(rate.split('/')[0]) * 100}/{rate.split('/')[1]}"
        for scope, rate in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].items()  # noqa: F405
    },
}
