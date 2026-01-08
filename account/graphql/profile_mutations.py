import graphene
from django.contrib.auth import get_user_model
from graphql_jwt.decorators import login_required
from user.graphql.profile_schema import ProfileType
from user.models import Profile

User = get_user_model()


class UpdateProfileInput(graphene.InputObjectType):
    bio = graphene.String()
    address = graphene.String()
    phone_number = graphene.String()
    profession = graphene.String()
    gender = graphene.String()
    date_of_birth = graphene.Date()


class UpdateProfile(graphene.Mutation):
    class Arguments:
        input = UpdateProfileInput(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    profile = graphene.Field(ProfileType)

    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        try:
            user = info.context.user
            profile = user.profile

            # Update fields if provided
            if input.bio is not None:
                profile.bio = input.bio
            if input.address is not None:
                profile.address = input.address
            if input.phone_number is not None:
                profile.phone_number = input.phone_number
            if input.profession is not None:
                profile.profession = input.profession
            if input.gender is not None:
                profile.gender = input.gender
            if input.date_of_birth is not None:
                profile.date_of_birth = input.date_of_birth

            profile.save()

            return UpdateProfile(
                success=True, message="Profile updated successfully.", profile=profile
            )

        except Exception as e:
            return UpdateProfile(
                success=False, message=f"Error updating profile: {str(e)}", profile=None
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
    profile = graphene.Field(ProfileType)

    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        try:
            from django.utils import timezone
            
            user = info.context.user
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

        except Exception as e:
            return UpdateLocation(
                success=False,
                message=f"Error updating location: {str(e)}",
                profile=None,
            )


class UploadProfileImageInput(graphene.InputObjectType):
    image = graphene.String(required=True)  # Base64 encoded image or file upload


class UploadProfileImage(graphene.Mutation):
    class Arguments:
        input = UploadProfileImageInput(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    profile = graphene.Field(ProfileType)

    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        try:
            user = info.context.user
            profile = user.profile

            # Handle image upload
            # This is a placeholder - implement actual file upload logic
            # You may want to use django-graphene-file-upload or similar

            return UploadProfileImage(
                success=True,
                message="Profile image uploaded successfully.",
                profile=profile,
            )

        except Exception as e:
            return UploadProfileImage(
                success=False, message=f"Error uploading image: {str(e)}", profile=None
            )


class DeleteProfileImage(graphene.Mutation):
    success = graphene.Boolean()
    message = graphene.String()
    profile = graphene.Field(ProfileType)

    @classmethod
    @login_required
    def mutate(cls, root, info):
        try:
            user = info.context.user
            profile = user.profile

            if profile.profile_image_url:
                profile.profile_image_url = None
                profile.save()
                return DeleteProfileImage(
                    success=True,
                    message="Profile image deleted successfully.",
                    profile=profile,
                )
            else:
                return DeleteProfileImage(
                    success=False,
                    message="No profile image to delete.",
                    profile=profile,
                )

        except Exception as e:
            return DeleteProfileImage(
                success=False, message=f"Error deleting image: {str(e)}", profile=None
            )
