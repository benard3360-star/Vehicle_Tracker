"""
Generate complete PostgreSQL setup files for manual execution
"""
import os
import pandas as pd

def generate_postgresql_setup():
    """Generate all PostgreSQL setup files"""
    
    print("Vehicle Intelligence System - PostgreSQL Setup Generator")
    print("="*60)
    
    # Check if CSV file exists
    csv_file = 'combined_dataset_with_features.csv'
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found!")
        print("Please run simple_postgresql_migration.py first")
        return
    
    # Load data to get statistics
    df = pd.read_csv(csv_file)
    print(f"Loaded {len(df)} records with engineered features")
    
    # Generate complete SQL setup
    sql_content = f"""
-- Vehicle Intelligence System - PostgreSQL Setup
-- Generated automatically with all engineered features

-- 1. Create database (run as postgres superuser)
DROP DATABASE IF EXISTS vehicle_intelligence_db;
CREATE DATABASE vehicle_intelligence_db;

-- 2. Connect to vehicle_intelligence_db and create table
\\c vehicle_intelligence_db;

-- Create combined_dataset table with all engineered features
DROP TABLE IF EXISTS combined_dataset;

CREATE TABLE combined_dataset (
    id SERIAL PRIMARY KEY,
    plate_number VARCHAR(20),
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    vehicle_type VARCHAR(50),
    plate_color VARCHAR(30),
    vehicle_brand VARCHAR(50),
    amount_paid DECIMAL(10,2),
    payment_time TIMESTAMP,
    payment_method VARCHAR(30),
    organization VARCHAR(100),
    parking_duration_minutes INTEGER,
    parking_status VARCHAR(20),
    created_at TIMESTAMP,
    -- Engineered Features Start Here --
    vehicle_id VARCHAR(50),
    -- Temporal Features
    entry_hour INTEGER,
    entry_day_of_week INTEGER,
    entry_month INTEGER,
    entry_quarter INTEGER,
    entry_season INTEGER,
    is_weekend INTEGER,
    is_business_hours INTEGER,
    is_peak_hours INTEGER,
    is_night_entry INTEGER,
    -- Duration Features
    duration_minutes REAL,
    duration_category INTEGER,
    duration_efficiency_score REAL,
    is_overstay INTEGER,
    -- Vehicle Behavior Features
    visit_frequency INTEGER,
    total_revenue REAL,
    unique_sites INTEGER,
    vehicle_usage_category INTEGER,
    vehicle_revenue_tier INTEGER,
    is_multi_site_vehicle INTEGER,
    -- Organization Features
    org_vehicle_count INTEGER,
    org_total_revenue REAL,
    organization_size_category INTEGER,
    organization_performance_tier INTEGER,
    -- Behavioral Features
    days_since_last_visit REAL,
    visit_frequency_category INTEGER,
    is_duration_anomaly INTEGER,
    is_payment_anomaly INTEGER,
    -- Financial Features
    revenue_per_minute REAL,
    is_digital_payment INTEGER,
    payment_efficiency_score REAL
);

-- 3. Import data from CSV
-- Note: Update the path to match your system
COPY combined_dataset (
    plate_number, entry_time, exit_time, vehicle_type, plate_color,
    vehicle_brand, amount_paid, payment_time, payment_method, organization,
    parking_duration_minutes, parking_status, created_at, vehicle_id,
    entry_hour, entry_day_of_week, entry_month, entry_quarter, entry_season,
    is_weekend, is_business_hours, is_peak_hours, is_night_entry,
    duration_minutes, duration_category, duration_efficiency_score, is_overstay,
    visit_frequency, total_revenue, unique_sites, vehicle_usage_category,
    vehicle_revenue_tier, is_multi_site_vehicle, org_vehicle_count, org_total_revenue,
    organization_size_category, organization_performance_tier, days_since_last_visit,
    visit_frequency_category, is_duration_anomaly, is_payment_anomaly,
    revenue_per_minute, is_digital_payment, payment_efficiency_score
) FROM '{os.path.abspath(csv_file)}' DELIMITER ',' CSV HEADER;

-- 4. Create feature summary table
CREATE TABLE feature_summary (
    id SERIAL PRIMARY KEY,
    total_records INTEGER,
    unique_vehicles INTEGER,
    organizations INTEGER,
    weekend_percentage REAL,
    overstay_percentage REAL,
    total_revenue REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert summary statistics
INSERT INTO feature_summary (total_records, unique_vehicles, organizations, weekend_percentage, overstay_percentage, total_revenue)
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT vehicle_id) as unique_vehicles,
    COUNT(DISTINCT organization) as organizations,
    AVG(is_weekend::float) * 100 as weekend_percentage,
    AVG(is_overstay::float) * 100 as overstay_percentage,
    SUM(amount_paid) as total_revenue
FROM combined_dataset;

-- 5. Create indexes for better performance
CREATE INDEX idx_combined_dataset_vehicle_id ON combined_dataset(vehicle_id);
CREATE INDEX idx_combined_dataset_organization ON combined_dataset(organization);
CREATE INDEX idx_combined_dataset_entry_time ON combined_dataset(entry_time);
CREATE INDEX idx_combined_dataset_entry_hour ON combined_dataset(entry_hour);
CREATE INDEX idx_combined_dataset_is_weekend ON combined_dataset(is_weekend);
CREATE INDEX idx_combined_dataset_is_overstay ON combined_dataset(is_overstay);

-- 6. Verify data import
SELECT 'Data Import Verification' as status;
SELECT COUNT(*) as total_records FROM combined_dataset;
SELECT organization, COUNT(*) as records FROM combined_dataset GROUP BY organization ORDER BY records DESC;

-- 7. Feature verification queries
SELECT 'Feature Verification' as status;
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT vehicle_id) as unique_vehicles,
    COUNT(DISTINCT organization) as organizations,
    ROUND(AVG(is_weekend::float) * 100, 1) as weekend_percentage,
    ROUND(AVG(is_overstay::float) * 100, 1) as overstay_percentage,
    ROUND(SUM(amount_paid), 2) as total_revenue
FROM combined_dataset;

-- Show sample of engineered features
SELECT 
    plate_number,
    organization,
    entry_hour,
    is_weekend,
    duration_minutes,
    is_overstay,
    vehicle_usage_category,
    revenue_per_minute
FROM combined_dataset 
LIMIT 10;
"""
    
    # Save SQL file
    with open('postgresql_complete_setup.sql', 'w') as f:
        f.write(sql_content)
    
    # Generate Django settings update
    django_settings = '''
# Add this to your vehicle_intelligence/settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'vehicle_intelligence_db',
        'USER': 'postgres',
        'PASSWORD': 'your_postgres_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Make sure you have psycopg2 installed:
# pip install psycopg2-binary
'''
    
    with open('django_settings_update.txt', 'w') as f:
        f.write(django_settings)
    
    # Generate setup instructions
    instructions = f"""
VEHICLE INTELLIGENCE SYSTEM - POSTGRESQL SETUP INSTRUCTIONS
===========================================================

Your data has been processed and is ready for PostgreSQL import!

FILES GENERATED:
- combined_dataset_with_features.csv ({len(df):,} records with 30+ engineered features)
- postgresql_complete_setup.sql (Complete database setup)
- django_settings_update.txt (Django configuration)

SETUP STEPS:

1. INSTALL POSTGRESQL
   - Download and install PostgreSQL from https://www.postgresql.org/
   - Remember your postgres user password

2. INSTALL PYTHON DEPENDENCIES
   pip install psycopg2-binary

3. UPDATE DJANGO SETTINGS
   - Copy content from django_settings_update.txt to vehicle_intelligence/settings.py
   - Update the password to match your PostgreSQL installation

4. CREATE DATABASE AND IMPORT DATA
   - Open PostgreSQL command line (psql) as postgres user
   - Run: \\i postgresql_complete_setup.sql
   - This will create the database, table, and import all {len(df):,} records

5. RUN DJANGO MIGRATIONS
   cd vehicle_intelligence
   python manage.py makemigrations
   python manage.py migrate

6. CREATE SUPERUSER
   python manage.py createsuperuser

7. START THE SERVER
   python manage.py runserver

ENGINEERED FEATURES INCLUDED:
=============================
+ Temporal Features (9): Hour, day, season, business hours, peak hours, etc.
+ Duration Features (4): Categories, efficiency scores, overstay detection
+ Vehicle Features (6): Usage patterns, revenue tiers, multi-site behavior
+ Organization Features (4): Size categories, performance tiers
+ Behavioral Features (4): Anomaly detection, visit frequency patterns
+ Financial Features (3): Revenue efficiency, digital payment analysis

STATISTICS:
===========
Total Records: {len(df):,}
Unique Vehicles: {df['vehicle_id'].nunique():,}
Organizations: {df['organization'].nunique()}
Weekend Visits: {df['is_weekend'].sum():,} ({df['is_weekend'].mean()*100:.1f}%)
Overstays: {df['is_overstay'].sum():,} ({df['is_overstay'].mean()*100:.1f}%)
Total Revenue: KSh {df['amount_paid'].sum():,.2f}

Your Vehicle Intelligence System will have full analytics capabilities with PostgreSQL!
"""
    
    with open('SETUP_INSTRUCTIONS.txt', 'w', encoding='utf-8') as f:
        f.write(instructions)
    
    print("\n" + "="*60)
    print("POSTGRESQL SETUP FILES GENERATED SUCCESSFULLY!")
    print("="*60)
    print("Generated files:")
    print("+ combined_dataset_with_features.csv - Data with engineered features")
    print("+ postgresql_complete_setup.sql - Complete database setup")
    print("+ django_settings_update.txt - Django configuration")
    print("+ SETUP_INSTRUCTIONS.txt - Step-by-step instructions")
    
    print(f"\nData Summary:")
    print(f"+ {len(df):,} records processed")
    print(f"+ {df['vehicle_id'].nunique():,} unique vehicles")
    print(f"+ {df['organization'].nunique()} organizations")
    print(f"+ 30+ engineered features added")
    
    print(f"\nNext Steps:")
    print("1. Install PostgreSQL")
    print("2. Follow instructions in SETUP_INSTRUCTIONS.txt")
    print("3. Your system will be running on PostgreSQL with all features!")

if __name__ == "__main__":
    generate_postgresql_setup()