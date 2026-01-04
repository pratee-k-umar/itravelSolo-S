import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

# Create your models here.


class Place(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    city = models.CharField(max_length=150)
    state = models.CharField(max_length=150)
    country = models.CharField(max_length=150)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    image = models.URLField(max_length=500, blank=True, default="")

    # Visual theme for consistent image fetching
    theme_color = models.CharField(
        max_length=7,
        blank=True,
        default="",
        help_text="Hex color code representing city's theme (e.g., #3B82F6 for blue)",
    )
    visual_tags = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Visual keywords for image search: sunset, mountains, modern, historic, etc.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("city", "state", "country")
        indexes = [
            models.Index(fields=["city"]),
            models.Index(fields=["state"]),
            models.Index(fields=["country"]),
            models.Index(fields=["latitude", "longitude"]),
        ]

    def __str__(self):
        if self.state:
            return f"{self.city}, {self.state}, {self.country}"
        return f"{self.city}, {self.country}"


class PlaceInsights(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    place = models.OneToOneField(
        Place, on_delete=models.CASCADE, related_name="insight"
    )

    # Basic info - stored directly
    main_quote = models.TextField()
    sub_quote = models.TextField()
    description = models.TextField()

    # Metadata
    is_stale = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    last_requested = models.DateTimeField(null=True, blank=True)
    version = models.IntegerField(default=1)

    class Meta:
        verbose_name = "Place Insight"
        verbose_name_plural = "Place Insights"
        indexes = [
            models.Index(fields=["expires_at"]),
            models.Index(fields=["is_stale"]),
        ]

    def __str__(self):
        return f"Insights for {self.place} (v{self.version})"


class MostFamousPlace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="famous_places"
    )
    name = models.CharField(max_length=200)
    quote = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    image = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.place.city}"


class FamousPlace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="notable_places"
    )
    name = models.CharField(max_length=200)
    quote = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    image = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.place.city}"


class FamousActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="notable_activities"
    )
    name = models.CharField(max_length=200)
    time = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.place.city}"


class SeasonalInsights(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="seasonal_insights"
    )
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
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="trap_areas"
    )
    name = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.place.city}"


class FoodSpecialty(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="food_specialties"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Food Specialties"

    def __str__(self):
        return f"{self.name} - {self.place.city}"


class HiddenGem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="hidden_gems"
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.place.city}"


class DayActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="day_activities"
    )
    activity = models.CharField(max_length=200)
    day_time = models.CharField(max_length=100)  # e.g., "Morning", "Afternoon"
    time = models.CharField(max_length=100)  # e.g., "6:00 AM - 9:00 AM"
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Day Activities"

    def __str__(self):
        return f"{self.activity} ({self.day_time}) - {self.place.city}"


class ThingToDo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="things_to_do"
    )
    activity_type = models.CharField(max_length=100)  # e.g., "Hiking", "Sightseeing"
    location = models.CharField(max_length=200)
    time = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Things To Do"

    def __str__(self):
        return f"{self.activity_type} at {self.location} - {self.place.city}"
