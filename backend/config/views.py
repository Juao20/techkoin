from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@require_GET
@ensure_csrf_cookie
def csrf(request):
    """Sets the CSRF cookie so the SPA can send it back on unsafe requests."""
    return JsonResponse({"detail": "ok"})
