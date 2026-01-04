from django.urls import path
from insights.views import CompletePlaceDataAPIView

urlpatterns = [
    path("place-data/", CompletePlaceDataAPIView.as_view(), name="complete-place-data"),
]
