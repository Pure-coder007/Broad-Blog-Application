from django.core.mail import send_mail
from .models import AuditLog


def send_verification_email(subject, message, recipient):
    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=[recipient],
        fail_silently=False,
    )



# def create_audit_log(request, user, action):
#     AuditLog.objects.create(
#         user=user,
#         action=action,
#         ip_address=request.META.get('REMOTE_ADDR'),
#         user_agent=request.META.get('HTTP_USER_AGENT', ''), 
#     )


def create_audit_log(
    request,
    user,
    action,
    status="SUCCESS",
    details=None,
):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")

    AuditLog.objects.create(
        user=user,
        action=action,
        status=status,
        ip_address=ip,
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        details=details or {},
    )