import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required
from user.models import Profile


class ProfileType(DjangoObjectType):
    class Meta:
        model = Profile
        exclude = (
            "user",
            "latitude",
            "longitude",
        )


class ProfileCRUDType(graphene.InputObjectType):
    profile_image = graphene.String()
    bio = graphene.String()
    address = graphene.String()
    phone_number = graphene.String()
    profession = graphene.String()
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


class UpdateLocation(graphene.Mutation):
    class Arguments:
        latitude = graphene.Decimal(required=True)
        longitude = graphene.Decimal(required=True)
        show_location = graphene.Boolean(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    profile = graphene.Field(lambda: ProfileType)

    @login_required
    def mutate(cls, info, latitude=None, longitude=None, show_location=None):
        user = info.context.user
        try:
            profile = user.profile

            updated = False
            if latitude is not None:
                profile.latitude = latitude
                profile.longitude = longitude
                updated = True

            if show_location is not None:
                profile.show_location = show_location
                updated = True

            if updated:
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
