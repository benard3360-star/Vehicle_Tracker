"""
Add engineered features to the combined_dataset table
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

def connect_to_database():
    """Connect to SQLite database"""
    return sqlite3.connect('db.sqlite3')

def add_feature_columns(conn):
    """Add feature columns to combined_dataset table"""
    cursor = conn.cursor()
    
    # List of feature columns to add
    feature_columns = [
        ('entry_hour', 'INTEGER'),
        ('entry_day_of_week', 'INTEGER'),
        ('entry_month', 'INTEGER'),
        ('entry_quarter', 'INTEGER'),
        ('entry_season', 'INTEGER'),
        ('is_weekend', 'INTEGER'),
        ('is_business_hours', 'INTEGER'),
        ('is_peak_hours', 'INTEGER'),
        ('is_night_entry', 'INTEGER'),
        ('duration_minutes', 'REAL'),
        ('duration_category', 'INTEGER'),
        ('duration_efficiency_score', 'REAL'),
        ('is_overstay', 'INTEGER'),
        ('visit_frequency', 'INTEGER'),
        ('total_revenue', 'REAL'),
        ('unique_sites', 'INTEGER'),
        ('vehicle_usage_category', 'INTEGER'),
        ('vehicle_revenue_tier', 'INTEGER'),
        ('is_multi_site_vehicle', 'INTEGER'),
        ('org_vehicle_count', 'INTEGER'),
        ('org_total_revenue', 'REAL'),
        ('organization_size_category', 'INTEGER'),
        ('organization_performance_tier', 'INTEGER'),
        ('days_since_last_visit', 'REAL'),
        ('visit_frequency_category', 'INTEGER'),
        ('is_duration_anomaly', 'INTEGER'),
        ('is_payment_anomaly', 'INTEGER'),
        ('revenue_per_minute', 'REAL'),
        ('is_digital_payment', 'INTEGER'),
        ('payment_efficiency_score', 'REAL')
    ]
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(combined_dataset)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    # Add missing columns
    for col_name, col_type in feature_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE combined_dataset ADD COLUMN {col_name} {col_type}")
                print(f"Added column: {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    print(f"Error adding column {col_name}: {e}")
    
    conn.commit()
    print("Feature columns added successfully")

def calculate_features():
    """Calculate all engineered features for the combined_dataset"""
    conn = connect_to_database()
    
    try:
        # Add feature columns first
        add_feature_columns(conn)
        
        # Load data into pandas for feature engineering
        print("Loading data from combined_dataset...")
        df = pd.read_sql_query("SELECT * FROM combined_dataset", conn)
        print(f"Loaded {len(df)} records")
        
        # Convert datetime columns
        df['Entry Time'] = pd.to_datetime(df['Entry Time'], errors='coerce')
        df['Exit Time'] = pd.to_datetime(df['Exit Time'], errors='coerce')
        df['Payment Time'] = pd.to_datetime(df['Payment Time'], errors='coerce')
        
        print("Calculating temporal features...")
        # === TEMPORAL FEATURES ===
        df['entry_hour'] = df['Entry Time'].dt.hour
        df['entry_day_of_week'] = df['Entry Time'].dt.dayofweek
        df['entry_month'] = df['Entry Time'].dt.month
        df['entry_quarter'] = df['Entry Time'].dt.quarter
        df['entry_season'] = df['entry_month'].map({12:0, 1:0, 2:0, 3:1, 4:1, 5:1, 6:2, 7:2, 8:2, 9:3, 10:3, 11:3})
        df['is_weekend'] = (df['entry_day_of_week'] >= 5).astype(int)
        df['is_business_hours'] = df['entry_hour'].between(9, 17).astype(int)
        df['is_peak_hours'] = df['entry_hour'].isin([8, 9, 17, 18]).astype(int)
        df['is_night_entry'] = df['entry_hour'].between(22, 5).astype(int)
        
        print("Calculating duration features...")
        # === DURATION FEATURES ===
        df['duration_minutes'] = ((df['Exit Time'] - df['Entry Time']).dt.total_seconds() / 60).fillna(0)
        df['duration_category'] = pd.cut(df['duration_minutes'], 
                                       bins=[0, 30, 120, 480, float('inf')], 
                                       labels=[0, 1, 2, 3], include_lowest=True).astype(float).fillna(0).astype(int)
        df['duration_efficiency_score'] = np.clip(100 - (df['duration_minutes'] - 60).abs() / 10, 0, 100)
        df['is_overstay'] = (df['duration_minutes'] > 240).astype(int)
        
        print("Calculating vehicle behavior features...")
        # === VEHICLE BEHAVIOR FEATURES ===
        # Create Vehicle ID if not exists
        if 'Vehicle Id' not in df.columns:
            df['Vehicle Id'] = df['Plate Number'].apply(lambda x: f"VH_{abs(hash(str(x))) % 1000000}")
        
        vehicle_stats = df.groupby('Vehicle Id').agg({
            'Entry Time': 'count',
            'Amount Paid': 'sum',
            'Organization': 'nunique'
        }).rename(columns={
            'Entry Time': 'visit_frequency',
            'Amount Paid': 'total_revenue',
            'Organization': 'unique_sites'
        })
        
        df = df.merge(vehicle_stats, left_on='Vehicle Id', right_index=True, how='left')
        
        df['vehicle_usage_category'] = pd.cut(df['visit_frequency'], 
                                            bins=[0, 2, 5, 10, float('inf')], 
                                            labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
        df['vehicle_revenue_tier'] = pd.cut(df['total_revenue'], 
                                          bins=[0, 100, 500, 1000, float('inf')], 
                                          labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
        df['is_multi_site_vehicle'] = (df['unique_sites'] > 1).astype(int)
        
        print("Calculating organization features...")
        # === ORGANIZATION FEATURES ===
        org_stats = df.groupby('Organization').agg({
            'Vehicle Id': 'nunique',
            'Amount Paid': 'sum'
        }).rename(columns={
            'Vehicle Id': 'org_vehicle_count',
            'Amount Paid': 'org_total_revenue'
        })
        
        df = df.merge(org_stats, left_on='Organization', right_index=True, how='left')
        
        df['organization_size_category'] = pd.cut(df['org_vehicle_count'], 
                                                bins=[0, 50, 200, 500, float('inf')], 
                                                labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
        df['organization_performance_tier'] = pd.cut(df['org_total_revenue'], 
                                                   bins=[0, 1000, 5000, 10000, float('inf')], 
                                                   labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
        
        print("Calculating behavioral features...")
        # === BEHAVIORAL FEATURES ===
        df = df.sort_values(['Vehicle Id', 'Entry Time'])
        df['days_since_last_visit'] = df.groupby('Vehicle Id')['Entry Time'].diff().dt.days.fillna(0)
        df['visit_frequency_category'] = pd.cut(df['days_since_last_visit'], 
                                              bins=[0, 1, 7, 30, float('inf')], 
                                              labels=[3, 2, 1, 0]).astype(float).fillna(0).astype(int)
        
        # Duration anomaly detection
        duration_mean = df['duration_minutes'].mean()
        duration_std = df['duration_minutes'].std()
        df['is_duration_anomaly'] = (abs(df['duration_minutes'] - duration_mean) > 2 * duration_std).astype(int)
        
        # Payment anomaly detection
        payment_mean = df['Amount Paid'].mean()
        payment_std = df['Amount Paid'].std()
        df['is_payment_anomaly'] = (abs(df['Amount Paid'] - payment_mean) > 2 * payment_std).astype(int)
        
        print("Calculating financial features...")
        # === FINANCIAL FEATURES ===
        df['revenue_per_minute'] = (df['Amount Paid'] / df['duration_minutes']).replace([np.inf, -np.inf], 0).fillna(0)
        df['is_digital_payment'] = df['Payment Method'].isin(['Card', 'Mobile', 'Digital']).astype(int)
        df['payment_efficiency_score'] = np.where(df['Amount Paid'] > 0, 
                                                np.clip(df['revenue_per_minute'] * 10, 0, 100), 0)
        
        print("Updating database with engineered features...")
        # Update the database with calculated features
        feature_columns = [
            'entry_hour', 'entry_day_of_week', 'entry_month', 'entry_quarter', 'entry_season',
            'is_weekend', 'is_business_hours', 'is_peak_hours', 'is_night_entry',
            'duration_minutes', 'duration_category', 'duration_efficiency_score', 'is_overstay',
            'visit_frequency', 'total_revenue', 'unique_sites', 'vehicle_usage_category',
            'vehicle_revenue_tier', 'is_multi_site_vehicle', 'org_vehicle_count', 'org_total_revenue',
            'organization_size_category', 'organization_performance_tier', 'days_since_last_visit',
            'visit_frequency_category', 'is_duration_anomaly', 'is_payment_anomaly',
            'revenue_per_minute', 'is_digital_payment', 'payment_efficiency_score'
        ]
        
        # Update records in batches
        cursor = conn.cursor()
        for index, row in df.iterrows():
            if pd.notna(row.get('id')):  # Make sure we have a valid ID
                update_values = []
                update_params = []
                
                for col in feature_columns:
                    if col in row and pd.notna(row[col]):
                        update_values.append(f"{col} = ?")
                        update_params.append(row[col])
                
                if update_values:
                    update_params.append(row['id'])
                    update_sql = f"UPDATE combined_dataset SET {', '.join(update_values)} WHERE id = ?"
                    cursor.execute(update_sql, update_params)
        
        conn.commit()
        
        # Generate summary
        print("\n" + "="*60)
        print("FEATURE ENGINEERING SUMMARY")
        print("="*60)
        print(f"Total Records Processed: {len(df):,}")
        print(f"\nTemporal Features:")
        print(f"  Weekend Visits: {df['is_weekend'].sum():,} ({df['is_weekend'].mean()*100:.1f}%)")
        print(f"  Peak Hour Visits: {df['is_peak_hours'].sum():,} ({df['is_peak_hours'].mean()*100:.1f}%)")
        print(f"  Night Entries: {df['is_night_entry'].sum():,} ({df['is_night_entry'].mean()*100:.1f}%)")
        
        print(f"\nDuration Features:")
        print(f"  Overstays: {df['is_overstay'].sum():,} ({df['is_overstay'].mean()*100:.1f}%)")
        print(f"  Average Duration: {df['duration_minutes'].mean():.1f} minutes")
        
        print(f"\nVehicle Features:")
        print(f"  Unique Vehicles: {df['Vehicle Id'].nunique():,}")
        print(f"  Multi-site Vehicles: {df['is_multi_site_vehicle'].sum():,}")
        
        print(f"\nFinancial Features:")
        print(f"  Total Revenue: KSh {df['Amount Paid'].sum():,.2f}")
        print(f"  Digital Payments: {df['is_digital_payment'].sum():,} ({df['is_digital_payment'].mean()*100:.1f}%)")
        
        print(f"\nFeature engineering completed successfully!")
        print(f"The combined_dataset table now contains {len(feature_columns)} engineered features.")
        
    except Exception as e:
        print(f"Error in feature engineering: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    calculate_features()