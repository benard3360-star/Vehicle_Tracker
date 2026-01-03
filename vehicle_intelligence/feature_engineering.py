# feature_engineering.py
"""
Advanced Feature Engineering for Vehicle Intelligence System
Enriches existing PostgreSQL data with calculated features for enhanced analytics
"""

import os
import sys
import django
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from django.db.models import Count, Sum, Avg, Max, Min, F, Q
from django.db import transaction

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

from main_app.models import ParkingRecord, Organization, CustomUser

class VehicleFeatureEngineer:
    """Advanced feature engineering for vehicle data"""
    
    def __init__(self):
        self.features_created = 0
        self.records_updated = 0
        
    def calculate_temporal_features(self):
        """Calculate time-based features"""
        print("Calculating temporal features...")
        
        records = ParkingRecord.objects.all()
        updated_count = 0
        
        for record in records.iterator(chunk_size=1000):
            try:
                # Extract temporal features from entry_time
                entry_time = record.entry_time
                
                # Hour-based features
                record.entry_hour = entry_time.hour
                record.entry_day_of_week = entry_time.weekday()  # 0=Monday, 6=Sunday
                record.entry_week_of_year = entry_time.isocalendar()[1]
                record.entry_month = entry_time.month
                record.entry_quarter = (entry_time.month - 1) // 3 + 1
                
                # Time period classifications
                record.is_weekend = entry_time.weekday() >= 5
                record.is_business_hours = 9 <= entry_time.hour <= 17
                record.is_peak_hours = entry_time.hour in [8, 9, 17, 18, 19]
                record.is_night_entry = entry_time.hour >= 22 or entry_time.hour <= 5
                
                # Season classification
                month = entry_time.month
                if month in [12, 1, 2]:
                    record.season = 'winter'
                elif month in [3, 4, 5]:
                    record.season = 'spring'
                elif month in [6, 7, 8]:
                    record.season = 'summer'
                else:
                    record.season = 'autumn'
                
                record.save(update_fields=[
                    'entry_hour', 'entry_day_of_week', 'entry_week_of_year', 
                    'entry_month', 'entry_quarter', 'is_weekend', 
                    'is_business_hours', 'is_peak_hours', 'is_night_entry', 'season'
                ])
                updated_count += 1
                
            except Exception as e:
                print(f"Error updating temporal features for record {record.id}: {e}")
                continue
        
        print(f"Updated temporal features for {updated_count} records")
        return updated_count
    
    def calculate_duration_features(self):
        """Calculate parking duration-based features"""
        print("Calculating duration features...")
        
        records = ParkingRecord.objects.filter(exit_time__isnull=False)
        updated_count = 0
        
        for record in records.iterator(chunk_size=1000):
            try:
                if record.exit_time and record.entry_time:
                    # Calculate duration in minutes
                    duration = (record.exit_time - record.entry_time).total_seconds() / 60
                    record.duration_minutes = int(duration)
                    
                    # Duration categories
                    if duration <= 30:
                        record.duration_category = 'short'  # ≤30 min
                    elif duration <= 120:
                        record.duration_category = 'medium'  # 30min-2h
                    elif duration <= 480:
                        record.duration_category = 'long'  # 2h-8h
                    else:
                        record.duration_category = 'extended'  # >8h
                    
                    # Overstay classification (assuming 4h policy)
                    record.is_overstay = duration > 240
                    
                    # Duration efficiency score (0-100)
                    optimal_duration = 120  # 2 hours
                    record.duration_efficiency = max(0, 100 - abs(duration - optimal_duration) / optimal_duration * 100)
                    
                    record.save(update_fields=[
                        'duration_minutes', 'duration_category', 
                        'is_overstay', 'duration_efficiency'
                    ])
                    updated_count += 1
                    
            except Exception as e:
                print(f"Error updating duration features for record {record.id}: {e}")
                continue
        
        print(f"Updated duration features for {updated_count} records")
        return updated_count
    
    def calculate_vehicle_features(self):
        """Calculate vehicle-specific aggregated features"""
        print("Calculating vehicle features...")
        
        # Get vehicle statistics
        vehicle_stats = ParkingRecord.objects.values('license_plate').annotate(
            total_visits=Count('id'),
            total_amount=Sum('amount_paid'),
            avg_duration=Avg('duration_minutes'),
            max_duration=Max('duration_minutes'),
            min_duration=Min('duration_minutes'),
            unique_organizations=Count('organization', distinct=True),
            first_visit=Min('entry_time'),
            last_visit=Max('entry_time')
        )
        
        updated_count = 0
        
        for stats in vehicle_stats:
            try:
                license_plate = stats['license_plate']
                
                # Update all records for this vehicle
                records = ParkingRecord.objects.filter(license_plate=license_plate)
                
                # Calculate loyalty metrics
                total_visits = stats['total_visits']
                unique_orgs = stats['unique_organizations']
                
                # Vehicle classification
                if total_visits >= 50:
                    vehicle_type_usage = 'frequent'
                elif total_visits >= 20:
                    vehicle_type_usage = 'regular'
                elif total_visits >= 5:
                    vehicle_type_usage = 'occasional'
                else:
                    vehicle_type_usage = 'rare'
                
                # Multi-site behavior
                is_multi_site = unique_orgs > 1
                
                # Revenue contribution
                total_revenue = stats['total_amount'] or 0
                if total_revenue >= 10000:
                    revenue_tier = 'high'
                elif total_revenue >= 5000:
                    revenue_tier = 'medium'
                elif total_revenue >= 1000:
                    revenue_tier = 'low'
                else:
                    revenue_tier = 'minimal'
                
                # Update all records for this vehicle
                records.update(
                    vehicle_visit_count=total_visits,
                    vehicle_total_revenue=total_revenue,
                    vehicle_avg_duration=stats['avg_duration'] or 0,
                    vehicle_unique_sites=unique_orgs,
                    vehicle_usage_type=vehicle_type_usage,
                    vehicle_is_multi_site=is_multi_site,
                    vehicle_revenue_tier=revenue_tier
                )
                
                updated_count += records.count()
                
            except Exception as e:
                print(f"Error updating vehicle features for {license_plate}: {e}")
                continue
        
        print(f"Updated vehicle features for {updated_count} records")
        return updated_count
    
    def calculate_organization_features(self):
        """Calculate organization-specific features"""
        print("Calculating organization features...")
        
        # Get organization statistics
        org_stats = ParkingRecord.objects.values('organization').annotate(
            total_vehicles=Count('license_plate', distinct=True),
            total_revenue=Sum('amount_paid'),
            avg_duration=Avg('duration_minutes'),
            total_visits=Count('id'),
            avg_amount=Avg('amount_paid')
        )
        
        updated_count = 0
        
        for stats in org_stats:
            try:
                org_name = stats['organization']
                
                # Calculate organization metrics
                total_vehicles = stats['total_vehicles']
                total_revenue = stats['total_revenue'] or 0
                avg_duration = stats['avg_duration'] or 0
                
                # Organization size classification
                if total_vehicles >= 100:
                    org_size = 'large'
                elif total_vehicles >= 50:
                    org_size = 'medium'
                elif total_vehicles >= 20:
                    org_size = 'small'
                else:
                    org_size = 'micro'
                
                # Revenue performance
                if total_revenue >= 50000:
                    org_performance = 'excellent'
                elif total_revenue >= 25000:
                    org_performance = 'good'
                elif total_revenue >= 10000:
                    org_performance = 'average'
                else:
                    org_performance = 'poor'
                
                # Update all records for this organization
                records = ParkingRecord.objects.filter(organization=org_name)
                records.update(
                    org_total_vehicles=total_vehicles,
                    org_total_revenue=total_revenue,
                    org_avg_duration=avg_duration,
                    org_size_category=org_size,
                    org_performance_tier=org_performance
                )
                
                updated_count += records.count()
                
            except Exception as e:
                print(f"Error updating organization features for {org_name}: {e}")
                continue
        
        print(f"Updated organization features for {updated_count} records")
        return updated_count
    
    def calculate_behavioral_features(self):
        """Calculate behavioral patterns and anomalies"""
        print("Calculating behavioral features...")
        
        updated_count = 0
        
        # Process records in chunks
        for record in ParkingRecord.objects.all().iterator(chunk_size=1000):
            try:
                # Get vehicle's historical data
                vehicle_history = ParkingRecord.objects.filter(
                    license_plate=record.license_plate,
                    entry_time__lt=record.entry_time
                ).order_by('-entry_time')[:10]  # Last 10 visits
                
                if vehicle_history.exists():
                    # Calculate patterns
                    avg_historical_duration = vehicle_history.aggregate(
                        avg_duration=Avg('duration_minutes')
                    )['avg_duration'] or 0
                    
                    avg_historical_amount = vehicle_history.aggregate(
                        avg_amount=Avg('amount_paid')
                    )['avg_amount'] or 0
                    
                    # Detect anomalies
                    current_duration = record.duration_minutes or 0
                    current_amount = record.amount_paid or 0
                    
                    # Duration anomaly (>50% deviation from historical average)
                    if avg_historical_duration > 0:
                        duration_deviation = abs(current_duration - avg_historical_duration) / avg_historical_duration
                        record.is_duration_anomaly = duration_deviation > 0.5
                    else:
                        record.is_duration_anomaly = False
                    
                    # Payment anomaly
                    if avg_historical_amount > 0:
                        payment_deviation = abs(current_amount - avg_historical_amount) / avg_historical_amount
                        record.is_payment_anomaly = payment_deviation > 0.5
                    else:
                        record.is_payment_anomaly = False
                    
                    # Visit frequency (days since last visit)
                    last_visit = vehicle_history.first()
                    if last_visit:
                        days_since_last = (record.entry_time.date() - last_visit.entry_time.date()).days
                        record.days_since_last_visit = days_since_last
                        
                        # Frequency classification
                        if days_since_last <= 1:
                            record.visit_frequency = 'daily'
                        elif days_since_last <= 7:
                            record.visit_frequency = 'weekly'
                        elif days_since_last <= 30:
                            record.visit_frequency = 'monthly'
                        else:
                            record.visit_frequency = 'rare'
                    else:
                        record.days_since_last_visit = 0
                        record.visit_frequency = 'first_time'
                else:
                    # First-time visitor
                    record.is_duration_anomaly = False
                    record.is_payment_anomaly = False
                    record.days_since_last_visit = 0
                    record.visit_frequency = 'first_time'
                
                record.save(update_fields=[
                    'is_duration_anomaly', 'is_payment_anomaly', 
                    'days_since_last_visit', 'visit_frequency'
                ])
                updated_count += 1
                
            except Exception as e:
                print(f"Error updating behavioral features for record {record.id}: {e}")
                continue
        
        print(f"Updated behavioral features for {updated_count} records")
        return updated_count
    
    def calculate_financial_features(self):
        """Calculate financial and revenue features"""
        print("Calculating financial features...")
        
        updated_count = 0
        
        for record in ParkingRecord.objects.all().iterator(chunk_size=1000):
            try:
                amount_paid = record.amount_paid or 0
                duration = record.duration_minutes or 0
                
                # Revenue per minute
                if duration > 0:
                    record.revenue_per_minute = amount_paid / duration
                else:
                    record.revenue_per_minute = 0
                
                # Payment efficiency (amount vs expected)
                expected_amount = max(50, duration * 0.5)  # Assume 0.5 KSh per minute minimum
                if expected_amount > 0:
                    record.payment_efficiency = (amount_paid / expected_amount) * 100
                else:
                    record.payment_efficiency = 0
                
                # Revenue category
                if amount_paid >= 500:
                    record.revenue_category = 'high'
                elif amount_paid >= 200:
                    record.revenue_category = 'medium'
                elif amount_paid >= 50:
                    record.revenue_category = 'low'
                else:
                    record.revenue_category = 'minimal'
                
                # Payment method efficiency (if available)
                payment_method = record.payment_method or 'unknown'
                if payment_method.lower() in ['mpesa', 'card', 'digital']:
                    record.is_digital_payment = True
                else:
                    record.is_digital_payment = False
                
                record.save(update_fields=[
                    'revenue_per_minute', 'payment_efficiency', 
                    'revenue_category', 'is_digital_payment'
                ])
                updated_count += 1
                
            except Exception as e:
                print(f"Error updating financial features for record {record.id}: {e}")
                continue
        
        print(f"Updated financial features for {updated_count} records")
        return updated_count
    
    def generate_feature_summary(self):
        """Generate summary of all calculated features"""
        print("\nGenerating feature summary...")
        
        total_records = ParkingRecord.objects.count()
        
        # Temporal features summary
        weekend_visits = ParkingRecord.objects.filter(is_weekend=True).count()
        peak_hour_visits = ParkingRecord.objects.filter(is_peak_hours=True).count()
        night_entries = ParkingRecord.objects.filter(is_night_entry=True).count()
        
        # Duration features summary
        overstays = ParkingRecord.objects.filter(is_overstay=True).count()
        short_stays = ParkingRecord.objects.filter(duration_category='short').count()
        
        # Vehicle features summary
        frequent_vehicles = ParkingRecord.objects.filter(vehicle_usage_type='frequent').values('license_plate').distinct().count()
        multi_site_vehicles = ParkingRecord.objects.filter(vehicle_is_multi_site=True).values('license_plate').distinct().count()
        
        # Financial features summary
        high_revenue_visits = ParkingRecord.objects.filter(revenue_category='high').count()
        digital_payments = ParkingRecord.objects.filter(is_digital_payment=True).count()
        
        print(f"\nFEATURE ENGINEERING SUMMARY")
        print(f"{'='*50}")
        print(f"Total Records Processed: {total_records:,}")
        print(f"\nTemporal Features:")
        print(f"  Weekend Visits: {weekend_visits:,} ({weekend_visits/total_records*100:.1f}%)")
        print(f"  Peak Hour Visits: {peak_hour_visits:,} ({peak_hour_visits/total_records*100:.1f}%)")
        print(f"  Night Entries: {night_entries:,} ({night_entries/total_records*100:.1f}%)")
        
        print(f"\nDuration Features:")
        print(f"  Overstays: {overstays:,} ({overstays/total_records*100:.1f}%)")
        print(f"  Short Stays (≤30min): {short_stays:,} ({short_stays/total_records*100:.1f}%)")
        
        print(f"\nVehicle Features:")
        print(f"  Frequent Vehicles: {frequent_vehicles:,}")
        print(f"  Multi-site Vehicles: {multi_site_vehicles:,}")
        
        print(f"\nFinancial Features:")
        print(f"  High Revenue Visits: {high_revenue_visits:,} ({high_revenue_visits/total_records*100:.1f}%)")
        print(f"  Digital Payments: {digital_payments:,} ({digital_payments/total_records*100:.1f}%)")
        
        return {
            'total_records': total_records,
            'weekend_percentage': weekend_visits/total_records*100,
            'peak_hour_percentage': peak_hour_visits/total_records*100,
            'overstay_percentage': overstays/total_records*100,
            'frequent_vehicles': frequent_vehicles,
            'digital_payment_percentage': digital_payments/total_records*100
        }
    
    def run_feature_engineering(self):
        """Run complete feature engineering pipeline"""
        print("Starting Advanced Feature Engineering Pipeline")
        print("="*60)
        
        start_time = datetime.now()
        
        try:
            with transaction.atomic():
                # Run all feature engineering steps
                self.calculate_temporal_features()
                self.calculate_duration_features()
                self.calculate_vehicle_features()
                self.calculate_organization_features()
                self.calculate_behavioral_features()
                self.calculate_financial_features()
                
                # Generate summary
                summary = self.generate_feature_summary()
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                print(f"\nFeature Engineering Complete!")
                print(f"Total Time: {duration:.2f} seconds")
                print(f"Enhanced {summary['total_records']:,} records with advanced features")
                
                return summary
                
        except Exception as e:
            print(f"Error in feature engineering pipeline: {e}")
            raise


def main():
    """Main execution function"""
    engineer = VehicleFeatureEngineer()
    summary = engineer.run_feature_engineering()
    
    print(f"\nFeature engineering completed successfully!")
    print(f"The dataset is now enriched with advanced features for enhanced analytics and visualizations.")


if __name__ == "__main__":
    main()