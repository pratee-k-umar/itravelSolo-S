from django.urls import path

from .views import UserView as User
from .views import RegisterView
from rest_framework_simplejwt.views import (
  TokenObtainPairView,
  TokenRefreshView,
)

urlpatterns = [
  path('register/', RegisterView.as_view(), name='register'),
  path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
  path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
  path('user/', User.as_view(), name='user_detail'),
]