from .models import Notification
from django.db import transaction


def create_notification(
    *,
    user,
    title,
    message,
    notification_type=Notification.SYSTEM,
):

    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
    )

    return notification


def create_welcome_notification(user):
    # For when a user registers

    return create_notification(
        user=user,
        title="Welcome to Broad Blog",
        message="Thank you for creating an account, We're excited to have you with us!",
        notification_type=Notification.WELCOME,
    )


def create_email_verified_notification(user):
    """
    Create a notification when a user verifies their email.
    """

    return create_notification(
        user=user,
        title="Email Verified",
        message="Your email has been verified successfully.",
        notification_type=Notification.EMAIL_VERIFIED,
    )


def create_login_notification(
    user,
    device_name="Unknown device",
    ip_address=None,
):
    if ip_address:
        message = (
            f"Your account was successfully logged in from {device_name}."
            f"  IP address: {ip_address}"
        )
    else:
        message = f"Your account was successfully logged in from {device_name}"

    return create_notification(
        user=user,
        title="New Login Detected",
        message=message,
        notification_type=Notification.LOGIN,
    )


def create_suspicious_login_notification(*, user, score, reasons):
    """
    Create a notification when suspicious login
    activity is detected.
    """
    reasons_text = " ".join(reasons)
    message = (
        "We detected unusual activity on your account."
        f"Risk Score: {score}."
        f" Reasons: {reasons_text}"
    )
    

    return create_notification(
        user=user,
        title="Suspicious Login Detected",
        message=message,
        notification_type=Notification.SECURITY,
    )
