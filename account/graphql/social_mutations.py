import graphene
from django.contrib.auth import get_user_model
from graphql_jwt.decorators import login_required
from user.graphql.social_link_schema import SocialLinkType
from user.graphql.social_schema import SocialType
from user.models import Social, SocialLink

User = get_user_model()


class AddSocialLinkInput(graphene.InputObjectType):
    platform = graphene.String(required=True)
    url = graphene.String(required=True)
    username = graphene.String()


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
                username=input.username if input.username else "",
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
    id = graphene.UUID(required=True)
    platform = graphene.String()
    url = graphene.String()
    username = graphene.String()


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

            if input.platform is not None:
                social_link.platform = input.platform
            if input.url is not None:
                social_link.url = input.url
            if input.username is not None:
                social_link.username = input.username

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
        id = graphene.UUID(required=True)

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


class AddFriend(graphene.Mutation):
    class Arguments:
        friend_id = graphene.UUID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    social = graphene.Field(SocialType)

    @classmethod
    @login_required
    def mutate(cls, root, info, friend_id):
        try:
            user = info.context.user
            friend = User.objects.get(id=friend_id)

            if friend == user:
                return AddFriend(
                    success=False,
                    message="You cannot add yourself as a friend.",
                    social=None,
                )

            user.social.friends.add(friend)

            return AddFriend(
                success=True, message="Friend added successfully.", social=user.social
            )

        except User.DoesNotExist:
            return AddFriend(success=False, message="User not found.", social=None)
        except Exception as e:
            return AddFriend(
                success=False, message=f"Error adding friend: {str(e)}", social=None
            )


class RemoveFriend(graphene.Mutation):
    class Arguments:
        friend_id = graphene.UUID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    social = graphene.Field(SocialType)

    @classmethod
    @login_required
    def mutate(cls, root, info, friend_id):
        try:
            user = info.context.user
            friend = User.objects.get(id=friend_id)

            user.social.friends.remove(friend)

            return RemoveFriend(
                success=True, message="Friend removed successfully.", social=user.social
            )

        except User.DoesNotExist:
            return RemoveFriend(success=False, message="User not found.", social=None)
        except Exception as e:
            return RemoveFriend(
                success=False, message=f"Error removing friend: {str(e)}", social=None
            )
