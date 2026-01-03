from django.core.management.base import BaseCommand
from main_app.models import ParkingRecord


class Command(BaseCommand):
    help = 'Update parking duration for existing records'

    def handle(self, *args, **options):
        self.stdout.write('Updating parking duration for existing records...')
        
        records = ParkingRecord.objects.filter(parking_duration_minutes__isnull=True)
        updated_count = 0
        
        for record in records:
            if record.entry_time and record.exit_time:
                duration = (record.exit_time - record.entry_time).total_seconds() / 60
                record.parking_duration_minutes = int(duration)
                record.save(update_fields=['parking_duration_minutes'])
                updated_count += 1
            elif record.entry_time:
                # For records without exit_time, set duration to 0
                record.parking_duration_minutes = 0
                record.save(update_fields=['parking_duration_minutes'])
                updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Updated {updated_count} records with parking duration')
        )