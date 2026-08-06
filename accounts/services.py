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