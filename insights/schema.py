import graphene
from graphene_django import DjangoObjectType
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
from insights.services.cache_manager import fetch_or_generate_insights


# GraphQL Types for all models
class PlaceType(DjangoObjectType):
    class Meta:
        model = Place
        fields = "__all__"


class PlaceInsightsType(DjangoObjectType):
    class Meta:
        model = PlaceInsights
        fields = "__all__"


class MostFamousPlaceType(DjangoObjectType):
    class Meta:
        model = MostFamousPlace
        fields = "__all__"


class FamousPlaceType(DjangoObjectType):
    class Meta:
        model = FamousPlace
        fields = "__all__"


class FamousActivityType(DjangoObjectType):
    class Meta:
        model = FamousActivity
        fields = "__all__"


class SeasonalInsightsType(DjangoObjectType):
    class Meta:
        model = SeasonalInsights
        fields = "__all__"


class TouristTrapType(DjangoObjectType):
    class Meta:
        model = TouristTrap
        fields = "__all__"


class FoodSpecialtyType(DjangoObjectType):
    class Meta:
        model = FoodSpecialty
        fields = "__all__"


class HiddenGemType(DjangoObjectType):
    class Meta:
        model = HiddenGem
        fields = "__all__"


class DayActivityType(DjangoObjectType):
    class Meta:
        model = DayActivity
        fields = "__all__"


class ThingToDoType(DjangoObjectType):
    class Meta:
        model = ThingToDo
        fields = "__all__"


# Comprehensive Place Data Type
class CompletePlaceDataType(graphene.ObjectType):
    """Complete place data including all related information"""

    # Core place info
    place = graphene.Field(PlaceType)
    insights = graphene.Field(PlaceInsightsType)

    # Landmarks with images
    most_famous_place = graphene.Field(MostFamousPlaceType)
    famous_places = graphene.List(FamousPlaceType)

    # Activities and things to do
    famous_activities = graphene.List(FamousActivityType)
    day_activities = graphene.List(DayActivityType)
    things_to_do = graphene.List(ThingToDoType)

    # Seasonal and location info
    seasonal_insights = graphene.List(SeasonalInsightsType)

    # Warnings and recommendations
    tourist_traps = graphene.List(TouristTrapType)

    # Food and hidden gems
    food_specialties = graphene.List(FoodSpecialtyType)
    hidden_gems = graphene.List(HiddenGemType)


class Query(graphene.ObjectType):
    # Original query - returns just PlaceInsights
    place_info = graphene.Field(
        PlaceInsightsType,
        city=graphene.String(required=True),
        state=graphene.String(),
        country=graphene.String(required=True),
    )

    # New comprehensive query - returns complete place data
    complete_place_data = graphene.Field(
        CompletePlaceDataType,
        city=graphene.String(required=True),
        state=graphene.String(),
        country=graphene.String(required=True),
    )

    def resolve_place_info(self, info, city, country, state=None):
        """Returns only PlaceInsights object"""
        from asgiref.sync import async_to_sync

        return async_to_sync(fetch_or_generate_insights)(city, state, country)

    def resolve_complete_place_data(self, info, city, country, state=None):
        """
        Returns complete place data with all related information including:
        - Place details with image
        - Insights (quotes, description)
        - Most famous place with image
        - Famous places with images
        - Activities, seasonal insights, tourist traps, food, hidden gems, etc.
        """
        from asgiref.sync import async_to_sync

        try:
            # Fetch or generate insights (triggers image fetching)
            place_insights = async_to_sync(fetch_or_generate_insights)(
                city, state or "", country
            )

            if place_insights is None:
                raise ValueError(
                    f"Could not generate or retrieve insights for {city}, {country}"
                )

            # Get the related place object
            place = place_insights.place

            # Fetch all related data using synchronous queries
            most_famous = MostFamousPlace.objects.filter(place=place).first()
            famous_places = list(FamousPlace.objects.filter(place=place))
            famous_activities = list(FamousActivity.objects.filter(place=place))
            day_activities = list(DayActivity.objects.filter(place=place))
            things_to_do = list(ThingToDo.objects.filter(place=place))
            seasonal_insights = list(SeasonalInsights.objects.filter(place=place))
            tourist_traps = list(TouristTrap.objects.filter(place=place))
            food_specialties = list(FoodSpecialty.objects.filter(place=place))
            hidden_gems = list(HiddenGem.objects.filter(place=place))

            return CompletePlaceDataType(
                place=place,
                insights=place_insights,
                most_famous_place=most_famous,
                famous_places=famous_places,
                famous_activities=famous_activities,
                day_activities=day_activities,
                things_to_do=things_to_do,
                seasonal_insights=seasonal_insights,
                tourist_traps=tourist_traps,
                food_specialties=food_specialties,
                hidden_gems=hidden_gems,
            )
        except ValueError as e:
            # User-friendly error for known issues
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"ValueError in resolve_complete_place_data: {str(e)}")
            raise Exception(f"Failed to generate insights: {str(e)}") from e
        except Exception as e:
            # Log the error for debugging
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Error in resolve_complete_place_data: {str(e)}", exc_info=True
            )
            raise


class Mutation(graphene.ObjectType):
    pass
