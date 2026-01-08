"""
GraphQL Mutations for User app
All mutation definitions for user operations
"""

import graphene
from django.utils import timezone
from graphql_jwt.decorators import login_required
from user.graphql.types import ProfileType
from user.models import Profile


class ProfileCRUDType(graphene.InputObjectType):
    """Input type for profile CRUD operations"""

    bio = graphene.String()
    profile_image_url = graphene.String()
    gender = graphene.String()
    date_of_birth = graphene.Date()


class CreateProfile(graphene.Mutation):
    class Arguments:
        input = ProfileCRUDType(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    profile = graphene.Field(lambda: ProfileType)

    @login_required
    def mutate(cls, info, input):
        user = info.context.user

        # Check if profile already exists (should be auto-created by signal)
        if hasattr(user, "profile") and user.profile:
            return CreateProfile(
                success=False,
                message="Profile already exists. Use updateProfile instead.",
                profile=user.profile,
            )

        profile = Profile.objects.create(user=user, **input)
        return CreateProfile(
            success=True, message="Profile created successfully.", profile=profile
        )


class UpdateProfile(graphene.Mutation):
    class Arguments:
        input = ProfileCRUDType(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    profile = graphene.Field(lambda: ProfileType)

    @login_required
    def mutate(cls, info, input):
        user = info.context.user
        try:
            profile = user.profile

            for key, value in input.items():
                setattr(profile, key, value)
            profile.save()

            return UpdateProfile(
                success=True, message="Profile updated successfully.", profile=profile
            )

        except Profile.DoesNotExist:
            return UpdateProfile(
                success=False, message="Profile does not exist.", profile=None
            )


class UpdateLocationInput(graphene.InputObjectType):
    latitude = graphene.Decimal(required=True)
    longitude = graphene.Decimal(required=True)
    show_location = graphene.Boolean()


class UpdateLocation(graphene.Mutation):
    class Arguments:
        input = UpdateLocationInput(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    profile = graphene.Field(lambda: ProfileType)

    @login_required
    def mutate(cls, info, input):
        user = info.context.user
        try:
            profile = user.profile

            profile.latitude = input.latitude
            profile.longitude = input.longitude
            profile.last_location_update = timezone.now()

            if input.show_location is not None:
                profile.show_location = input.show_location

            profile.save()

            return UpdateLocation(
                success=True, message="Location updated successfully.", profile=profile
            )

        except Profile.DoesNotExist:
            return UpdateLocation(
                success=False,
                message="Profile does not exist. Please create a profile first.",
                profile=None,
            )
