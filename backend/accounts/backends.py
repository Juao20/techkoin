from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .phone import normalize_phone


class EmailOrPhoneBackend(ModelBackend):
    """Authenticate with an e-mail address or a Beninese phone number."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        User = get_user_model()
        identifier = username.strip()
        if "@" in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
        else:
            phone = normalize_phone(identifier)
            user = User.objects.filter(phone=phone).first() if phone else None
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
