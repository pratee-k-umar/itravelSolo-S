import json
import logging

from django.conf import settings
from google.genai import errors
from insights.services.client.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

client = GeminiClient.get_client()


class Gemini:
    def __init__(self, city: str, state: str, country: str):
        self.city = city
        self.state = state
        self.country = country

    def build_prompt(self) -> str:
        """
        Detailed prompt template for generating place insights using Gemini API.
        """
        place_name = (
            f"{self.city}, {self.state}, {self.country}"
            if self.state
            else f"{self.city}, {self.country}"
        )

        prompt_template = f"""
        You are an expert travel guide with deep cultural, historical, and practical knowledge of travel destinations.
        Your task is to generate comprehensive, accurate, and complete insights about {place_name}.

        IMPORTANT RULES:
        1. Output MUST be valid JSON and nothing else.
        2. Follow the structure EXACTLY as defined.
        3. All coordinates must be in structured numeric format: {{ "lat": <float>, "lng": <float> }}
        4. Famous places must be a list of objects.
        5. Things-to-do must be a dictionary where each key is an activity and value is a list of locations.
        6. Day activities must be a list of objects.
        8. You MUST include all major annual festivals, fairs, cultural events, or globally/nationally significant happenings the place is known for.
        9. If information is unavailable, use "N/A", an empty string "", or an empty list [] — do NOT skip known events.
        10. Be concise but informative. Avoid filler.
        OUTPUT STRICT JSON STRUCTURE: {{
            "main_quote": "Two words quote",
            "sub_quote": "Four words quote related to main_quote",

            "description": "A one-line 15–20 word description of the place.",
            
            "visual_theme": {{
                "color": "Hex color code representing the city's visual theme (e.g., '#3B82F6' for blue skies, '#F59E0B' for golden/sunset, '#10B981' for nature/green, '#EF4444' for vibrant/red)",
                "tags": "3-5 visual keywords separated by spaces (e.g., 'mountains sunset nature', 'modern architecture skyline', 'historic heritage golden')"
            }},

            "most_famous_place": {{
                "name": "Landmark name",
                "quote": "Four to six word quote about the place",
                "coordinates": {{ "lat": 0.0, "lng": 0.0 }}
            }},

            "famous_places": [
                {{
                    "name": "Place name",
                    "quote": "Four–five word quote about the place",
                    "coordinates": {{ "lat": 0.0, "lng": 0.0 }}
                }}
            ],

            "famous_activities": {{
                "Activity name": "Time of day (e.g., Morning / Evening / All Day)"
            }},

            "things_to_do": {{
                "One word ActivityName ex. Hiking, Trekking etc": [
                    {{
                        "location": "Location name",
                        "time": "time",
                        "coordinates": {{ "lat": 0.0, "lng": 0.0 }}
                    }}
                ]
            }},

            "food_specialties": ["Local dish name"],

            "tourist_traps": ["Description of trap area or situation"],

            "seasonal_behavior": {{
                "season": "Weather pattern or seasonal activity",
            }},

            "day_activities": [
                {{
                    "activity": "Activity name",
                    "day_time": "Specific time",
                    "time": "time range"
                }}
            ],

            "hidden_gems": ["Lesser-known attraction or experience"],
            
            "suggestion_pool": {{
                "time_based": {{
                    "morning": ["Suggestion text"],
                    "afternoon": ["Suggestion text"],
                    "evening": ["Suggestion text"],
                    "night": ["Suggestion text"]
                }},

                "location_based": [
                    {{
                        "context": "Near ghats / landmarks / markets",
                        "suggestions": ["Suggestion text"]
                    }}
                ],

                "situation_based": {{
                    "crowded": ["Suggestion text"],
                    "quiet": ["Suggestion text"],
                    "tourist_heavy": ["Suggestion text"],
                    "local_area": ["Suggestion text"]
                }},

                "stuck_like_scenarios": [
                    {{
                        "scenario": "User stuck near tourist-heavy area with limited transport",
                        "suggestions": ["Suggestion text"]
                    }}
                ]
            }}
        }}

        Now generate the JSON for {place_name}.
        """

        return prompt_template

    async def generate_place_insights(self) -> dict:
        """
        Generate detailed place insights using the Gemini API.
        Raises ValueError if generation fails.
        """
        if not settings.GEMINI_API_KEY:
            raise ValueError("Gemini API key is not configured in Django settings.")

        prompt = self.build_prompt()

        try:
            # Configure generation with sufficient output tokens
            generation_config = {
                "max_output_tokens": 8192,  # Increase from default to prevent truncation
                "temperature": 0.7,
            }

            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt, config=generation_config
            )
            if response.text:
                parsed_data = _parse_and_validate_gemini_output(response.text)
                if parsed_data is None:
                    raise ValueError(
                        f"Failed to parse Gemini response for {self.city}, {self.country}"
                    )
                return parsed_data

            else:
                logger.error(
                    f"Gemini API returned no text for {self.city}, {self.state}, {self.country}."
                )
                raise ValueError("Gemini API returned empty response.")

        except errors.APIError as e:
            logger.error(
                f"Google API Error during Gemini call for {self.city}, {self.state}, {self.country}: {e}"
            )
            raise ValueError(f"Gemini API error: {str(e)}") from e

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for {self.city}, {self.country}: {e}")
            raise ValueError(f"Invalid JSON response from Gemini: {str(e)}") from e

        except Exception as e:
            logger.error(
                f"An unexpected error occurred during Gemini API call for {self.city}, {self.state}, {self.country}: {e}"
            )
            raise ValueError(
                f"Unexpected error during insight generation: {str(e)}"
            ) from e


