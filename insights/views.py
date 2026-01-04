from asgiref.sync import async_to_sync
from django.shortcuts import render
from insights.models import Place, PlaceInsights
from insights.rest.serializers import CompletePlaceDataSerializer
from insights.services.cache_manager import fetch_or_generate_insights
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class CompletePlaceDataAPIView(APIView):
    """
    Public API endpoint to get complete place data.

    Required parameters:
    - city: Name of the city
    - country: Name of the country

    Optional parameters:
    - state: Name of the state (optional)

    Example:
    GET /api/insights/place-data/?city=Paris&country=France
    GET /api/insights/place-data/?city=Mumbai&state=Maharashtra&country=India
    """

    def get(self, request):
        # Get required parameters
        city = request.query_params.get("city")
        country = request.query_params.get("country")
        state = request.query_params.get("state", "")

        # Validate required parameters
        if not city or not country:
            return Response(
                {"error": "Both 'city' and 'country' parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch the complete place data
        try:
            place_data = async_to_sync(self._get_complete_place_data)(
                city, state, country
            )

            if not place_data:
                return Response(
                    {"error": "Place data not found or could not be generated."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = CompletePlaceDataSerializer(place_data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback

            traceback.print_exc()
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    async def _get_complete_place_data(self, city: str, state: str, country: str):
        """
        Fetch complete place data using the cache manager.
        """
        # Get or create place data
        insights = await fetch_or_generate_insights(
            city=city, state=state, country=country
        )

        if not insights:
            return None

        # Fetch place with select_related to avoid sync queries
        insights = await PlaceInsights.objects.select_related("place").aget(
            id=insights.id
        )
        place = insights.place

        # Fetch all related data
        most_famous_place = await place.famous_places.afirst()  # MostFamousPlace
        notable_places = [fp async for fp in place.notable_places.all()]  # FamousPlace
        famous_activities = [
            fa async for fa in place.notable_activities.all()
        ]  # FamousActivity
        day_activities = [da async for da in place.day_activities.all()]  # DayActivity
        things_to_do = [ttd async for ttd in place.things_to_do.all()]  # ThingToDo
        seasonal_insights = [
            si async for si in place.seasonal_insights.all()
        ]  # SeasonalInsights
        tourist_traps = [tt async for tt in place.trap_areas.all()]  # TouristTrap
        food_specialties = [
            fs async for fs in place.food_specialties.all()
        ]  # FoodSpecialty
        hidden_gems = [hg async for hg in place.hidden_gems.all()]  # HiddenGem

        return {
            "place": place,
            "insights": insights,
            "most_famous_place": most_famous_place,
            "famous_places": notable_places,
            "famous_activities": famous_activities,
            "day_activities": day_activities,
            "things_to_do": things_to_do,
            "seasonal_insights": seasonal_insights,
            "tourist_traps": tourist_traps,
            "food_specialties": food_specialties,
            "hidden_gems": hidden_gems,
        }
