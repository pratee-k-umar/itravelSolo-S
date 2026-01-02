import graphene
import graphql_jwt
from graphql_jwt.decorators import login_required
from user.graphql.social_schema import SocialType
from user.graphql.user_schema import (
    Disable_MFA,
    Enable_MFA,
    LoginUser,
    RegisterUser,
    RequestEmailVerificationOTP,
    RequestMFAEnableOTP,
    UserType,
    VerifyEmailOTP,
    VerifyMFAOTP,
)

from .models import User
from .graphql.profile_schema import (
    CreateProfile,
    ProfileType,
    UpdateLocation,
    UpdateProfile,
)
from .graphql.social_link_schema import SocialLinkType


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

    @login_required
    def resolve_social(self, info):
        return info.context.user.social

    @login_required
    def resolve_social_links(self, info):
        return info.context.user.social_links.all()

    def resolve_all_users(self, info):
        return User.objects.all()

    def resolve_user_by_id(self, info, id):
        try:
            return User.objects.get(id=id)
        except User.DoesNotExist:
            return None


class Mutation(graphene.ObjectType):
    # JWT Token Management
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()

    # Authentication
    login_user = LoginUser.Field()
    register_user = RegisterUser.Field()

    # Email Verification
    request_email_verification_otp = RequestEmailVerificationOTP.Field()
    verify_email_otp = VerifyEmailOTP.Field()

    # MFA Management
    verify_mfa_otp = VerifyMFAOTP.Field()
    request_mfa_enable_otp = RequestMFAEnableOTP.Field()
    enable_mfa = Enable_MFA.Field()
    disable_mfa = Disable_MFA.Field()

    # Profile Mutations
    create_profile = CreateProfile.Field()
    update_profile = UpdateProfile.Field()
    update_location = UpdateLocation.Field()
