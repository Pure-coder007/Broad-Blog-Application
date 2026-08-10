from . import views
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("jwt/create/", TokenObtainPairView.as_view(), name="jwt_create"),
    path("jwt/refresh/", TokenRefreshView.as_view(), name="jwt_refresh"),
    path("jwt/verify/", TokenVerifyView.as_view(), name="jwt_verify"),
    path(
        "verify-email/<uidb64>/<token>/",
        views.VerifyEmailView.as_view(),
        name="verify-email",
    ),
    path(
        "resend-email-verification/",
        views.ResendVerificationEmailView.as_view(),
        name="resend-email-verification",
    ),
    path(
        "forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"
    ),
    path(
        "reset-password/<uidb64>/<token>/",
        views.ResetPasswordView.as_view(),
        name="reset-password",
    ),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path(
        "change-password/", views.ChangePasswordView.as_view(), name="change-password"
    ),
    path("user-profile/", views.ProfileView.as_view(), name="user-profile"),
    path("update-profile/", views.UpdateProfileView.as_view(), name="update-profile"),
    path(
        "profile/upload-profile-picture/",
        views.ProfilePictureUploadView.as_view(),
        name="upload-profile-picture",
    ),
    path("profile/upload-cv/", views.FileUploadView.as_view(), name="upload-cv"),
    path("delete-account/", views.DeleteAccountView.as_view(), name="delete-account"),
    path("change-email/", views.ChangeEmailView.as_view(), name="change-email"),
    path(
        "confirm-email-change/<uidb64>/<token>",
        views.ConfirmEmailChangeView.as_view(),
        name="confirm-email-change",
    ),
    path(
        "admin-dashboard/", views.AdminDashboardView.as_view(), name="admin-dashboard"
    ),
    path(
        "admin/users/<uuid:user_id>/role/",
        views.ChangeUserRoleView.as_view(),
        name="change-user-role",
    ),
    path("admin/users/", views.AdminUserListView.as_view(), name="admin-user-list"),
    path(
        "admin/users/<uuid:user_id>/",
        views.AdminUserDetailView.as_view(),
        name="admin-user-detail",
    ),
    path(
        "admin/users/<uuid:user_id>/status/",
        views.ChangeUserStatusView.as_view(),
        name="change-user-status",
    ),
    path(
        "admin/users/<uuid:user_id>/delete/",
        views.DeleteUserView.as_view(),
        name="delete-user",
    ),
    path(
        "admin/users/<uuid:user_id>/restore/",
        views.RestoreUserView.as_view(),
        name="restore-user",
    ),
    path("sessions/", views.UserSessionListView.as_view(), name="user-sessions"),
    path(
        "logout-all/", views.LogoutAllDevicesView.as_view(), name="logout-all-devices"
    ),
    path("notifications/", views.NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/<uuid:notification_id>/",
        views.NotificationDetailView.as_view(),
        name="notification-detail",
    ),
    path(
        "notifications/<uuid:notification_id>/mark-as-read/",
        views.MarkNotificationAsReadView.as_view(),
        name="mark-notification-as-read",
    ),
    path(
        "notifications/read-all/",
        views.MarkAllNotificationsAsRead.as_view(),
        name="read-all",
    ),
    path(
        "delete/notifications/<notification_id>/",
        views.DeleteNotificationView.as_view(),
        name="delete-notification",
    ),
    path(
        "delete/notifications/",
        views.DeleteAllNotificationsView.as_view(),
        name="delete-all-notifications",
    ),
]
