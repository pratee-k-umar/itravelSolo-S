"""
GraphQL Mutations for Travel app
All mutation definitions for trip operations
"""

import graphene
from django.utils import timezone
from graphql_jwt.decorators import login_required
from travel.graphql.location_types import LocationHistoryType
from travel.graphql.types import TripMatchType, TripType
from travel.models import Trip, TripMatch
from travel.services.hotspot_detector import HotspotDetector
from travel.services.location_tracker import LocationTracker
from travel.services.matching import find_trip_matches
from travel.services.proximity_matcher import ProximityMatcher
from travel.services.suggestion_engine import SuggestionEngine


class CreateTripInput(graphene.InputObjectType):
    destination = graphene.String(required=True)
    destination_lat = graphene.Decimal()
    destination_lng = graphene.Decimal()
    start_date = graphene.Date(required=True)
    end_date = graphene.Date(required=True)
    interests = graphene.List(graphene.String)
    description = graphene.String()
    max_companions = graphene.Int()
    privacy = graphene.String()


class CreateTrip(graphene.Mutation):
    class Arguments:
        input = CreateTripInput(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    trip = graphene.Field(TripType)

    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        try:
            user = info.context.user

            # Validate dates
            if input.start_date > input.end_date:
                return CreateTrip(
                    success=False,
                    message="Start date must be before end date.",
                    trip=None,
                )

            # Auto-set origin from user's current location
            origin_name = "Current Location"
            origin_lat = None
            origin_lng = None

            if (
                hasattr(user, "profile")
                and user.profile.latitude
                and user.profile.longitude
            ):
                origin_lat = user.profile.latitude
                origin_lng = user.profile.longitude
                # Could reverse geocode here to get location name if needed

            # Create trip
            trip = Trip.objects.create(
                user=user,
                origin=origin_name,
                destination=input.destination,
                origin_lat=origin_lat,
                origin_lng=origin_lng,
                destination_lat=(
                    input.destination_lat if hasattr(input, "destination_lat") else None
                ),
                destination_lng=(
                    input.destination_lng if hasattr(input, "destination_lng") else None
                ),
                start_date=input.start_date,
                end_date=input.end_date,
                interests=input.interests if hasattr(input, "interests") else [],
                description=input.description if hasattr(input, "description") else "",
                max_companions=(
                    input.max_companions if hasattr(input, "max_companions") else 0
                ),
                privacy=input.privacy if hasattr(input, "privacy") else "friends_only",
            )

            return CreateTrip(
                success=True, message="Trip created successfully.", trip=trip
            )

        except Exception as e:
            return CreateTrip(
                success=False, message=f"Error creating trip: {str(e)}", trip=None
            )


class UpdateTripInput(graphene.InputObjectType):
    trip_id = graphene.UUID(required=True)
    origin = graphene.String()
    destination = graphene.String()
    origin_lat = graphene.Decimal()
    origin_lng = graphene.Decimal()
    destination_lat = graphene.Decimal()
    destination_lng = graphene.Decimal()
    start_date = graphene.Date()
    end_date = graphene.Date()
    interests = graphene.List(graphene.String)
    description = graphene.String()
    max_companions = graphene.Int()
    privacy = graphene.String()


class UpdateTrip(graphene.Mutation):
    class Arguments:
        input = UpdateTripInput(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    trip = graphene.Field(TripType)

    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        try:
            user = info.context.user

            # Get trip
            trip = Trip.objects.get(id=input.trip_id, user=user)

            # Update fields if provided
            if hasattr(input, "origin") and input.origin:
                trip.origin = input.origin
            if hasattr(input, "destination") and input.destination:
                trip.destination = input.destination
            if hasattr(input, "origin_lat"):
                trip.origin_lat = input.origin_lat
            if hasattr(input, "origin_lng"):
                trip.origin_lng = input.origin_lng
            if hasattr(input, "destination_lat"):
                trip.destination_lat = input.destination_lat
            if hasattr(input, "destination_lng"):
                trip.destination_lng = input.destination_lng
            if hasattr(input, "start_date") and input.start_date:
                trip.start_date = input.start_date
            if hasattr(input, "end_date") and input.end_date:
                trip.end_date = input.end_date
            if hasattr(input, "interests"):
                trip.interests = input.interests
            if hasattr(input, "description"):
                trip.description = input.description
            if hasattr(input, "max_companions"):
                trip.max_companions = input.max_companions
            if hasattr(input, "privacy"):
                trip.privacy = input.privacy

            # Validate dates if both are provided
            if trip.start_date > trip.end_date:
                return UpdateTrip(
                    success=False,
                    message="Start date must be before end date.",
                    trip=None,
                )

            trip.save()

            return UpdateTrip(
                success=True, message="Trip updated successfully.", trip=trip
            )

        except Trip.DoesNotExist:
            return UpdateTrip(
                success=False, message="Trip not found or unauthorized.", trip=None
            )
        except Exception as e:
            return UpdateTrip(
                success=False, message=f"Error updating trip: {str(e)}", trip=None
            )


class DeleteTrip(graphene.Mutation):
    class Arguments:
        trip_id = graphene.UUID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @login_required
    def mutate(cls, root, info, trip_id):
        try:
            user = info.context.user

            # Get trip
            trip = Trip.objects.get(id=trip_id, user=user)
            trip.delete()

            return DeleteTrip(success=True, message="Trip deleted successfully.")

        except Trip.DoesNotExist:
            return DeleteTrip(success=False, message="Trip not found or unauthorized.")
        except Exception as e:
            return DeleteTrip(success=False, message=f"Error deleting trip: {str(e)}")


# =====================================================
# Trip Matching Mutations
# =====================================================


class StartTrip(graphene.Mutation):
    """Start a trip and activate automatic matching"""

    class Arguments:
        trip_id = graphene.UUID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    trip = graphene.Field(TripType)
    matches_found = graphene.Int()

    @classmethod
    @login_required
    def mutate(cls, root, info, trip_id):
        try:
            user = info.context.user

            # Get trip
            trip = Trip.objects.get(id=trip_id, user=user)

            # Check if already started
            if trip.is_active:
                return StartTrip(
                    success=False,
                    message="Trip is already active.",
                    trip=trip,
                    matches_found=0,
                )

            # Activate the trip
            trip.is_active = True
            trip.save()

            # Automatically find matches
            matches = find_trip_matches(trip, limit=20)

            return StartTrip(
                success=True,
                message=f"Trip started successfully. Found {len(matches)} potential matches.",
                trip=trip,
                matches_found=len(matches),
            )

        except Trip.DoesNotExist:
            return StartTrip(
                success=False,
                message="Trip not found or unauthorized.",
                trip=None,
                matches_found=0,
            )
        except Exception as e:
            return StartTrip(
                success=False,
                message=f"Error starting trip: {str(e)}",
                trip=None,
                matches_found=0,
            )


class EndTrip(graphene.Mutation):
    """End/deactivate a trip"""

    class Arguments:
        trip_id = graphene.UUID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    trip = graphene.Field(TripType)

    @classmethod
    @login_required
    def mutate(cls, root, info, trip_id):
        try:
            user = info.context.user

            # Get trip
            trip = Trip.objects.get(id=trip_id, user=user)

            # Check if already ended
            if not trip.is_active:
                return EndTrip(
                    success=False,
                    message="Trip is already inactive.",
                    trip=trip,
                )

            # Deactivate the trip
            trip.is_active = False
            trip.save()

            return EndTrip(
                success=True,
                message="Trip ended successfully.",
                trip=trip,
            )

        except Trip.DoesNotExist:
            return EndTrip(
                success=False,
                message="Trip not found or unauthorized.",
                trip=None,
            )
        except Exception as e:
            return EndTrip(
                success=False,
                message=f"Error ending trip: {str(e)}",
                trip=None,
            )


class FindMatches(graphene.Mutation):
    class Arguments:
        trip_id = graphene.UUID(required=True)
        limit = graphene.Int()

    success = graphene.Boolean()
    message = graphene.String()
    matches = graphene.List(TripMatchType)

    @classmethod
    @login_required
    def mutate(cls, root, info, trip_id, limit=10):
        try:
            user = info.context.user

            # Get trip
            trip = Trip.objects.get(id=trip_id, user=user)

            # Find matches
            matches = find_trip_matches(trip, limit=limit)

            return FindMatches(
                success=True,
                message=f"Found {len(matches)} matches.",
                matches=matches,
            )

        except Trip.DoesNotExist:
            return FindMatches(
                success=False, message="Trip not found or unauthorized.", matches=[]
            )
        except Exception as e:
            return FindMatches(
                success=False, message=f"Error finding matches: {str(e)}", matches=[]
            )


class AcceptMatch(graphene.Mutation):
    class Arguments:
        match_id = graphene.UUID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    match = graphene.Field(TripMatchType)

    @classmethod
    @login_required
    def mutate(cls, root, info, match_id):
        try:
            user = info.context.user

            # Get match
            match = TripMatch.objects.get(
                id=match_id, trip__user=user, status="pending"
            )

            # Update status
            match.status = "accepted"
            match.save()

            # Increment companions count
            trip = match.trip
            trip.current_companions += 1
            trip.save()

            return AcceptMatch(
                success=True, message="Match accepted successfully.", match=match
            )

        except TripMatch.DoesNotExist:
            return AcceptMatch(
                success=False,
                message="Match not found or already processed.",
                match=None,
            )
        except Exception as e:
            return AcceptMatch(
                success=False, message=f"Error accepting match: {str(e)}", match=None
            )


class RejectMatch(graphene.Mutation):
    class Arguments:
        match_id = graphene.UUID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @login_required
    def mutate(cls, root, info, match_id):
        try:
            user = info.context.user

            # Get match
            match = TripMatch.objects.get(
                id=match_id, trip__user=user, status="pending"
            )

            # Update status
            match.status = "rejected"
            match.save()

            return RejectMatch(success=True, message="Match rejected successfully.")

        except TripMatch.DoesNotExist:
            return RejectMatch(
                success=False, message="Match not found or already processed."
            )
        except Exception as e:
            return RejectMatch(
                success=False, message=f"Error rejecting match: {str(e)}"
            )


# =====================================================
# Location Tracking Mutations
# =====================================================


class UpdateLocationInput(graphene.InputObjectType):
    """Input for updating user location"""

    latitude = graphene.Decimal(required=True)
    longitude = graphene.Decimal(required=True)
    accuracy = graphene.Float()
    altitude = graphene.Float()
    speed = graphene.Float()
    heading = graphene.Float()
    is_background = graphene.Boolean()
    battery_level = graphene.Int()
    recorded_at = graphene.DateTime()


class UpdateLocation(graphene.Mutation):
    """Record user's current location"""

    class Arguments:
        input = UpdateLocationInput(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    location = graphene.Field(LocationHistoryType)

    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        try:
            user = info.context.user

            # Record location
            location = LocationTracker.record_location(
                user=user,
                latitude=float(input.latitude),
                longitude=float(input.longitude),
                accuracy=input.accuracy if hasattr(input, "accuracy") else None,
                altitude=input.altitude if hasattr(input, "altitude") else None,
                speed=input.speed if hasattr(input, "speed") else None,
                heading=input.heading if hasattr(input, "heading") else None,
                is_background=(
                    input.is_background if hasattr(input, "is_background") else False
                ),
                battery_level=(
                    input.battery_level if hasattr(input, "battery_level") else None
                ),
                recorded_at=(
                    input.recorded_at if hasattr(input, "recorded_at") else None
                ),
            )

            # Check for suggestions if trip is active
            if location.trip and location.trip.is_active:
                suggestion_engine = SuggestionEngine()
                suggestion_engine.check_and_generate_suggestions(
                    user=user,
                    trip=location.trip,
                    latitude=float(input.latitude),
                    longitude=float(input.longitude),
                )

            # Check for activity hotspots and notify user
            hotspot_detector = HotspotDetector(user)
            hotspot_notification = hotspot_detector.detect_and_notify(
                latitude=float(input.latitude),
                longitude=float(input.longitude),
            )

            # Update proximity for pending matches
            proximity_stats = ProximityMatcher.update_match_distances(
                user=user,
                latitude=float(input.latitude),
                longitude=float(input.longitude),
            )

            # Build response message with proximity info
            message = "Location recorded successfully."
            if hotspot_notification:
                message += " 🔥 Hotspot detected nearby!"
            if proximity_stats["close_matches"]:
                close_count = len(proximity_stats["close_matches"])
                message += f" {close_count} match(es) nearby!"
            if proximity_stats["expired_count"] > 0:
                message += (
                    f" {proximity_stats['expired_count']} distant match(es) removed."
                )

            return UpdateLocation(
                success=True,
                message=message,
                location=location,
            )

        except Exception as e:
            return UpdateLocation(
                success=False,
                message=f"Error recording location: {str(e)}",
                location=None,
            )


# =====================================================
# Mutation Collection
# =====================================================


class TravelMutations(graphene.ObjectType):
    """All travel-related mutations"""

    # Trip CRUD
    create_trip = CreateTrip.Field()
    update_trip = UpdateTrip.Field()
    delete_trip = DeleteTrip.Field()

    # Trip lifecycle
    start_trip = StartTrip.Field()
    end_trip = EndTrip.Field()

    # Matching
    find_matches = FindMatches.Field()
    accept_match = AcceptMatch.Field()
    reject_match = RejectMatch.Field()

    # Location tracking
    update_location = UpdateLocation.Field()
