import logging
from datetime import datetime, timedelta

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
from insights.scraper.image_service import ImageService
from insights.services.gemini import Gemini

logger = logging.getLogger(__name__)


async def save_generate_data(place: Place, insights: dict) -> PlaceInsights:
    """
    Saves parsed AI insights into PlaceInsights and related models.
    Uses normalized database tables instead of JSON fields.
    """

    if not insights:
        logger.warning(f"No insights data provided for place: {place}")
        return None

    expires_at = timezone.now() + timedelta(days=90)

    # Get existing insight to increment version
    existing = await PlaceInsights.objects.filter(place=place).afirst()
    new_version = existing.version + 1 if existing else 1

    # Extract and save visual theme to Place
    visual_theme = insights.get("visual_theme", {})
    if visual_theme:
        place.theme_color = visual_theme.get("color", "")
        place.visual_tags = visual_theme.get("tags", "")
        await place.asave(update_fields=["theme_color", "visual_tags"])
        logger.info(
            f"Saved theme for {place}: color={place.theme_color}, tags={place.visual_tags}"
        )

    # Save or update main PlaceInsights
    place_insights, created = await PlaceInsights.objects.aupdate_or_create(
        place=place,
        defaults={
            "main_quote": insights.get("main_quote", ""),
            "sub_quote": insights.get("sub_quote", ""),
            "description": insights.get("description", ""),
            "expires_at": expires_at,
            "is_stale": False,
            "version": new_version,
        },
    )

    # Delete old related data to avoid duplicates
    await MostFamousPlace.objects.filter(place=place).adelete()
    await FamousPlace.objects.filter(place=place).adelete()
    await FamousActivity.objects.filter(place=place).adelete()
    await SeasonalInsights.objects.filter(place=place).adelete()
    await TouristTrap.objects.filter(place=place).adelete()
    await FoodSpecialty.objects.filter(place=place).adelete()
    await HiddenGem.objects.filter(place=place).adelete()
    await DayActivity.objects.filter(place=place).adelete()
    await ThingToDo.objects.filter(place=place).adelete()

    # Save Most Famous Place
    mfp = insights.get("most_famous_place", {})
    if mfp and mfp.get("name"):
        coords = mfp.get("coordinates", {})
        await MostFamousPlace.objects.acreate(
            place=place,
            name=mfp.get("name", ""),
            quote=mfp.get("quote", ""),
            latitude=coords.get("lat", 0.0),
            longitude=coords.get("lng", 0.0),
            image="",  # Can be populated later
        )

    # Save Famous Places
    for fp in insights.get("famous_places", []):
        if fp.get("name"):
            coords = fp.get("coordinates", {})
            await FamousPlace.objects.acreate(
                place=place,
                name=fp.get("name", ""),
                quote=fp.get("quote", ""),
                latitude=coords.get("lat", 0.0),
                longitude=coords.get("lng", 0.0),
                image="",  # Can be populated later
            )

    # Save Famous Activities
    for activity_name, time_of_day in insights.get("famous_activities", {}).items():
        await FamousActivity.objects.acreate(
            place=place, name=activity_name, time=time_of_day
        )

    # Save Seasonal Behavior
    seasonal = insights.get("seasonal_behavior", {})
    for season, description in seasonal.items():
        if description:
            await SeasonalInsights.objects.acreate(
                place=place,
                season=season.capitalize(),
                description=description,
                recommended_activities=[],
                cautions=[],
            )

    # Save Tourist Traps
    for trap in insights.get("tourist_traps", []):
        if trap:
            await TouristTrap.objects.acreate(
                place=place,
                name=trap[:200],  # First 200 chars as name
                latitude=0.0,  # Default, can be enhanced later
                longitude=0.0,
                reason=trap,
            )

    # Save Food Specialties
    for food in insights.get("food_specialties", []):
        if food:
            await FoodSpecialty.objects.acreate(place=place, name=food)

    # Save Hidden Gems
    for gem in insights.get("hidden_gems", []):
        if gem:
            await HiddenGem.objects.acreate(
                place=place, name=gem[:200], description=gem
            )

    # Save Day Activities
    for activity in insights.get("day_activities", []):
        if activity.get("activity"):
            await DayActivity.objects.acreate(
                place=place,
                activity=activity.get("activity", ""),
                day_time=activity.get("day_time", ""),
                time=activity.get("time", ""),
            )

    # Save Things To Do
    for activity_type, locations in insights.get("things_to_do", {}).items():
        for location_data in locations:
            if location_data.get("location"):
                coords = location_data.get("coordinates", {})
                await ThingToDo.objects.acreate(
                    place=place,
                    activity_type=activity_type,
                    location=location_data.get("location", ""),
                    time=location_data.get("time", ""),
                    latitude=coords.get("lat"),
                    longitude=coords.get("lng"),
                )

    logger.info(
        f"Successfully {'created' if created else 'updated'} insights for Place: {place} (v{new_version})"
    )
    # Auto-fetch images for all places (main place, most famous place, famous places)
    image_service = ImageService()

    try:
        # 1. Fetch image for main place (city/destination)
        await image_service.populate_place_image(place)

        # 2. Fetch image for most famous place
        await image_service.populate_most_famous_place_image(place)

        # 3. Fetch images for famous places (up to 5)
        images_updated = await image_service.populate_famous_place_images(
            place, limit=5
        )
        logger.info(
            f"Updated images: main place + most famous + {images_updated} famous places for {place}"
        )
    except Exception as e:
        logger.error(f"Error fetching images for {place}: {e}")
        # Don't fail the entire operation if image fetching fails

    return place_insights


async def fetch_or_generate_insights(
    city: str, state: str, country: str
) -> PlaceInsights:
    place, _ = await Place.objects.aget_or_create(
        city=city.strip(), state=state.strip(), country=country.strip()
    )

    try:
        place_insights = await PlaceInsights.objects.aget(place=place)

        if place_insights.expires_at < timezone.now() or place_insights.is_stale:
            logger.info(f"Insights for {place} are stale or expired. Regenerating...")

            parsed = await Gemini(city, state, country).generate_place_insights()

            if parsed is None:
                raise ValueError(
                    f"Failed to generate insights for {place} - Gemini returned None"
                )

            place_insights = await save_generate_data(place, parsed)

        else:
            logger.info(f"Returning cached insights for {place}")

    except PlaceInsights.DoesNotExist:
        logger.info(f"No insights found for {place}. Generating new AI insights...")

        parsed = await Gemini(city, state, country).generate_place_insights()

        if parsed is None:
            raise ValueError(
                f"Failed to generate insights for {place} - Gemini returned None or invalid data"
            )

        place_insights = await save_generate_data(place, parsed)

    if place_insights is None:
        raise ValueError(f"Failed to create or retrieve insights for {place}")

    place_insights.last_requested = timezone.now()
    await place_insights.asave(update_fields=["last_requested"])

    return place_insights
