from graphene_django import DjangoObjectType
from user.models import Social


class SocialType(DjangoObjectType):
    class Meta:
        model = Social
        fields = (
            "id",
            "friends",
            "adventures",
            "places_visited",
        )
