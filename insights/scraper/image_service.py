import logging
from typing import Dict, List, Optional

from django.db import models
from insights.models import FamousPlace, MostFamousPlace, Place
from insights.scraper.unsplash_scraper import UnsplashScraper

logger = logging.getLogger(__name__)


def _hex_to_unsplash_color(hex_color: str) -> Optional[str]:
    """
    Map hex color code to closest Unsplash predefined color.
    Unsplash only supports: black_and_white, black, white, yellow, orange, red, purple, magenta, green, teal, blue
    
    Args:
        hex_color: Hex color code (e.g., "#3B82F6")
    
    Returns:
        Unsplash color name or None
    """
    if not hex_color or not hex_color.startswith("#"):
        return None
    
    try:
        # Remove # and convert to RGB
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Check for grayscale
        avg = (r + g + b) / 3
        if abs(r - avg) < 30 and abs(g - avg) < 30 and abs(b - avg) < 30:
            if avg < 50:
                return "black"
            elif avg > 200:
                return "white"
            else:
                return "black_and_white"
        
        # Determine dominant color
        max_val = max(r, g, b)
        
        if max_val == r:
            # Red-dominant
            if g > 100 and b < 100:  # Orange-ish
                return "orange"
            elif g > 150:  # Yellow-ish
                return "yellow"
            elif b > 100:  # Purple/Magenta
                return "magenta" if r > b else "purple"
            else:
                return "red"
        elif max_val == g:
            # Green-dominant
            if b > 100:  # Teal-ish
                return "teal"
            else:
                return "green"
        else:
            # Blue-dominant
            if g > 100:  # Teal-ish
                return "teal"
            elif r > 100:  # Purple-ish
                return "purple"
            else:
                return "blue"
    
    except (ValueError, IndexError) as e:
        logger.warning(f"Invalid hex color format: {hex_color} - {e}")
        return None


