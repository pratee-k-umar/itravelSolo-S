"""
GraphQL Types for Trip Suggestions and Hotspots
"""

import graphene
from graphene_django import DjangoObjectType
from travel.models import ActivityHotspot, TripSuggestion


class TripSuggestionType(DjangoObjectType):
    """Trip suggestion type"""

    class Meta:
        model = TripSuggestion
        fields = (
            "id",
            "user",
            "trip",
            "suggestion_type",
            "content",
            "title",
            "latitude",
            "longitude",
            "location_name",
            "related_place_id",
            "hotspot_user_count",
            "hotspot_friend_names",
            "is_read",
            "read_at",
            "is_acted_upon",
            "user_rating",
            "is_dismissed",
            "created_at",
            "updated_at",
        )


class ActivityHotspotType(DjangoObjectType):
    """Activity hotspot type"""

    class Meta:
        model = ActivityHotspot
        fields = (
            "id",
            "latitude",
            "longitude",
            "place_name",
            "related_place_id",
            "user_count",
            "active_users",
            "first_detected",
            "last_activity",
            "expires_at",
        )

    is_expired = graphene.Boolean()

    def resolve_is_expired(self, info):
        return self.is_expired
