import graphene
from graphene_django import DjangoObjectType
from user.models import Profile, User


class UserType(DjangoObjectType):
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