class ImageService:
    """
    Service for fetching and managing place images from Unsplash.
    All images are fetched in landscape orientation.
    """

    def __init__(self):
        self.unsplash = UnsplashScraper()

    async def fetch_place_image(self, place: Place) -> Optional[str]:
        """
        Fetch the best quality landscape image for a place using theme-based filtering.
        Uses place's theme color and visual tags for consistency.

        Args:
            place: Place model instance

        Returns:
            Image URL or None
        """
        # Build query with visual tags
        query = self._build_search_query(place)
        if place.visual_tags:
            query += f" {place.visual_tags}"

        # Convert hex color to Unsplash color format
        unsplash_color = _hex_to_unsplash_color(place.theme_color) if place.theme_color else None

        # Get top 10 results with color filter
        images = await self.unsplash.search_images(
            query,
            per_page=10,
            orientation="landscape",
            color=unsplash_color
        )

        if not images:
            logger.warning(f"No images found for: {query} (hex: {place.theme_color}, unsplash: {unsplash_color})")
            # Retry without color filter
            images = await self.unsplash.search_images(
                query, per_page=10, orientation="landscape"
            )

        if not images:
            logger.warning(f"No images found for: {query}")
            return None

        # Auto-select best image with enhanced filtering
        best_image = self._select_best_image(images, query)
        return best_image["url_regular"] if best_image else None

    async def fetch_landmark_image(
        self, landmark_name: str, city: str, place: Place = None
    ) -> Optional[str]:
        """
        Fetch the best quality landscape image for a landmark using theme-based filtering.
        Uses place's theme color for visual consistency.

        Args:
            landmark_name: Name of landmark (e.g., "Eiffel Tower")
            city: City name for context
            place: Optional Place instance for theme color

        Returns:
            Image URL or None
        """
        # Build enhanced query with smart tags
        query = self._build_landmark_query(landmark_name, city, place)

        # Convert hex color to Unsplash color format
        unsplash_color = _hex_to_unsplash_color(place.theme_color) if place and place.theme_color else None

        # Get top 10 results with optional color filter
        images = await self.unsplash.search_images(
            query, per_page=10, orientation="landscape", color=unsplash_color
        )

        if not images and unsplash_color:
            # Retry without color filter if no results
            logger.info(f"No images with color {unsplash_color} (hex: {place.theme_color if place else 'N/A'}), retrying without color filter")
            images = await self.unsplash.search_images(
                query, per_page=10, orientation="landscape"
            )

        if not images:
            logger.warning(f"No images found for: {query}")
            return None

        # Auto-select best image using quality heuristics
        best_image = self._select_best_image(images, query)
        return best_image["url_regular"] if best_image else None

    async def fetch_multiple_images(self, query: str, count: int = 5) -> List[Dict]:
        """
        Fetch multiple landscape images for a query.

        Args:
            query: Search term
            count: Number of images to fetch

        Returns:
            List of image data dictionaries
        """
        return await self.unsplash.search_images(
            query, per_page=count, orientation="landscape"
        )

    async def populate_famous_place_images(self, place: Place, limit: int = 5) -> int:
        """
        Fetch and update landscape images for all FamousPlace entries.

        Args:
            place: Place model instance
            limit: Maximum number of famous places to update

        Returns:
            Number of images updated
        """
        # Get famous places without images (empty string or null)
        famous_places_qs = FamousPlace.objects.filter(place=place).filter(
            models.Q(image="") | models.Q(image__isnull=True)
        )[:limit]

        updated_count = 0

        async for fp in famous_places_qs:
            try:
                logger.info(f"Fetching image for landmark: {fp.name} in {place.city}")
                image_url = await self.fetch_landmark_image(
                    landmark_name=fp.name, city=place.city, place=place
                )

                if image_url:
                    fp.image = image_url
                    await fp.asave(update_fields=["image"])
                    updated_count += 1
                    logger.info(f"✓ Updated image for {fp.name}: {image_url[:80]}...")
                else:
                    logger.warning(f"✗ No image found for {fp.name}")
            except Exception as e:
                logger.error(f"Error fetching image for {fp.name}: {e}", exc_info=True)
                logger.warning(f"Could not find image for {fp.name}")

        return updated_count

    async def populate_place_image(self, place: Place) -> bool:
        """
        Fetch and update landscape image for the main Place (city/destination).

        Args:
            place: Place model instance

        Returns:
            True if updated successfully
        """
        if place.image:
            logger.info(f"Image already exists for {place}")
            return True

        image_url = await self.fetch_place_image(place)

        if image_url:
            place.image = image_url
            await place.asave(update_fields=["image"])
            logger.info(f"Updated image for main place {place}: {image_url}")
            return True

        logger.warning(f"Could not find image for main place {place}")
        return False

    async def populate_most_famous_place_image(self, place: Place) -> bool:
        """
        Fetch and update landscape image for MostFamousPlace entry.

        Args:
            place: Place model instance

        Returns:
            True if updated successfully
        """
        try:
            most_famous = await MostFamousPlace.objects.aget(place=place)

            if most_famous.image:
                logger.info(f"Image already exists for {most_famous.name}")
                return True

            image_url = await self.fetch_landmark_image(
                landmark_name=most_famous.name, city=place.city, place=place
            )

            if image_url:
                most_famous.image = image_url
                await most_famous.asave(update_fields=["image"])
                logger.info(f"Updated image for {most_famous.name}: {image_url}")
                return True

        except MostFamousPlace.DoesNotExist:
            logger.warning(f"No MostFamousPlace found for {place}")

        return False

    def _build_search_query(self, place: Place) -> str:
        """Build optimized search query for place images."""
        if place.state:
            return f"{place.city} {place.state} {place.country}"
        return f"{place.city} {place.country}"

    def _build_landmark_query(self, landmark_name: str, city: str, place: Place = None) -> str:
        """
        Build enhanced search query for landmark with smart tags.
        Adds relevant keywords to avoid random/irrelevant images.
        """
        # Base query
        query = f"{landmark_name} {city}"
        
        # Add landmark-specific tags to improve relevance
        landmark_lower = landmark_name.lower()
        
        # Architecture/Building keywords
        if any(word in landmark_lower for word in ["palace", "fort", "temple", "mosque", "church", "cathedral", "building", "tower", "arch"]):
            query += " architecture landmark monument"
        
        # Nature keywords
        elif any(word in landmark_lower for word in ["lake", "river", "waterfall", "falls", "beach", "mountain", "hill", "valley", "peak"]):
            query += " landscape nature scenic view"
        
        # Gardens/Parks
        elif any(word in landmark_lower for word in ["garden", "park", "botanical"]):
            query += " nature garden park"
        
        # Museums/Cultural
        elif any(word in landmark_lower for word in ["museum", "gallery", "memorial", "statue"]):
            query += " cultural heritage landmark"
        
        # Railway/Transport
        elif any(word in landmark_lower for word in ["railway", "train", "station"]):
            query += " historic railway transport"
        
        # General landmark fallback
        else:
            query += " landmark famous tourist attraction"
        
        logger.debug(f"Enhanced landmark query: {query}")
        return query

    def _select_best_image(self, images: List[Dict], query: str = "") -> Optional[Dict]:
        """
        Intelligent auto-selection of best image from results.
        Filters by quality heuristics AND relevance to ensure consistent, high-quality images.

        Selection criteria (in priority order):
        1. Filter out irrelevant images (interior shots, people close-ups, cars, etc.)
        2. Minimum resolution (2000px width for crisp mobile display)
        3. Aspect ratio (prefer 16:9 or 3:2 for landscape)
        4. Has description (better curated images usually have descriptions)
        5. Higher relevance (earlier in search results)

        Args:
            images: List of image data from Unsplash
            query: Original search query for relevance checking

        Returns:
            Best image dict or None
        """
        if not images:
            return None

        # Filter 0: Remove ONLY clearly irrelevant images (be more lenient)
        # Only filter if description CLEARLY indicates it's irrelevant
        irrelevant_keywords = [
            "selfie", "portrait of", "close-up of person", "face of",
            "car interior", "inside car", "dashboard",
            "office interior", "restaurant interior", "indoor room"
        ]
        
        relevant_images = []
        for img in images:
            desc = (img.get("description") or "").lower()
            # Only skip if description CLEARLY contains specific irrelevant phrases
            is_irrelevant = any(keyword in desc for keyword in irrelevant_keywords)
            
            if is_irrelevant:
                logger.debug(f"Filtering out clearly irrelevant image: {desc[:60]}")
                continue
            relevant_images.append(img)
        
        # If we filtered too much (less than 3 images), use original set
        working_set = relevant_images if len(relevant_images) >= 3 else images
        logger.info(f"Image filtering: {len(images)} total → {len(working_set)} after relevance filter")

        # Filter 1: Minimum quality (width >= 1500px - lowered from 2000)
        quality_images = [
            img
            for img in working_set
            if img.get("width", 0) >= 1500 and img.get("height", 0) >= 800
        ]

        # If no high-res found, use top 8 from working set (increased from 5)
        if not quality_images:
            quality_images = working_set[:8]
            logger.info(f"No high-res images, using top {len(quality_images)} from working set")

        # Filter 2: Good aspect ratio (1.4 to 2.5 for landscape)
        good_ratio_images = []
        for img in quality_images:
            width = img.get("width", 0)
            height = img.get("height", 0)
            if height > 0:
                ratio = width / height
                # Prefer 16:9 (1.78) or 3:2 (1.5) landscape ratios
                if 1.4 <= ratio <= 2.5:
                    good_ratio_images.append(img)

        # Use good ratio images if found, otherwise use quality images
        candidates = good_ratio_images if good_ratio_images else quality_images

        # Filter 3: Prefer images with descriptions (better curated)
        with_description = [
            img
            for img in candidates
            if img.get("description") and len(img.get("description", "")) > 10
        ]

        final_candidates = with_description if with_description else candidates

        # Return first from final candidates (most relevant from filtered set)
        if final_candidates:
            selected = final_candidates[0]
            logger.info(
                f"Auto-selected image: {selected.get('description', 'No description')[:50]} "
                f"({selected.get('width')}x{selected.get('height')})"
            )
            return selected

        # Fallback to absolute first result
        return images[0]
