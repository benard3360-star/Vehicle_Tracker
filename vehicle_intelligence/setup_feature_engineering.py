#!/usr/bin/env python
"""
Complete setup script for feature engineering pipeline
This script will:
1. Reset migrations if needed
2. Create database tables
3. Load Excel data
4. Run feature engineering
5. Verify results
"""

import os
import sys
import django
from django.core.management import execute_from_command_line
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

from main_app.models import ParkingRecord, Organization

def check_table_exists(table_name):
    """Check if a table exists in the database"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
        """, [table_name])
        return cursor.fetchone()[0]

def main():
    print("Setting up Feature Engineering Pipeline")
    print("=" * 50)
    
    # Step 1: Check if parking_records table exists
    print("1. Checking database tables...")
    
    if not check_table_exists('parking_records'):
        print("   [ERROR] parking_records table doesn't exist")
        print("   [INFO] Creating database tables...")
        
        # Run migrations without the problematic index migration
        try:
            execute_from_command_line(['manage.py', 'migrate', 'main_app', '0003'])
            print("   [SUCCESS] Base tables created successfully")
        except Exception as e:
            print(f"   [ERROR] Error creating tables: {e}")
            return False
    else:
        print("   [SUCCESS] parking_records table exists")
    
    # Step 2: Check if data exists
    print("\n2. Checking data...")
    try:
        record_count = ParkingRecord.objects.count()
        print(f"   [INFO] Found {record_count} parking records")
        
        if record_count == 0:
            print("   [INFO] Loading Excel data...")
            execute_from_command_line(['manage.py', 'load_excel_data'])
            record_count = ParkingRecord.objects.count()
            print(f"   [SUCCESS] Loaded {record_count} records")
    except Exception as e:
        print(f"   [ERROR] Error checking/loading data: {e}")
        return False
    
    # Step 3: Apply remaining migrations (indexes)
    print("\n3. Applying performance indexes...")
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        print("   [SUCCESS] Database indexes created")
    except Exception as e:
        print(f"   [WARNING] Could not create indexes: {e}")
    
    # Step 4: Check if features exist
    print("\n4. Checking feature engineering status...")
    try:
        features_count = ParkingRecord.objects.filter(entry_hour__isnull=False).count()
        print(f"   [INFO] Found {features_count} records with features")
        
        if features_count == 0:
            print("   [INFO] Running feature engineering...")
            execute_from_command_line(['manage.py', 'run_feature_engineering'])
            features_count = ParkingRecord.objects.filter(entry_hour__isnull=False).count()
            print(f"   [SUCCESS] Enhanced {features_count} records with features")
        else:
            print("   [SUCCESS] Features already exist")
    except Exception as e:
        print(f"   [ERROR] Error in feature engineering: {e}")
        return False
    
    # Step 5: Verification
    print("\n5. Final verification...")
    try:
        total_records = ParkingRecord.objects.count()
        featured_records = ParkingRecord.objects.filter(entry_hour__isnull=False).count()
        organizations = Organization.objects.count()
        
        print(f"   [INFO] Total Records: {total_records:,}")
        print(f"   [INFO] Featured Records: {featured_records:,}")
        print(f"   [INFO] Organizations: {organizations}")
        print(f"   [INFO] Feature Coverage: {(featured_records/total_records*100):.1f}%")
        
        if featured_records > 0:
            # Show sample features
            sample = ParkingRecord.objects.filter(entry_hour__isnull=False).first()
            print(f"\n   [INFO] Sample Features:")
            print(f"      • Temporal: Hour={sample.entry_hour}, Weekend={sample.is_weekend}")
            print(f"      • Duration: Category={sample.duration_category}, Efficiency={sample.duration_efficiency}")
            print(f"      • Vehicle: Usage={sample.vehicle_usage_type}, Revenue Tier={sample.vehicle_revenue_tier}")
            print(f"      • Financial: Revenue/min={sample.revenue_per_minute}, Category={sample.revenue_category}")
        
        print("\n[SUCCESS] Feature Engineering Pipeline Setup Complete!")
        print("   Your data is now ready for advanced analytics and AI insights.")
        return True
        
    except Exception as e:
        print(f"   [ERROR] Error in verification: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n[SUCCESS] Setup completed successfully!")
        print("   You can now use the enhanced features in your analytics dashboard.")
    else:
        print("\n[ERROR] Setup failed. Please check the errors above.")
        sys.exit(1)