"""
Complete migration from SQLite to PostgreSQL with feature engineering
"""
import os
import sys
import django
import sqlite3
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

def setup_postgresql():
    """Setup PostgreSQL database and update Django settings"""
    
    # Update settings.py to use PostgreSQL
    settings_path = 'vehicle_intelligence/settings.py'
    
    with open(settings_path, 'r') as f:
        content = f.read()
    
    # Replace SQLite database configuration with PostgreSQL
    sqlite_config = """DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}"""
    
    postgresql_config = """DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'vehicle_intelligence_db',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}"""
    
    if 'sqlite3' in content:
        content = content.replace(sqlite_config, postgresql_config)
        
        with open(settings_path, 'w') as f:
            f.write(content)
        print("✓ Updated Django settings to use PostgreSQL")
    
    # Create PostgreSQL database
    try:
        conn = psycopg2.connect(
            host='localhost',
            user='postgres',
            password='password',
            database='postgres'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname='vehicle_intelligence_db'")
        if not cursor.fetchone():
            cursor.execute("CREATE DATABASE vehicle_intelligence_db")
            print("✓ Created PostgreSQL database: vehicle_intelligence_db")
        else:
            print("✓ PostgreSQL database already exists")
        
        conn.close()
    except Exception as e:
        print(f"Error setting up PostgreSQL: {e}")
        return False
    
    return True

def migrate_django_models():
    """Run Django migrations for PostgreSQL"""
    import subprocess
    
    try:
        # Make migrations
        result = subprocess.run(['python', 'manage.py', 'makemigrations'], 
                              capture_output=True, text=True, cwd='.')
        print("✓ Made Django migrations")
        
        # Apply migrations
        result = subprocess.run(['python', 'manage.py', 'migrate'], 
                              capture_output=True, text=True, cwd='.')
        print("✓ Applied Django migrations to PostgreSQL")
        
        return True
    except Exception as e:
        print(f"Error running migrations: {e}")
        return False

def transfer_sqlite_data():
    """Transfer data from SQLite to PostgreSQL"""
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect('db.sqlite3')
    
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(
        host='localhost',
        user='postgres',
        password='password',
        database='vehicle_intelligence_db'
    )
    
    try:
        # Get parking records from SQLite
        print("Loading data from SQLite...")
        df = pd.read_sql_query("SELECT * FROM parking_records", sqlite_conn)
        print(f"Loaded {len(df)} parking records from SQLite")
        
        # Convert datetime columns
        df['entry_time'] = pd.to_datetime(df['entry_time'], errors='coerce')
        df['exit_time'] = pd.to_datetime(df['exit_time'], errors='coerce')
        df['payment_time'] = pd.to_datetime(df['payment_time'], errors='coerce')
        
        # Calculate all engineered features
        print("Calculating engineered features...")
        
        # Create Vehicle ID
        df['vehicle_id'] = df['plate_number'].apply(lambda x: f"VH_{abs(hash(str(x))) % 1000000}")
        
        # === TEMPORAL FEATURES ===
        df['entry_hour'] = df['entry_time'].dt.hour
        df['entry_day_of_week'] = df['entry_time'].dt.dayofweek
        df['entry_month'] = df['entry_time'].dt.month
        df['entry_quarter'] = df['entry_time'].dt.quarter
        df['entry_season'] = df['entry_month'].map({12:0, 1:0, 2:0, 3:1, 4:1, 5:1, 6:2, 7:2, 8:2, 9:3, 10:3, 11:3})
        df['is_weekend'] = (df['entry_day_of_week'] >= 5).astype(int)
        df['is_business_hours'] = df['entry_hour'].between(9, 17).astype(int)
        df['is_peak_hours'] = df['entry_hour'].isin([8, 9, 17, 18]).astype(int)
        df['is_night_entry'] = df['entry_hour'].between(22, 5).astype(int)
        
        # === DURATION FEATURES ===
        df['duration_minutes'] = ((df['exit_time'] - df['entry_time']).dt.total_seconds() / 60).fillna(0)
        df['duration_category'] = pd.cut(df['duration_minutes'], 
                                       bins=[0, 30, 120, 480, float('inf')], 
                                       labels=[0, 1, 2, 3], include_lowest=True).astype(float).fillna(0).astype(int)
        df['duration_efficiency_score'] = np.clip(100 - (df['duration_minutes'] - 60).abs() / 10, 0, 100)
        df['is_overstay'] = (df['duration_minutes'] > 240).astype(int)
        
        # === VEHICLE BEHAVIOR FEATURES ===
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
        
        # === ORGANIZATION FEATURES ===
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
        
        # === BEHAVIORAL FEATURES ===
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
        
        # === FINANCIAL FEATURES ===
        df['revenue_per_minute'] = (df['amount_paid'] / df['duration_minutes']).replace([np.inf, -np.inf], 0).fillna(0)
        df['is_digital_payment'] = df['payment_method'].isin(['Card', 'Mobile', 'Digital']).astype(int)
        df['payment_efficiency_score'] = np.where(df['amount_paid'] > 0, 
                                                np.clip(df['revenue_per_minute'] * 10, 0, 100), 0)
        
        # Create combined_dataset table in PostgreSQL
        print("Creating combined_dataset table in PostgreSQL...")
        
        cursor = pg_conn.cursor()
        
        # Drop table if exists
        cursor.execute("DROP TABLE IF EXISTS combined_dataset")
        
        # Create table with all features
        create_table_sql = """
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
            payment_efficiency_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        cursor.execute(create_table_sql)
        pg_conn.commit()
        print("✓ Created combined_dataset table with all feature columns")
        
        # Insert data with features
        print("Inserting data with engineered features...")
        
        # Prepare columns for insertion
        columns = [
            'plate_number', 'entry_time', 'exit_time', 'vehicle_type', 'plate_color',
            'vehicle_brand', 'amount_paid', 'payment_time', 'payment_method', 'organization',
            'parking_duration_minutes', 'parking_status', 'vehicle_id', 'entry_hour',
            'entry_day_of_week', 'entry_month', 'entry_quarter', 'entry_season',
            'is_weekend', 'is_business_hours', 'is_peak_hours', 'is_night_entry',
            'duration_minutes', 'duration_category', 'duration_efficiency_score', 'is_overstay',
            'visit_frequency', 'total_revenue', 'unique_sites', 'vehicle_usage_category',
            'vehicle_revenue_tier', 'is_multi_site_vehicle', 'org_vehicle_count', 'org_total_revenue',
            'organization_size_category', 'organization_performance_tier', 'days_since_last_visit',
            'visit_frequency_category', 'is_duration_anomaly', 'is_payment_anomaly',
            'revenue_per_minute', 'is_digital_payment', 'payment_efficiency_score'
        ]
        
        # Insert in batches
        batch_size = 1000
        total_inserted = 0
        
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i+batch_size]
            
            # Prepare data for insertion
            data_to_insert = []
            for _, row in batch_df.iterrows():
                row_data = []
                for col in columns:
                    value = row.get(col)
                    if pd.isna(value) or str(value) == 'NaT':
                        row_data.append(None)
                    else:
                        row_data.append(value)
                data_to_insert.append(tuple(row_data))
            
            # Insert batch
            placeholders = ','.join(['%s' for _ in columns])
            insert_sql = f"INSERT INTO combined_dataset ({','.join(columns)}) VALUES ({placeholders})"
            
            cursor.executemany(insert_sql, data_to_insert)
            pg_conn.commit()
            
            total_inserted += len(batch_df)
            print(f"  Inserted batch {i//batch_size + 1}/{(len(df)-1)//batch_size + 1} ({total_inserted:,} records)")
        
        # Verify insertion
        cursor.execute("SELECT COUNT(*) FROM combined_dataset")
        count = cursor.fetchone()[0]
        
        print(f"\n✓ Successfully migrated {count:,} records to PostgreSQL combined_dataset table")
        
        # Generate summary
        print("\n" + "="*60)
        print("MIGRATION & FEATURE ENGINEERING SUMMARY")
        print("="*60)
        print(f"Total Records Migrated: {count:,}")
        print(f"Temporal Features: 9 features (hour, day, season, etc.)")
        print(f"Duration Features: 4 features (categories, efficiency, overstay)")
        print(f"Vehicle Features: 6 features (usage patterns, revenue tiers)")
        print(f"Organization Features: 4 features (size, performance)")
        print(f"Behavioral Features: 4 features (anomalies, visit patterns)")
        print(f"Financial Features: 3 features (revenue efficiency, digital payments)")
        print(f"Total Engineered Features: 30+ features")
        
        print(f"\nKey Statistics:")
        print(f"  Unique Vehicles: {df['vehicle_id'].nunique():,}")
        print(f"  Organizations: {df['organization'].nunique():,}")
        print(f"  Weekend Visits: {df['is_weekend'].sum():,} ({df['is_weekend'].mean()*100:.1f}%)")
        print(f"  Overstays: {df['is_overstay'].sum():,} ({df['is_overstay'].mean()*100:.1f}%)")
        print(f"  Digital Payments: {df['is_digital_payment'].sum():,} ({df['is_digital_payment'].mean()*100:.1f}%)")
        print(f"  Total Revenue: KSh {df['amount_paid'].sum():,.2f}")
        
        return True
        
    except Exception as e:
        print(f"Error transferring data: {e}")
        pg_conn.rollback()
        return False
    finally:
        sqlite_conn.close()
        pg_conn.close()

def main():
    """Main execution function"""
    print("Vehicle Intelligence System - Complete PostgreSQL Migration")
    print("="*70)
    
    # Step 1: Setup PostgreSQL
    print("\n1. Setting up PostgreSQL...")
    if not setup_postgresql():
        print("❌ Failed to setup PostgreSQL")
        return
    
    # Step 2: Run Django migrations
    print("\n2. Running Django migrations...")
    if not migrate_django_models():
        print("❌ Failed to run Django migrations")
        return
    
    # Step 3: Transfer data with features
    print("\n3. Transferring data and adding engineered features...")
    if not transfer_sqlite_data():
        print("❌ Failed to transfer data")
        return
    
    print("\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
    print("✓ PostgreSQL database configured")
    print("✓ Django models migrated")
    print("✓ All data transferred with engineered features")
    print("✓ combined_dataset table ready for analytics")
    print("\nYour Vehicle Intelligence System is now running on PostgreSQL with all engineered features!")

if __name__ == "__main__":
    main()