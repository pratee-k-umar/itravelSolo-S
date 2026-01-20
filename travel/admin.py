from django.contrib import admin
from travel.models import Trip, TripMatch, LocationHistory, TripSuggestion, ActivityHotspot


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['destination', 'user', 'start_date', 'end_date', 'is_active', 'privacy']
    list_filter = ['is_active', 'privacy', 'start_date']
    search_fields = ['destination', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(TripMatch)
class TripMatchAdmin(admin.ModelAdmin):
    list_display = ['trip', 'matched_user', 'score', 'status', 'current_distance_km', 'is_proximity_expired']
    list_filter = ['status', 'is_proximity_expired']
    readonly_fields = ['id', 'created_at']


@admin.register(LocationHistory)
class LocationHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'latitude', 'longitude', 'recorded_at', 'trip']
    list_filter = ['recorded_at', 'is_background']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at']


@admin.register(TripSuggestion)
class TripSuggestionAdmin(admin.ModelAdmin):
    list_display = ['user', 'suggestion_type', 'title', 'is_read', 'hotspot_user_count', 'created_at']
    list_filter = ['suggestion_type', 'is_read', 'is_acted_upon', 'is_dismissed']
    search_fields = ['user__email', 'title', 'content']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ActivityHotspot)
class ActivityHotspotAdmin(admin.ModelAdmin):
    list_display = ['place_name', 'latitude', 'longitude', 'user_count', 'last_activity', 'is_expired']
    list_filter = ['last_activity', 'user_count']
    search_fields = ['place_name']
    readonly_fields = ['id', 'first_detected']
    
    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
