"""
GraphQL Queries for Travel app
All query definitions for trip operations
"""

import graphene
from django.db.models import Q
from django.utils import timezone
from graphql_jwt.decorators import login_required
from travel.graphql.location_types import LocationHistoryType
from travel.graphql.suggestion_types import ActivityHotspotType, TripSuggestionType
from travel.graphql.types import TripMatchType, TripType
from travel.models import (
    ActivityHotspot,
    LocationHistory,
    Trip,
    TripMatch,
    TripSuggestion,
)


class TravelQueries(graphene.ObjectType):
    """Query definitions for travel operations"""

    # Trip queries
    my_trips = graphene.List(
        TripType, description="Get all trips for authenticated user"
    )
    trip_by_id = graphene.Field(TripType, trip_id=graphene.UUID(required=True))
    upcoming_trips = graphene.List(
        TripType, description="Get upcoming trips for authenticated user"
    )
    past_trips = graphene.List(
        TripType, description="Get past/completed trips for authenticated user"
    )
    active_trips = graphene.List(
        TripType, description="Get currently ongoing trips for authenticated user"
    )

    # Match queries
    trip_matches = graphene.List(
        TripMatchType,
        trip_id=graphene.UUID(required=True),
        status=graphene.String(),
        description="Get matches for a specific trip",
    )
    my_pending_matches = graphene.List(
        TripMatchType, description="Get all pending matches for user's trips"
    )

    # Suggestion queries
    my_trip_suggestions = graphene.List(
        TripSuggestionType,
        trip_id=graphene.UUID(),
        suggestion_type=graphene.String(),
        unread_only=graphene.Boolean(),
        description="Get AI suggestions for user's trips",
    )

    # Hotspot queries
    active_hotspots = graphene.List(
        ActivityHotspotType,
        latitude=graphene.Decimal(),
        longitude=graphene.Decimal(),
        radius_km=graphene.Float(),
        description="Get active hotspots near a location",
    )

    # Location history queries
    trip_location_history = graphene.List(
        LocationHistoryType,
        trip_id=graphene.UUID(required=True),
        description="Get location history for a specific trip",
    )

    # ==================== Trip Resolvers ====================

    @login_required
    def resolve_my_trips(self, info):
        """Return all trips for authenticated user"""
        return Trip.objects.filter(user=info.context.user)

    @login_required
    def resolve_trip_by_id(self, info, trip_id):
        """Return specific trip by ID"""
        try:
            return Trip.objects.get(id=trip_id, user=info.context.user)
        except Trip.DoesNotExist:
            return None

    @login_required
    def resolve_upcoming_trips(self, info):
        """Return upcoming trips (start date in the future)"""
        today = timezone.now().date()
        return Trip.objects.filter(user=info.context.user, start_date__gt=today)

    @login_required
    def resolve_past_trips(self, info):
        """Return past/completed trips"""
        today = timezone.now().date()
        return Trip.objects.filter(user=info.context.user, end_date__lt=today)

    @login_required
    def resolve_active_trips(self, info):
        """Return currently ongoing trips"""
        today = timezone.now().date()
        return Trip.objects.filter(
            user=info.context.user,
            start_date__lte=today,
            end_date__gte=today,
        )

    # ==================== Match Resolvers ====================

    @login_required
    def resolve_trip_matches(self, info, trip_id, status=None):
        """Return matches for a specific trip"""
        try:
            trip = Trip.objects.get(id=trip_id, user=info.context.user)
            matches = TripMatch.objects.filter(trip=trip)

            if status:
                matches = matches.filter(status=status)

            return matches

        except Trip.DoesNotExist:
            return []

    @login_required
    def resolve_my_pending_matches(self, info):
        """Return all pending matches for user's trips"""
        user_trips = Trip.objects.filter(user=info.context.user)
        return TripMatch.objects.filter(trip__in=user_trips, status="pending")

    # ==================== Suggestion Resolvers ====================

    @login_required
    def resolve_my_trip_suggestions(
        self, info, trip_id=None, suggestion_type=None, unread_only=False
    ):
        """Return AI suggestions for user's trips"""
        suggestions = TripSuggestion.objects.filter(user=info.context.user)

        if trip_id:
            suggestions = suggestions.filter(trip_id=trip_id)

        if suggestion_type:
            suggestions = suggestions.filter(suggestion_type=suggestion_type)

        if unread_only:
            suggestions = suggestions.filter(is_read=False)

        return suggestions.order_by("-created_at")

    # ==================== Hotspot Resolvers ====================

    @login_required
    def resolve_active_hotspots(
        self, info, latitude=None, longitude=None, radius_km=10.0
    ):
        """Return active hotspots, optionally filtered by proximity"""
        now = timezone.now()
        hotspots = ActivityHotspot.objects.filter(expires_at__gte=now)

        # If location provided, filter by distance
        if latitude and longitude:
            # Simple bounding box filter (good enough for small distances)
            # 1 degree ≈ 111km
            lat_delta = radius_km / 111.0
            lng_delta = radius_km / (111.0 * abs(float(latitude)))

            hotspots = hotspots.filter(
                latitude__gte=float(latitude) - lat_delta,
                latitude__lte=float(latitude) + lat_delta,
                longitude__gte=float(longitude) - lng_delta,
                longitude__lte=float(longitude) + lng_delta,
            )

        return hotspots.order_by("-user_count", "-last_activity")

    # ==================== Location History Resolvers ====================

    @login_required
    def resolve_trip_location_history(self, info, trip_id):
        """Return location history for a specific trip"""
        try:
            trip = Trip.objects.get(id=trip_id, user=info.context.user)
            return LocationHistory.objects.filter(trip=trip).order_by("recorded_at")
        except Trip.DoesNotExist:
            return []
