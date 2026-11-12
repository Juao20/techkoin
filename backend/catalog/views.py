from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from rest_framework import generics

from .models import Brand, City, DeviceModel, GraphicsCard, Processor
from .serializers import (
    BrandSerializer,
    CitySerializer,
    DeviceModelListSerializer,
    DeviceModelSerializer,
    GpuSerializer,
    ProcessorSerializer,
)

cached = method_decorator(cache_control(public=True, max_age=300), name="dispatch")


class NoPagination:
    pagination_class = None


@cached
class BrandList(NoPagination, generics.ListAPIView):
    serializer_class = BrandSerializer

    def get_queryset(self):
        qs = Brand.objects.all()
        category = self.request.query_params.get("category")
        if category:
            qs = [b for b in qs if category in b.categories]
        return qs


@cached
class CityList(NoPagination, generics.ListAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer


class ProcessorList(NoPagination, generics.ListAPIView):
    serializer_class = ProcessorSerializer

    def get_queryset(self):
        q = self.request.query_params.get("q", "").strip()
        qs = Processor.objects.all()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(family__icontains=q))
        return qs[:20]


class GpuList(NoPagination, generics.ListAPIView):
    serializer_class = GpuSerializer

    def get_queryset(self):
        q = self.request.query_params.get("q", "").strip()
        qs = GraphicsCard.objects.all()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs[:20]


class DeviceModelList(NoPagination, generics.ListAPIView):
    """Autocomplete: 10 results, matches name, brand and aliases."""

    serializer_class = DeviceModelListSerializer

    def get_queryset(self):
        qs = DeviceModel.objects.filter(is_active=True).select_related("brand")
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        q = self.request.query_params.get("q", "").strip().lower()
        if not q:
            return qs[:10]
        compact = q.replace(" ", "")
        matches = []
        for m in qs:
            haystack = f"{m.brand.name} {m.name}".lower()
            aliases = [a.lower() for a in m.aliases]
            if (
                all(part in haystack for part in q.split())
                or compact in haystack.replace(" ", "")
                or any(compact in a.replace(" ", "") for a in aliases)
            ):
                matches.append(m)
            if len(matches) == 10:
                break
        return matches


class DeviceModelDetail(generics.RetrieveAPIView):
    queryset = DeviceModel.objects.filter(is_active=True).select_related(
        "brand", "default_processor", "default_gpu"
    )
    serializer_class = DeviceModelSerializer
    lookup_field = "slug"
