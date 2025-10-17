from rest_framework.permissions import AllowAny
from rest_framework import generics
from .models import User
from .serializers import RegisterSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer

# Create your views here.

class RegisterView(generics.CreateAPIView):
  queryset = User.objects.all()
  permission_classes = (AllowAny,)
  serializer_class = RegisterSerializer
  
  def create(self, request, *args, **kwargs):
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    
    refresh_token = RefreshToken.for_user(user)
    
    user_data = UserSerializer(user).data
    
    return Response({
      "user": user_data,
      "refresh": str(refresh_token),
      "access": str(refresh_token.access_token),
    }, status=status.HTTP_201_CREATED)