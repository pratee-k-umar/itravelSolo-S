import logging
from typing import Dict, List, Optional

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class UnsplashScraper:
    """
    Fetches high-quality images from Unsplash API.
    Get free API key at: https://unsplash.com/developers
    """

    BASE_URL = "https://api.unsplash.com"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, "UNSPLASH_ACCESS_KEY", None)
        if not self.api_key:
            logger.warning("UNSPLASH_ACCESS_KEY not configured in settings")

    async def search_images(
        self,
        query: str,
        per_page: int = 10,
        orientation: str = "landscape",
        color: str = None,
    ) -> List[Dict]:
        """
        Search for images by keyword with optional color filtering.

        Args:
            query: Search term (e.g., "Paris Eiffel Tower")
            per_page: Number of results (max 30)
            orientation: landscape, portrait, or squarish
            color: Color filter (blue, green, orange, yellow, red, purple, teal, black_and_white, white, black)

        Returns:
            List of image data dictionaries
        """
        if not self.api_key:
            logger.error("Cannot search images: API key not configured")
            return []

        url = f"{self.BASE_URL}/search/photos"
        params = {
            "query": query,
            "per_page": min(per_page, 30),
            "orientation": orientation,
        }

        # Add color filter if specified
        if color:
            params["color"] = color

        headers = {"Authorization": f"Client-ID {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()

                data = response.json()
                results = data.get("results", [])

                images = []
                for result in results:
                    images.append(
                        {
                            "id": result.get("id"),
                            "url_full": result["urls"].get("full"),
                            "url_regular": result["urls"].get("regular"),
                            "url_small": result["urls"].get("small"),
                            "url_thumb": result["urls"].get("thumb"),
                            "width": result.get("width"),
                            "height": result.get("height"),
                            "description": result.get("description")
                            or result.get("alt_description"),
                            "photographer": result["user"].get("name"),
                            "photographer_url": result["user"]["links"].get("html"),
                            "download_url": result["links"].get("download_location"),
                        }
                    )

                logger.info(f"Found {len(images)} images for query: {query}")
                return images

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Unsplash API HTTP error for '{query}': {e.response.status_code} - {e.response.text}"
            )
            return []
        except Exception as e:
            logger.error(f"Error fetching images from Unsplash for '{query}': {e}")
            return []

    async def get_random_image(
        self, query: str, orientation: str = "landscape"
    ) -> Optional[Dict]:
        """
        Get a random image for the query.

        Args:
            query: Search term
            orientation: landscape, portrait, or squarish

        Returns:
            Single image data dictionary or None
        """
        if not self.api_key:
            logger.error("Cannot get random image: API key not configured")
            return None

        url = f"{self.BASE_URL}/photos/random"
        params = {"query": query, "orientation": orientation}
        headers = {"Authorization": f"Client-ID {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()

                result = response.json()

                return {
                    "id": result.get("id"),
                    "url_full": result["urls"].get("full"),
                    "url_regular": result["urls"].get("regular"),
                    "url_small": result["urls"].get("small"),
                    "url_thumb": result["urls"].get("thumb"),
                    "width": result.get("width"),
                    "height": result.get("height"),
                    "description": result.get("description")
                    or result.get("alt_description"),
                    "photographer": result["user"].get("name"),
                    "photographer_url": result["user"]["links"].get("html"),
                    "download_url": result["links"].get("download_location"),
                }

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Unsplash API HTTP error for random '{query}': {e.response.status_code}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Error fetching random image from Unsplash for '{query}': {e}"
            )
            return None

    async def trigger_download(self, download_url: str) -> bool:
        """
        Trigger download tracking (required by Unsplash API guidelines).
        Call this when user actually views/downloads the image.

        Args:
            download_url: The download_location URL from image data

        Returns:
            True if successful
        """
        if not self.api_key or not download_url:
            return False

        headers = {"Authorization": f"Client-ID {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(download_url, headers=headers)
                response.raise_for_status()
                logger.info(f"Download tracked for: {download_url}")
                return True
        except Exception as e:
            logger.error(f"Error tracking download: {e}")
            return False
