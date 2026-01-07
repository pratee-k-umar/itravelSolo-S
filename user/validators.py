"""
Validation utilities for user input.
"""

import re
from typing import Tuple


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