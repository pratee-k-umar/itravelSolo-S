"""
Validation utilities for user input.
"""

import re
from typing import Tuple


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email format.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required."

    # Basic email regex pattern
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(email_pattern, email):
        return False, "Invalid email format."

    if len(email) > 254:  # RFC 5321
        return False, "Email address is too long."

    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validate password strength.

    Requirements:
    - At least 8 characters
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required."

    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if len(password) > 128:
        return False, "Password is too long (max 128 characters)."

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."

    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."

    # Optional: Check for special characters
    # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
    #     return False, "Password must contain at least one special character."

    return True, ""


def validate_name(name: str, field_name: str = "Name") -> Tuple[bool, str]:
    """
    Validate user name fields (first_name, last_name).

    Args:
        name: Name to validate
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, f"{field_name} is required."

    if len(name) < 2:
        return False, f"{field_name} must be at least 2 characters long."

    if len(name) > 50:
        return False, f"{field_name} is too long (max 50 characters)."

    # Allow letters, spaces, hyphens, and apostrophes
    if not re.match(r"^[a-zA-Z\s\-']+$", name):
        return False, f"{field_name} contains invalid characters."

    return True, ""


def validate_phone_number(phone: str) -> Tuple[bool, str]:
    """
    Validate phone number format.

    Args:
        phone: Phone number to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return True, ""  # Phone is optional

    # Remove common separators
    cleaned = re.sub(r"[\s\-\(\)]", "", phone)

    # Check if it starts with + and contains only digits after that
    if cleaned.startswith("+"):
        if not cleaned[1:].isdigit():
            return False, "Invalid phone number format."
        if len(cleaned) < 10 or len(cleaned) > 15:
            return False, "Phone number must be between 10 and 15 digits."
    else:
        if not cleaned.isdigit():
            return False, "Invalid phone number format."
        if len(cleaned) < 10 or len(cleaned) > 15:
            return False, "Phone number must be between 10 and 15 digits."

    return True, ""


def validate_url(url: str, field_name: str = "URL") -> Tuple[bool, str]:
    """
    Validate URL format.

    Args:
        url: URL to validate
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, f"{field_name} is required."

    url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"

    if not re.match(url_pattern, url, re.IGNORECASE):
        return False, f"Invalid {field_name} format."

    if len(url) > 500:
        return False, f"{field_name} is too long (max 500 characters)."

    return True, ""


def sanitize_input(text: str) -> str:
    """
    Sanitize user input by stripping whitespace and basic XSS prevention.

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Strip leading/trailing whitespace
    sanitized = text.strip()

    # Remove null bytes
    sanitized = sanitized.replace("\x00", "")

    return sanitized
