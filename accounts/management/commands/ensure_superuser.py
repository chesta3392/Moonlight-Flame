import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Create a Django superuser securely from environment variables'

    def handle(self, *args, **options):
        username = os.environ.get("SUPERUSER_USERNAME")
        email = os.environ.get("SUPERUSER_EMAIL", "admin@example.com")
        password = os.environ.get("SUPERUSER_PASSWORD")

        if not username or not password:
            self.stdout.write(self.style.WARNING(
                "Superuser credentials not set in environment (SUPERUSER_USERNAME & SUPERUSER_PASSWORD). Skipping superuser creation."
            ))
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.SUCCESS(
                f"User '{username}' already exists. Leaving unchanged."
            ))
        else:
            self.stdout.write(f"Creating superuser '{username}'...")
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(
                f"Superuser '{username}' created successfully."
            ))
