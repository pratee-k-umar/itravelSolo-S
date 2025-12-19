from graphene_django import DjangoObjectType

from user.models import SocialLink


class SocialLinkType(DjangoObjectType):
    class Meta:
        model = SocialLink
        fields = (
            "id",
            "platform",
            "url",
        )
