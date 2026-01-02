import logging
import random
import string
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


def generate_otp(length=6):
    """Generate a numeric OTP of given length."""

    return "".join(random.choices(string.digits, k=length))


def send_otp_email(
    user, otp, subject="Your Verification OTP", template_name="otp+email.txt"
):
    """Send OTP via email."""

    message = f"Hi {user.first_name},\n\nYour OTP is: {otp}\n\nThis OTP is valid for {settings.OTP_EXPIRATION_MINUTES} minutes.\n\nThank you!"

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        logger.info(f"OTP email sent successfully to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Error sending OTP email to {user.email}: {str(e)}")
        return False


def valid_otp(user, otp_input, expiration_min):
    """Checks if the provided OTP is valid and not expired."""

    if not user.otp_secret or not user.otp_created_at:
        return False, "No OTP found. Please request a new one."

    if user.otp_secret != otp_input:
        return False, "Invalid OTP. Please try again."

    expiration_time = user.otp_created_at + timedelta(minutes=expiration_min)
    if timezone.now() > expiration_time:
        return False, "OTP has expired. Please request a new one."

    return True, "OTP is valid."


def get_email_from_payload_handler(payload):
    """Extract email from JWT payload."""

    return payload.get("email") or payload.get("email_id") or payload.get("sub")
