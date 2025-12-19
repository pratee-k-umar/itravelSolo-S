import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required

from user.models import Profile


class ProfileType(DjangoObjectType):
    class Meta:
        model = Profile
        fields = (
            "id",
            "user",
            "profile_image",
            "bio",
            "address",
            "phone_number",
            "profession",
            "gender",
            "date_of_birth",
            "last_seen",
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
            profile = Profile(user=user)
            success = False
            profile = None
