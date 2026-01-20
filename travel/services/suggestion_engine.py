"""
AI-powered suggestion engine for contextual travel tips
Generates suggestions when users are near significant places
"""

from decimal import Decimal
from math import atan2, cos, radians, sin, sqrt
from typing import Dict, List, Optional

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from insights.models import (
    FamousPlace,
    HiddenGem,
    MostFamousPlace,
    Place,
    ThingToDo,
    TouristTrap,
)
from insights.services.client.gemini_client import GeminiClient
from travel.models import LocationHistory, Trip, TripSuggestion

User = get_user_model()


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points in meters using Haversine formula

    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates

    Returns:
        Distance in meters
    """
    R = 6371000  # Earth radius in meters

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


class SuggestionEngine:
    """Generates contextual AI suggestions based on location"""

    # Proximity thresholds (in meters)
    FAMOUS_PLACE_RADIUS = 100
    HIDDEN_GEM_RADIUS = 50
    TOURIST_TRAP_RADIUS = 200
    ACTIVITY_LOCATION_RADIUS = 150

    def __init__(self):
        self.gemini_client = GeminiClient.get_client()

    def check_and_generate_suggestions(
        self,
        user: User,
        trip: Trip,
        latitude: float,
        longitude: float,
    ) -> List[TripSuggestion]:
        """
        Main entry point: check if user is near significant places and generate suggestions

        Args:
            user: User object
            trip: Active trip
            latitude: Current latitude
            longitude: Current longitude

        Returns:
            List of generated TripSuggestion objects
        """
        generated_suggestions = []

        # Check if already suggested for this location recently
        if self._already_suggested_here(user, trip, latitude, longitude):
            return []

        # Find nearby significant places
        nearby_places = self._find_nearby_places(latitude, longitude)

        if not nearby_places:
            return []

        # Generate suggestions for each nearby place
        for place_info in nearby_places:
            suggestion = self._generate_suggestion(
                user=user,
                trip=trip,
                latitude=latitude,
                longitude=longitude,
                place_info=place_info,
            )
            if suggestion:
                generated_suggestions.append(suggestion)

        return generated_suggestions

    def _already_suggested_here(
        self,
        user: User,
        trip: Trip,
        latitude: float,
        longitude: float,
        radius: float = 50.0,
    ) -> bool:
        """
        Check if we already generated suggestion near this location
        Prevents duplicate suggestions for same place
        """
        recent_suggestions = TripSuggestion.objects.filter(
            user=user,
            trip=trip,
            created_at__gte=timezone.now() - timezone.timedelta(hours=2),
        )

        for suggestion in recent_suggestions:
            distance = calculate_distance(
                float(suggestion.latitude),
                float(suggestion.longitude),
                latitude,
                longitude,
            )
            if distance < radius:
                return True

        return False

    def _find_nearby_places(
        self,
        latitude: float,
        longitude: float,
    ) -> List[Dict]:
        """
        Find all significant places near current location

        Returns list of dicts with place info and type
        """
        nearby = []

        # Check famous places
        famous_places = MostFamousPlace.objects.all()
        for place in famous_places:
            distance = calculate_distance(
                latitude, longitude, place.latitude, place.longitude
            )
            if distance <= self.FAMOUS_PLACE_RADIUS:
                nearby.append(
                    {
                        "type": "famous_place",
                        "name": place.name,
                        "quote": place.quote,
                        "distance": distance,
                        "place_id": place.id,
                        "city": place.place.city,
                    }
                )

        # Check other famous places
        other_famous = FamousPlace.objects.all()
        for place in other_famous:
            distance = calculate_distance(
                latitude, longitude, place.latitude, place.longitude
            )
            if distance <= self.FAMOUS_PLACE_RADIUS:
                nearby.append(
                    {
                        "type": "famous_place",
                        "name": place.name,
                        "quote": place.reason,
                        "distance": distance,
                        "place_id": place.id,
                        "city": place.place.city,
                    }
                )

        # Check hidden gems
        hidden_gems = HiddenGem.objects.exclude(
            latitude__isnull=True, longitude__isnull=True
        )
        for gem in hidden_gems:
            distance = calculate_distance(
                latitude, longitude, gem.latitude, gem.longitude
            )
            if distance <= self.HIDDEN_GEM_RADIUS:
                nearby.append(
                    {
                        "type": "hidden_gem",
                        "name": gem.name,
                        "description": gem.description,
                        "distance": distance,
                        "place_id": gem.id,
                        "city": gem.place.city,
                    }
                )

        # Check tourist traps
        tourist_traps = TouristTrap.objects.exclude(
            latitude__isnull=True, longitude__isnull=True
        )
        for trap in tourist_traps:
            distance = calculate_distance(
                latitude, longitude, trap.latitude, trap.longitude
            )
            if distance <= self.TOURIST_TRAP_RADIUS:
                nearby.append(
                    {
                        "type": "tourist_trap",
                        "name": trap.name,
                        "description": trap.reason,
                        "distance": distance,
                        "place_id": trap.id,
                        "city": trap.place.city,
                    }
                )

        # Check activity locations
        activities = ThingToDo.objects.exclude(
            latitude__isnull=True, longitude__isnull=True
        )
        for activity in activities:
            distance = calculate_distance(
                latitude, longitude, activity.latitude, activity.longitude
            )
            if distance <= self.ACTIVITY_LOCATION_RADIUS:
                nearby.append(
                    {
                        "type": "activity",
                        "name": f"{activity.activity_type} at {activity.location}",
                        "activity_type": activity.activity_type,
                        "location": activity.location,
                        "time": activity.time or "Anytime",
                        "distance": distance,
                        "place_id": activity.id,
                        "city": activity.place.city,
                    }
                )

        return nearby

    def _generate_suggestion(
        self,
        user: User,
        trip: Trip,
        latitude: float,
        longitude: float,
        place_info: Dict,
    ) -> Optional[TripSuggestion]:
        """
        Generate AI suggestion using Gemini for a specific place
        """
        try:
            # Build context-specific prompt
            prompt = self._build_prompt(user, trip, place_info)

            # Call Gemini
            response = self.gemini_client.generate_content(prompt)
            suggestion_text = response.text.strip()

            # Determine suggestion type
            suggestion_type = self._determine_type(place_info["type"])

            # Create suggestion
            suggestion = TripSuggestion.objects.create(
                user=user,
                trip=trip,
                suggestion_type=suggestion_type,
                content=suggestion_text,
                title=place_info["name"],
                latitude=Decimal(str(latitude)),
                longitude=Decimal(str(longitude)),
                location_name=place_info.get("city", ""),
                related_place_id=place_info.get("place_id"),
            )

            return suggestion

        except Exception as e:
            print(f"Error generating suggestion: {e}")
            return None

    def _build_prompt(self, user: User, trip: Trip, place_info: Dict) -> str:
        """Build Gemini prompt based on place type and context"""

        current_hour = timezone.now().hour
        time_of_day = self._get_time_of_day(current_hour)

        base_prompt = f"""You are a knowledgeable local travel guide. A traveler is currently near {place_info['name']} in {place_info.get('city', 'the area')}.

