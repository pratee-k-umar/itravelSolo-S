import graphene
from account.graphql.mutations import (  # Profile mutations; Social link mutations; Friend request mutations
    AcceptFriendRequest,
    AddSocialLink,
    CancelFriendRequest,
    DeclineFriendRequest,
    DeleteProfileImage,
    DeleteSocialLink,
    RemoveFriend,
    SendFriendRequest,
    UpdateLocation,
    UpdateProfile,
    UpdateProfileImage,
    UpdateSocialLink,
)
from account.graphql.queries import AccountQueries


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
    update_profile_image = UpdateProfileImage.Field()
    delete_profile_image = DeleteProfileImage.Field()

    # Social Link Management
    add_social_link = AddSocialLink.Field()
    update_social_link = UpdateSocialLink.Field()
    delete_social_link = DeleteSocialLink.Field()

    # Friend Request System
    send_friend_request = SendFriendRequest.Field()
    accept_friend_request = AcceptFriendRequest.Field()
    decline_friend_request = DeclineFriendRequest.Field()
    cancel_friend_request = CancelFriendRequest.Field()
    remove_friend = RemoveFriend.Field()
