"""
Location tracking service for recording user locations during trips
"""

from decimal import Decimal
from typing import Optional

from django.contrib.auth import get_user_model
from django.utils import timezone
from travel.models import LocationHistory, Trip

User = get_user_model()


class LocationTracker:
    """Service for tracking and storing user locations"""

    @staticmethod
    def record_location(
        user: User,
        latitude: float,
        longitude: float,
        accuracy: Optional[float] = None,
        altitude: Optional[float] = None,
        speed: Optional[float] = None,
        heading: Optional[float] = None,
        is_background: bool = False,
        battery_level: Optional[int] = None,
        recorded_at: Optional[timezone.datetime] = None,
    ) -> LocationHistory:
        """
        Record a location point for a user

        Args:
            user: User object
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            accuracy: Location accuracy in meters
            altitude: Altitude in meters
            speed: Speed in m/s
            heading: Heading in degrees (0-360)
            is_background: Whether recorded in background
            battery_level: Device battery level (0-100)
            recorded_at: When location was recorded (defaults to now)

        Returns:
            LocationHistory object
        """
        if recorded_at is None:
            recorded_at = timezone.now()

        # Find active trip if any
        active_trip = Trip.objects.filter(
            user=user,
            is_active=True,
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date(),
        ).first()

        # Create location record
        location = LocationHistory.objects.create(
            user=user,
            trip=active_trip,
            latitude=Decimal(str(latitude)),
            longitude=Decimal(str(longitude)),
            accuracy=accuracy,
            altitude=altitude,
            speed=speed,
            heading=heading,
            is_background=is_background,
            battery_level=battery_level,
            recorded_at=recorded_at,
        )

        # Update user's current location in profile
        if hasattr(user, "profile"):
            user.profile.latitude = Decimal(str(latitude))
            user.profile.longitude = Decimal(str(longitude))
            user.profile.last_location_update = recorded_at
            user.profile.save(
                update_fields=["latitude", "longitude", "last_location_update"]
            )

        return location

    @staticmethod
    def get_recent_locations(user: User, trip: Optional[Trip] = None, limit: int = 100):
        """
        Get recent location history for a user

        Args:
            user: User object
            trip: Optional trip to filter by
            limit: Maximum number of records to return

        Returns:
            QuerySet of LocationHistory objects
        """
        queryset = LocationHistory.objects.filter(user=user)

        if trip:
            queryset = queryset.filter(trip=trip)

        return queryset[:limit]

    @staticmethod
    def get_trip_route(trip: Trip):
        """
        Get all location points for a trip to visualize the route

        Args:
            trip: Trip object

        Returns:
            QuerySet of LocationHistory objects ordered by time
        """
        return LocationHistory.objects.filter(trip=trip).order_by("recorded_at")

    @staticmethod
    def cleanup_old_locations(days: int = 90):
        """
        Delete location records older than specified days

        Args:
            days: Number of days to keep

        Returns:
            Number of records deleted
        """
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        count, _ = LocationHistory.objects.filter(recorded_at__lt=cutoff_date).delete()
        return count
