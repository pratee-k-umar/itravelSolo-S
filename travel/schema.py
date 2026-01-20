"""
GraphQL Schema for Travel app
Combines queries and mutations
"""

import graphene
from travel.graphql.mutations import (
    AcceptMatch,
    CreateTrip,
    DeleteTrip,
    EndTrip,
    FindMatches,
    RejectMatch,
    StartTrip,
    UpdateLocation,
    UpdateTrip,
)
from travel.graphql.queries import TravelQueries


class Query(TravelQueries, graphene.ObjectType):
    """Travel app queries"""

    pass


class Mutation(graphene.ObjectType):
    """Travel app mutations"""

    # Trip CRUD
    create_trip = CreateTrip.Field()
    update_trip = UpdateTrip.Field()
    delete_trip = DeleteTrip.Field()

    # Trip Lifecycle
    start_trip = StartTrip.Field()
    end_trip = EndTrip.Field()

    # Trip Matching
    find_matches = FindMatches.Field()
    accept_match = AcceptMatch.Field()
    reject_match = RejectMatch.Field()

    # Location Tracking
    update_location = UpdateLocation.Field()
