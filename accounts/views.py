from django.shortcuts import render
from .serializer import SignUpSerializer, ResendVerificationSerializer, ForgotPasswordSerializer, ChangePasswordSerializer, ResetPasswordSerializer, ProfileSerializer, UpdateProfileSerializer, ProfilePictureSerializer, FileUploadSerializer, DeleteAccountSerializer, ChangeEmailSerializer, ChangeUserRoleSerializer, AdminUserSerializer, ChangeUserStatusSerializer, UserSessionSerializer
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny, IsAuthenticated
from .tokens import create_jwt_pair_for_user
from rest_framework.throttling import ScopedRateThrottle
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
import os
from .services import create_notification
from django.utils import timezone
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.shortcuts import get_object_or_404
from .tokens import email_verification_token
from .utils import send_verification_email, create_audit_log, get_client_ip
from .models import User, PasswordHistory, AuditLog, UserSession, Notification
from posts.models import Post
from django.db.models import Q
from user_agents import parse
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.contrib.auth.tokens import default_token_generator
from rest_framework.parsers import MultiPartParser, FormParser
from .permissions import IsAdmin, IsAdminOrModerator, IsModerator

today = timezone.now().date()



# Paginator class
class AdminUserPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 100



# Create your views here.
class SignUpView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = SignUpSerializer

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    @transaction.atomic
    def post(self, request: Request):

        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            # ==========================
            # Create User
            # ==========================
            user = serializer.save()

            # ==========================
            # Generate Verification Link
            # ==========================
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = email_verification_token.make_token(user)

            verification_link = request.build_absolute_uri(
                f"/auth/verify-email/{uid}/{token}/"
            )
            
            create_notification(
                user=user,
                title="Welcome to Broad Blog",
                message=f"Thank you for creating an account. We're excited to have you with us!",
                notification_type=Notification.WELCOME
            )


            # ==========================
            # Send Email
            # ==========================
            send_verification_email(
                subject="Verify your email",
                message=f"Click the link below:\n\n{verification_link}",
                recipient=user.email,
            )

            # ==========================
            # Audit Log
            # ==========================
            create_audit_log(
                request=request,
                user=user,
                action="REGISTER",
                status="SUCCESS",
                details={
                    "registered_user": user.email,
                },
            )
            
            
            return Response(
                {
                    "message": (
                        "Registration successful. "
                        "Please check your email to verify your account."
                    ),
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            transaction.set_rollback(True)

            return Response(
                {
                    "message": "Registration failed.",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        try:
            # Decode the user's ID from the URL
            uid = force_str(urlsafe_base64_decode(uidb64))
            # Retrieve the user
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"message": "Invalid verification link."}, status=status.HTTP_400_BAD_REQUEST)
        
        

        # Check if the account has already been verified
        if user.is_active:
            return Response({"message": "Email is already verified."}, status=status.HTTP_409_CONFLICT)

        # Validate the verification token
        if email_verification_token.check_token(user, token):
            user.is_active = True
            user.save(update_fields=["is_active"])
            
            create_notification(
                user=user,
                title="Email Verified",
                message="Your email has been verified successfully.",
                notification_type=Notification.EMAIL_VERIFIED,
            )
            
            return Response(
                {"message": "Email verified successfully.", "data": {"email": user.email, "username": user.username}},
                status=status.HTTP_200_OK)
            
        

        # Invalid or expired token
        return Response({"message": "Invalid or expired verification link."}, status=status.HTTP_400_BAD_REQUEST)




class LoginView(APIView):
    permission_classes = [AllowAny]

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @transaction.atomic
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        # ==========================
        # Check if user exists
        # ==========================

        try:
            user = User.objects.get(email=email)

        except User.DoesNotExist:

            return Response(
                {
                    "message": "Invalid email or password."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================
        # Check if account is deleted
        # ==========================

        if user.is_deleted:

            return Response(
                {
                    "message": "Account has already been deleted."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================
        # Check email verification
        # ==========================

        if not user.is_active:

            return Response(
                {
                    "message": "Please verify your email before logging in."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ==========================
        # Authenticate user
        # ==========================

        user = authenticate(
            email=email,
            password=password,
        )

        if user is None:

            return Response(
                {
                    "message": "Invalid email or password."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================
        # Generate JWT Tokens
        # ==========================

        tokens = create_jwt_pair_for_user(user)

        # ==========================
        # Save Login Session
        # ==========================
        
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        
        agent = parse(user_agent)
        
        parts = [
            agent.browser.family,
            agent.browser.version_string,
            "on",
            agent.os.family,
            agent.os.version_string,
        ]

        device_name = " ".join(filter(None, parts))

        UserSession.objects.create(
            user=user,
            refresh_token=tokens["refresh"],
            ip_address=get_client_ip(request),
            user_agent=user_agent,
            device_name=device_name
        )

        # ==========================
        # Create Audit Log
        # ==========================

        create_audit_log(
            request=request,
            user=user,
            action="LOGIN",
            status="SUCCESS",
            details={
                "email": user.email,
            },
        )

        # ==========================
        # Success Response
        # ==========================

        return Response(
            {
                "message": "Login successful.",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "role": user.role,
                },
                "token": tokens,
            },
            status=status.HTTP_200_OK,
        )

    def get(self, request):

        return Response(
            {
                "user": str(request.user),
                "auth": str(request.auth),
            },
            status=status.HTTP_200_OK,
        )

class ResendVerificationEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "resend_verification"

    def post(self, request: Request):
        serializer = ResendVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "Validation failed.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        email = serializer.validated_data["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "message": "If an account with that email exists and is not yet verified, a verification email has been sent."},
                status=status.HTTP_200_OK)
        if user.is_active:
            return Response({"message": "Email is already verified."}, status=status.HTTP_409_CONFLICT)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)

        verification_link = request.build_absolute_uri(
            f"/auth/verify-email/{uid}/{token}/"
        )

        send_verification_email(
            subject="Verify your email",
            message=f"Click the link below:\n\n{verification_link}",
            recipient=user.email,
        )
        return Response({"message": "Verification email sent successfully."}, status=status.HTTP_200_OK)


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "forgot_password"

    def post(self, request: Request):
        serializer = ForgotPasswordSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                "message": "Validation failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        email = serializer.validated_data["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {
                    "message": (
                        "If an account with that email exists, "
                        "a password reset link has been sent."
                    )
                },
                status=status.HTTP_200_OK,
            )

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        reset_link = request.build_absolute_uri(
            f"/auth/reset-password/{uid}/{token}/"
        )
        print(uid)
        print("Reset link", reset_link)

        send_verification_email(
            subject="Reset your password",
            message=f"Click the link below:\n\n{reset_link}",
            recipient=user.email,
        )
        
        user = request.user
        
        create_audit_log(
            request=request,
            user=user,
            action="PASSWORD_RESET",
            details={
                "method": "reset-link"
            }
            )
        
        return Response({"message": "If an account with that email exists, a password reset link has been sent."},
                        status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        serializer = ResetPasswordSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "message": "Validation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)

        except (
                TypeError,
                ValueError,
                OverflowError,
                User.DoesNotExist,
        ):
            return Response(
                {
                    "message": "Invalid password reset link."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not default_token_generator.check_token(user, token):
            return Response(
                {
                    "message": "Invalid or expired password reset link."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(
            serializer.validated_data["password"]
        )
        
        

        user.save(update_fields=["password"])
        
        

        return Response(
            {
                "message": "Password reset successfully."
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {
                    "message": "Refresh token is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            create_audit_log(
                request=request,
                user=request.user,
                action="LOGOUT",
                status="SUCCESS",
                details={
                    "email": request.user.email,
                },
            )

            return Response(
                {
                    "message": "Logged out successfully."
                },
                status=status.HTTP_200_OK,
            )

        except TokenError:

            transaction.set_rollback(True)

            create_audit_log(
                request=request,
                user=request.user,
                action="LOGOUT",
                status="FAILED",
                details={
                    "reason": "Invalid or expired refresh token",
                },
            )

            return Response(
                {
                    "message": "Invalid or expired refresh token."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )




class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "change_password"

    def post(self, request: Request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        
        serializer.is_valid(raise_exception=True)
            
        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        
        if not user.check_password(old_password):
            return Response({"message": "Invalid old password."}, status=status.HTTP_400_BAD_REQUEST)
        
        if user.check_password(new_password):
            return Response({"message": "New password cannot be the same as the old password."}, status=status.HTTP_400_BAD_REQUEST)
        
        history = PasswordHistory.objects.filter(user=user).order_by("-created")[:5]

        for previous_password in history:
            if check_password(new_password, previous_password.password):
                return Response(
                    {
                        "message": "New password cannot be the same as the last 5 passwords."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        with transaction.atomic():
            PasswordHistory.objects.create(
                user=user,
                password=user.password,
            )

            user.set_password(new_password)
            user.save(update_fields=["password"])
            

            all_history = PasswordHistory.objects.filter(user=user).order_by("-created")

            if all_history.count() > 5:
                all_history[5:].delete()
           
        user = request.user     
                
        create_audit_log(
            request=request,
            user=user,
            action="PASSWORD_CHANGE",
            details={
                "method": "authenticated"
            }
        )
        
        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)
    
        
    
    
    



class ProfileView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = ProfileSerializer(request.user.profile)
        
        return Response({
            "message": "Profile retrieved successfully",
            "profile": serializer.data
        }, status=status.HTTP_200_OK)
        
        
        

class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def patch(self, request):
        profile = request.user.profile
        serializer = UpdateProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )
        
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        user = request.user
        
        create_audit_log(
            request=request,
            user=user,
            action="UPDATE_PROFILE",
            details={
                "updated_fields": list(serializer.validated_data.keys())

            }
        )
        
        return Response({
            "message": "Profile updated successfully",
            "profile": ProfileSerializer(profile).data,
        }, status=status.HTTP_200_OK,)
        
        
    


class ProfilePictureUploadView(APIView):
    permission_classes = [IsAuthenticated]
    
    parser_classes = [MultiPartParser, FormParser]
    
    def patch(self, request):
        profile = request.user.profile
        
        serializer = ProfilePictureSerializer(profile, data=request.data, partial=True)
        
        serializer.is_valid(raise_exception=True)
        
        # Delete old picture if one exists
        if profile.profile_picture:
            if os.path.isfile(profile.profile_picture.path):
                os.remove(profile.profile_picture.path)
            
        serializer.save()
        
        return Response({
            "message": "Profile picture updated successfully",
            "profile_picture": request.build_absolute_uri(profile.profile_picture.url)
        }, status=status.HTTP_200_OK,)
        
        


class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request):
        profile = request.user.profile
        
        # Check if a file was actually uploaded
        if not request.FILES.get("cv"):
            return Response(
                {
                    "message": "Please upload a CV."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
                    
        print("FILES:", request.FILES)
        print("DATA:", request.data)
        print("CONTENT TYPE:", request.content_type)
                

        serializer = FileUploadSerializer(
            profile,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        print(serializer.validated_data)

        old_file = profile.cv

        profile = serializer.save()
        
        print(profile.cv)
        print(profile.cv.name)

        if old_file and old_file != profile.cv:
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)
        user = request.user       
        
        create_audit_log(
            request=request,
            user=user,
            action="CV_UPLOAD",
            details={
                "filename": profile.cv.name,
                "size": profile.cv.size,
            }
        )
        

        return Response(
            {
                "message": "CV uploaded successfully.",
                "cv": request.build_absolute_uri(profile.cv.url),
            },
            status=status.HTTP_200_OK,
        )
        
        
        
        
        
        
class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        serializer = DeleteAccountSerializer(
            data = request.data,
            context = {'request': request},
        )
        
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        if user.is_deleted:
                return Response({
                    "message": "Account has already been deleted."
                }, status=status.HTTP_400_BAD_REQUEST,)
            
        
        with transaction.atomic():
            user.is_deleted = True
            user.is_active = False
            user.deleted_at = timezone.now()
            
            
            user.save(
                update_fields=[
                    "is_deleted",
                    "is_active",
                    "deleted_at",
                ]
            )
        
        user = request.user
            
        create_audit_log(
            request=request,
            user=user,
            action="DELETE_ACCOUNT",
            details={
                "email": user.email
            }
        )
            
        return Response({
            "message": "Account deleted successfully"
        }, status=status.HTTP_200_OK,)
        
        
        
        

class ChangeEmailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def patch(self, request):
        serializer = ChangeEmailSerializer(
            data = request.data,
            context={"request": request},
        )
        
        serializer.is_valid(raise_exception=True)
        user = request.user
        
        new_email = serializer.validated_data["new_email"]
        
        user.pending_email = new_email
        user.save(update_fields=["pending_email"])
        
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        
        verification_link = request.build_absolute_uri(
            f"/auth/confirm-email-change/{uid}/{token}"
        )
        
        
        send_verification_email(
            subject="Confirm your new email",
            message=f"Click the link below:\n\n{verification_link}",
            recipient=new_email,
        )
        
        create_audit_log(
            request=request,
            user=request.user,
            action="EMAIL_CHANGE_REQUEST",
            details={
                "pending_email": new_email,
            },
        )
        
        return Response({
            "message": "A verification email has been sent to your new email address."
        }, status=status.HTTP_200_OK,)
        
        

class ConfirmEmailChangeView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        
        except(
            TypeError,
            ValueError,
            OverflowError,
            User.DoesNotExist,
        ):
        
            return Response({
                "message": "Invalid verification link"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not email_verification_token.check_token(user, token):
            return Response({
                "message": "Invalid or expired verification link"
            })
            
        if not user.pending_email:
            return Response({
                "message": "No pending email change found"
            }, status=status.HTTP_400_BAD_REQUEST,)
            
        
        old_email = user.email
        
        with transaction.atomic():
            user.email = user.pending_email
            user.pending_email = None
            user.save(update_fields=["email", "pending_email"])
            
            
        create_audit_log(
            request=request,
            user=user,
            action="EMAIL_CHANGED",
            status="SUCCESS",
            details={
                "old_email": old_email,
                "new_email": user.email
            }
        )
        
        return Response({
            "message": "Email changed successfully",
            "email": user.email,
        }, status=status.HTTP_200_OK,)
        
        

class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        today = timezone.now().date()

        # ==========================
        # User Statistics
        # ==========================

        total_users = User.objects.count()

        total_active_users = User.objects.filter(
            is_active=True
        ).count()

        total_inactive_users = User.objects.filter(
            is_active=False
        ).count()

        total_deleted_users = User.objects.filter(
            is_deleted=True
        ).count()

        total_admin_users = User.objects.filter(
            role=User.ADMIN
        ).count()

        total_moderator_users = User.objects.filter(
            role=User.MODERATOR
        ).count()

        total_normal_users = User.objects.filter(
            role=User.USER
        ).count()

        total_superusers = User.objects.filter(
            is_superuser=True
        ).count()

        today_registrations = User.objects.filter(
            profile__created__date=today
        ).count()

        recent_users = User.objects.order_by(
            "-profile__created"
        )[:5]

        # ==========================
        # Post Statistics
        # ==========================

        total_posts = Post.objects.count()

        todays_posts = Post.objects.filter(
            created__date=today
        ).count()

        # ==========================
        # Audit Log Statistics
        # ==========================

        total_audit_logs = AuditLog.objects.count()

        recent_audit_logs = AuditLog.objects.order_by(
            "-created"
        )[:5]

        # ==========================
        # Audit Log
        # ==========================

        create_audit_log(
            request=request,
            user=request.user,
            action="ADMIN_DASHBOARD",
            status="SUCCESS",
            details={
                "dashboard": "overview",
            },
        )

        # ==========================
        # Response
        # ==========================

        return Response(
            {
                "message": "Admin dashboard loaded successfully.",
                "data": {
                    "users": {
                        "total": total_users,
                        "active": total_active_users,
                        "inactive": total_inactive_users,
                        "deleted": total_deleted_users,
                        "admins": total_admin_users,
                        "moderators": total_moderator_users,
                        "normal_users": total_normal_users,
                        "superusers": total_superusers,
                        "today_registrations": today_registrations,
                        "recent_users": [
                            {
                                "id": user.id,
                                "username": user.username,
                                "email": user.email,
                                "role": user.role,
                                "is_active": user.is_active,
                                "created": user.profile.created,
                            }
                            for user in recent_users
                        ],
                    },
                    "posts": {
                        "total": total_posts,
                        "today": todays_posts,
                    },
                    "audit_logs": {
                        "total": total_audit_logs,
                        "recent": [
                            {
                                "user": log.user.email,
                                "action": log.action,
                                "status": log.status,
                                "ip_address": log.ip_address,
                                "created": log.created,
                                "user_agent": log.user_agent,
                                "details": log.details,
                            }
                            for log in recent_audit_logs
                        ],
                    },
                },
            },
            status=status.HTTP_200_OK,
        )
        
        
        


class ChangeUserRoleView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, user_id):
        serializer = ChangeUserRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = get_object_or_404(User, id=user_id)
        new_role = serializer.validated_data["role"]

        # Prevent changing your own role
        if request.user == user:
            return Response(
                {
                    "message": "You cannot change your own role."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent modifying superusers
        if user.is_superuser:
            return Response(
                {
                    "message": "You cannot modify a superuser."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Prevent assigning the same role
        if user.role == new_role:
            return Response(
                {
                    "message": f"{user.username} is already a {new_role}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Only superusers can assign the Admin role
        if (
            new_role == User.ADMIN
            and not request.user.is_superuser
        ):
            return Response(
                {
                    "message": "Only superusers can assign the Admin role."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        old_role = user.role

        user.role = new_role
        user.save(update_fields=["role"])

        create_audit_log(
            request=request,
            user=request.user,
            action="ROLE_CHANGED",
            status="SUCCESS",
            details={
                "target_user": user.email,
                "old_role": old_role,
                "new_role": new_role,
            },
        )

        return Response(
            {
                "message": "User role updated successfully.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "old_role": old_role,
                    "new_role": new_role,
                    "is_active": user.is_active,
                    "is_deleted": user.is_deleted,
                    # "is_admin": user.is_admin,
                    "is_superuser": user.is_superuser,
                },
            },
            status=status.HTTP_200_OK,
        )
        
        

class AdminUserListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):

        users = User.objects.all()
        role = request.query_params.get("role")
        is_active = request.query_params.get("is_active")
        is_deleted = request.query_params.get("is_deleted")
        ordering = request.query_params.get("ordering", "-date_joined")
        

        search = request.query_params.get("search")

        if search:
            users = users.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        users = users.order_by("-date_joined")
        
        
        if role:
            users = users.filter(role=role.upper())
        
        if is_active:
            users = users.filter(is_active=is_active.lower() == "true")
        
        if is_deleted:
            users = users.filter(is_deleted=is_deleted.lower() == "true")
            
        allowed_orderings = [
            "username",
            "-username",
            "email",
            "-email",
            "date_joined",
            "-date_joined",
            "role",
            "-role"
        ]   
        
        if ordering in allowed_orderings:
            users = users.order_by(ordering)
        else:
            users = users.order_by("-date_joined")
        
        
        # serializer = AdminUserSerializer(users, many=True)
        paginator = AdminUserPagination()
        
        paginated_users = paginator.paginate_queryset(
            users,
            request
        )
        
        serializer = AdminUserSerializer(paginated_users, many=True)

        create_audit_log(
            request=request,
            user=request.user,
            action="VIEW_USERS",
            status="SUCCESS",
            details={
                "count": users.count(),
                "search": search,
            },
        )

        return paginator.get_paginated_response(
            {
                "message": "Users retrieved successfully.",
                "users": serializer.data,
            }
        )
        
        
        




class AdminUserDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        serializer = AdminUserSerializer(user)
        
        create_audit_log(
            request=request,
            user=request.user,
            action="VIEW_USER",
            status="SUCCESS",
            details={
                "viewed_user": user.email,
                "user_id": str(user.id),
            },
        )
        
        return Response(
            {
                "message": "User retrieved successfully.",
                "user": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
        
        
        
        

class ChangeUserStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def patch(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        
        # Prevent an admin from disabling themselves
        if user == request.user:
            return Response({
                "message": "You cannot change your own account status"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ChangeUserStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        old_status = user.is_active
        new_status = serializer.validated_data["is_active"]
        
        if old_status == new_status:
            return Response({
                "message": f"User is already {'active' if new_status else 'inactive'}"
            }, status=status.HTTP_400_BAD_REQUEST,)
        
        
        user.is_active = new_status
        user.save(update_fields=["is_active"])
        
        create_audit_log(
            request=request,
            user=request.user,
            action="CHANGE_USER_STATUS",
            status="SUCCESS",
            details={
                "target_user": user.email,
                "old_status": old_status,
                "new_status": new_status,
            },
        )
        
        return Response(
            {
                "message": "User status updated successfully.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "old_status": old_status,
                    "new_status": new_status,
                    "is_active": user.is_active,
                    "is_deleted": user.is_deleted,
                    # "is_admin": user.is_admin,
                    "is_superuser": user.is_superuser,
                },
            },
            status=status.HTTP_200_OK,
        )
        
        
        
class DeleteUserView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def patch(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        
        
        # Prevent deleting yourself
        if user == request.user:
            return Response({
                "message": "You cannot delete your own account"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if user.is_deleted:
            return Response({
                "message": "User has already been deleted"
            }, status=status.HTTP_400_BAD_REQUEST)
            
            
        user.is_deleted = True
        user.is_active = False
        user.deleted_at = timezone.now()
        user.save(update_fields=["is_deleted", "is_active", "deleted_at"])
        
        create_audit_log(
            request=request,
            user=request.user,
            action="DELETE_USER",
            status="SUCCESS",
            details={
                "deleted_user": user.email,
                "deleted_by": request.user.email
            },
        )
        
        return Response(
            {
                "message": "User deleted successfully.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "email": user.email,
                    "is_active": user.is_active,
                    "is_deleted": user.is_deleted,
                    "deleted_at": user.deleted_at,
                    # "is_admin": user.is_admin,
                    "is_superuser": user.is_superuser,
                }
            },
            status=status.HTTP_200_OK,
        )
        


class RestoreUserView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def patch(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        
        if user == request.user:
            return Response({
                "message": "You cannot restore your own account"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not user.is_deleted:
            return Response({
                "message": "This user is not deleted"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.is_deleted = False
        user.is_active = True
        user.deleted_at = None
        user.restored_at = timezone.now()
        user.save(update_fields=["is_deleted", "is_active", "deleted_at", "restored_at"])
        
        create_audit_log(
            request=request,
            user=request.user,
            action="RESTORE_USER",
            status="SUCCESS",
            details={
                "restored_user": user.email,
                "restored_by": request.user.email
            },
        )
        
        return Response(
            {
                "message": "User restored successfully.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "email": user.email,
                    "is_active": user.is_active,
                    "is_deleted": user.is_deleted,
                    "restored_at": user.restored_at,
                    # "is_admin": user.is_admin,
                    "is_superuser": user.is_superuser,
                }
            },
            status=status.HTTP_200_OK,
        )
        
        


class UserSessionListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        sessions = UserSession.objects.filter(
            user=request.user,
            is_active=True,
        ).order_by("-created")
        
        serializer = UserSessionSerializer(
            sessions,
            many=True,
        )
        
        create_audit_log(
            request=request,
            user=request.user,
            action="VIEW_SESSIONS",
            status="SUCCESS",
            details={
                "total_sessions": sessions.count()
            },
        )
        
        return Response(
            {
                "message": "User sessions retrieved successfully.",
                "count": sessions.count(),
                "user_sessions": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
        
        
        
        

class LogoutAllDevicesView(APIView):
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        sessions = UserSession.objects.filter(
            user=request.user,
            is_active=True,
        )
        
        logged_out = 0
        
        for session in sessions:
            try:
                RefreshToken(session.refresh_token).blacklist()
            except TokenError:
                pass
            
            session.is_active = False
            session.save(update_fields=["is_active"])
            
            logged_out += 1
            
        create_audit_log(
            request=request,
            user=request.user,
            action="LOGOUT_ALL_DEVICES",
            status="SUCCESS",
            details={
                "total_sessions": sessions.count(),
                "sessions_logged_out": logged_out,
            },
        )
        
        return Response(
            {
                "message": "Logged out from all devices successfully.",
                "total_sessions": sessions.count(),
                "sessions_logged_out": logged_out,
            },
            status=status.HTTP_200_OK,
        )