"""
Real-time proximity matching service
Tracks distance between matched users and auto-expires distant matches
"""

from decimal import Decimal
from math import atan2, cos, radians, sin, sqrt
from typing import List

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from travel.models import Trip, TripMatch

User = get_user_model()


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points in kilometers using Haversine formula

    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates

    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth radius in kilometers

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


class ProximityMatcher:
    """Manages real-time proximity tracking for trip matches"""

    # Distance thresholds
    CLOSE_PROXIMITY_KM = 0.5  # 500m - notify users they're very close
    NEARBY_THRESHOLD_KM = 2.0  # 2km - still nearby
    AUTO_EXPIRE_KM = 5.0  # 5km - auto-expire when users separate beyond this distance

    @staticmethod
    def update_match_distances(user: User, latitude: float, longitude: float) -> dict:
        """
        Update distances for all pending matches involving this user

        Args:
            user: User whose location updated
            latitude: Current latitude
            longitude: Current longitude

        Returns:
            Dict with stats: updated_count, expired_count, close_matches
        """
        stats = {
            "updated_count": 0,
            "expired_count": 0,
            "close_matches": [],
        }

        # Find all pending matches where this user is involved
        pending_matches = TripMatch.objects.filter(
            Q(trip__user=user) | Q(matched_user=user),
            status="pending",
            is_proximity_expired=False,
        )

        for match in pending_matches:
            # Determine the other user
            other_user = (
                match.matched_user if match.trip.user == user else match.trip.user
            )

            # Get other user's current location
            if not hasattr(other_user, "profile") or not other_user.profile.latitude:
                continue

            other_lat = float(other_user.profile.latitude)
            other_lng = float(other_user.profile.longitude)

            # Calculate current distance
            distance = calculate_distance_km(latitude, longitude, other_lat, other_lng)

            # Update match
            match.current_distance_km = distance
            match.last_distance_update = timezone.now()
            match.save(update_fields=["current_distance_km", "last_distance_update"])
            stats["updated_count"] += 1

            # Check if very close
            if distance <= ProximityMatcher.CLOSE_PROXIMITY_KM:
                stats["close_matches"].append(
                    {
                        "match_id": str(match.id),
                        "other_user": other_user.get_full_name(),
                        "distance_meters": int(distance * 1000),
                    }
                )

            # Check for auto-expiry
            if ProximityMatcher._should_expire(match, distance):
                match.is_proximity_expired = True
                match.status = "rejected"  # Auto-reject distant matches
                match.save(update_fields=["is_proximity_expired", "status"])
                stats["expired_count"] += 1

        return stats

    @staticmethod
    def _should_expire(match: TripMatch, current_distance: float) -> bool:
        """
        Determine if match should be auto-expired based on distance
        Expires only when users go OUT of range (beyond 5km)

        Args:
            match: TripMatch object
            current_distance: Current distance in km

        Returns:
            True if match should be expired
        """
        # Don't expire if already interacted with
        if match.status != "pending":
            return False

        # Expire immediately if beyond threshold - users separated
        if current_distance > ProximityMatcher.AUTO_EXPIRE_KM:
            return True

        return False

    @staticmethod
    def get_nearby_matches(user: User, max_distance_km: float = 2.0) -> List[TripMatch]:
        """
        Get all pending matches where users are currently nearby

        Args:
            user: User to check
            max_distance_km: Maximum distance to consider "nearby"

        Returns:
            List of TripMatch objects sorted by distance
        """
        pending_matches = TripMatch.objects.filter(
            Q(trip__user=user) | Q(matched_user=user),
            status="pending",
            is_proximity_expired=False,
            current_distance_km__lte=max_distance_km,
            current_distance_km__isnull=False,
        ).order_by("current_distance_km")

        return list(pending_matches)

    @staticmethod
    def check_close_proximity_alerts(user: User) -> List[dict]:
        """
        Check if user is very close to any matches (trigger alerts)

        Args:
            user: User to check

        Returns:
            List of dicts with match info for close proximity
        """
        close_matches = TripMatch.objects.filter(
            Q(trip__user=user) | Q(matched_user=user),
            status="pending",
            is_proximity_expired=False,
            current_distance_km__lte=ProximityMatcher.CLOSE_PROXIMITY_KM,
            current_distance_km__isnull=False,
        ).order_by("current_distance_km")

        alerts = []
        for match in close_matches:
            other_user = (
                match.matched_user if match.trip.user == user else match.trip.user
            )
            alerts.append(
                {
                    "match_id": str(match.id),
                    "other_user_id": str(other_user.id),
                    "other_user_name": other_user.get_full_name(),
                    "distance_meters": int(match.current_distance_km * 1000),
                    "match_score": match.score,
                }
            )

        return alerts

    @staticmethod
    def cleanup_expired_matches():
        """
        Periodic cleanup task to remove old expired matches
        Should be run via Celery task or cron

        Returns:
            Number of matches cleaned up
        """
        # Remove proximity-expired matches older than 7 days
        cutoff_date = timezone.now() - timezone.timedelta(days=7)
        count, _ = TripMatch.objects.filter(
            is_proximity_expired=True,
            updated_at__lt=cutoff_date,
        ).delete()

        return count
