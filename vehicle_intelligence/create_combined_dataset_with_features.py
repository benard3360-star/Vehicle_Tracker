"""
Create combined_dataset table and add engineered features
"""
import sqlite3
import pandas as pd
import numpy as np
import glob
import os
from datetime import datetime

def connect_to_database():
    """Connect to SQLite database"""
    return sqlite3.connect('db.sqlite3')

def check_existing_tables():
    """Check what tables exist in the database"""
    conn = connect_to_database()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("Existing tables in database:")
    for table in tables:
        print(f"  - {table[0]}")
        
        # Get row count for each table
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"    Records: {count:,}")
    
    conn.close()
    return [table[0] for table in tables]

def load_excel_data():
    """Load and combine Excel data files"""
    file_path = 'Data'
    
    if not os.path.exists(file_path):
        print(f"Data folder '{file_path}' not found. Please ensure Excel files are in the Data folder.")
        return None
    
    # Get all Excel files in the folder
    all_files = glob.glob(os.path.join(file_path, "*.xlsx"))
    
    if not all_files:
        print("No Excel files found in Data folder")
        return None
    
    print(f"Found {len(all_files)} Excel files")
    
    # List to hold all DataFrames
    df_list = []
    
    for file in all_files:
        print(f"Processing: {file}")
        # Read the Excel file
        df = pd.read_excel(file)
        
        # Extract the last part of the filename as Organization
        location_name = os.path.splitext(os.path.basename(file))[0].split('-')[-1]
        df['Organization'] = location_name
        
        # Append to the list
        df_list.append(df)
    
    # Concatenate all DataFrames vertically
    master_df = pd.concat(df_list, ignore_index=True)
    
    # Clean organization names
    master_df['Organization'].replace('1st December United Mall', 'United Mall', regex=True, inplace=True)
    
    # Clean column names
    master_df.columns = (
        master_df.columns
        .str.replace(r"\\(Kenyan Time\\)", "", regex=True)
        .str.strip()
        .str.title()
    )
    
    print(f"Combined dataset shape: {master_df.shape}")
    print(f"Organizations found: {master_df['Organization'].unique()}")
    
    return master_df

