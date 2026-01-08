import graphene
from graphql_jwt.decorators import login_required
from user.graphql.types import (
    FriendRequestType,
    ProfileType,
    SocialLinkType,
    SocialType,
    UserType,
)
from user.models import FriendRequest


class AccountQueries(graphene.ObjectType):
    """
    Account-related queries for profile and social data
    """

    my_profile = graphene.Field(
        ProfileType, description="Get authenticated user's profile"
    )
    my_social = graphene.Field(
        SocialType, description="Get authenticated user's social data"
    )
    my_social_links = graphene.List(
        SocialLinkType, description="Get authenticated user's social links"
    )
    my_friends = graphene.List(UserType, description="Get authenticated user's friends")

    # Friend request queries
    pending_friend_requests = graphene.List(
        FriendRequestType, description="Get pending friend requests received"
    )
    sent_friend_requests = graphene.List(
        FriendRequestType, description="Get friend requests you sent"
    )

    @login_required
    def resolve_my_profile(self, info):
        """Return the authenticated user's profile"""
        return info.context.user.profile

    @login_required
    def resolve_my_social(self, info):
        """Return the authenticated user's social data"""
        return info.context.user.social

    @login_required
    def resolve_my_social_links(self, info):
        """Return the authenticated user's social links"""
        return info.context.user.social_links.all()

    @login_required
    def resolve_my_friends(self, info):
        """Return the authenticated user's friends"""
        return info.context.user.social.friends.all()

    @login_required
    def resolve_pending_friend_requests(self, info):
        """Return pending friend requests received by the authenticated user"""
        return FriendRequest.objects.filter(
            to_user=info.context.user, status="pending"
        ).order_by("-created_at")

    @login_required
    def resolve_sent_friend_requests(self, info):
        """Return friend requests sent by the authenticated user"""
        return FriendRequest.objects.filter(
            from_user=info.context.user, status="pending"
        ).order_by("-created_at")

    def resolve_my_profile(self, info):
        """Return the authenticated user's profile"""
        return info.context.user.profile

    @login_required
    def resolve_my_social(self, info):
        """Return the authenticated user's social data"""
        return info.context.user.social

    @login_required
    def resolve_my_social_links(self, info):
        """Return the authenticated user's social links"""
        return info.context.user.social_links.all()

    @login_required
    def resolve_my_friends(self, info):
        """Return the authenticated user's friends"""
        return info.context.user.social.friends.all()
