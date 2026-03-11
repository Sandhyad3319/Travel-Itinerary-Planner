from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

UserModel = get_user_model()


class EmailBackend(ModelBackend):
    """
    Authenticate using email OR username.
    Safely handles duplicate matches.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        # Prefer exact email match first
        user = (
            UserModel.objects
            .filter(email__iexact=username)
            .first()
        )

        # Fallback to username match
        if user is None:
            user = (
                UserModel.objects
                .filter(username__iexact=username)
                .first()
            )

        if user and user.check_password(password):
            return user

        return None
