from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
import uuid, os
from django.conf import settings
from django.utils import timezone


def upload_profile_picture(instance, filename):
    ext = os.path.splitext(filename)[1]
    return f"profile_pictures/{uuid.uuid4()}{ext}"


def upload_cv(instance, filename):
    ext = os.path.splitext(filename)[1]
    return f"cv/{uuid.uuid4()}{ext}"


# Create your models here.
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff being True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser being True.")
        return self.create_user(email=email, password=password, **extra_fields)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    
    USER = "USER"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"
    
    ROLE_CHOICES = (
        ("USER", "User"),
        ("MODERATOR", "Moderator"),
        ("ADMIN", "Admin"),
        )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=USER)
    email = models.EmailField(max_length=80, unique=True)
    pending_email = models.EmailField(max_length=80, blank=True, null=True, unique=True)
    username = models.CharField(max_length=80, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    restored_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    objects = CustomUserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.username
    
    
    
    
class UserSession(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    
    refresh_token = models.TextField()
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    device_name = models.CharField(
        max_length=255,
        blank=True,
    )
    user_agent = models.TextField(blank=True,)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True,)
    last_activity = models.DateTimeField(auto_now=True,)
    
    class Meta:
        ordering = ["-created"]
        
    def __str__(self):
        return f"{self.user.email} ({self.ip_address})"
    
    

    


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    
    phone_number = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True, db_index=True)
    city = models.CharField(max_length=100, blank=True, db_index=True)
    website = models.URLField(blank=True)
    profile_picture = models.ImageField(upload_to=upload_profile_picture, blank=True, null=True,)
    cv = models.FileField(upload_to=upload_cv, blank=True, null=True,)
    date_of_birth = models.DateField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created"]
    
    def __str__(self):
        return f"{self.user.email}'s Profile"
    
    
    
    



class PasswordHistory(models.Model):
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="password_history")
    password = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created"]
        
    def __str__(self):
        return f"{self.user.email} - {self.created}"
    
    
    
    
class AuditLog(models.Model):
    ACTIONS = (
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("REGISTER", "Register"),
        ("VERIFY_EMAIL", "Verify Email"),
        ("PASSWORD_CHANGE", "Password Change"),
        ("PASSWORD_RESET", "Password Reset"),
        ("PROFILE_UPDATE", "Profile Update"),
        ("PROFILE_PICTURE", "Profile Picture Upload"),
        ("CV_UPLOAD", "CV Upload"),
        ("EMAIL_CHANGE_REQUEST", "Email Change Request"),
        ("EMAIL_CHANGED", "Email Changed"),
        ("LOGOUT", "Logout"),
        ("LOGOUT_ALL_DEVICES", "Logout all devices"),
        ("ACCOUNT_DELETE", "Account Delete"),
        ("ADMIN_DASHBOARD", "Admin Dashboard"),
        ("ROLE_CHANGED", "Role Changed"),
        ("VIEW_USERS", "View Users"),
        ("VIEW_USER", "View Single User"),
        ("UPDATE_USER_STATUS", "Update User Status"),
        ("DELETE_USER", "Delete User"),
        ("VIEW_NOTIFICATION", "View Notification"),
        ("DELETE_NOTIFICATION", "Delete Notification"),
        ("DELETE_ALL_NOTIFICATIONS", "Delete All Notifications"),
        ("MARK_ALL_NOTIFICATIONS_READ", "Mark All Notifications As Read"),
        ("MARK_NOTIFICATION_AS_READ", "Mark Notification As Read"),
        ("VIEW_NOTIFICATIONS", "View Notifications"),
        ("RESTORE_USER", "Restore User"),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="audit_logs")
    
    action = models.CharField(max_length=30, choices=ACTIONS)
    
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    user_agent = models.TextField(
        blank=True,
    )
    
    status = models.CharField(max_length=20, choices=[
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ], blank=True, default='SUCCESS')
    
    
    details = models.JSONField(default=dict, blank=True)

    created = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.user.email} - {self.action}"
    
    
    
class Notification(models.Model):
    
    # Notification Types
    WELCOME = "WELCOME"
    EMAIL_VERIFIED = "EMAIL_VERIFIED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    ROLE_CHANGED = "ROLE_CHANGED"
    ACCOUNT_RESTORED = "ACCOUNT_RESTORED"
    ACCOUNT_DELETED = "ACCOUNT_DELETED"
    SYSTEM = "SYSTEM"
    
    NOTIFICATION_TYPES = (
        (WELCOME, "Welcome"),
        (EMAIL_VERIFIED, "Email Verified"),
        (PASSWORD_CHANGED, "Password Changed"),
        (ROLE_CHANGED, "Role Changed"),
        (ACCOUNT_RESTORED, "Account Restored"),
        (ACCOUNT_DELETED, "Account Deleted"),
        (SYSTEM, "System"),
    )
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, 
        related_name="notifications",
        
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        default=SYSTEM,
    )
    is_read = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        
    def __str__(self):
        return f"{self.user.email} - {self.title}"