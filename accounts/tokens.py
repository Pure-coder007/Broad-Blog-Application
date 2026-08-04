from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator

User = get_user_model()


def create_jwt_pair_for_user(user: User):
    refresh = RefreshToken.for_user(user)

    tokens = {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }
    return tokens


email_verification_token = PasswordResetTokenGenerator()
