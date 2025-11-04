import graphene
import graphql_jwt
from graphene_django.types import DjangoObjectType
from .models import User, Profile

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
    fields = ('id', 'first_name', 'last_name', 'email', 'profile')
  
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
  errors = graphene.List(graphene.String)
  
  @classmethod
  def mutate(cls, root, info, input):
    try:
      user = User.Objects.create_user(
        first_name=input.first_name,
        last_name=input.last_name,
        email=input.email,
        password=input.password
      )
      return RegisterUser(user=user, success=True, errors=None)
    except Exception as e:
      return RegisterUser(user=None, success=False, errors=[str(e)])

class Mutation(graphene.ObjectType):
  token_auth = graphql_jwt.ObtainJSONWebToken.Field()
  verify_token = graphql_jwt.Verify.Field()
  refresh_token = graphql_jwt.Refresh.Field()
  
  register_user = RegisterUser.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)