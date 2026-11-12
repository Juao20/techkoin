from rest_framework import serializers

from .models import Brand, City, DeviceModel, GraphicsCard, Processor


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["name", "slug", "categories"]


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["name", "slug"]


class ProcessorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Processor
        fields = ["id", "name", "vendor", "family", "generation", "segment", "perf_score"]


class GpuSerializer(serializers.ModelSerializer):
    class Meta:
        model = GraphicsCard
        fields = ["id", "name", "vendor", "vram_gb", "dedicated", "perf_score"]


class DeviceModelListSerializer(serializers.ModelSerializer):
    brand = serializers.CharField(source="brand.name")
    label = serializers.SerializerMethodField()

    class Meta:
        model = DeviceModel
        fields = ["slug", "label", "name", "brand", "category", "release_year"]

    def get_label(self, obj):
        return str(obj)


class DeviceModelSerializer(DeviceModelListSerializer):
    default_processor = ProcessorSerializer(read_only=True)
    default_gpu = GpuSerializer(read_only=True)

    class Meta(DeviceModelListSerializer.Meta):
        fields = DeviceModelListSerializer.Meta.fields + [
            "reference_price_new_fcfa",
            "default_processor",
            "default_gpu",
            "ram_options_gb",
            "storage_options_gb",
            "screen_size_in",
            "screen_resolution",
            "refresh_rate_hz",
            "os",
            "has_5g",
            "dual_sim",
            "esim",
            "stylus_support",
            "cellular_option",
        ]
