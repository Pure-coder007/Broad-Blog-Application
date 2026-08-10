from datetime import timedelta

from django.utils import timezone

from .models import UserSession


def detect_suspicious_login(
    *,
    user,
    ip_address,
    device_name,
):
    

    # ==========================
    # Find the previous session
    # ==========================

    previous_session = (
        UserSession.objects
        .filter(user=user)
        .order_by("-created")
        .first()
    )

    # ==========================
    # No previous session
    # ==========================

    if not previous_session:

        return {
            "suspicious": False,
            "score": 0,
            "reasons": [],
            "previous_session": None,
        }

    score = 0
    reasons = []

    # ==========================
    # Check IP address
    # ==========================

    if (
        previous_session.ip_address
        and ip_address
        and previous_session.ip_address != ip_address
    ):

        score += 1

        reasons.append(
            "Login originated from a different IP address."
        )

    # ==========================
    # Check device
    # ==========================

    if (
        previous_session.device_name
        and device_name
        and previous_session.device_name != device_name
    ):

        score += 1

        reasons.append(
            "Login originated from a different device."
        )

    # ==========================
    # Check recent login
    # ==========================

    recent_threshold = (
        timezone.now() - timedelta(minutes=30)
    )

    if previous_session.created >= recent_threshold:

        score += 1

        reasons.append(
            "A previous login occurred within the last 30 minutes."
        )

    # ==========================
    # Determine suspicious status
    # ==========================

    suspicious = score >= 2

    # ==========================
    # Return security result
    # ==========================

    return {
        "suspicious": suspicious,
        "score": score,
        "reasons": reasons,
        "previous_session": previous_session,
    }