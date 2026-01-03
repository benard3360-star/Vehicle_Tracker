# run_feature_engineering.py
from django.core.management.base import BaseCommand
from django.db import transaction
import sys
import os

# Add the parent directory to the path to import feature_engineering
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from feature_engineering import VehicleFeatureEngineer

class Command(BaseCommand):
    help = 'Run advanced feature engineering on parking records'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to the database',
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=1000,
            help='Number of records to process in each chunk',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting Feature Engineering Pipeline')
        )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('⚠️  DRY RUN MODE - No changes will be made')
            )
        
        try:
            engineer = VehicleFeatureEngineer()
            
            if options['dry_run']:
                # In dry run, just show what would be done
                from main_app.models import ParkingRecord
                total_records = ParkingRecord.objects.count()
                self.stdout.write(
                    f"Would process {total_records:,} parking records"
                )
                self.stdout.write("Features that would be calculated:")
                self.stdout.write("  ✓ Temporal features (hour, day, season, etc.)")
                self.stdout.write("  ✓ Duration features (categories, efficiency)")
                self.stdout.write("  ✓ Vehicle features (usage patterns, revenue)")
                self.stdout.write("  ✓ Organization features (size, performance)")
                self.stdout.write("  ✓ Behavioral features (anomalies, frequency)")
                self.stdout.write("  ✓ Financial features (efficiency, categories)")
            else:
                # Run actual feature engineering
                summary = engineer.run_feature_engineering()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Feature engineering completed successfully!'
                    )
                )
                self.stdout.write(
                    f'📊 Enhanced {summary["total_records"]:,} records'
                )
                self.stdout.write(
                    f'📈 Key insights:'
                )
                self.stdout.write(
                    f'   • Weekend visits: {summary["weekend_percentage"]:.1f}%'
                )
                self.stdout.write(
                    f'   • Peak hour visits: {summary["peak_hour_percentage"]:.1f}%'
                )
                self.stdout.write(
                    f'   • Overstay rate: {summary["overstay_percentage"]:.1f}%'
                )
                self.stdout.write(
                    f'   • Frequent vehicles: {summary["frequent_vehicles"]:,}'
                )
                self.stdout.write(
                    f'   • Digital payments: {summary["digital_payment_percentage"]:.1f}%'
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {str(e)}')
            )
            raise e