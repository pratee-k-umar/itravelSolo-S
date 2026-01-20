import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

# Create your models here.


class Trip(models.Model):
    """Trip model for travel planning and matching"""

    PRIVACY_CHOICES = [
        ("public", "Public"),
        ("friends_only", "Friends Only"),
        ("private", "Private"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trips"
    )

    # Location
    origin = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    origin_lat = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    origin_lng = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    destination_lat = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    destination_lng = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    route_polyline = models.TextField(blank=True, null=True)

    # Dates
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Trip details
    interests = models.JSONField(
        default=list,
        help_text="List of interests/activities for the trip",
        blank=True,
    )
    description = models.TextField(blank=True)

    # Companions
    max_companions = models.PositiveIntegerField(default=0)
    current_companions = models.PositiveIntegerField(default=0)

    # Status
    is_active = models.BooleanField(
        default=False,
        help_text="Whether the trip has been started and matching is active",
    )

    # Settings
    privacy = models.CharField(
        max_length=20, choices=PRIVACY_CHOICES, default="friends_only"
    )

    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.first_name}'s trip from {self.origin} to {self.destination}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["destination"]),
        ]

    @property
    def duration_days(self):
        """Calculate trip duration in days"""
        return (self.end_date - self.start_date).days + 1

    @property
    def is_upcoming(self):
        """Check if trip is in the future"""
        return self.start_date > timezone.now().date()

    @property
    def is_ongoing(self):
        """Check if trip is currently ongoing based on dates"""
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date


class TripMatch(models.Model):
    """Match between trips for companion finding"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="matches")
    matched_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trip_matches"
    )
    matched_trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="reverse_matches",
        null=True,
        blank=True,
    )

    # Matching details
    score = models.FloatField(help_text="Matching score (0-100)")
    common_interests = models.JSONField(default=list)
    distance_km = models.FloatField(
        null=True, blank=True, help_text="Distance between destinations in km"
    )

    # Real-time proximity tracking
    current_distance_km = models.FloatField(
        null=True,
        blank=True,
        help_text="Current real-time distance between users in km",
    )
    last_distance_update = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When current_distance_km was last updated",
    )
    is_proximity_expired = models.BooleanField(
        default=False,
        help_text="Auto-expired due to distance threshold exceeded",
    )

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-score", "-created_at"]
        unique_together = ["trip", "matched_user"]
        indexes = [
            models.Index(fields=["trip", "status"]),
            models.Index(fields=["matched_user", "status"]),
        ]

    def __str__(self):
        return f"Match: {self.trip.user.first_name} → {self.matched_user.first_name} ({self.score:.1f}%)"


class LocationHistory(models.Model):
    """Track user location history during active trips"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="location_history",
    )
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="location_points",
        null=True,
        blank=True,
        help_text="Associated trip if location was recorded during active trip",
    )

    # Location data
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy = models.FloatField(
        null=True,
        blank=True,
        help_text="Location accuracy in meters",
    )
    altitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Altitude in meters",
    )

    # Metadata
    speed = models.FloatField(
        null=True,
        blank=True,
        help_text="Speed in meters per second",
    )
    heading = models.FloatField(
        null=True,
        blank=True,
        help_text="Heading/bearing in degrees (0-360)",
    )

    # Context
    is_background = models.BooleanField(
        default=False,
        help_text="Whether location was recorded in background",
    )
    battery_level = models.IntegerField(
        null=True,
        blank=True,
        help_text="Device battery level (0-100)",
    )

    # Timestamps
    recorded_at = models.DateTimeField(
        help_text="When the location was actually recorded by device",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["user", "-recorded_at"]),
            models.Index(fields=["trip", "-recorded_at"]),
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["recorded_at"]),
        ]
        verbose_name = "Location History"
        verbose_name_plural = "Location Histories"

    def __str__(self):
        return f"{self.user.email} @ ({self.latitude}, {self.longitude}) - {self.recorded_at}"


class TripSuggestion(models.Model):
    """AI-generated contextual suggestions during trips"""

    SUGGESTION_TYPES = [
        ("activity", "Activity"),
        ("food", "Food"),
        ("safety", "Safety"),
        ("cultural", "Cultural"),
        ("hidden_gem", "Hidden Gem"),
        ("timing", "Timing"),
        ("warning", "Warning"),
        ("activity_hotspot", "Activity Hotspot"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trip_suggestions",
    )
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="suggestions",
    )

    # Suggestion content
    suggestion_type = models.CharField(max_length=20, choices=SUGGESTION_TYPES)
    content = models.TextField(help_text="The suggestion text generated by AI")
    title = models.CharField(max_length=255, blank=True)

    # Location context where suggestion was generated
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    location_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name of place if suggestion is location-specific",
    )

    # Related place from insights DB (if applicable)
    related_place_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of related place from insights app",
    )

    # Hotspot-specific data (for activity_hotspot type)
    hotspot_user_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of users at this hotspot location",
    )
    hotspot_friend_names = models.JSONField(
        default=list,
        blank=True,
        help_text="List of friend names if any friends are in the hotspot",
    )

    # User engagement
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_acted_upon = models.BooleanField(
        default=False,
        help_text="Whether user acted on this suggestion",
    )
    user_rating = models.IntegerField(
        null=True,
        blank=True,
        help_text="User rating 1-5 stars",
    )
    is_dismissed = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "trip", "-created_at"]),
            models.Index(fields=["trip", "is_read"]),
            models.Index(fields=["suggestion_type"]),
            models.Index(fields=["latitude", "longitude"]),
        ]
        verbose_name = "Trip Suggestion"
        verbose_name_plural = "Trip Suggestions"

    def __str__(self):
        return f"{self.suggestion_type}: {self.title or self.content[:50]} - {self.user.email}"


class ActivityHotspot(models.Model):
    """Tracks real-time clusters of app users at locations"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Location
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    place_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name of the place (matched from insights DB)",
    )
    related_place_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of related place from insights app",
    )

    # Hotspot metadata
    user_count = models.IntegerField(default=0)
    active_users = models.JSONField(
        default=list,
        help_text="List of user IDs currently at this location",
    )

    # Timestamps
    first_detected = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        help_text="When this hotspot expires if no activity",
    )

    class Meta:
        ordering = ["-last_activity"]
        indexes = [
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["-last_activity"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["user_count"]),
        ]
        verbose_name = "Activity Hotspot"
        verbose_name_plural = "Activity Hotspots"

    def __str__(self):
        return f"Hotspot at {self.place_name or f'({self.latitude}, {self.longitude})'} - {self.user_count} users"

    @property
    def is_expired(self):
        """Check if hotspot has expired"""
        return timezone.now() > self.expires_at