def _parse_and_validate_gemini_output(json_data) -> dict:
    """
    Parses and validates Gemini output into a consistent, database-safe structure.
    """
    # Strip markdown code fences if present
    json_str = json_data.strip()
    if json_str.startswith("```json"):
        json_str = json_str[7:]  # Remove ```json
    if json_str.startswith("```"):
        json_str = json_str[3:]  # Remove ```
    if json_str.endswith("```"):
        json_str = json_str[:-3]  # Remove trailing ```
    json_str = json_str.strip()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e} | Raw: {json_str[:400]}")
        return None

    place_data = {
        "main_quote": "",
        "sub_quote": "",
        "description": "",
        "most_famous_place": {
            "name": "",
            "quote": "",
            "coordinates": {"lat": 0.0, "lng": 0.0},
        },
        "famous_places": [],
        "famous_activities": {},
        "things_to_do": {},
        "food_specialties": [],
        "tourist_traps": [],
        "seasonal_behavior": {
            "spring": "",
            "summer": "",
            "autumn": "",
            "winter": "",
        },
        "day_activities": [],
        "hidden_gems": [],
    }

    place_data["main_quote"] = str(data.get("main_quote", ""))
    place_data["sub_quote"] = str(data.get("sub_quote", ""))
    place_data["description"] = str(data.get("description", ""))

    mfp = data.get("most_famous_place", {})
    if isinstance(mfp, dict):
        place_data["most_famous_place"]["name"] = mfp.get("name", "")
        place_data["most_famous_place"]["quote"] = mfp.get("quote", "")

        coords = mfp.get("coordinates", {})
        place_data["most_famous_place"]["coordinates"] = {
            "lat": float(coords.get("lat", 0.0) or 0.0),
            "lng": float(coords.get("lng", 0.0) or 0.0),
        }

    famous_places = []
    for item in data.get("famous_places", []):
        if not isinstance(item, dict):
            continue

        coords = item.get("coordinates", {})
        famous_places.append(
            {
                "name": item.get("name", ""),
                "quote": item.get("quote", ""),
                "coordinates": {
                    "lat": float(coords.get("lat", 0.0) or 0.0),
                    "lng": float(coords.get("lng", 0.0) or 0.0),
                },
            }
        )

    place_data["famous_places"] = famous_places

    fa = data.get("famous_activities", {})
    place_data["famous_activities"] = fa if isinstance(fa, dict) else {}

    ttd_clean = {}
    ttd = data.get("things_to_do", {})

    if isinstance(ttd, dict):
        for activity, locations in ttd.items():
            safe_locations = []
            if isinstance(locations, list):
                for loc in locations:
                    if not isinstance(loc, dict):
                        continue

                    coords = loc.get("coordinates", {})
                    safe_locations.append(
                        {
                            "location": loc.get("location", ""),
                            "time": loc.get("time", ""),
                            "coordinates": {
                                "lat": float(coords.get("lat", 0.0) or 0.0),
                                "lng": float(coords.get("lng", 0.0) or 0.0),
                            },
                        }
                    )
            ttd_clean[activity] = safe_locations

    place_data["things_to_do"] = ttd_clean

    place_data["food_specialties"] = (
        data.get("food_specialties", [])
        if isinstance(data.get("food_specialties"), list)
        else []
    )
    place_data["tourist_traps"] = (
        data.get("tourist_traps", [])
        if isinstance(data.get("tourist_traps"), list)
        else []
    )

    sb = data.get("seasonal_behavior", {})
    for season in ["spring", "summer", "autumn", "winter"]:
        place_data["seasonal_behavior"][season] = str(sb.get(season, ""))

    day_clean = []
    for entry in data.get("day_activities", []):
        if isinstance(entry, dict):
            day_clean.append(
                {"activity": entry.get("activity", ""), "time": entry.get("time", "")}
            )
    place_data["day_activities"] = day_clean

    place_data["hidden_gems"] = (
        data.get("hidden_gems", []) if isinstance(data.get("hidden_gems"), list) else []
    )

    return place_data
