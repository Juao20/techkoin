from django.conf import settings

from .base import PaymentProvider
from .fedapay import FedaPayProvider
from .simulator import SimulatorProvider

PROVIDERS = {"simulator": SimulatorProvider, "fedapay": FedaPayProvider}


def get_provider(name: str | None = None) -> PaymentProvider:
    return PROVIDERS[name or settings.PAYMENT_PROVIDER]()
