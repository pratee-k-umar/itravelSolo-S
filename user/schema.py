import graphene
import graphql_jwt
from graphene_django.types import DjangoObjectType
from .models import User, Profile
from .utils import generate_otp, send_otp_email, valid_otp
from django.utils import timezone
from django.conf import settings

class RegisterUserInput(graphene.InputObjectType):
  first_name = graphene.String(required=True)
  last_name = graphene.String(required=True)
  email = graphene.String(required=True)
  password = graphene.String(required=True)

class ProfileType(DjangoObjectType):
  class Meta:
    model = Profile
    fields = ('id', 'user', 'profile_image', 'bio', 'address', 'phone_number', 'profession', 'last_seen')

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
      
      return VerifyEmailOTP(success=True, message="Email verified successfully.", user=user)
    
    except User.DoesNotExist:
      return VerifyEmailOTP(success=False, message="User with this email does not exist.", user=None)
    
    except Exception as e:
      return VerifyEmailOTP(success=False, message=f"An error occurred: {str(e)}", user=None)

class Mutation(graphene.ObjectType):
  token_auth = graphql_jwt.ObtainJSONWebToken.Field()
  verify_token = graphql_jwt.Verify.Field()
  refresh_token = graphql_jwt.Refresh.Field()
  
  register_user = RegisterUser.Field()
  request_email_verification_otp = RequestEmailVerificationOTP.Field()
  verify_email_otp = VerifyEmailOTP.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)