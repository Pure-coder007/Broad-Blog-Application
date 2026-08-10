from rest_framework import serializers
from .models import User, Profile, UserSession, Notification
from django.contrib.auth.password_validation import validate_password
import os


# ROLE_CHOICES = (
#         ("USER", "User"),
#         ("MODERATOR", "Moderator"),
#         ("ADMIN", "Admin"),
#         )


# from rest_framework.authtoken.models import Token


class SignUpSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=80)
    username = serializers.CharField(max_length=80)
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "password",
            "password_confirm",
        )

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = False
        user.save()
        return user


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    confirm_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        validate_password(attrs["new_password"], self.context["request"].user)
        return attrs


# USER PROFILE SECTION


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Profile
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "bio",
            "phone_number",
            "country",
            "city",
            "website",
            "profile_picture",
            "date_of_birth",
        )


class UpdateProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = Profile
        fields = (
            "first_name",
            "last_name",
            "bio",
            "phone_number",
            "country",
            "city",
            "website",
            "profile_picture",
            "date_of_birth",
        )

    def validate(self, attrs):
        allowed_fields = set(self.fields.keys())
        received_fields = set(self.initial_data.keys())

        unknown_fields = received_fields - allowed_fields

        if unknown_fields:
            raise serializers.ValidationError(
                {field: "Unknown field." for field in unknown_fields}
            )

        return attrs


class ProfilePictureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("profile_picture",)

    def validate_profile_picture(self, value):

        # maximum size 2MB
        max_size = 2 * 1024 * 1024

        if value.size > max_size:
            raise serializers.ValidationError("Image size should not exceed 2MB.")

        # Allowed file types
        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]

        ext = os.path.splitext(value.name)[1].lower()

        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                "Only JPG, JPEG, PNG and WEBP images are allowed."
            )

        return value


class FileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("cv",)

    def validate_cv(self, value):
        MAX_FILE_SIZE = 5 * 1024 * 1024

        allowed_extensions = (
            ".pdf",
            ".doc",
            ".docx",
        )

        allowed_content_types = (
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        ext = os.path.splitext(value.name)[1].lower()

        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                "Only PDF, DOC and DOCX files are allowed."
            )

        if value.content_type not in allowed_content_types:
            raise serializers.ValidationError("Invalid file type.")

        if value.size > MAX_FILE_SIZE:
            raise serializers.ValidationError("Maximum file size is 5 MB.")

        return value


class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    def validate_password(self, value):
        user = self.context["request"].user

        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect password.")

        return value


class ChangeEmailSerializer(serializers.Serializer):
    new_email = serializers.EmailField()

    def validate_new_email(self, value):
        user = self.context["request"].user

        if value == user.email:
            raise serializers.ValidationError("This is already your current email.")

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")

        if User.objects.filter(pending_email=value).exists():
            raise serializers.ValidationError(
                "This email is awaiting verification by another user."
            )

        return value


class ChangeUserRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)


class AdminUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "is_active",
            "is_deleted",
            "is_superuser",
            "date_joined",
            "last_login",
        ]


class ChangeUserStatusSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class UserSessionSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserSession
        fields = [
            "id",
            "ip_address",
            "user_agent",
            "created",
            "last_activity",
            "is_active",
            "device_name",
        ]


class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "notification_type",
            "is_read",
            "created",
        ]
