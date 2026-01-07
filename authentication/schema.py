import graphene
import graphql_jwt
from authentication.graphql.mutation import (
    DisableMFA,
    EnableMFA,
    FirebaseOAuthLogin,
    LoginUser,
    RegisterUser,
    RequestEmailVerificationOTP,
    RequestMFAEnableOTP,
    VerifyEmailOTP,
    VerifyMFAOTP,
)


class Query(graphene.ObjectType):
    # Auth queries can be added here if needed
    pass


class Mutation(graphene.ObjectType):
    # JWT Token Management
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()

    # Authentication
    login_user = LoginUser.Field()
    register_user = RegisterUser.Field()
    firebase_oauth_login = FirebaseOAuthLogin.Field()

    # Email Verification
    request_email_verification_otp = RequestEmailVerificationOTP.Field()
    verify_email_otp = VerifyEmailOTP.Field()

    # MFA Management
    verify_mfa_otp = VerifyMFAOTP.Field()
    request_mfa_enable_otp = RequestMFAEnableOTP.Field()
    enable_mfa = EnableMFA.Field()
    disable_mfa = DisableMFA.Field()
