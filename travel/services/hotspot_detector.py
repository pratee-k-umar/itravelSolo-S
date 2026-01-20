"""
Activity Hotspot Detection Service

Detects when multiple iTravelSolo users cluster at a location,
creating real-time activity notifications for nearby travelers.
"""

import math
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
from travel.models import ActivityHotspot, LocationHistory, Trip, TripSuggestion
from user.models import Profile, User


class HotspotDetector:
    """Detects and manages activity hotspots"""

    # Configuration - Use settings with fallbacks
    MIN_USERS_FOR_HOTSPOT = getattr(settings, "HOTSPOT_MIN_USERS", 2)
    CLUSTER_RADIUS_KM = getattr(settings, "HOTSPOT_CLUSTER_RADIUS_KM", 0.1)
    NOTIFICATION_RADIUS_KM = getattr(settings, "HOTSPOT_NOTIFICATION_RADIUS_KM", 1.5)
    ACTIVITY_WINDOW_MINUTES = getattr(settings, "HOTSPOT_ACTIVITY_WINDOW_MINUTES", 30)
    HOTSPOT_EXPIRY_MINUTES = getattr(settings, "HOTSPOT_EXPIRY_MINUTES", 60)

    def __init__(self, user: User):
        self.user = user
        self.now = timezone.now()

    def detect_and_notify(
        self, latitude: float, longitude: float
    ) -> Optional[TripSuggestion]:
        """
        Main method: Detect hotspots and create notifications

        Args:
            latitude: User's current latitude
            longitude: User's current longitude

        Returns:
            TripSuggestion if a hotspot notification was created, None otherwise
        """
        # First, cleanup expired hotspots
        self._cleanup_expired_hotspots()

        # Update or create hotspots based on recent activity
        self._update_hotspots()

        # Check if user is on an active trip
        active_trip = self._get_active_trip()
        if not active_trip:
            return None

        # Find nearby hotspots (within notification radius)
        nearby_hotspot = self._find_nearby_hotspot(latitude, longitude)

        if nearby_hotspot:
            # Check if user is already AT the hotspot (too close)
            distance_to_hotspot = self._calculate_distance(
                latitude,
                longitude,
                float(nearby_hotspot.latitude),
                float(nearby_hotspot.longitude),
            )

            # Don't notify if user is already at the hotspot
            if distance_to_hotspot < self.CLUSTER_RADIUS_KM:
                return None

            # Create notification
            return self._create_hotspot_notification(
                active_trip, nearby_hotspot, latitude, longitude, distance_to_hotspot
            )

        return None

    def _cleanup_expired_hotspots(self):
        """Remove expired hotspots"""
        ActivityHotspot.objects.filter(expires_at__lt=self.now).delete()

    def _update_hotspots(self):
        """Scan recent location history and update/create hotspots"""
        # Get all recent locations (last 30 minutes) from users on active trips
        recent_time = self.now - timedelta(minutes=self.ACTIVITY_WINDOW_MINUTES)

        # Get users on active trips
        active_trip_users = Trip.objects.filter(
            is_active=True,
            start_date__lte=self.now.date(),
            end_date__gte=self.now.date(),
        ).values_list("user_id", flat=True)

        # Get their recent locations (most recent per user)
        recent_locations = (
            LocationHistory.objects.filter(
                user_id__in=active_trip_users, recorded_at__gte=recent_time
            )
            .order_by("user_id", "-recorded_at")
            .distinct("user_id")
        )

        # Group locations into clusters
        clusters = self._cluster_locations(recent_locations)

        # Update or create hotspots for significant clusters
        for cluster in clusters:
            if cluster["user_count"] >= self.MIN_USERS_FOR_HOTSPOT:
                self._update_or_create_hotspot(cluster)

    def _cluster_locations(self, locations: List[LocationHistory]) -> List[Dict]:
        """
        Group locations into clusters based on proximity

        Args:
            locations: List of LocationHistory objects

        Returns:
            List of clusters with metadata
        """
        clusters = []
        processed_users = set()

        for location in locations:
            if location.user_id in processed_users:
                continue

            # Find all nearby locations (within cluster radius)
            nearby = []
            for other_location in locations:
                if other_location.user_id in processed_users:
                    continue

                distance = self._calculate_distance(
                    float(location.latitude),
                    float(location.longitude),
                    float(other_location.latitude),
                    float(other_location.longitude),
                )

                if distance <= self.CLUSTER_RADIUS_KM:
                    nearby.append(other_location)
                    processed_users.add(other_location.user_id)

            if len(nearby) >= self.MIN_USERS_FOR_HOTSPOT:
                # Calculate cluster center (average position)
                avg_lat = sum(float(loc.latitude) for loc in nearby) / len(nearby)
                avg_lng = sum(float(loc.longitude) for loc in nearby) / len(nearby)

                # Try to match with a known place
                place_name, place_id = self._match_place(avg_lat, avg_lng)

                clusters.append(
                    {
                        "latitude": avg_lat,
                        "longitude": avg_lng,
                        "user_count": len(nearby),
                        "user_ids": [loc.user_id for loc in nearby],
                        "place_name": place_name,
                        "place_id": place_id,
                    }
                )

        return clusters

    def _match_place(
        self, latitude: float, longitude: float
    ) -> Tuple[str, Optional[str]]:
        """
        Try to match coordinates with a known place from insights DB

        Args:
            latitude: Cluster center latitude
            longitude: Cluster center longitude

        Returns:
            Tuple of (place_name, place_id)
        """
        # Try to import insights models (may not exist in all environments)
        try:
            from insights.models import (
                HiddenGem,
                MostFamousPlace,
                ThingToDo,
                TouristTrap,
            )

            # Search for nearby places (within 200m)
            search_radius = 0.2  # km

            # Check each place type
            for model in [MostFamousPlace, HiddenGem, TouristTrap, ThingToDo]:
                places = model.objects.all()
                for place in places:
                    if hasattr(place, "latitude") and hasattr(place, "longitude"):
                        distance = self._calculate_distance(
                            latitude,
                            longitude,
                            float(place.latitude),
                            float(place.longitude),
                        )
                        if distance <= search_radius:
                            return (place.name, str(place.id))

        except ImportError:
            pass

        return ("", None)

    def _update_or_create_hotspot(self, cluster: Dict):
        """Update existing hotspot or create new one"""
        # Check if there's an existing hotspot nearby
        existing_hotspots = ActivityHotspot.objects.filter(expires_at__gte=self.now)

        for hotspot in existing_hotspots:
            distance = self._calculate_distance(
                cluster["latitude"],
                cluster["longitude"],
                float(hotspot.latitude),
                float(hotspot.longitude),
            )

            # If within cluster radius, update existing hotspot
            if distance <= self.CLUSTER_RADIUS_KM:
                hotspot.user_count = cluster["user_count"]
                hotspot.active_users = cluster["user_ids"]
                hotspot.last_activity = self.now
                hotspot.expires_at = self.now + timedelta(
                    minutes=self.HOTSPOT_EXPIRY_MINUTES
                )
                if cluster["place_name"]:
                    hotspot.place_name = cluster["place_name"]
                    hotspot.related_place_id = cluster["place_id"]
                hotspot.save()
                return

        # Create new hotspot
        ActivityHotspot.objects.create(
            latitude=Decimal(str(cluster["latitude"])),
            longitude=Decimal(str(cluster["longitude"])),
            place_name=cluster["place_name"],
            related_place_id=cluster["place_id"],
            user_count=cluster["user_count"],
            active_users=cluster["user_ids"],
            expires_at=self.now + timedelta(minutes=self.HOTSPOT_EXPIRY_MINUTES),
        )

    def _get_active_trip(self) -> Optional[Trip]:
        """Get user's active trip if any"""
        return Trip.objects.filter(
            user=self.user,
            is_active=True,
            start_date__lte=self.now.date(),
            end_date__gte=self.now.date(),
        ).first()

    def _find_nearby_hotspot(
        self, latitude: float, longitude: float
    ) -> Optional[ActivityHotspot]:
        """
        Find hotspots within notification radius

        Args:
            latitude: User's current latitude
            longitude: User's current longitude

        Returns:
            Closest hotspot within notification radius, or None
        """
        active_hotspots = ActivityHotspot.objects.filter(
            expires_at__gte=self.now, user_count__gte=self.MIN_USERS_FOR_HOTSPOT
        )

        closest_hotspot = None
        min_distance = float("inf")

        for hotspot in active_hotspots:
            distance = self._calculate_distance(
                latitude,
                longitude,
                float(hotspot.latitude),
                float(hotspot.longitude),
            )

            if distance <= self.NOTIFICATION_RADIUS_KM and distance < min_distance:
                min_distance = distance
                closest_hotspot = hotspot

        return closest_hotspot

    def _create_hotspot_notification(
        self,
        trip: Trip,
        hotspot: ActivityHotspot,
        user_lat: float,
        user_lng: float,
        distance_km: float,
    ) -> Optional[TripSuggestion]:
        """
        Create a hotspot notification for the user

        Args:
            trip: User's active trip
            hotspot: The nearby hotspot
            user_lat: User's current latitude
            user_lng: User's current longitude
            distance_km: Distance to hotspot in km

        Returns:
            Created TripSuggestion or None
        """
        # Check if we already sent this notification recently (avoid spam)
        recent_time = self.now - timedelta(hours=2)
        existing_notification = TripSuggestion.objects.filter(
            user=self.user,
            trip=trip,
            suggestion_type="activity_hotspot",
            related_place_id=hotspot.related_place_id,
            created_at__gte=recent_time,
        ).exists()

        if existing_notification:
            return None

        # Get friend names if any friends are in the hotspot
        friend_names = self._get_friend_names_in_hotspot(hotspot)

        # Create appropriate message
        location_text = (
            hotspot.place_name or f"({hotspot.latitude}, {hotspot.longitude})"
        )
        distance_text = (
            f"{distance_km:.1f}km"
            if distance_km >= 1
            else f"{int(distance_km * 1000)}m"
        )

        if friend_names:
            # Friends are present
            friends_text = ", ".join(friend_names)
            title = "🔥 Your Friends Are Nearby!"
            content = (
                f"Your friends {friends_text} are part of a crowd of "
                f"{hotspot.user_count} iTravelSolo travelers at {location_text} "
                f"({distance_text} from you). Want to check it out?"
            )
        else:
            # Only strangers
            title = "🔥 Activity Nearby!"
            content = (
                f"{hotspot.user_count} iTravelSolo travelers are currently at "
                f"{location_text} ({distance_text} from you). "
                f"Something interesting might be happening! Want to check it out?"
            )

        # Create suggestion
        suggestion = TripSuggestion.objects.create(
            user=self.user,
            trip=trip,
            suggestion_type="activity_hotspot",
            title=title,
            content=content,
            latitude=Decimal(str(hotspot.latitude)),
            longitude=Decimal(str(hotspot.longitude)),
            location_name=hotspot.place_name,
            related_place_id=hotspot.related_place_id,
            hotspot_user_count=hotspot.user_count,
            hotspot_friend_names=friend_names,
        )

        return suggestion

    def _get_friend_names_in_hotspot(self, hotspot: ActivityHotspot) -> List[str]:
        """
        Get list of friend names who are at the hotspot

        Args:
            hotspot: The hotspot to check

        Returns:
            List of friend names
        """
        # Get user's friends
        try:
            user_profile = Profile.objects.get(user=self.user)
            friend_ids = user_profile.friends.values_list("id", flat=True)
        except Profile.DoesNotExist:
            return []

        # Check which friends are in the hotspot
        friend_names = []
        for user_id in hotspot.active_users:
            if user_id in friend_ids:
                try:
                    friend_profile = Profile.objects.get(user_id=user_id)
                    name = (
                        friend_profile.name or friend_profile.user.email.split("@")[0]
                    )
                    friend_names.append(name)
                except Profile.DoesNotExist:
                    continue

        return friend_names

    def _calculate_distance(
        self, lat1: float, lng1: float, lat2: float, lng2: float
    ) -> float:
        """
        Calculate distance between two coordinates using Haversine formula

        Args:
            lat1, lng1: First coordinate
            lat2, lng2: Second coordinate

        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers

        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)

        # Haversine formula
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        return R * c