Current context:
- Time: {time_of_day}
- Distance: {int(place_info['distance'])}m away
- Traveler interests: {', '.join(trip.interests) if trip.interests else 'general exploration'}
"""

        if place_info["type"] == "famous_place":
            prompt = (
                base_prompt
                + f"""
This is a famous landmark. Provide a helpful, concise suggestion (2-3 sentences) about:
- Best way to experience it right now
- Insider tip most tourists don't know
- What to watch out for

Keep it friendly and actionable."""
            )

        elif place_info["type"] == "hidden_gem":
            prompt = (
                base_prompt
                + f"""
This is a hidden gem: {place_info['description']}

Provide an enthusiastic, concise tip (2-3 sentences) about:
- Why it's special
- What to do/see there
- Best time if applicable

Make them excited to discover it!"""
            )

        elif place_info["type"] == "tourist_trap":
            prompt = (
                base_prompt
                + f"""
This is a known tourist trap: {place_info['description']}

Provide a friendly warning (2-3 sentences) with:
- What to be aware of
- Better alternatives nearby if you know any
- How to enjoy it without getting scammed if they still want to visit

Be helpful, not preachy."""
            )

        elif place_info["type"] == "activity":
            prompt = (
                base_prompt
                + f"""
This is an activity location: {place_info['activity_type']}
Best time: {place_info['time']}

Provide practical advice (2-3 sentences):
- Is now a good time for this activity?
- What to bring/prepare
- Pro tip for this activity

Be specific and actionable."""
            )

        else:
            prompt = (
                base_prompt
                + "\nProvide a helpful travel tip (2-3 sentences) for this location."
            )

        return prompt

    def _get_time_of_day(self, hour: int) -> str:
        """Convert hour to readable time of day"""
        if 5 <= hour < 12:
            return "Morning"
        elif 12 <= hour < 17:
            return "Afternoon"
        elif 17 <= hour < 21:
            return "Evening"
        else:
            return "Night"

    def _determine_type(self, place_type: str) -> str:
        """Map place type to suggestion type"""
        mapping = {
            "famous_place": "cultural",
            "hidden_gem": "hidden_gem",
            "tourist_trap": "warning",
            "activity": "activity",
        }
        return mapping.get(place_type, "activity")
