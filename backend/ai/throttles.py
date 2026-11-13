from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class FeatureThrottle(SimpleRateThrottle):
    """Per-feature hourly limit, doubled for signed-in users (spec 10.1).

    The view names its feature with `ai_feature`; limits come from settings.AI_LIMITS as
    {feature: (visitor, signed_in)}.
    """

    def __init__(self):  # the scope depends on the view, so DRF's class-level lookup is skipped
        pass

    def allow_request(self, request, view):
        feature = getattr(view, "ai_feature", None)
        if feature is None:
            return True
        self.scope = f"ai_{feature}"
        visitor, signed_in = settings.AI_LIMITS[feature]
        limit = signed_in if request.user and request.user.is_authenticated else visitor
        self.rate = f"{limit}/hour"
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        ident = (
            f"user-{request.user.pk}"
            if request.user and request.user.is_authenticated
            else self.get_ident(request)
        )
        return self.cache_format % {"scope": self.scope, "ident": ident}
