import graphene
from graphene_django.types import DjangoObjectType
from .models import User, Profile

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

schema = graphene.Schema(query=Query)