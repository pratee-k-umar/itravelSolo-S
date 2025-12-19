import graphene
import graphql_jwt
from graphql_jwt.decorators import login_required

from .schemas.social_link_schema import SocialLinkType

from .schemas.profile_schema import ProfileType, UpdateLocation
from user.schemas.social_schema import SocialType
from user.schemas.user_schema import LoginUser, RegisterUser, RequestEmailVerificationOTP, UserType, VerifyEmailOTP

from .models import User


class Query(graphene.ObjectType):
    all_user = graphene.List(UserType)
    user_by_id = graphene.Field(UserType, id=graphene.UUID(required=True))
    me = graphene.Field(UserType)
    profile = graphene.Field(ProfileType)
    social = graphene.Field(SocialType)
    social_links = graphene.List(SocialLinkType)

    @login_required
    def resolve_me(self, info):
        return info.context.user

    @login_required
    def resolve_profile(self, info):
        return info.context.user.profile

    def resolve_all_users(self, info):
        return User.objects.all()

    def resolve_user_by_id(self, info, id):
        try:
            return User.objects.get(id=id)
        except User.DoesNotExist:
            return None


class Mutation(graphene.ObjectType):
    login_user = LoginUser.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()

    register_user = RegisterUser.Field()
    request_email_verification_otp = RequestEmailVerificationOTP.Field()
    verify_email_otp = VerifyEmailOTP.Field()
    updateLocation = UpdateLocation.Field()
