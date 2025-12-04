import uuid
from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField

# Create your models here.

class Place(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  city = models.CharField(max_length=150)
  state = models.CharField(max_length=150)
  country = models.CharField(max_length=150)
  latitude = models.FloatField(null=True, blank=True)
  longitude = models.FloatField(null=True, blank=True)
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    unique_together = ('city', 'state', 'country')

  def __str__(self):
    return f"{self.city}, {self.state}, {self.country}"

class PlaceInsights(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="insights")
  description = models.TextField()
  history = models.TextField()
  cultural_notes = models.TextField()
  famous_for = ArrayField(models.CharField(max_length=255))
  things_to_do = ArrayField(models.CharField(max_length=255))
  food_specialties = ArrayField(models.CharField(max_length=255))
  quotes = ArrayField(models.CharField(max_length=500))
  hero_image_keywords = ArrayField(models.CharField(max_length=255))
  neighbourhood_patterns = ArrayField(models.CharField(max_length=255))
  tourist_traps = ArrayField(models.JSONField())  
  time_based_actions = models.JSONField()
  is_stale = models.BooleanField(default=False)
  last_updated = models.DateTimeField(auto_now=True)
  expires_at = models.DateTimeField()
  last_requested = models.DateTimeField(null=True, blank=True)
  version = models.IntegerField(default=1)

  def __str__(self):
    return f"Insights for {self.place} (v{self.version})"

class SeasonalInsights(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="seasonal_insights")
  season = models.CharField(max_length=50)
  description = models.TextField()
  recommended_activities = ArrayField(models.CharField(max_length=255))
  cautions = ArrayField(models.CharField(max_length=255))
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    unique_together = ("place", "season")

  def __str__(self):
    return f"{self.place.city} - {self.season}"

class TouristTrap(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="trap_areas")
  name = models.CharField(max_length=200)
  latitude = models.FloatField()
  longitude = models.FloatField()
  reason = models.TextField()
  created_at = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return f"{self.name} - {self.place.city}"
