import uuid
from django.conf import settings
from django.db import models

# Create your models here.

class Trip(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trips')
  origin = models.CharField(max_length=255)
  destination = models.CharField(max_length=255)
  route_polyline = models.TextField(blank=True, null=True)
  companions = models.PositiveIntegerField(default=0)
  updated_at = models.DateTimeField(auto_now=True)
  created_at = models.DateTimeField(auto_now_add=True)
  
  def __str__(self):
    return f"{self.user.first_name}'s trip from {self.origin} to {self.destination}"
  
  class Meta:
    ordering = ['-created_at']