"""
GraphQL Types for Travel Location and Tracking
"""

import graphene
from graphene_django import DjangoObjectType
from travel.models import LocationHistory


class LocationHistoryType(DjangoObjectType):
    """Location history point"""

    class Meta:
        model = LocationHistory
        fields = (
            "id",
            "user",
            "trip",
            "latitude",
            "longitude",
            "accuracy",
            "altitude",
            "speed",
            "heading",
            "is_background",
            "battery_level",
            "recorded_at",
            "created_at",
        )


class LocationPointType(graphene.ObjectType):
    """Simple location point for route display"""

    latitude = graphene.Decimal()
    longitude = graphene.Decimal()
    timestamp = graphene.DateTime()
    speed = graphene.Float()
