import graphene
from authentication.helpers.firebase_auth import (
    get_or_create_user_from_firebase,
    verify_firebase_token,
)
from authentication.helpers.utils import generate_otp, send_otp_email, valid_otp
from authentication.helpers.validators import (
    sanitize_input,
    validate_email,
    validate_name,
    validate_password,
)
from django.conf import settings
from django.utils import timezone
from graphql_jwt.shortcuts import create_refresh_token, get_token
from user.graphql.types import UserType
from user.models import User


class RegisterUserInput(graphene.InputObjectType):
    first_name = graphene.String(required=True)
    last_name = graphene.String(required=True)
    email = graphene.String(required=True)
    password = graphene.String(required=True)


class RegisterUser(graphene.Mutation):
    class Arguments:
        input = RegisterUserInput(required=True)

    user = graphene.Field(UserType)
    success = graphene.Boolean()
    message = graphene.String()
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, input):
        try:
            # Sanitize and validate inputs
            email = sanitize_input(input.email).lower()
            first_name = sanitize_input(input.first_name)
            last_name = sanitize_input(input.last_name)

            # Validate email
            is_valid_email, email_error = validate_email(email)
            if not is_valid_email:
                return RegisterUser(
                    user=None,
                    success=False,
                    message=email_error,
                    errors=[email_error],
                )

            # Validate names
            is_valid_first, first_error = validate_name(first_name, "First name")
            if not is_valid_first:
                return RegisterUser(
                    user=None,
                    success=False,
                    message=first_error,
                    errors=[first_error],
                )

            is_valid_last, last_error = validate_name(last_name, "Last name")
            if not is_valid_last:
                return RegisterUser(
                    user=None,
                    success=False,
                    message=last_error,
                    errors=[last_error],
                )

            # Validate password
            is_valid_pwd, pwd_error = validate_password(input.password)
            if not is_valid_pwd:
                return RegisterUser(
                    user=None,
                    success=False,
                    message=pwd_error,
                    errors=[pwd_error],
                )

            # Check if user already exists
            if User.objects.filter(email=email).exists():
                return RegisterUser(
                    user=None,
                    success=False,
                    message="User with this email already exists.",
                    errors=["Email already registered."],
                )

            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=input.password,
            )

            if (
                user.otp_created_at
                and (timezone.now() - user.otp_created_at).total_seconds()
                < settings.OTP_COOLDOWN_SECONDS
            ):
                return RegisterUser(
                    user=None,
                    success=False,
                    message="Please wait before requesting a new OTP.",
                    errors=["OTP request cooldown in effect."],
                )

            otp = generate_otp()
            user.otp_secret = otp
            user.otp_created_at = timezone.now()
            user.save()

            if send_otp_email(user, otp, subject="Email Verification OTP"):
                return RegisterUser(
                    user=user,
                    success=True,
                    message="User registered successfully. OTP sent to your email for verification.",
                    errors=None,
                )
            else:
                return RegisterUser(
                    user=user,
                    success=False,
                    message="User registered, but failed to send OTP email.",
                    errors=["Failed to send OTP email."],
                )
        except Exception as e:
            return RegisterUser(user=None, success=False, errors=[str(e)])


class RequestEmailVerificationOTP(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info, email):
        try:
            user = User.objects.get(email=email)
            if user.email_verified:
                return RequestEmailVerificationOTP(
                    success=False, message="Email is already verified."
                )

            if (
                user.otp_created_at
                and (timezone.now() - user.otp_created_at).total_seconds()
                < settings.OTP_COOLDOWN_SECONDS
            ):
                return RequestEmailVerificationOTP(
                    success=False, message="Please wait before requesting a new OTP."
                )

            otp = generate_otp()
            user.otp_secret = otp
            user.otp_created_at = timezone.now()
            user.save()

            if send_otp_email(user, otp, subject="Email Verification OTP"):
                return RequestEmailVerificationOTP(
                    success=True, message="OTP sent to your email."
                )
            else:
                return RequestEmailVerificationOTP(
                    success=False, message="Failed to send OTP email."
                )
        except User.DoesNotExist:
            return RequestEmailVerificationOTP(
                success=False, message="User with this email does not exist."
            )

        except Exception as e:
            return RequestEmailVerificationOTP(success=False, message=str(e))


