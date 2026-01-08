import graphene
from account.graphql.profile_mutations import (
    DeleteProfileImage,
    UpdateLocation,
    UpdateProfile,
    UploadProfileImage,
)
from account.graphql.queries import AccountQueries
from account.graphql.social_mutations import (
    AddFriend,
    AddSocialLink,
    DeleteSocialLink,
    RemoveFriend,
    UpdateSocialLink,
)


class Query(AccountQueries, graphene.ObjectType):
    """
    Account queries - profile and social management
    """

    pass


class Mutation(graphene.ObjectType):
    """
    Account mutations - profile and social management
    """

    # Profile Management
    update_profile = UpdateProfile.Field()
    update_location = UpdateLocation.Field()
    upload_profile_image = UploadProfileImage.Field()
    delete_profile_image = DeleteProfileImage.Field()

    # Social Link Management
    add_social_link = AddSocialLink.Field()
    update_social_link = UpdateSocialLink.Field()
    delete_social_link = DeleteSocialLink.Field()

    # Friend Management
    add_friend = AddFriend.Field()
    remove_friend = RemoveFriend.Field()
