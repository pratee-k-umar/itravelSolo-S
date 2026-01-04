from insights.models import (
    DayActivity,
    FamousActivity,
    FamousPlace,
    FoodSpecialty,
    HiddenGem,
    MostFamousPlace,
    Place,
    PlaceInsights,
    SeasonalInsights,
    ThingToDo,
    TouristTrap,
)
from rest_framework import serializers


class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = [
            "id",
            "city",
            "state",
            "country",
            "latitude",
            "longitude",
            "image",
            "theme_color",
            "visual_tags",
            "created_at",
        ]


class PlaceInsightsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaceInsights
        fields = [
            "id",
            "main_quote",
            "sub_quote",
            "description",
            "version",
            "last_updated",
            "expires_at",
        ]


class MostFamousPlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MostFamousPlace
        fields = ["id", "name", "quote", "latitude", "longitude", "image"]


class FamousPlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamousPlace
        fields = ["id", "name", "quote", "latitude", "longitude", "image"]


class FamousActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = FamousActivity
        fields = ["id", "name", "time"]


class SeasonalInsightsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeasonalInsights
        fields = ["id", "season", "description", "recommended_activities", "cautions"]


class TouristTrapSerializer(serializers.ModelSerializer):
    class Meta:
        model = TouristTrap
        fields = ["id", "name", "latitude", "longitude", "reason"]


class FoodSpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodSpecialty
        fields = ["id", "name", "description"]


class HiddenGemSerializer(serializers.ModelSerializer):
    class Meta:
        model = HiddenGem
        fields = ["id", "name", "description", "latitude", "longitude"]


class DayActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DayActivity
        fields = ["id", "activity", "day_time", "time"]


class ThingToDoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThingToDo
        fields = ["id", "activity_type", "location", "time", "latitude", "longitude"]


class CompletePlaceDataSerializer(serializers.Serializer):
    """
    Complete place data including all related information.
    """

    place = PlaceSerializer()
    insights = PlaceInsightsSerializer()
    most_famous_place = MostFamousPlaceSerializer(allow_null=True)
    famous_places = FamousPlaceSerializer(many=True)
    famous_activities = FamousActivitySerializer(many=True)
    day_activities = DayActivitySerializer(many=True)
    things_to_do = ThingToDoSerializer(many=True)
    seasonal_insights = SeasonalInsightsSerializer(many=True)
    tourist_traps = TouristTrapSerializer(many=True)
    food_specialties = FoodSpecialtySerializer(many=True)
    hidden_gems = HiddenGemSerializer(many=True)
