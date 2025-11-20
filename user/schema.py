import graphene
import graphql_jwt
from graphene_django.types import DjangoObjectType
from .models import User, Profile
from .utils import generate_otp, send_otp_email, valid_otp
from django.utils import timezone
from django.conf import settings
from graphql_jwt.shortcuts import get_token, create_refresh_token
from django.contrib.auth import authenticate
from graphql_jwt.decorators import login_required
from graphql import GraphQLError

class RegisterUserInput(graphene.InputObjectType):
  first_name = graphene.String(required=True)
  last_name = graphene.String(required=True)
  email = graphene.String(required=True)
  password = graphene.String(required=True)

class ProfileType(DjangoObjectType):
  class Meta:
    model = Profile
    fields = ('id', 'user', 'profile_image', 'bio', 'address', 'phone_number', 'profession', 'gender', 'date_of_birth', 'last_seen')

class UserType(DjangoObjectType):
  class Meta:
    model = User
    fields = ('id', 'first_name', 'last_name', 'email', 'profile', 'email_verified', 'mfa_enabled', 'is_active')
  
  def resolve_profile(root, info):
    try:
      return root.profile
    except Profile.DoesNotExist:
      return None

class Query(graphene.ObjectType):
  all_user = graphene.List(UserType)
  user_by_id = graphene.Field(UserType, id=graphene.UUID(required=True))
  me = graphene.Field(UserType)
  
  @login_required
  def resolve_me(self, info):
    return info.context.user
  
  def resolve_all_users(root, info):
    return User.objects.all()
  
  def resolve_user_by_id(root, info, id):
    try:
      return User.objects.get(id=id)
    except User.DoesNotExist:
      return None

class RegisterUser(graphene.Mutation):
  class Arguments:
    input = RegisterUserInput(required=True)
  
  user = graphene.Field(UserType)
  success = graphene.Boolean()
  message = graphene.String()
  errors = graphene.List(graphene.String)
  
  @classmethod
  def mutate(cls, root, info, input):
    try:
      user = User.objects.create_user(
        first_name=input.first_name,
        last_name=input.last_name,
        email=input.email,
        password=input.password
      )
      
      if user.otp_created_at and (timezone.now() - user.otp_created_at).total_seconds() < settings.OTP_COOLDOWN_SECONDS:
        return RegisterUser(user=None, success=False, message="Please wait before requesting a new OTP.", errors=["OTP request cooldown in effect."])
      
      otp = generate_otp()
      user.otp_secret = otp
      user.otp_created_at = timezone.now()
      user.save()
      
      if send_otp_email(user, otp, subject="Email Verification OTP"):
        return RegisterUser(user=user, success=True, message="User registered successfully. OTP sent to your email for verification.", errors=None)
      else:
        return RegisterUser(user=user, success=False, message="User registered, but failed to send OTP email.", errors=["Failed to send OTP email."])
      # return RegisterUser(user=user, success=True, errors=None)
    except Exception as e:
      return RegisterUser(user=None, success=False, errors=[str(e)])

class RequestEmailVerificationOTP(graphene.Mutation):
  class Arguments:
    email = graphene.String(required=True)
  
  success = graphene.Boolean()
  message = graphene.String()
  
  @classmethod
  def mutate(cls, root, info, email):
    try:
      user = User.objects.get(email=email)
      if user.email_verified:
        return RequestEmailVerificationOTP(success=False, message="Email is already verified.")
      
      if user.otp_created_at and (timezone.now() - user.otp_created_at).total_seconds() < settings.OTP_COOLDOWN_SECONDS:
        return RequestEmailVerificationOTP(success=False, message="Please wait before requesting a new OTP.")
      
      otp = generate_otp()
      user.otp_secret = otp
      user.otp_created_at = timezone.now()
      user.save()
      
      if send_otp_email(user, otp, subject="Email Verification OTP"):
        return RequestEmailVerificationOTP(success=True, message="OTP sent to your email.")
      else:
        return RequestEmailVerificationOTP(success=False, message="Failed to send OTP email.")
    except User.DoesNotExist:
      return RequestEmailVerificationOTP(success=False, message="User with this email does not exist.")
    
    except Exception as e:
      return RequestEmailVerificationOTP(success=False, message=str(e))

class VerifyEmailOTP(graphene.Mutation):
  class Arguments:
    email = graphene.String(required=True)
    otp = graphene.String(required=True)
  
  success = graphene.Boolean()
  message = graphene.String()
  token = graphene.String()
  refresh_token = graphene.String()
  user = graphene.Field(UserType)

  @classmethod
  def mutate(cls, root, info, email, otp):
    try:
      user = User.objects.get(email=email)
      if user.email_verified:
        return VerifyEmailOTP(success=False, message="Email is already verified.", user=None)
      
      is_valid, message = valid_otp(user, otp, settings.OTP_EXPIRATION_MINUTES)

      if not is_valid:
        return VerifyEmailOTP(success=False, message=message, user=None)
      
      user.email_verified = True
      user.is_active = True
      user.otp_secret = None
      user.otp_created_at = None
      user.save()
      
      token = get_token(user)
      refresh_token = create_refresh_token(user)
      
      return VerifyEmailOTP(success=True, message="Email verified successfully.", user=user, token = token, refresh_token = refresh_token)
    
    except User.DoesNotExist:
      return VerifyEmailOTP(success=False, message="User with this email does not exist.", user=None)
    
    except Exception as e:
      return VerifyEmailOTP(success=False, message=f"An error occurred: {str(e)}", user=None)

