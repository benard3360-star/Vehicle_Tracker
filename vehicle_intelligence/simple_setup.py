#!/usr/bin/env python
"""
Simple Feature Engineering Setup Script
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

def main():
    print("Feature Engineering Setup")
    print("=" * 40)
    
    # Step 1: Apply all migrations
    print("1. Applying database migrations...")
    try:
        execute_from_command_line(['manage.py', 'migrate', '--run-syncdb'])
        print("   [SUCCESS] Database migrations applied")
    except Exception as e:
        print(f"   [ERROR] Migration failed: {e}")
        return False
    
    # Step 2: Load data if needed
    print("\n2. Loading data...")
    try:
        from main_app.models import ParkingRecord
        record_count = ParkingRecord.objects.count()
        
        if record_count == 0:
            print("   [INFO] No data found, loading Excel files...")
            execute_from_command_line(['manage.py', 'load_excel_data'])
            record_count = ParkingRecord.objects.count()
            print(f"   [SUCCESS] Loaded {record_count} records")
        else:
            print(f"   [INFO] Found {record_count} existing records")
    except Exception as e:
        print(f"   [ERROR] Data loading failed: {e}")
        return False
    
    # Step 3: Run feature engineering
    print("\n3. Running feature engineering...")
    try:
        from main_app.models import ParkingRecord
        features_count = ParkingRecord.objects.filter(entry_hour__isnull=False).count()
        
        if features_count == 0:
            print("   [INFO] No features found, running feature engineering...")
            execute_from_command_line(['manage.py', 'run_feature_engineering'])
            features_count = ParkingRecord.objects.filter(entry_hour__isnull=False).count()
            print(f"   [SUCCESS] Enhanced {features_count} records with features")
        else:
            print(f"   [INFO] Found {features_count} records already have features")
    except Exception as e:
        print(f"   [ERROR] Feature engineering failed: {e}")
        return False
    
    # Step 4: Summary
    print("\n4. Summary:")
    try:
        from main_app.models import ParkingRecord, Organization
        total_records = ParkingRecord.objects.count()
        featured_records = ParkingRecord.objects.filter(entry_hour__isnull=False).count()
        organizations = Organization.objects.count()
        
        print(f"   Total Records: {total_records:,}")
        print(f"   Featured Records: {featured_records:,}")
        print(f"   Organizations: {organizations}")
        print(f"   Feature Coverage: {(featured_records/total_records*100):.1f}%")
        
        if featured_records > 0:
            print("\n   [SUCCESS] Feature engineering setup complete!")
            print("   Your data is ready for advanced analytics.")
            return True
        else:
            print("\n   [WARNING] No features were created.")
            return False
            
    except Exception as e:
        print(f"   [ERROR] Summary failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✓ Setup completed successfully!")
    else:
        print("\n✗ Setup failed.")
        sys.exit(1)