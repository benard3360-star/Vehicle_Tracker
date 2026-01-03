#!/usr/bin/env python
"""
Fix database schema and create missing tables
"""

import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

def create_parking_records_table():
    """Create the parking_records table manually"""
    sql = """
    CREATE TABLE IF NOT EXISTS parking_records (
        id BIGSERIAL PRIMARY KEY,
        plate_number VARCHAR(20) NOT NULL,
        entry_time TIMESTAMP WITH TIME ZONE NOT NULL,
        exit_time TIMESTAMP WITH TIME ZONE,
        vehicle_type VARCHAR(50) NOT NULL,
        plate_color VARCHAR(30) NOT NULL,
        vehicle_brand VARCHAR(50) NOT NULL,
        amount_paid DECIMAL(10, 2) NOT NULL,
        payment_time TIMESTAMP WITH TIME ZONE,
        payment_method VARCHAR(30) NOT NULL,
        organization VARCHAR(100) NOT NULL,
        parking_duration_minutes INTEGER,
        parking_status VARCHAR(20) DEFAULT 'completed',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        
        -- Feature engineering fields
        entry_hour INTEGER,
        entry_day_of_week INTEGER,
        entry_week_of_year INTEGER,
        entry_month INTEGER,
        entry_quarter INTEGER,
        is_weekend BOOLEAN DEFAULT FALSE,
        is_business_hours BOOLEAN DEFAULT FALSE,
        is_peak_hours BOOLEAN DEFAULT FALSE,
        is_night_entry BOOLEAN DEFAULT FALSE,
        season VARCHAR(10),
        
        duration_minutes INTEGER,
        duration_category VARCHAR(20),
        is_overstay BOOLEAN DEFAULT FALSE,
        duration_efficiency FLOAT,
        
        vehicle_visit_count INTEGER,
        vehicle_total_revenue DECIMAL(12, 2),
        vehicle_avg_duration FLOAT,
        vehicle_unique_sites INTEGER,
        vehicle_usage_type VARCHAR(20),
        vehicle_is_multi_site BOOLEAN DEFAULT FALSE,
        vehicle_revenue_tier VARCHAR(20),
        
        org_total_vehicles INTEGER,
        org_total_revenue DECIMAL(12, 2),
        org_avg_duration FLOAT,
        org_size_category VARCHAR(20),
        org_performance_tier VARCHAR(20),
        
        is_duration_anomaly BOOLEAN DEFAULT FALSE,
        is_payment_anomaly BOOLEAN DEFAULT FALSE,
        days_since_last_visit INTEGER,
        visit_frequency VARCHAR(20),
        
        revenue_per_minute FLOAT,
        payment_efficiency FLOAT,
        revenue_category VARCHAR(20),
        is_digital_payment BOOLEAN DEFAULT FALSE
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS parking_rec_plate_n_71d6b6_idx ON parking_records(plate_number, entry_time);
    CREATE INDEX IF NOT EXISTS parking_rec_organiz_214adf_idx ON parking_records(organization, entry_time);
    CREATE INDEX IF NOT EXISTS parking_rec_is_week_9cc412_idx ON parking_records(is_weekend, entry_time);
    CREATE INDEX IF NOT EXISTS parking_rec_is_peak_f7a66a_idx ON parking_records(is_peak_hours, entry_time);
    CREATE INDEX IF NOT EXISTS parking_rec_vehicle_172534_idx ON parking_records(vehicle_usage_type);
    CREATE INDEX IF NOT EXISTS parking_rec_duratio_b2cc46_idx ON parking_records(duration_category);
    CREATE INDEX IF NOT EXISTS parking_rec_revenue_da9ae1_idx ON parking_records(revenue_category);
    """
    
    with connection.cursor() as cursor:
        cursor.execute(sql)
    print("✓ parking_records table created successfully")

def fix_migration_state():
    """Mark migrations as applied"""
    from django.db.migrations.recorder import MigrationRecorder
    
    recorder = MigrationRecorder(connection)
    
    # Mark migrations as applied
    migrations_to_mark = [
        ('main_app', '0001_initial'),
        ('main_app', '0002_add_feature_engineering_fields'),
        ('main_app', '0003_rename_location_to_organization'),
        ('main_app', '0004_parkingrecord_parking_rec_is_week_9cc412_idx_and_more'),
    ]
    
    for app, migration in migrations_to_mark:
        if not recorder.migration_qs.filter(app=app, name=migration).exists():
            recorder.record_applied(app, migration)
            print(f"✓ Marked {app}.{migration} as applied")

def main():
    print("Fixing Database Schema")
    print("=" * 30)
    
    try:
        # Create missing table
        create_parking_records_table()
        
        # Fix migration state
        fix_migration_state()
        
        # Verify
        from main_app.models import ParkingRecord, Organization
        print(f"✓ ParkingRecord model accessible: {ParkingRecord.objects.count()} records")
        print(f"✓ Organization model accessible: {Organization.objects.count()} organizations")
        
        print("\n✓ Database schema fixed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)