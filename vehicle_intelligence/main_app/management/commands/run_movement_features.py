from django.core.management.base import BaseCommand
from django.db import transaction
import sys
import os

# Add the parent directory to the path to import movement_feature_engineering
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from movement_feature_engineering import VehicleMovementFeatureEngineer

class Command(BaseCommand):
    help = 'Run feature engineering on vehicle movement data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to the database',
        )
        parser.add_argument(
            '--step',
            type=str,
            choices=['temporal', 'behavior', 'organization', 'driver', 'all'],
            default='all',
            help='Run specific feature engineering step',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting Vehicle Movement Feature Engineering')
        )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        try:
            engineer = VehicleMovementFeatureEngineer()
            
            if options['dry_run']:
                # In dry run, just show what would be done
                from main_app.models import VehicleMovement, Vehicle
                total_movements = VehicleMovement.objects.count()
                total_vehicles = Vehicle.objects.count()
                
                self.stdout.write(f"Would process {total_movements:,} vehicle movements")
                self.stdout.write(f"Would analyze {total_vehicles:,} vehicles")
                self.stdout.write("Features that would be calculated:")
                
                if options['step'] in ['temporal', 'all']:
                    self.stdout.write("  • Temporal features (hour, day, season, trip type)")
                if options['step'] in ['behavior', 'all']:
                    self.stdout.write("  • Vehicle behavior (usage patterns, route efficiency)")
                if options['step'] in ['organization', 'all']:
                    self.stdout.write("  • Organization features (activity levels, vehicle counts)")
                if options['step'] in ['driver', 'all']:
                    self.stdout.write("  • Driver features (experience, efficiency ratings)")
                    
            else:
                # Run actual feature engineering
                if options['step'] == 'temporal':
                    engineer.add_temporal_features()
                elif options['step'] == 'behavior':
                    engineer.add_vehicle_behavior_features()
                elif options['step'] == 'organization':
                    engineer.add_organization_features()
                elif options['step'] == 'driver':
                    engineer.add_driver_features()
                else:  # all
                    summary = engineer.run_complete_feature_engineering()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Feature engineering completed successfully!'
                        )
                    )
                    self.stdout.write(f'Enhanced {summary["total_movements"]:,} movement records')
                    self.stdout.write(f'Key insights:')
                    self.stdout.write(f'   • Temporal coverage: {summary["temporal_coverage"]:.1f}%')
                    self.stdout.write(f'   • Weekend trips: {summary["weekend_percentage"]:.1f}%')
                    self.stdout.write(f'   • Peak hour trips: {summary["peak_hour_percentage"]:.1f}%')
                    self.stdout.write(f'   • Frequent routes: {summary["frequent_routes"]:,}')
                    self.stdout.write(f'   • Active locations: {summary["active_locations"]:,}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
            raise e