def create_combined_dataset_table(df):
    """Create combined_dataset table with data and engineered features"""
    conn = connect_to_database()
    cursor = conn.cursor()
    
    try:
        # Drop table if exists
        cursor.execute("DROP TABLE IF EXISTS combined_dataset")
        
        # Create table with all columns including feature columns
        create_table_sql = """
        CREATE TABLE combined_dataset (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "Entry Time" TEXT,
            "Exit Time" TEXT,
            "Payment Time" TEXT,
            "Plate Number" TEXT,
            "Vehicle Type" TEXT,
            "Plate Color" TEXT,
            "Vehicle Brand" TEXT,
            "Amount Paid" REAL,
            "Payment Method" TEXT,
            "Organization" TEXT,
            "Vehicle Id" TEXT,
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
        )
        """
        cursor.execute(create_table_sql)
        conn.commit()
        print("Created combined_dataset table with feature columns")
        
        # Convert datetime columns
        df['Entry Time'] = pd.to_datetime(df['Entry Time'], errors='coerce')
        df['Exit Time'] = pd.to_datetime(df['Exit Time'], errors='coerce')
        df['Payment Time'] = pd.to_datetime(df['Payment Time'], errors='coerce')
        
        print("Calculating engineered features...")
        
        # Create Vehicle ID if not exists
        df['Vehicle Id'] = df['Plate Number'].apply(lambda x: f"VH_{abs(hash(str(x))) % 1000000}")
        
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
        
        # === DURATION FEATURES ===
        df['duration_minutes'] = ((df['Exit Time'] - df['Entry Time']).dt.total_seconds() / 60).fillna(0)
        df['duration_category'] = pd.cut(df['duration_minutes'], 
                                       bins=[0, 30, 120, 480, float('inf')], 
                                       labels=[0, 1, 2, 3], include_lowest=True).astype(float).fillna(0).astype(int)
        df['duration_efficiency_score'] = np.clip(100 - (df['duration_minutes'] - 60).abs() / 10, 0, 100)
        df['is_overstay'] = (df['duration_minutes'] > 240).astype(int)
        
        # === VEHICLE BEHAVIOR FEATURES ===
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
        
        # === FINANCIAL FEATURES ===
        df['revenue_per_minute'] = (df['Amount Paid'] / df['duration_minutes']).replace([np.inf, -np.inf], 0).fillna(0)
        df['is_digital_payment'] = df['Payment Method'].isin(['Card', 'Mobile', 'Digital']).astype(int)
        df['payment_efficiency_score'] = np.where(df['Amount Paid'] > 0, 
                                                np.clip(df['revenue_per_minute'] * 10, 0, 100), 0)
        
        # Convert datetime columns to strings for SQLite
        df['Entry Time'] = df['Entry Time'].astype(str)
        df['Exit Time'] = df['Exit Time'].astype(str)
        df['Payment Time'] = df['Payment Time'].astype(str)
        
        # Insert data into table
        print("Inserting data with engineered features...")
        columns_to_insert = [
            'Entry Time', 'Exit Time', 'Payment Time', 'Plate Number', 'Vehicle Type',
            'Plate Color', 'Vehicle Brand', 'Amount Paid', 'Payment Method', 'Organization',
            'Vehicle Id', 'entry_hour', 'entry_day_of_week', 'entry_month', 'entry_quarter',
            'entry_season', 'is_weekend', 'is_business_hours', 'is_peak_hours', 'is_night_entry',
            'duration_minutes', 'duration_category', 'duration_efficiency_score', 'is_overstay',
            'visit_frequency', 'total_revenue', 'unique_sites', 'vehicle_usage_category',
            'vehicle_revenue_tier', 'is_multi_site_vehicle', 'org_vehicle_count', 'org_total_revenue',
            'organization_size_category', 'organization_performance_tier', 'days_since_last_visit',
            'visit_frequency_category', 'is_duration_anomaly', 'is_payment_anomaly',
            'revenue_per_minute', 'is_digital_payment', 'payment_efficiency_score'
        ]
        
        # Prepare data for insertion
        data_to_insert = []
        for _, row in df.iterrows():
            row_data = []
            for col in columns_to_insert:
                if col in row:
                    value = row[col]
                    if pd.isna(value) or str(value) == 'NaT':
                        row_data.append(None)
                    else:
                        row_data.append(value)
                else:
                    row_data.append(None)
            data_to_insert.append(tuple(row_data))
        
        placeholders = ','.join(['?' for _ in columns_to_insert])
        insert_sql = f"INSERT INTO combined_dataset ({','.join([f'\"{col}\"' for col in columns_to_insert])}) VALUES ({placeholders})"
        
        cursor.executemany(insert_sql, data_to_insert)
        conn.commit()
        
        # Verify insertion
        cursor.execute("SELECT COUNT(*) FROM combined_dataset")
        count = cursor.fetchone()[0]
        
        # Generate summary
        print("\n" + "="*60)
        print("FEATURE ENGINEERING SUMMARY")
        print("="*60)
        print(f"Total Records Processed: {count:,}")
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
        
        print(f"\nOrganization Features:")
        print(f"  Organizations: {df['Organization'].nunique():,}")
        print(f"  Average Vehicles per Org: {df['org_vehicle_count'].mean():.1f}")
        
        print(f"\nFinancial Features:")
        print(f"  Total Revenue: KSh {df['Amount Paid'].sum():,.2f}")
        print(f"  Digital Payments: {df['is_digital_payment'].sum():,} ({df['is_digital_payment'].mean()*100:.1f}%)")
        print(f"  Average Revenue per Minute: KSh {df['revenue_per_minute'].mean():.2f}")
        
        print(f"\nFeature engineering completed successfully!")
        print(f"The combined_dataset table now contains {len(columns_to_insert)} columns with comprehensive engineered features.")
        
        return count
        
    except Exception as e:
        print(f"Error creating combined_dataset table: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """Main execution function"""
    print("Vehicle Intelligence System - Feature Engineering")
    print("="*60)
    
    # Check existing tables
    existing_tables = check_existing_tables()
    
    # Load Excel data
    print("\nLoading Excel data...")
    df = load_excel_data()
    
    if df is not None:
        # Create combined_dataset table with engineered features
        print("\nCreating combined_dataset table with engineered features...")
        record_count = create_combined_dataset_table(df)
        
        print(f"\nSuccess! Created combined_dataset table with {record_count:,} records and comprehensive engineered features.")
    else:
        print("No data to process. Please ensure Excel files are available in the Data folder.")

if __name__ == "__main__":
    main()