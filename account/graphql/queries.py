import graphene
from graphql_jwt.decorators import login_required
from user.graphql.profile_schema import ProfileType
from user.graphql.social_link_schema import SocialLinkType
from user.graphql.social_schema import SocialType
from user.graphql.user_schema import UserType


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