class LoginUser(graphene.Mutation):
  class Arguments:
    email = graphene.String(required=True)
    password = graphene.String(required=True)
  
  success = graphene.Boolean()
  message = graphene.String()
  mfa_required = graphene.Boolean()
  token = graphene.String()
  refresh_token = graphene.String()
  user = graphene.Field(UserType)
  
  @classmethod
  def mutate(cls, root, info, email, password):
    try:
      user = User.objects.get(email=email)
      
      if not user.is_active:
        return LoginUser(success=False, message='Account is not active. Please verify your email.', mfa_required=False, token=None, refresh_token=None, user=None)
      
      if not user.check_password(password):
        return LoginUser(success=False, message='Invalid credentials.', mfa_required=False, token=None, refresh_token=None, user=None)
      
      if user.mfa_enabled:
        otp = generate_otp()
        user.otp_secret = otp
        user.otp_created_at = timezone.now()
        user.save()
        
        if send_otp_email(user, otp, subject="Your Two-factor OTP"):
          return LoginUser(success=True, message='Two-factor OTP sent to your email.', mfa_required=True, token=None, refresh_token=None, user=None)
        
        else:
          return LoginUser(success=False, message='Failed to send OTP email.', mfa_required=False, token=None, refresh_token=None, user=None)
      
      else:
        token = get_token(user)
        refresh_token = create_refresh_token(user)
        
        return LoginUser(success=True, message='Login successful.', mfa_required=False, token=token, refresh_token=refresh_token, user=user)
    
    except User.DoesNotExist:
      return LoginUser(success=False, message='Invalid credentials.', mfa_required=False, token=None, refresh_token=None, user=None)
    
    except Exception as e:
      return LoginUser(success=False, message=f'An error occurred: {str(e)}', mfa_required=False, token=None, refresh_token=None, user=None)

class RequestMFAOTP(graphene.Mutation):
  success = graphene.Boolean()
  message = graphene.String()
  
  @classmethod
  @login_required
  def mutate(cls, root, info):
    user = info.context.user
    if not user.email_verified:
      return RequestMFAOTP(success=False, message='Email is not verified.')
    
    if not user.mfa_enabled:
      return RequestMFAOTP(success=False, message='MFA is not enabled for this account.')
    
    otp = generate_otp()
    user.otp_secret = otp
    user.otp_created_at = timezone.now()
    user.save()
    
    if send_otp_email(user, otp, subject="Confirm MFA OTP"):
      return RequestMFAOTP(success=True, message='MFA OTP sent to your email.')

    else:
      return RequestMFAOTP(success=False, message='Failed to send MFA OTP email.')

class Enable_MFA(graphene.Mutation):
  class Arguments:
    otp = graphene.String(required=True)
  
  success = graphene.Boolean()
  message = graphene.String()
  user = graphene.Field(UserType)

  @classmethod
  @login_required
  def mutate(cls, root, info, otp):
    user = info.context.user
    if user.mfa_enabled:
      return Enable_MFA(success=False, message='MFA is already enabled.', user=user)
    
    if user.mfa_enabled:
      return Enable_MFA(success=False, message='MFA is already enabled.', user=user)
    
    is_valid, message = valid_otp(user, otp, settings.OTP_EXPIRATION_MINUTES)
    
    if not is_valid:
      return Enable_MFA(success=False, message=message, user=user)
    
    user.mfa_enabled = True
    user.otp_secret = None
    user.otp_created_at = None
    user.save()
    return Enable_MFA(success=True, message='MFA enabled successfully.', user=user)

class Disable_MFA(graphene.Mutation):
  success = graphene.Boolean()
  message = graphene.String()
  user = graphene.Field(UserType)
  
  @classmethod
  @login_required
  def mutate(cls, root, info):
    user = info.context.user
    if not user.mfa_enabled:
      return Disable_MFA(success=False, message='MFA is not enabled.', user=user)
    
    user.mfa_enabled = False

class Mutation(graphene.ObjectType):
  login_user = LoginUser.Field()
  verify_token = graphql_jwt.Verify.Field()
  refresh_token = graphql_jwt.Refresh.Field()
  
  register_user = RegisterUser.Field()
  request_email_verification_otp = RequestEmailVerificationOTP.Field()
  verify_email_otp = VerifyEmailOTP.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)