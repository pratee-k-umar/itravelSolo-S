"""
Django management command to create test trips for users

Usage:
    python manage.py create_test_trips --user-emails email1 email2 --destination "Paris"
    python manage.py create_test_trips --all-users --destination "Tokyo" --start-now
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from travel.models import Trip
from travel.services.matching import find_trip_matches
from user.models import User


class Command(BaseCommand):
    help = "Create test trips for users to test matching and hotspot features"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-emails",
            nargs="+",
            type=str,
            help="List of user emails to create trips for",
        )
        parser.add_argument(
            "--all-users",
            action="store_true",
            help="Create trips for all users in database",
        )
        parser.add_argument(
            "--destination",
            type=str,
            default="Paris, France",
            help="Trip destination",
        )
        parser.add_argument(
            "--dest-lat",
            type=float,
            default=48.8566,
            help="Destination latitude",
        )
        parser.add_argument(
            "--dest-lng",
            type=float,
            default=2.3522,
            help="Destination longitude",
        )
        parser.add_argument(
            "--start-now",
            action="store_true",
            help="Set trip start date to today (and activate it)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Trip duration in days (default: 7)",
        )

    def handle(self, *args, **options):
        users = []

        if options["user_emails"]:
            for email in options["user_emails"]:
                try:
                    user = User.objects.get(email=email)
                    users.append(user)
                except User.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"User not found: {email}"))
        elif options["all_users"]:
            users = User.objects.all()
        else:
            self.stdout.write(
                self.style.ERROR("Must specify either --user-emails or --all-users")
            )
            return

        if not users:
            self.stdout.write(self.style.ERROR("No users found"))
            return

        # Set trip dates
        if options["start_now"]:
            start_date = timezone.now().date()
        else:
            start_date = timezone.now().date() + timedelta(days=3)

        end_date = start_date + timedelta(days=options["days"])

        self.stdout.write(
            self.style.SUCCESS(f"\n🎯 Creating trips to {options['destination']}")
        )
        self.stdout.write(f"📅 {start_date} → {end_date}\n")

        trips_created = 0

        for user in users:
            # Check if user already has profile with location
            if not hasattr(user, "profile") or not user.profile.latitude:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  {user.email}: No profile location (origin will be empty)"
                    )
                )

            trip = Trip.objects.create(
                user=user,
                origin="Current Location",
                destination=options["destination"],
                origin_lat=user.profile.latitude if hasattr(user, "profile") else None,
                origin_lng=user.profile.longitude if hasattr(user, "profile") else None,
                destination_lat=options["dest_lat"],
                destination_lng=options["dest_lng"],
                start_date=start_date,
                end_date=end_date,
                interests=["sightseeing", "photography", "food"],
                description="Test trip for hotspot and matching",
                max_companions=5,
                privacy="public",
                is_active=options["start_now"],
            )

            status = "🟢 ACTIVE" if options["start_now"] else "⏸️  INACTIVE"
            self.stdout.write(
                self.style.SUCCESS(f"✓ {user.email}: Trip created {status}")
            )

            # If started, find matches
            if options["start_now"]:
                matches = find_trip_matches(trip, limit=20)
                if matches:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  └─ Found {len(matches)} potential matches"
                        )
                    )

            trips_created += 1

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Successfully created {trips_created} trips!")
        )

        if options["start_now"]:
            self.stdout.write(
                self.style.WARNING(
                    "\n💡 Trips are ACTIVE! Update locations to test proximity and hotspots.\n"
                )
            )
