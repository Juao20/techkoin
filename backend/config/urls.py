from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from .spa import spa_with_meta

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("config.api_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Everything else is the single-page app; shared pages get Open Graph tags (see config/spa.py).
urlpatterns += [re_path(r"^(?!api/|admin/|media/|static/)(?P<path>.*)$", spa_with_meta)]
