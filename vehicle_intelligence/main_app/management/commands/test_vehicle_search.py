from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Test vehicle search functionality'
    
    def add_arguments(self, parser):
        parser.add_argument('plate', type=str, help='License plate to search for')
    
    def handle(self, *args, **options):
        plate = options['plate']
        
        self.stdout.write(f'Searching for vehicle: {plate}')
        self.stdout.write('=' * 50)
        
        with connection.cursor() as cursor:
            # Check if vehicle exists
            cursor.execute(
                'SELECT COUNT(*) FROM real_movement_analytics WHERE plate_number ILIKE %s',
                [f'%{plate}%']
            )
            count = cursor.fetchone()[0]
            
            if count == 0:
                self.stdout.write(self.style.ERROR(f'No records found for {plate}'))
                return
            
            # Get vehicle details
            cursor.execute('''
                SELECT 
                    plate_number,
                    vehicle_brand,
                    vehicle_type,
                    organization,
                    COUNT(*) as total_visits,
                    SUM(amount_paid) as total_revenue,
                    AVG(duration_minutes) as avg_duration,
                    MAX(entry_time) as last_visit
                FROM real_movement_analytics 
                WHERE plate_number ILIKE %s
                GROUP BY plate_number, vehicle_brand, vehicle_type, organization
            ''', [f'%{plate}%'])
            
            results = cursor.fetchall()
            
            for result in results:
                self.stdout.write(f'Plate: {result[0]}')
                self.stdout.write(f'Brand: {result[1]}')
                self.stdout.write(f'Type: {result[2]}')
                self.stdout.write(f'Organization: {result[3]}')
                self.stdout.write(f'Total Visits: {result[4]}')
                self.stdout.write(f'Total Revenue: KSh {result[5]:,.2f}')
                self.stdout.write(f'Avg Duration: {result[6]:.1f} minutes')
                self.stdout.write(f'Last Visit: {result[7]}')
                
            self.stdout.write(self.style.SUCCESS(f'Found {len(results)} record(s) for {plate}'))