class VerifyEmailOTP(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        otp = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    token = graphene.String()
    refresh_token = graphene.String()
    user = graphene.Field(UserType)

    @classmethod
    def mutate(cls, root, info, email, otp):
        try:
            user = User.objects.get(email=email)
            if user.email_verified:
                return VerifyEmailOTP(
                    success=False, message="Email is already verified.", user=None
                )

            is_valid, message = valid_otp(user, otp, settings.OTP_EXPIRATION_MINUTES)

            if not is_valid:
                return VerifyEmailOTP(success=False, message=message, user=None)

            user.email_verified = True
            user.is_active = True
            user.otp_secret = None
            user.otp_created_at = None
            user.save()

            token = get_token(user)
            refresh_token = create_refresh_token(user)

            return VerifyEmailOTP(
                success=True,
                message="Email verified successfully.",
                user=user,
                token=token,
                refresh_token=refresh_token,
            )

        except User.DoesNotExist:
            return VerifyEmailOTP(
                success=False, message="User with this email does not exist.", user=None
            )

        except Exception as e:
            return VerifyEmailOTP(
                success=False, message=f"An error occurred: {str(e)}", user=None
            )


class LoginUser(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    mfa_required = graphene.Boolean()
    token = graphene.String()
    refresh_token = graphene.String()
    user = graphene.Field(UserType)

    @classmethod
    def mutate(cls, root, info, email, password):
        try:
            user = User.objects.get(email=email)

            if not user.is_active:
                return LoginUser(
                    success=False,
                    message="Account is not active. Please verify your email.",
                    mfa_required=False,
                    token=None,
                    refresh_token=None,
                    user=None,
                )

            if not user.check_password(password):
                return LoginUser(
                    success=False,
                    message="Invalid credentials.",
                    mfa_required=False,
                    token=None,
                    refresh_token=None,
                    user=None,
                )

            if user.mfa_enabled:
                otp = generate_otp()
                user.otp_secret = otp
                user.otp_created_at = timezone.now()
                user.save()

                if send_otp_email(user, otp, subject="Your Two-factor OTP"):
                    return LoginUser(
                        success=True,
                        message="Two-factor OTP sent to your email.",
                        mfa_required=True,
                        token=None,
                        refresh_token=None,
                        user=None,
                    )

                else:
                    return LoginUser(
                        success=False,
                        message="Failed to send OTP email.",
                        mfa_required=False,
                        token=None,
                        refresh_token=None,
                        user=None,
                    )

            else:
                token = get_token(user)
                refresh_token = create_refresh_token(user)

                return LoginUser(
                    success=True,
                    message="Login successful.",
                    mfa_required=False,
                    token=token,
                    refresh_token=refresh_token,
                    user=user,
                )

        except User.DoesNotExist:
            return LoginUser(
                success=False,
                message="Invalid credentials.",
                mfa_required=False,
                token=None,
                refresh_token=None,
                user=None,
            )

        except Exception as e:
            return LoginUser(
                success=False,
                message=f"An error occurred: {str(e)}",
                mfa_required=False,
                token=None,
                refresh_token=None,
                user=None,
            )


class VerifyMFAOTP(graphene.Mutation):
    """Verify MFA OTP during login when MFA is enabled."""

    class Arguments:
        email = graphene.String(required=True)
        otp = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    token = graphene.String()
    refresh_token = graphene.String()
    user = graphene.Field(UserType)

    @classmethod
    def mutate(cls, root, info, email, otp):
        try:
            user = User.objects.get(email=email)

            if not user.is_active:
                return VerifyMFAOTP(
                    success=False,
                    message="Account is not active.",
                    token=None,
                    refresh_token=None,
                    user=None,
                )

            if not user.mfa_enabled:
                return VerifyMFAOTP(
                    success=False,
                    message="MFA is not enabled for this account.",
                    token=None,
                    refresh_token=None,
                    user=None,
                )

            is_valid, message = valid_otp(user, otp, settings.OTP_EXPIRATION_MINUTES)

            if not is_valid:
                return VerifyMFAOTP(
                    success=False,
                    message=message,
                    token=None,
                    refresh_token=None,
                    user=None,
                )

            # Clear OTP after successful verification
            user.otp_secret = None
            user.otp_created_at = None
            user.save()

            # Generate tokens
            token = get_token(user)
            refresh_token = create_refresh_token(user)

            return VerifyMFAOTP(
                success=True,
                message="MFA verification successful.",
                token=token,
                refresh_token=refresh_token,
                user=user,
            )

        except User.DoesNotExist:
            return VerifyMFAOTP(
                success=False,
                message="Invalid credentials.",
                token=None,
                refresh_token=None,
                user=None,
            )

        except Exception as e:
            return VerifyMFAOTP(
                success=False,
                message=f"An error occurred: {str(e)}",
                token=None,
                refresh_token=None,
                user=None,
            )


class RequestMFAEnableOTP(graphene.Mutation):
    """Request OTP to enable MFA for the authenticated user."""

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info):
        user = info.context.user

        if not user.is_authenticated:
            return RequestMFAEnableOTP(
                success=False, message="Authentication required."
            )

        if not user.email_verified:
            return RequestMFAEnableOTP(
                success=False, message="Email must be verified before enabling MFA."
            )

        if user.mfa_enabled:
            return RequestMFAEnableOTP(success=False, message="MFA is already enabled.")

        # Check cooldown
        if (
            user.otp_created_at
            and (timezone.now() - user.otp_created_at).total_seconds()
            < settings.OTP_COOLDOWN_SECONDS
        ):
            return RequestMFAEnableOTP(
                success=False, message="Please wait before requesting a new OTP."
            )

        otp = generate_otp()
        user.otp_secret = otp
        user.otp_created_at = timezone.now()
        user.save()

        if send_otp_email(user, otp, subject="Enable Two-Factor Authentication"):
            return RequestMFAEnableOTP(
                success=True, message="OTP sent to your email to enable MFA."
            )
        else:
            return RequestMFAEnableOTP(
                success=False, message="Failed to send OTP email."
            )


class EnableMFA(graphene.Mutation):
    class Arguments:
        otp = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    user = graphene.Field(UserType)

    @classmethod
    def mutate(cls, root, info, otp):
        user = info.context.user

        if not user.is_authenticated:
            return EnableMFA(
                success=False, message="Authentication required.", user=None
            )

        if user.mfa_enabled:
            return EnableMFA(
                success=False, message="MFA is already enabled.", user=user
            )

        is_valid, message = valid_otp(user, otp, settings.OTP_EXPIRATION_MINUTES)

        if not is_valid:
            return EnableMFA(success=False, message=message, user=user)

        user.mfa_enabled = True
        user.otp_secret = None
        user.otp_created_at = None
        user.save()
        return EnableMFA(success=True, message="MFA enabled successfully.", user=user)


class DisableMFA(graphene.Mutation):
    success = graphene.Boolean()
    message = graphene.String()
    user = graphene.Field(UserType)

    @classmethod
    def mutate(cls, root, info):
        user = info.context.user

        if not user.is_authenticated:
            return DisableMFA(
                success=False, message="Authentication required.", user=None
            )

        if not user.mfa_enabled:
            return DisableMFA(success=False, message="MFA is not enabled.", user=user)

        user.mfa_enabled = False
        user.otp_secret = None
        user.otp_created_at = None
        user.save()
        return DisableMFA(success=True, message="MFA disabled successfully.", user=user)


class FirebaseOAuthLogin(graphene.Mutation):
    """
    Authenticate user using Firebase ID token from mobile app.
    Mobile app authenticates with Firebase/Google, then sends the ID token here.
    """

    class Arguments:
        id_token = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    token = graphene.String()
    refresh_token = graphene.String()
    user = graphene.Field(UserType)
    is_new_user = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, id_token):
        try:
            # Verify Firebase token
            is_valid, result = verify_firebase_token(id_token)

            if not is_valid:
                return FirebaseOAuthLogin(
                    success=False,
                    message=result,  # Error message
                    token=None,
                    refresh_token=None,
                    user=None,
                    is_new_user=False,
                )

            # Get or create user from Firebase data
            user_data = result
            user, created = get_or_create_user_from_firebase(user_data)

            # Generate JWT tokens
            token = get_token(user)
            refresh_token_value = create_refresh_token(user)

            return FirebaseOAuthLogin(
                success=True,
                message=(
                    "Authentication successful."
                    if not created
                    else "Account created and authenticated successfully."
                ),
                token=token,
                refresh_token=refresh_token_value,
                user=user,
                is_new_user=created,
            )

        except ValueError as e:
            return FirebaseOAuthLogin(
                success=False,
                message=str(e),
                token=None,
                refresh_token=None,
                user=None,
                is_new_user=False,
            )

        except Exception as e:
            return FirebaseOAuthLogin(
                success=False,
                message=f"Authentication error: {str(e)}",
                token=None,
                refresh_token=None,
                user=None,
                is_new_user=False,
            )
