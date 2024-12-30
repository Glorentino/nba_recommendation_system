from django.core.management.base import BaseCommand
from api.dataset_generator import generate_dataset

class Command(BaseCommand):
    help = "Generate and update the player dataset."

    def handle(self, *args, **kwargs):
        self.stdout.write("Updating player dataset...")
        generate_dataset()
        self.stdout.write("Player dataset updated successfully!")