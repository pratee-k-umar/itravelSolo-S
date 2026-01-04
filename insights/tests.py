import json
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

from django.test import TestCase
from django.utils import timezone
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
from insights.services.cache_manager import (
    fetch_or_generate_insights,
    save_generate_data,
)
from insights.services.gemini import Gemini, _parse_and_validate_gemini_output


class GeminiServiceTests(TestCase):
    """Test suite for Gemini AI service"""

    def setUp(self):
        """Set up test data"""
        self.gemini = Gemini(city="Paris", state="", country="France")
        self.sample_ai_response = {
            "main_quote": "City Light",
            "sub_quote": "Romance and Culture",
            "description": "The capital of France known for art, fashion, and cuisine.",
            "most_famous_place": {
                "name": "Eiffel Tower",
                "quote": "Iconic iron landmark",
                "coordinates": {"lat": 48.8584, "lng": 2.2945},
            },
            "famous_places": [
                {
                    "name": "Louvre Museum",
                    "quote": "World's largest art museum",
                    "coordinates": {"lat": 48.8606, "lng": 2.3376},
                }
            ],
            "famous_activities": {
                "Seine River Cruise": "Evening",
                "Visit Montmartre": "Morning",
            },
            "things_to_do": {
                "Museums": [
                    {
                        "location": "Louvre Museum",
                        "time": "All day",
                        "coordinates": {"lat": 48.8606, "lng": 2.3376},
                    }
                ]
            },
            "food_specialties": ["Croissant", "Escargot", "Crème Brûlée"],
            "tourist_traps": ["Overpriced cafes near Eiffel Tower"],
            "seasonal_behavior": {
                "summer": "Peak tourist season with warm weather",
                "winter": "Festive Christmas markets",
            },
            "day_activities": [
                {
                    "activity": "Morning cafe visit",
                    "day_time": "Morning",
                    "time": "8:00 AM",
                }
            ],
            "hidden_gems": ["Canal Saint-Martin", "Musée Rodin Gardens"],
        }

    def test_build_prompt_with_state(self):
        """Test prompt building with state"""
        gemini = Gemini(city="Austin", state="Texas", country="USA")
        prompt = gemini.build_prompt()

        self.assertIn("Austin, Texas, USA", prompt)
        self.assertIn("JSON", prompt)
        self.assertIn("coordinates", prompt)

    def test_build_prompt_without_state(self):
        """Test prompt building without state"""
        prompt = self.gemini.build_prompt()

        self.assertIn("Paris, France", prompt)
        self.assertNotIn("Paris,  France", prompt)  # No double space

    def test_parse_valid_gemini_output(self):
        """Test parsing valid AI response"""
        json_string = json.dumps(self.sample_ai_response)

        parsed = _parse_and_validate_gemini_output(json_string)

        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed["main_quote"], "City Light")
        self.assertEqual(len(parsed["food_specialties"]), 3)

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON"""
        invalid_json = "{ invalid json here }"

        parsed = _parse_and_validate_gemini_output(invalid_json)

        self.assertIsNone(parsed)

    def test_parse_empty_response(self):
        """Test parsing empty response"""
        parsed = _parse_and_validate_gemini_output("")

        self.assertIsNone(parsed)

    @patch("insights.services.gemini.client.models.generate_content")
    async def test_generate_place_insights_success(self, mock_generate):
        """Test successful AI insight generation"""
        mock_response = Mock()
        mock_response.text = json.dumps(self.sample_ai_response)
        mock_generate.return_value = mock_response

        result = await self.gemini.generate_place_insights()

        self.assertIsNotNone(result)
        self.assertEqual(result["main_quote"], "City Light")

    @patch("insights.services.gemini.client.models.generate_content")
    async def test_generate_place_insights_api_error(self, mock_generate):
        """Test AI generation with API error"""
        from google.genai import errors

        mock_generate.side_effect = Exception("API Error")

        result = await self.gemini.generate_place_insights()

        self.assertIsNone(result)


class CacheManagerTests(TestCase):
    """Test suite for cache manager service"""

    async def asyncSetUp(self):
        """Async setup for test data"""
        self.place = await Place.objects.acreate(
            city="Paris", state="", country="France", latitude=48.8566, longitude=2.3522
        )

        self.insights_data = {
            "main_quote": "City Light",
            "sub_quote": "Romance and Culture",
            "description": "The capital of France.",
            "most_famous_place": {
                "name": "Eiffel Tower",
                "quote": "Iconic landmark",
                "coordinates": {"lat": 48.8584, "lng": 2.2945},
            },
            "famous_places": [
                {
                    "name": "Louvre",
                    "quote": "Art museum",
                    "coordinates": {"lat": 48.8606, "lng": 2.3376},
                }
            ],
            "famous_activities": {"Cruise": "Evening"},
            "things_to_do": {
                "Museums": [
                    {
                        "location": "Louvre",
                        "time": "All day",
                        "coordinates": {"lat": 48.8606, "lng": 2.3376},
                    }
                ]
            },
            "food_specialties": ["Croissant"],
            "tourist_traps": ["Expensive cafes"],
            "seasonal_behavior": {"summer": "Busy"},
            "day_activities": [
                {"activity": "Cafe", "day_time": "Morning", "time": "8 AM"}
            ],
            "hidden_gems": ["Canal Saint-Martin"],
        }

    async def test_save_generate_data_creates_insights(self):
        """Test saving AI data creates PlaceInsights"""
        await self.asyncSetUp()

        result = await save_generate_data(self.place, self.insights_data)

        self.assertIsNotNone(result)
        self.assertEqual(result.main_quote, "City Light")
        self.assertEqual(result.version, 1)

    async def test_save_generate_data_creates_related_models(self):
        """Test saving creates all related normalized models"""
        await self.asyncSetUp()

        await save_generate_data(self.place, self.insights_data)

        # Check MostFamousPlace
        mfp = await MostFamousPlace.objects.filter(place=self.place).afirst()
        self.assertIsNotNone(mfp)
        self.assertEqual(mfp.name, "Eiffel Tower")

        # Check FamousPlace
        fp_count = await FamousPlace.objects.filter(place=self.place).acount()
        self.assertEqual(fp_count, 1)

        # Check FamousActivity
        fa_count = await FamousActivity.objects.filter(place=self.place).acount()
        self.assertEqual(fa_count, 1)

        # Check FoodSpecialty
        food_count = await FoodSpecialty.objects.filter(place=self.place).acount()
        self.assertEqual(food_count, 1)

        # Check HiddenGem
        gem_count = await HiddenGem.objects.filter(place=self.place).acount()
        self.assertEqual(gem_count, 1)

    async def test_save_generate_data_updates_version(self):
        """Test that updating insights increments version"""
        await self.asyncSetUp()

        # First save
        result1 = await save_generate_data(self.place, self.insights_data)
        self.assertEqual(result1.version, 1)

        # Second save should increment version
        result2 = await save_generate_data(self.place, self.insights_data)
        self.assertEqual(result2.version, 2)

    async def test_save_generate_data_deletes_old_relations(self):
        """Test that updating insights deletes old related data"""
        await self.asyncSetUp()

        # First save
        await save_generate_data(self.place, self.insights_data)
        initial_count = await FoodSpecialty.objects.filter(place=self.place).acount()

        # Update with new data
        new_data = self.insights_data.copy()
        new_data["food_specialties"] = ["Baguette", "Cheese"]
        await save_generate_data(self.place, new_data)

        # Should have only new items
        final_count = await FoodSpecialty.objects.filter(place=self.place).acount()
        self.assertEqual(final_count, 2)

    async def test_save_generate_data_with_empty_insights(self):
        """Test saving with empty insights data"""
        await self.asyncSetUp()

        result = await save_generate_data(self.place, {})

        self.assertIsNone(result)

    @patch("insights.services.cache_manager.save_generate_data")
    @patch("insights.services.gemini.Gemini.generate_place_insights")
    async def test_fetch_or_generate_cached(self, mock_generate, mock_save):
        """Test fetching cached insights"""
        await self.asyncSetUp()

        # Create existing cached insight
        await PlaceInsights.objects.acreate(
            place=self.place,
            main_quote="Cached Quote",
            expires_at=timezone.now() + timedelta(days=30),
            is_stale=False,
            version=1,
        )

        result = await fetch_or_generate_insights(
            city=self.place.city, state=self.place.state, country=self.place.country
        )

        # Should return cached data without calling AI
        self.assertIsNotNone(result)
        mock_generate.assert_not_called()

    @patch("insights.services.gemini.Gemini.generate_place_insights")
    async def test_fetch_or_generate_expired_cache(self, mock_generate):
        """Test generating new insights when cache expired"""
        await self.asyncSetUp()

        # Create expired insight
        await PlaceInsights.objects.acreate(
            place=self.place,
            main_quote="Expired",
            expires_at=timezone.now() - timedelta(days=1),
            is_stale=True,
            version=1,
        )

        mock_generate.return_value = self.insights_data

        result = await fetch_or_generate_insights(
            city=self.place.city, state=self.place.state, country=self.place.country
        )

        # Should call AI to generate new data
        mock_generate.assert_called_once()


class PlaceModelTests(TestCase):
    """Test suite for Place and related models"""

    async def asyncSetUp(self):
        """Create test place"""
        self.place = await Place.objects.acreate(
            city="Tokyo",
            state="",
            country="Japan",
            latitude=35.6762,
            longitude=139.6503,
        )

    async def test_place_creation(self):
        """Test Place model creation"""
        await self.asyncSetUp()

        self.assertIsNotNone(self.place.id)
        self.assertEqual(str(self.place), "Tokyo, Japan")

    async def test_place_with_state(self):
        """Test Place string representation with state"""
        place = await Place.objects.acreate(
            city="Austin",
            state="Texas",
            country="USA",
            latitude=30.2672,
            longitude=-97.7431,
        )

        self.assertEqual(str(place), "Austin, Texas, USA")

    async def test_most_famous_place_creation(self):
        """Test MostFamousPlace creation"""
        await self.asyncSetUp()

        mfp = await MostFamousPlace.objects.acreate(
            place=self.place,
            name="Tokyo Tower",
            quote="Iconic landmark",
            latitude=35.6586,
            longitude=139.7454,
        )

        self.assertIsNotNone(mfp.id)
        self.assertEqual(mfp.place, self.place)

    async def test_cascade_delete(self):
        """Test that deleting place deletes related insights"""
        await self.asyncSetUp()

        # Create insights and related data
        await PlaceInsights.objects.acreate(
            place=self.place,
            main_quote="Test",
            expires_at=timezone.now() + timedelta(days=90),
            version=1,
        )
        await FoodSpecialty.objects.acreate(place=self.place, name="Sushi")

        place_id = self.place.id
        await self.place.adelete()

        # Related objects should be deleted
        insights_count = await PlaceInsights.objects.filter(place_id=place_id).acount()
        food_count = await FoodSpecialty.objects.filter(place_id=place_id).acount()

        self.assertEqual(insights_count, 0)
        self.assertEqual(food_count, 0)
