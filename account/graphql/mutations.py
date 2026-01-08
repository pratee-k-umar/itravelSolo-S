"""
GraphQL Mutations for Account app
All mutation definitions for account operations
"""

import graphene
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from graphql_jwt.decorators import login_required
from user.graphql.types import FriendRequestType, ProfileType, SocialLinkType, UserType
from user.models import FriendRequest, Profile, SocialLink

User = get_user_model()

# Profile Mutations


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
            user = info.context.user
            profile = user.profile

            # Update location
            profile.latitude = input.latitude
            profile.longitude = input.longitude
            # Manually set last_location_update timestamp
            profile.last_location_update = timezone.now()

            # Update show_location if provided
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


class UpdateProfileImageInput(graphene.InputObjectType):
    profile_image_url = graphene.String(required=True)


class UpdateProfileImage(graphene.Mutation):
    class Arguments:
        input = UpdateProfileImageInput(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    profile = graphene.Field(ProfileType)

    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        try:
            user = info.context.user
            profile = user.profile

            profile.profile_image_url = input.profile_image_url
            profile.save()

            return UpdateProfileImage(
                success=True,
                message="Profile image updated successfully.",
                profile=profile,
            )

        except Exception as e:
            return UpdateProfileImage(
                success=False,
                message=f"Error updating profile image: {str(e)}",
                profile=None,
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

            # Clear the profile image URL
            profile.profile_image_url = ""
            profile.save()

            return DeleteProfileImage(
                success=True,
                message="Profile image deleted successfully.",
                profile=profile,
            )

        except Exception as e:
            return DeleteProfileImage(
                success=False,
                message=f"Error deleting profile image: {str(e)}",
                profile=None,
            )


# =====================================================
# Social Link Mutations
# =====================================================


class AddSocialLinkInput(graphene.InputObjectType):
    platform = graphene.String(required=True)
    url = graphene.String(required=True)


class AddSocialLink(graphene.Mutation):
    class Arguments:
        input = AddSocialLinkInput(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    social_link = graphene.Field(SocialLinkType)

    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        try:
            user = info.context.user

            social_link = SocialLink.objects.create(
                user=user,
                platform=input.platform,
                url=input.url,
            )

            return AddSocialLink(
                success=True,
                message="Social link added successfully.",
                social_link=social_link,
            )

        except Exception as e:
            return AddSocialLink(
                success=False,
                message=f"Error adding social link: {str(e)}",
                social_link=None,
            )


class UpdateSocialLinkInput(graphene.InputObjectType):
    id = graphene.ID(required=True)
    platform = graphene.String()
    url = graphene.String()


class UpdateSocialLink(graphene.Mutation):
    class Arguments:
        input = UpdateSocialLinkInput(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    social_link = graphene.Field(SocialLinkType)

    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        try:
            user = info.context.user

            social_link = SocialLink.objects.get(id=input.id, user=user)

            # Update fields if provided
            if input.platform is not None:
                social_link.platform = input.platform
            if input.url is not None:
                social_link.url = input.url

            social_link.save()

            return UpdateSocialLink(
                success=True,
                message="Social link updated successfully.",
                social_link=social_link,
            )

        except SocialLink.DoesNotExist:
            return UpdateSocialLink(
                success=False, message="Social link not found.", social_link=None
            )
        except Exception as e:
            return UpdateSocialLink(
                success=False,
                message=f"Error updating social link: {str(e)}",
                social_link=None,
            )


class DeleteSocialLink(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @login_required
    def mutate(cls, root, info, id):
        try:
            user = info.context.user

            social_link = SocialLink.objects.get(id=id, user=user)
            social_link.delete()

            return DeleteSocialLink(
                success=True, message="Social link deleted successfully."
            )

        except SocialLink.DoesNotExist:
            return DeleteSocialLink(success=False, message="Social link not found.")
        except Exception as e:
            return DeleteSocialLink(
                success=False, message=f"Error deleting social link: {str(e)}"
            )


# =====================================================
# Friend Request Mutations
# =====================================================


class SendFriendRequest(graphene.Mutation):
    class Arguments:
        to_user_id = graphene.UUID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    friend_request = graphene.Field(FriendRequestType)

    @classmethod
    @login_required
    def mutate(cls, root, info, to_user_id):
        try:
            from_user = info.context.user

            # Prevent self-friend request
            if str(from_user.id) == str(to_user_id):
                return SendFriendRequest(
                    success=False,
                    message="You cannot send a friend request to yourself.",
                    friend_request=None,
                )

            # Check if users are already friends
            if from_user.social.friends.filter(id=to_user_id).exists():
                return SendFriendRequest(
                    success=False,
                    message="You are already friends with this user.",
                    friend_request=None,
                )

            # Get to_user
            try:
                to_user = User.objects.get(id=to_user_id)
            except User.DoesNotExist:
                return SendFriendRequest(
                    success=False, message="User not found.", friend_request=None
                )

            # Check if friend request already exists
            existing_request = FriendRequest.objects.filter(
                from_user=from_user, to_user=to_user, status="pending"
            ).first()

            if existing_request:
                return SendFriendRequest(
                    success=False,
                    message="Friend request already sent.",
                    friend_request=existing_request,
                )

            # Check if reverse request exists
            reverse_request = FriendRequest.objects.filter(
                from_user=to_user, to_user=from_user, status="pending"
            ).first()

            if reverse_request:
                return SendFriendRequest(
                    success=False,
                    message="This user has already sent you a friend request. Accept it instead.",
                    friend_request=reverse_request,
                )

            # Create friend request
            friend_request = FriendRequest.objects.create(
                from_user=from_user, to_user=to_user, status="pending"
            )

            return SendFriendRequest(
                success=True,
                message="Friend request sent successfully.",
                friend_request=friend_request,
            )

        except Exception as e:
            return SendFriendRequest(
                success=False,
                message=f"Error sending friend request: {str(e)}",
                friend_request=None,
            )


class AcceptFriendRequest(graphene.Mutation):
    class Arguments:
        request_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    friend_request = graphene.Field(FriendRequestType)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate(cls, root, info, request_id):
        try:
            to_user = info.context.user

            # Get the friend request
            friend_request = FriendRequest.objects.get(
                id=request_id, to_user=to_user, status="pending"
            )

            from_user = friend_request.from_user

            # Add each other as friends (mutual friendship)
            from_user.social.friends.add(to_user)
            to_user.social.friends.add(from_user)

            # Update request status
            friend_request.status = "accepted"
            friend_request.save()

            return AcceptFriendRequest(
                success=True,
                message="Friend request accepted successfully.",
                friend_request=friend_request,
            )

        except FriendRequest.DoesNotExist:
            return AcceptFriendRequest(
                success=False, message="Friend request not found.", friend_request=None
            )
        except Exception as e:
            return AcceptFriendRequest(
                success=False,
                message=f"Error accepting friend request: {str(e)}",
                friend_request=None,
            )


class DeclineFriendRequest(graphene.Mutation):
    class Arguments:
        request_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    friend_request = graphene.Field(FriendRequestType)

    @classmethod
    @login_required
    def mutate(cls, root, info, request_id):
        try:
            to_user = info.context.user

            # Get the friend request
            friend_request = FriendRequest.objects.get(
                id=request_id, to_user=to_user, status="pending"
            )

            # Update request status
            friend_request.status = "rejected"
            friend_request.save()

            return DeclineFriendRequest(
                success=True,
                message="Friend request declined.",
                friend_request=friend_request,
            )

        except FriendRequest.DoesNotExist:
            return DeclineFriendRequest(
                success=False, message="Friend request not found.", friend_request=None
            )
        except Exception as e:
            return DeclineFriendRequest(
                success=False,
                message=f"Error declining friend request: {str(e)}",
                friend_request=None,
            )


class CancelFriendRequest(graphene.Mutation):
    class Arguments:
        request_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @login_required
    def mutate(cls, root, info, request_id):
        try:
            from_user = info.context.user

            # Get the friend request
            friend_request = FriendRequest.objects.get(
                id=request_id, from_user=from_user, status="pending"
            )

            # Delete the request
            friend_request.delete()

            return CancelFriendRequest(
                success=True, message="Friend request cancelled successfully."
            )

        except FriendRequest.DoesNotExist:
            return CancelFriendRequest(
                success=False, message="Friend request not found."
            )
        except Exception as e:
            return CancelFriendRequest(
                success=False, message=f"Error cancelling friend request: {str(e)}"
            )


class RemoveFriend(graphene.Mutation):
    class Arguments:
        friend_id = graphene.UUID(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    @classmethod
    @login_required
    def mutate(cls, root, info, friend_id):
        try:
            user = info.context.user

            # Get friend
            try:
                friend = User.objects.get(id=friend_id)
            except User.DoesNotExist:
                return RemoveFriend(success=False, message="User not found.")

            # Check if they are friends
            if not user.social.friends.filter(id=friend_id).exists():
                return RemoveFriend(
                    success=False, message="You are not friends with this user."
                )

            # Remove mutual friendship
            user.social.friends.remove(friend)
            friend.social.friends.remove(user)

            # Update any accepted friend requests to rejected
            FriendRequest.objects.filter(
                from_user=user, to_user=friend, status="accepted"
            ).update(status="rejected")
            FriendRequest.objects.filter(
                from_user=friend, to_user=user, status="accepted"
            ).update(status="rejected")

            return RemoveFriend(success=True, message="Friend removed successfully.")

        except Exception as e:
            return RemoveFriend(
                success=False, message=f"Error removing friend: {str(e)}"
            )
