"""
Django management command to simulate location data for testing

Usage:
    python manage.py simulate_hotspot --user-emails email1 email2 email3 --lat 48.8584 --lng 2.2945
    python manage.py simulate_hotspot --count 5 --lat 48.8584 --lng 2.2945
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from travel.models import LocationHistory, Trip
from travel.services.location_tracker import LocationTracker
from user.models import User


class Command(BaseCommand):
    help = "Simulate multiple users at a location to test hotspot detection"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-emails",
            nargs="+",
            type=str,
            help="List of user emails to simulate",
        )
        parser.add_argument(
            "--count",
            type=int,
            help="Number of fake locations to create for testing (uses existing users)",
        )
        parser.add_argument(
            "--lat",
            type=float,
            required=True,
            help="Latitude for the location",
        )
        parser.add_argument(
            "--lng",
            type=float,
            required=True,
            help="Longitude for the location",
        )
        parser.add_argument(
            "--radius",
            type=float,
            default=50,
            help="Random radius variation in meters (default: 50m)",
        )
        parser.add_argument(
            "--active-trips-only",
            action="store_true",
            help="Only simulate for users with active trips",
        )

    def handle(self, *args, **options):
        lat = options["lat"]
        lng = options["lng"]
        radius = options["radius"]

        # Convert radius from meters to degrees (approximate)
        radius_degrees = radius / 111000  # 1 degree ≈ 111km

        users = []

        if options["user_emails"]:
            # Use specified users
            for email in options["user_emails"]:
                try:
                    user = User.objects.get(email=email)
                    users.append(user)
                except User.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"User not found: {email}"))

        elif options["count"]:
            # Get random existing users with active trips
            if options["active_trips_only"]:
                today = timezone.now().date()
                active_trips = Trip.objects.filter(
                    is_active=True,
                    start_date__lte=today,
                    end_date__gte=today,
                )
                user_ids = active_trips.values_list("user_id", flat=True).distinct()
                users = User.objects.filter(id__in=user_ids)[: options["count"]]
            else:
                users = User.objects.all()[: options["count"]]

        else:
            self.stdout.write(
                self.style.ERROR("Must specify either --user-emails or --count")
            )
            return

        if not users:
            self.stdout.write(self.style.ERROR("No users found to simulate"))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎯 Simulating {len(users)} users at location ({lat}, {lng})\n"
            )
        )

        for user in users:
            # Add small random variation to make it realistic
            random_lat = lat + random.uniform(-radius_degrees, radius_degrees)
            random_lng = lng + random.uniform(-radius_degrees, radius_degrees)

            # Record location
            location = LocationTracker.record_location(
                user=user,
                latitude=random_lat,
                longitude=random_lng,
                accuracy=random.uniform(5, 15),
                is_background=False,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ {user.email}: ({random_lat:.6f}, {random_lng:.6f})"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Successfully simulated {len(users)} users!")
        )
        self.stdout.write(
            self.style.WARNING(
                "\n💡 Now update location for any user to trigger hotspot detection!\n"
            )
        )
