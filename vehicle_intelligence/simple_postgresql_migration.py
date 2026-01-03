"""
Simple PostgreSQL migration script
"""
import os
import sys
import sqlite3
import pandas as pd
import numpy as np

def update_django_settings():
    """Update Django settings to use PostgreSQL"""
    settings_path = 'vehicle_intelligence/settings.py'
    
    try:
        with open(settings_path, 'r') as f:
            content = f.read()
        
        # Check if already using PostgreSQL
        if 'postgresql' in content:
            print("Django settings already configured for PostgreSQL")
            return True
        
        # Replace SQLite with PostgreSQL configuration
        if 'sqlite3' in content:
            # Find and replace the DATABASES section
            import re
            
            # Pattern to match the entire DATABASES configuration
            pattern = r"DATABASES\s*=\s*\{[^}]*\}"
            
            postgresql_config = """DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'vehicle_intelligence_db',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}"""
            
            content = re.sub(pattern, postgresql_config, content, flags=re.DOTALL)
            
            with open(settings_path, 'w') as f:
                f.write(content)
            
            print("Updated Django settings to use PostgreSQL")
            return True
    
    except Exception as e:
        print(f"Error updating Django settings: {e}")
        return False

def create_combined_dataset_sql():
    """Generate SQL to create combined_dataset table with all features"""
    
    # Load data from SQLite to get structure and calculate features
    conn = sqlite3.connect('db.sqlite3')
    
    try:
        # Load parking records
        df = pd.read_sql_query("SELECT * FROM parking_records", conn)
        print(f"Loaded {len(df)} records from SQLite")
        
        # Convert datetime columns
        df['entry_time'] = pd.to_datetime(df['entry_time'], errors='coerce')
        df['exit_time'] = pd.to_datetime(df['exit_time'], errors='coerce')
        df['payment_time'] = pd.to_datetime(df['payment_time'], errors='coerce')
        
        # Calculate engineered features
        print("Calculating engineered features...")
        
        # Vehicle ID
        df['vehicle_id'] = df['plate_number'].apply(lambda x: f"VH_{abs(hash(str(x))) % 1000000}")
        
        # Temporal features
        df['entry_hour'] = df['entry_time'].dt.hour
        df['entry_day_of_week'] = df['entry_time'].dt.dayofweek
        df['entry_month'] = df['entry_time'].dt.month
        df['entry_quarter'] = df['entry_time'].dt.quarter
        df['entry_season'] = df['entry_month'].map({12:0, 1:0, 2:0, 3:1, 4:1, 5:1, 6:2, 7:2, 8:2, 9:3, 10:3, 11:3})
        df['is_weekend'] = (df['entry_day_of_week'] >= 5).astype(int)
        df['is_business_hours'] = df['entry_hour'].between(9, 17).astype(int)
        df['is_peak_hours'] = df['entry_hour'].isin([8, 9, 17, 18]).astype(int)
        df['is_night_entry'] = df['entry_hour'].between(22, 5).astype(int)
        
        # Duration features
        df['duration_minutes'] = ((df['exit_time'] - df['entry_time']).dt.total_seconds() / 60).fillna(0)
        df['duration_category'] = pd.cut(df['duration_minutes'], 
                                       bins=[0, 30, 120, 480, float('inf')], 
                                       labels=[0, 1, 2, 3], include_lowest=True).astype(float).fillna(0).astype(int)
        df['duration_efficiency_score'] = np.clip(100 - (df['duration_minutes'] - 60).abs() / 10, 0, 100)
        df['is_overstay'] = (df['duration_minutes'] > 240).astype(int)
        
        # Vehicle behavior features
        vehicle_stats = df.groupby('vehicle_id').agg({
            'entry_time': 'count',
            'amount_paid': 'sum',
            'organization': 'nunique'
        }).rename(columns={
            'entry_time': 'visit_frequency',
            'amount_paid': 'total_revenue',
            'organization': 'unique_sites'
        })
        
        df = df.merge(vehicle_stats, left_on='vehicle_id', right_index=True, how='left')
        
        df['vehicle_usage_category'] = pd.cut(df['visit_frequency'], 
                                            bins=[0, 2, 5, 10, float('inf')], 
                                            labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
        df['vehicle_revenue_tier'] = pd.cut(df['total_revenue'], 
                                          bins=[0, 100, 500, 1000, float('inf')], 
                                          labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
        df['is_multi_site_vehicle'] = (df['unique_sites'] > 1).astype(int)
        
        # Organization features
        org_stats = df.groupby('organization').agg({
            'vehicle_id': 'nunique',
            'amount_paid': 'sum'
        }).rename(columns={
            'vehicle_id': 'org_vehicle_count',
            'amount_paid': 'org_total_revenue'
        })
        
        df = df.merge(org_stats, left_on='organization', right_index=True, how='left')
        
        df['organization_size_category'] = pd.cut(df['org_vehicle_count'], 
                                                bins=[0, 50, 200, 500, float('inf')], 
                                                labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
        df['organization_performance_tier'] = pd.cut(df['org_total_revenue'], 
                                                   bins=[0, 1000, 5000, 10000, float('inf')], 
                                                   labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
        
        # Behavioral features
        df = df.sort_values(['vehicle_id', 'entry_time'])
        df['days_since_last_visit'] = df.groupby('vehicle_id')['entry_time'].diff().dt.days.fillna(0)
        df['visit_frequency_category'] = pd.cut(df['days_since_last_visit'], 
                                              bins=[0, 1, 7, 30, float('inf')], 
                                              labels=[3, 2, 1, 0]).astype(float).fillna(0).astype(int)
        
        # Anomaly detection
        duration_mean = df['duration_minutes'].mean()
        duration_std = df['duration_minutes'].std()
        df['is_duration_anomaly'] = (abs(df['duration_minutes'] - duration_mean) > 2 * duration_std).astype(int)
        
        payment_mean = df['amount_paid'].mean()
        payment_std = df['amount_paid'].std()
        df['is_payment_anomaly'] = (abs(df['amount_paid'] - payment_mean) > 2 * payment_std).astype(int)
        
        # Financial features
        df['revenue_per_minute'] = (df['amount_paid'] / df['duration_minutes']).replace([np.inf, -np.inf], 0).fillna(0)
        df['is_digital_payment'] = df['payment_method'].isin(['Card', 'Mobile', 'Digital']).astype(int)
        df['payment_efficiency_score'] = np.where(df['amount_paid'] > 0, 
                                                np.clip(df['revenue_per_minute'] * 10, 0, 100), 0)
        
        # Save processed data to CSV for PostgreSQL import
        output_file = 'combined_dataset_with_features.csv'
        df.to_csv(output_file, index=False)
        print(f"Saved processed data to {output_file}")
        
        # Generate PostgreSQL CREATE TABLE and COPY commands
        sql_commands = f"""
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
    vehicle_id VARCHAR(50),
    entry_hour INTEGER,
    entry_day_of_week INTEGER,
    entry_month INTEGER,
    entry_quarter INTEGER,
    entry_season INTEGER,
    is_weekend INTEGER,
    is_business_hours INTEGER,
    is_peak_hours INTEGER,
    is_night_entry INTEGER,
    duration_minutes REAL,
    duration_category INTEGER,
    duration_efficiency_score REAL,
    is_overstay INTEGER,
    visit_frequency INTEGER,
    total_revenue REAL,
    unique_sites INTEGER,
    vehicle_usage_category INTEGER,
    vehicle_revenue_tier INTEGER,
    is_multi_site_vehicle INTEGER,
    org_vehicle_count INTEGER,
    org_total_revenue REAL,
    organization_size_category INTEGER,
    organization_performance_tier INTEGER,
    days_since_last_visit REAL,
    visit_frequency_category INTEGER,
    is_duration_anomaly INTEGER,
    is_payment_anomaly INTEGER,
    revenue_per_minute REAL,
    is_digital_payment INTEGER,
    payment_efficiency_score REAL
);

-- Copy data from CSV (run this after creating the table)
-- COPY combined_dataset FROM '{os.path.abspath(output_file)}' DELIMITER ',' CSV HEADER;

-- Verify data
SELECT COUNT(*) as total_records FROM combined_dataset;
SELECT organization, COUNT(*) as records FROM combined_dataset GROUP BY organization;
"""
        
        # Save SQL commands
        with open('postgresql_setup.sql', 'w') as f:
            f.write(sql_commands)
        
        print("Generated PostgreSQL setup commands in postgresql_setup.sql")
        
        # Print summary
        print("\n" + "="*60)
        print("FEATURE ENGINEERING SUMMARY")
        print("="*60)
        print(f"Total Records: {len(df):,}")
        print(f"Unique Vehicles: {df['vehicle_id'].nunique():,}")
        print(f"Organizations: {df['organization'].nunique():,}")
        print(f"Weekend Visits: {df['is_weekend'].sum():,} ({df['is_weekend'].mean()*100:.1f}%)")
        print(f"Overstays: {df['is_overstay'].sum():,} ({df['is_overstay'].mean()*100:.1f}%)")
        print(f"Digital Payments: {df['is_digital_payment'].sum():,} ({df['is_digital_payment'].mean()*100:.1f}%)")
        print(f"Total Revenue: KSh {df['amount_paid'].sum():,.2f}")
        print(f"Engineered Features: 30+ features added")
        
        return True
        
    except Exception as e:
        print(f"Error processing data: {e}")
        return False
    finally:
        conn.close()

def main():
    """Main execution"""
    print("Vehicle Intelligence System - PostgreSQL Migration")
    print("="*60)
    
    # Step 1: Update Django settings
    print("\n1. Updating Django settings...")
    update_django_settings()
    
    # Step 2: Process data and generate SQL
    print("\n2. Processing data and generating PostgreSQL setup...")
    if create_combined_dataset_sql():
        print("\nMigration preparation completed!")
        print("\nNext steps:")
        print("1. Install PostgreSQL and create database 'vehicle_intelligence_db'")
        print("2. Run: python manage.py migrate")
        print("3. Execute postgresql_setup.sql in your PostgreSQL database")
        print("4. Import combined_dataset_with_features.csv into the combined_dataset table")
        print("\nAll engineered features will be available in PostgreSQL!")
    else:
        print("Migration preparation failed!")

if __name__ == "__main__":
    main()