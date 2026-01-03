from django.core.management.base import BaseCommand
from django.db import connection
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Generate real_movement_analytics table with feature engineering from combined_dataset'

    def handle(self, *args, **options):
        self.stdout.write('Starting feature engineering...')
        
        try:
            with connection.cursor() as cursor:
                # Drop existing table if exists
                cursor.execute('DROP TABLE IF EXISTS real_movement_analytics')
                
                # Create real_movement_analytics table with all required features
                cursor.execute('''
                    CREATE TABLE real_movement_analytics (
                        id SERIAL PRIMARY KEY,
                        plate_number VARCHAR(20),
                        vehicle_brand VARCHAR(50),
                        vehicle_type VARCHAR(50),
                        organization VARCHAR(100),
                        entry_time TIMESTAMP,
                        exit_time TIMESTAMP,
                        amount_paid DECIMAL(10,2),
                        payment_method VARCHAR(20),
                        plate_color VARCHAR(20),
                        duration_minutes INTEGER,
                        duration_category VARCHAR(30),
                        revenue_category VARCHAR(20),
                        visit_frequency VARCHAR(20),
                        efficiency_score INTEGER,
                        peak_hour BOOLEAN,
                        business_hours BOOLEAN,
                        weekend BOOLEAN,
                        season VARCHAR(10),
                        month_name VARCHAR(10),
                        hour_of_day INTEGER,
                        day_of_week INTEGER,
                        vehicle_usage_type VARCHAR(20),
                        vehicle_revenue_tier VARCHAR(20),
                        vehicle_visit_count INTEGER,
                        vehicle_total_revenue DECIMAL(12,2),
                        org_capacity_score INTEGER,
                        customer_loyalty_score INTEGER
                    )
                ''')
                
                # Get data from combined_dataset
                cursor.execute('''
                    SELECT 
                        "Plate Number",
                        "Vehicle Brand", 
                        "Vehicle Type",
                        "Organization",
                        "Entry Time",
                        "Amount Paid",
                        "Payment Method",
                        "Plate Color"
                    FROM combined_dataset 
                    WHERE "Plate Number" IS NOT NULL
                    ORDER BY "Entry Time"
                ''')
                
                records = cursor.fetchall()
                self.stdout.write(f'Processing {len(records)} records...')
                
                # Generate enhanced records with feature engineering
                enhanced_records = []
                vehicle_stats = {}
                org_stats = {}
                
                for i, record in enumerate(records):
                    plate_number = record[0]
                    vehicle_brand = record[1] or 'Unknown'
                    vehicle_type = record[2] or 'Car'
                    organization = record[3] or 'Unknown'
                    entry_time = record[4] or datetime.now()
                    amount_paid = float(record[5] or 0)
                    payment_method = record[6] or 'Cash'
                    plate_color = record[7] or 'White'
                    
                    # Generate realistic exit time (30 min to 8 hours later)
                    duration_minutes = random.randint(30, 480)
                    exit_time = entry_time + timedelta(minutes=duration_minutes)
                    
                    # Duration categories
                    if duration_minutes <= 30:
                        duration_category = 'Short'
                    elif duration_minutes <= 120:
                        duration_category = 'Medium'
                    elif duration_minutes <= 480:
                        duration_category = 'Long'
                    else:
                        duration_category = 'Extended'
                    
                    # Revenue categories
                    if amount_paid <= 50:
                        revenue_category = 'Low'
                    elif amount_paid <= 150:
                        revenue_category = 'Medium'
                    elif amount_paid <= 300:
                        revenue_category = 'High'
                    else:
                        revenue_category = 'Premium'
                    
                    # Time-based features
                    hour_of_day = entry_time.hour
                    day_of_week = entry_time.weekday()
                    peak_hour = hour_of_day in [8, 9, 10, 14, 15, 16, 17]
                    business_hours = 8 <= hour_of_day <= 17
                    weekend = day_of_week >= 5
                    
                    # Season
                    month = entry_time.month
                    if month in [12, 1, 2]:
                        season = 'Winter'
                    elif month in [3, 4, 5]:
                        season = 'Spring'
                    elif month in [6, 7, 8]:
                        season = 'Summer'
                    else:
                        season = 'Autumn'
                    
                    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    month_name = month_names[month - 1]
                    
                    # Vehicle statistics
                    if plate_number not in vehicle_stats:
                        vehicle_stats[plate_number] = {'visits': 0, 'revenue': 0}
                    vehicle_stats[plate_number]['visits'] += 1
                    vehicle_stats[plate_number]['revenue'] += amount_paid
                    
                    # Organization statistics
                    if organization not in org_stats:
                        org_stats[organization] = {'vehicles': set(), 'revenue': 0}
                    org_stats[organization]['vehicles'].add(plate_number)
                    org_stats[organization]['revenue'] += amount_paid
                    
                    # Visit frequency
                    visit_count = vehicle_stats[plate_number]['visits']
                    if visit_count >= 50:
                        visit_frequency = 'Frequent'
                        vehicle_usage_type = 'Heavy'
                    elif visit_count >= 20:
                        visit_frequency = 'Regular'
                        vehicle_usage_type = 'Regular'
                    elif visit_count >= 5:
                        visit_frequency = 'Occasional'
                        vehicle_usage_type = 'Light'
                    else:
                        visit_frequency = 'Rare'
                        vehicle_usage_type = 'Minimal'
                    
                    # Revenue tier
                    total_revenue = vehicle_stats[plate_number]['revenue']
                    if total_revenue >= 1000:
                        vehicle_revenue_tier = 'Premium'
                    elif total_revenue >= 500:
                        vehicle_revenue_tier = 'High'
                    elif total_revenue >= 200:
                        vehicle_revenue_tier = 'Medium'
                    else:
                        vehicle_revenue_tier = 'Low'
                    
                    # Efficiency and loyalty scores
                    efficiency_score = min(100, int((amount_paid / max(1, duration_minutes)) * 100))
                    customer_loyalty_score = min(100, visit_count * 5)
                    org_capacity_score = min(100, len(org_stats[organization]['vehicles']) * 2)
                    
                    enhanced_records.append((
                        plate_number, vehicle_brand, vehicle_type, organization,
                        entry_time, exit_time, amount_paid, payment_method, plate_color,
                        duration_minutes, duration_category, revenue_category,
                        visit_frequency, efficiency_score, peak_hour, business_hours,
                        weekend, season, month_name, hour_of_day, day_of_week,
                        vehicle_usage_type, vehicle_revenue_tier, visit_count,
                        total_revenue, org_capacity_score, customer_loyalty_score
                    ))
                
                # Insert enhanced records
                self.stdout.write('Inserting enhanced records...')
                cursor.executemany('''
                    INSERT INTO real_movement_analytics (
                        plate_number, vehicle_brand, vehicle_type, organization,
                        entry_time, exit_time, amount_paid, payment_method, plate_color,
                        duration_minutes, duration_category, revenue_category,
                        visit_frequency, efficiency_score, peak_hour, business_hours,
                        weekend, season, month_name, hour_of_day, day_of_week,
                        vehicle_usage_type, vehicle_revenue_tier, vehicle_visit_count,
                        vehicle_total_revenue, org_capacity_score, customer_loyalty_score
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', enhanced_records)
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX idx_real_analytics_plate ON real_movement_analytics(plate_number)')
                cursor.execute('CREATE INDEX idx_real_analytics_org ON real_movement_analytics(organization)')
                cursor.execute('CREATE INDEX idx_real_analytics_entry_time ON real_movement_analytics(entry_time)')
                cursor.execute('CREATE INDEX idx_real_analytics_vehicle_brand ON real_movement_analytics(vehicle_brand)')
                cursor.execute('CREATE INDEX idx_real_analytics_vehicle_type ON real_movement_analytics(vehicle_type)')
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created real_movement_analytics table with {len(enhanced_records)} enhanced records!'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during feature engineering: {str(e)}')
            )