from rest_framework import serializers
from .models import User

class RegisterSerializer(serializers.ModelSerializer):
  class Meta:
    model = User
    fields = ['first_name', 'last_name', 'email', 'password', 'profile_image']
    extra_kwargs = {'password': {'write_only': True}}
  
  def create(self, validated_data):
    user = User.objects.create_user(
      first_name=validated_data.get('first_name', ''),
      last_name=validated_data.get('last_name', ''),
      email=validated_data['email'],
      password=validated_data['password'],
      profile_image=validated_data.get('profile_image', None)
    )
    return user

class UserSerializer(serializers.ModelSerializer):
  class Meta:
    model = User
    fields = ['id', 'first_name', 'last_name', 'email', 'profile_image']