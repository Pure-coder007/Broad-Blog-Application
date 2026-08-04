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
    
    
# Get user ip address
def get_client_ip(request):
    x_fowarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_fowarded_for:
        return x_fowarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR")