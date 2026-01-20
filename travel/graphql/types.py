"""
GraphQL Types for Travel app
All DjangoObjectType definitions
"""

import graphene
from graphene_django import DjangoObjectType
from travel.models import Trip, TripMatch
from user.graphql.types import UserType


class TripType(DjangoObjectType):
    """Trip type for travel planning"""

    class Meta:
        model = Trip
        fields = (
            "id",
            "user",
            "origin",
            "destination",
            "origin_lat",
            "origin_lng",
            "destination_lat",
            "destination_lng",
            "route_polyline",
            "start_date",
            "end_date",
            "interests",
            "description",
            "max_companions",
            "current_companions",
            "privacy",
            "created_at",
            "updated_at",
        )

    duration_days = graphene.Int()
    is_upcoming = graphene.Boolean()
    is_active = graphene.Boolean()

    def resolve_duration_days(self, info):
        return self.duration_days

    def resolve_is_upcoming(self, info):
        return self.is_upcoming

    def resolve_is_active(self, info):
        return self.is_active


class TripMatchType(DjangoObjectType):
    """Trip match type for companion matching"""

    class Meta:
        model = TripMatch
        fields = (
            "id",
            "trip",
            "matched_user",
            "matched_trip",
            "score",
            "common_interests",
            "distance_km",
            "status",
            "created_at",
            "updated_at",
        )

    matched_user = graphene.Field(UserType)

    def resolve_matched_user(self, info):
        return self.matched_user
