"""
GraphQL Types for User app
All DjangoObjectType definitions
"""

import graphene
from graphene_django import DjangoObjectType
from user.models import FriendRequest, Profile, Social, SocialLink, User


class UserType(DjangoObjectType):
    """User type with profile access"""

    class Meta:
        model = User
        exclude = (
            "password",
            "otp_secret",
            "otp_created_at",
            "is_staff",
        )

    def resolve_profile(self, info):
        try:
            return self.profile
        except Profile.DoesNotExist:
            return None


class ProfileType(DjangoObjectType):
    """Profile type for user profile data"""

    class Meta:
        model = Profile
        exclude = ("user",)


class SocialType(DjangoObjectType):
    """Social type for user social data and friends"""

    class Meta:
        model = Social
        fields = (
            "id",
            "friends",
            "adventures",
            "places_visited",
            "favorites",
        )


class SocialLinkType(DjangoObjectType):
    """Social link type for external social media links"""

    class Meta:
        model = SocialLink
        fields = (
            "id",
            "platform",
            "url",
        )


class FriendRequestType(DjangoObjectType):
    """Friend request type with from_user and to_user"""

    class Meta:
        model = FriendRequest
        fields = "__all__"

    from_user = graphene.Field(UserType)
    to_user = graphene.Field(UserType)

    def resolve_from_user(self, info):
        return self.from_user

    def resolve_to_user(self, info):
        return self.to_user
