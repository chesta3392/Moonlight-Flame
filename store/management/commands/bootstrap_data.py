from django.core.management.base import BaseCommand
from django.core.management import call_command
from store.models import Candle

class Command(BaseCommand):
    help = 'Bootstrap initial product data if the database is empty'

    def handle(self, *args, **options):
        if Candle.objects.exists():
            self.stdout.write(self.style.SUCCESS('Candle database is not empty. Skipping bootstrapping.'))
        else:
            self.stdout.write('Bootstrap database with initial products...')
            call_command('loaddata', 'candles.json')
            self.stdout.write(self.style.SUCCESS('Successfully loaded initial products.'))
