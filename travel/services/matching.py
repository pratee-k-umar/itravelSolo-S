"""
Matching service for finding compatible trip companions
"""

import math
from typing import List, Tuple

from django.db.models import Q
from django.utils import timezone
from travel.models import Trip, TripMatch


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    # Radius of earth in kilometers
    r = 6371

    return c * r


def calculate_date_overlap(trip1: Trip, trip2: Trip) -> int:
    """Calculate number of overlapping days between two trips"""
    start = max(trip1.start_date, trip2.start_date)
    end = min(trip1.end_date, trip2.end_date)

    if start <= end:
        return (end - start).days + 1
    return 0


def calculate_interest_match(interests1: list, interests2: list) -> Tuple[list, float]:
    """
    Calculate common interests between two trips
    Returns (common_interests, match_percentage)
    """
    if not interests1 or not interests2:
        return [], 0.0

    common = list(set(interests1) & set(interests2))
    total_unique = len(set(interests1) | set(interests2))

    if total_unique == 0:
        return [], 0.0

    match_percentage = (len(common) / total_unique) * 100
    return common, match_percentage


def calculate_match_score(
    trip: Trip, candidate_trip: Trip, max_distance_km: float = 5
) -> Tuple[float, dict]:
    """
    Calculate matching score between two trips

    Returns: (score, details_dict)
    Score is 0-100, with weights:
    - Date overlap: 50%
    - Distance: 30% (max 5km)
    - Interests: 20%
    """
    details = {
        "date_overlap_days": 0,
        "distance_score": 0,
        "interest_score": 0,
        "common_interests": [],
        "distance_km": None,
    }

    # 1. Date overlap (50 points max)
    overlap_days = calculate_date_overlap(trip, candidate_trip)
    max_trip_duration = max(trip.duration_days, candidate_trip.duration_days)

    if overlap_days == 0:
        return 0.0, details  # No overlap = no match

    date_score = (overlap_days / max_trip_duration) * 50
    details["date_overlap_days"] = overlap_days

    # 2. Distance score (30 points max)
    if (
        trip.destination_lat
        and trip.destination_lng
        and candidate_trip.destination_lat
        and candidate_trip.destination_lng
    ):
        distance = haversine_distance(
            float(trip.destination_lat),
            float(trip.destination_lng),
            float(candidate_trip.destination_lat),
            float(candidate_trip.destination_lng),
        )
        details["distance_km"] = round(distance, 2)

        # Closer is better, max distance is max_distance_km
        if distance > max_distance_km:
            distance_score = 0
        else:
            distance_score = ((max_distance_km - distance) / max_distance_km) * 30
    else:
        # No coordinates, use destination name match
        if trip.destination.lower() == candidate_trip.destination.lower():
            distance_score = 30
        else:
            distance_score = 0

    details["distance_score"] = round(distance_score, 2)

    # 3. Interest match (20 points max)
    common_interests, interest_percentage = calculate_interest_match(
        trip.interests, candidate_trip.interests
    )
    interest_score = (interest_percentage / 100) * 20
    details["interest_score"] = round(interest_score, 2)
    details["common_interests"] = common_interests

    # Total score
    total_score = date_score + distance_score + interest_score

    return round(total_score, 2), details


def find_trip_matches(trip: Trip, limit: int = 10) -> List[TripMatch]:
    """
    Find and create matches for a trip

    Args:
        trip: The trip to find matches for
        limit: Maximum number of matches to return

    Returns:
        List of TripMatch objects (saved to database)
    """
    # Delete existing pending matches
    TripMatch.objects.filter(trip=trip, status="pending").delete()

    # Find candidate trips
    candidates = (
        Trip.objects.filter(
            Q(privacy="public")
            | Q(privacy="friends_only", user__in=trip.user.social.friends.all())
        )
        .exclude(user=trip.user)  # Exclude own trips
        .filter(
            start_date__lte=trip.end_date,  # Trip starts before our trip ends
            end_date__gte=trip.start_date,  # Trip ends after our trip starts
        )
    )

    matches = []
    for candidate_trip in candidates:
        # Calculate match score
        score, details = calculate_match_score(trip, candidate_trip)

        # Only create match if score is above threshold (e.g., 30%)
        if score >= 30:
            match = TripMatch.objects.create(
                trip=trip,
                matched_user=candidate_trip.user,
                matched_trip=candidate_trip,
                score=score,
                common_interests=details["common_interests"],
                distance_km=details["distance_km"],
                status="pending",
            )
            matches.append(match)

    # Sort by score and return top N
    matches.sort(key=lambda x: x.score, reverse=True)
    return matches[:limit]
