import logging

import firebase_admin
from django.conf import settings
from firebase_admin import auth, credentials

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
try:
    if not firebase_admin._apps:
        # Check if service account file is provided
        firebase_key = getattr(settings, "FIREBASE_SERVICE_ACCOUNT_KEY", None)
        if firebase_key:
            cred = credentials.Certificate(firebase_key)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized with service account")
        else:
            # Skip Firebase initialization if no service account provided
            # Firebase auth will not be available until configured
            logger.warning(
                "Firebase service account not configured. OAuth login will not work until FIREBASE_SERVICE_ACCOUNT_KEY is set in settings."
            )
except Exception as e:
    logger.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")


def verify_firebase_token(id_token):
    """
    Verify Firebase ID token and return decoded token data.

    Args:
        id_token (str): Firebase ID token from mobile app

    Returns:
        tuple: (success: bool, data: dict or error_message: str)
    """
    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)

        # Extract user information
        user_data = {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "email_verified": decoded_token.get("email_verified", False),
            "name": decoded_token.get("name"),
            "picture": decoded_token.get("picture"),
            "provider": decoded_token.get("firebase", {}).get("sign_in_provider"),
        }

        return True, user_data

    except auth.ExpiredIdTokenError:
        logger.warning("Firebase token has expired")
        return False, "Token has expired. Please sign in again."

    except auth.RevokedIdTokenError:
        logger.warning("Firebase token has been revoked")
        return False, "Token has been revoked. Please sign in again."

    except auth.InvalidIdTokenError:
        logger.warning("Invalid Firebase token")
        return False, "Invalid token. Please sign in again."

    except Exception as e:
        logger.error(f"Error verifying Firebase token: {str(e)}")
        return False, f"Authentication error: {str(e)}"


def get_or_create_user_from_firebase(user_data):
    """
    Get or create a user based on Firebase authentication data.

    Args:
        user_data (dict): User data from Firebase token

    Returns:
        tuple: (user: User, created: bool)
    """
    from user.models import User

    email = user_data.get("email")
    firebase_uid = user_data.get("uid")
    provider = user_data.get("provider", "google")

    if not email:
        raise ValueError("Email is required from Firebase authentication")

    if not firebase_uid:
        raise ValueError("Firebase UID is required from Firebase authentication")

    try:
        # Try to get existing user by firebase_uid first (most reliable)
        user = User.objects.get(firebase_uid=firebase_uid)
        created = False

        # Update user info if needed
        if not user.email_verified and user_data.get("email_verified"):
            user.email_verified = True
            user.is_active = True
            user.save()

    except User.DoesNotExist:
        # Try to find by email (user might have registered with email/password first)
        try:
            user = User.objects.get(email=email)
            created = False

            # Link Firebase account to existing user
            user.firebase_uid = firebase_uid
            user.auth_provider = provider
            if user_data.get("email_verified"):
                user.email_verified = True
                user.is_active = True

            # Set profile image URL if available and user doesn't have one
            picture_url = user_data.get("picture")
            if picture_url and not user.profile.profile_image_url:
                user.profile.profile_image_url = picture_url
                user.profile.save()
                logger.info(f"Profile image URL set for existing user: {email}")

            user.save()

        except User.DoesNotExist:
            # Create new user from Firebase data
            name_parts = user_data.get("name", "").split(" ", 1)
            first_name = name_parts[0] if name_parts else "User"
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            user = User.objects.create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                email_verified=user_data.get("email_verified", False),
                is_active=True,
                auth_provider=provider,
                firebase_uid=firebase_uid,
                # Set a random unusable password since OAuth user doesn't need one
                password=None,
            )

            # Set unusable password for OAuth users
            user.set_unusable_password()
            user.save()

            # Set profile image URL if available
            picture_url = user_data.get("picture")
            if picture_url:
                user.profile.profile_image_url = picture_url
                user.profile.save()
                logger.info(f"Profile image URL set for new user: {email}")

            created = True

    return user, created
