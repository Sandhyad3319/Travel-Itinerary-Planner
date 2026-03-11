from django.core.management.base import BaseCommand
from planner.models import Destination

class Command(BaseCommand):
    help = 'Populate the database with sample destinations'

    def handle(self, *args, **options):
        destinations = [
            {
                'name': 'Paris',
                'country': 'France',
                'description': 'The City of Light, famous for its art, fashion, and culture.'
            },
            {
                'name': 'Tokyo',
                'country': 'Japan',
                'description': 'A bustling metropolis blending traditional culture with modern technology.'
            },
            {
                'name': 'New York City',
                'country': 'USA',
                'description': 'The city that never sleeps, known for its iconic skyline and diverse culture.'
            },
            {
                'name': 'Bali',
                'country': 'Indonesia',
                'description': 'Tropical paradise with beautiful beaches, temples, and vibrant culture.'
            },
            {
                'name': 'Rome',
                'country': 'Italy',
                'description': 'The Eternal City, rich in history, art, and ancient architecture.'
            },
            {
                'name': 'Sydney',
                'country': 'Australia',
                'description': 'Coastal city famous for its opera house, harbor, and beaches.'
            },
        ]

        created_count = 0
        for dest_data in destinations:
            destination, created = Destination.objects.get_or_create(
                name=dest_data['name'],
                country=dest_data['country'],
                defaults={'description': dest_data['description']}
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created destination: {destination.name}, {destination.country}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} destinations')
        )