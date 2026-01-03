"""
Inspect existing combined_dataset table and add engineered features
"""
import sqlite3
import pandas as pd
import numpy as np

def inspect_combined_dataset():
    """Inspect the existing combined_dataset table"""
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='combined_dataset';")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("combined_dataset table does not exist!")
            return None
        
        # Get table structure
        cursor.execute("PRAGMA table_info(combined_dataset)")
        columns = cursor.fetchall()
        
        print("Current combined_dataset table structure:")
        print("="*50)
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Get record count
        cursor.execute("SELECT COUNT(*) FROM combined_dataset")
        count = cursor.fetchone()[0]
        print(f"\nTotal records: {count:,}")
        
        # Get sample data
        cursor.execute("SELECT * FROM combined_dataset LIMIT 5")
        sample_data = cursor.fetchall()
        
        print("\nSample data (first 5 rows):")
        column_names = [col[1] for col in columns]
        df_sample = pd.DataFrame(sample_data, columns=column_names)
        print(df_sample.to_string())
        
        return column_names, count
        
    except Exception as e:
        print(f"Error inspecting table: {e}")
        return None
    finally:
        conn.close()

def add_engineered_features():
    """Add engineered features to existing combined_dataset table"""
    conn = sqlite3.connect('db.sqlite3')
    
    try:
        # Load existing data
        print("\nLoading existing data from combined_dataset...")
        df = pd.read_sql_query("SELECT * FROM combined_dataset", conn)
        print(f"Loaded {len(df)} records")
        
        # Display current columns
        print(f"\nCurrent columns: {list(df.columns)}")
        
        # Convert datetime columns (handle different possible column names)
        datetime_columns = []
        for col in df.columns:
            if 'entry' in col.lower() and 'time' in col.lower():
                datetime_columns.append(col)
            elif 'exit' in col.lower() and 'time' in col.lower():
                datetime_columns.append(col)
            elif 'payment' in col.lower() and 'time' in col.lower():
                datetime_columns.append(col)
        
        # Find the actual column names
        entry_time_col = None
        exit_time_col = None
        payment_time_col = None
        amount_col = None
        plate_col = None
        org_col = None
        payment_method_col = None
        
        for col in df.columns:
            if 'entry' in col.lower() and 'time' in col.lower():
                entry_time_col = col
            elif 'exit' in col.lower() and 'time' in col.lower():
                exit_time_col = col
            elif 'payment' in col.lower() and 'time' in col.lower():
                payment_time_col = col
            elif 'amount' in col.lower() or 'paid' in col.lower():
                amount_col = col
            elif 'plate' in col.lower() and 'number' in col.lower():
                plate_col = col
            elif 'organization' in col.lower() or 'location' in col.lower():
                org_col = col
            elif 'payment' in col.lower() and 'method' in col.lower():
                payment_method_col = col
        
        print(f"Identified columns:")
        print(f"  Entry Time: {entry_time_col}")
        print(f"  Exit Time: {exit_time_col}")
        print(f"  Amount: {amount_col}")
        print(f"  Organization: {org_col}")
        
        if not entry_time_col:
            print("Error: Could not find entry time column!")
            return
        
        # Convert datetime columns
        df[entry_time_col] = pd.to_datetime(df[entry_time_col], errors='coerce')
        if exit_time_col:
            df[exit_time_col] = pd.to_datetime(df[exit_time_col], errors='coerce')
        if payment_time_col:
            df[payment_time_col] = pd.to_datetime(df[payment_time_col], errors='coerce')
        
        print("\nCalculating engineered features...")
        
        # Create Vehicle ID if not exists
        if plate_col and 'Vehicle Id' not in df.columns:
            df['Vehicle Id'] = df[plate_col].apply(lambda x: f"VH_{abs(hash(str(x))) % 1000000}")
        
        # === TEMPORAL FEATURES ===
        print("  - Temporal features...")
        df['entry_hour'] = df[entry_time_col].dt.hour
        df['entry_day_of_week'] = df[entry_time_col].dt.dayofweek
        df['entry_month'] = df[entry_time_col].dt.month
        df['entry_quarter'] = df[entry_time_col].dt.quarter
        df['entry_season'] = df['entry_month'].map({12:0, 1:0, 2:0, 3:1, 4:1, 5:1, 6:2, 7:2, 8:2, 9:3, 10:3, 11:3})
        df['is_weekend'] = (df['entry_day_of_week'] >= 5).astype(int)
        df['is_business_hours'] = df['entry_hour'].between(9, 17).astype(int)
        df['is_peak_hours'] = df['entry_hour'].isin([8, 9, 17, 18]).astype(int)
        df['is_night_entry'] = df['entry_hour'].between(22, 5).astype(int)
        
        # === DURATION FEATURES ===
        print("  - Duration features...")
        if exit_time_col:
            df['duration_minutes'] = ((df[exit_time_col] - df[entry_time_col]).dt.total_seconds() / 60).fillna(0)
        else:
            df['duration_minutes'] = 0
            
        df['duration_category'] = pd.cut(df['duration_minutes'], 
                                       bins=[0, 30, 120, 480, float('inf')], 
                                       labels=[0, 1, 2, 3], include_lowest=True).astype(float).fillna(0).astype(int)
        df['duration_efficiency_score'] = np.clip(100 - (df['duration_minutes'] - 60).abs() / 10, 0, 100)
        df['is_overstay'] = (df['duration_minutes'] > 240).astype(int)
        
        # === VEHICLE BEHAVIOR FEATURES ===
        print("  - Vehicle behavior features...")
        if 'Vehicle Id' in df.columns:
            vehicle_stats = df.groupby('Vehicle Id').agg({
                entry_time_col: 'count',
                amount_col: 'sum' if amount_col else entry_time_col,
                org_col: 'nunique' if org_col else entry_time_col
            }).rename(columns={
                entry_time_col: 'visit_frequency',
                amount_col: 'total_revenue' if amount_col else 'visit_frequency',
                org_col: 'unique_sites' if org_col else 'visit_frequency'
            })
            
            # Handle case where amount_col doesn't exist
            if not amount_col:
                vehicle_stats['total_revenue'] = 0
            if not org_col:
                vehicle_stats['unique_sites'] = 1
            
            df = df.merge(vehicle_stats, left_on='Vehicle Id', right_index=True, how='left')
            
            df['vehicle_usage_category'] = pd.cut(df['visit_frequency'], 
                                                bins=[0, 2, 5, 10, float('inf')], 
                                                labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
            df['vehicle_revenue_tier'] = pd.cut(df['total_revenue'], 
                                              bins=[0, 100, 500, 1000, float('inf')], 
                                              labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
            df['is_multi_site_vehicle'] = (df['unique_sites'] > 1).astype(int)
        else:
            # Default values if Vehicle Id doesn't exist
            df['visit_frequency'] = 1
            df['total_revenue'] = df[amount_col] if amount_col else 0
            df['unique_sites'] = 1
            df['vehicle_usage_category'] = 0
            df['vehicle_revenue_tier'] = 0
            df['is_multi_site_vehicle'] = 0
        
        # === ORGANIZATION FEATURES ===
        print("  - Organization features...")
        if org_col:
            org_stats = df.groupby(org_col).agg({
                'Vehicle Id': 'nunique' if 'Vehicle Id' in df.columns else 'count',
                amount_col: 'sum' if amount_col else 'count'
            }).rename(columns={
                'Vehicle Id': 'org_vehicle_count',
                amount_col: 'org_total_revenue' if amount_col else 'org_vehicle_count'
            })
            
            if not amount_col:
                org_stats['org_total_revenue'] = 0
            
            df = df.merge(org_stats, left_on=org_col, right_index=True, how='left')
            
            df['organization_size_category'] = pd.cut(df['org_vehicle_count'], 
                                                    bins=[0, 50, 200, 500, float('inf')], 
                                                    labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
            df['organization_performance_tier'] = pd.cut(df['org_total_revenue'], 
                                                       bins=[0, 1000, 5000, 10000, float('inf')], 
                                                       labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
        else:
            df['org_vehicle_count'] = 1
            df['org_total_revenue'] = df[amount_col] if amount_col else 0
            df['organization_size_category'] = 0
            df['organization_performance_tier'] = 0
        
        # === BEHAVIORAL FEATURES ===
        print("  - Behavioral features...")
        if 'Vehicle Id' in df.columns:
            df = df.sort_values(['Vehicle Id', entry_time_col])
            df['days_since_last_visit'] = df.groupby('Vehicle Id')[entry_time_col].diff().dt.days.fillna(0)
        else:
            df['days_since_last_visit'] = 0
            
        df['visit_frequency_category'] = pd.cut(df['days_since_last_visit'], 
                                              bins=[0, 1, 7, 30, float('inf')], 
                                              labels=[3, 2, 1, 0]).astype(float).fillna(0).astype(int)
        
        # Anomaly detection
        if amount_col:
            duration_mean = df['duration_minutes'].mean()
            duration_std = df['duration_minutes'].std()
            df['is_duration_anomaly'] = (abs(df['duration_minutes'] - duration_mean) > 2 * duration_std).astype(int)
            
            payment_mean = df[amount_col].mean()
            payment_std = df[amount_col].std()
            df['is_payment_anomaly'] = (abs(df[amount_col] - payment_mean) > 2 * payment_std).astype(int)
        else:
            df['is_duration_anomaly'] = 0
            df['is_payment_anomaly'] = 0
        
        # === FINANCIAL FEATURES ===
        print("  - Financial features...")
        if amount_col:
            df['revenue_per_minute'] = (df[amount_col] / df['duration_minutes']).replace([np.inf, -np.inf], 0).fillna(0)
            df['payment_efficiency_score'] = np.where(df[amount_col] > 0, 
                                                    np.clip(df['revenue_per_minute'] * 10, 0, 100), 0)
        else:
            df['revenue_per_minute'] = 0
            df['payment_efficiency_score'] = 0
            
        if payment_method_col:
            df['is_digital_payment'] = df[payment_method_col].isin(['Card', 'Mobile', 'Digital']).astype(int)
        else:
            df['is_digital_payment'] = 0
        
        # Add feature columns to database
        print("\nAdding feature columns to database...")
        cursor = conn.cursor()
        
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
        
        # Add missing feature columns
        for col_name, col_type in feature_columns:
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE combined_dataset ADD COLUMN {col_name} {col_type}")
                    print(f"  Added column: {col_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        print(f"  Error adding column {col_name}: {e}")
        
        conn.commit()
        
        # Update records with calculated features
        print("\nUpdating records with engineered features...")
        for index, row in df.iterrows():
            if pd.notna(row.get('id')):
                update_values = []
                update_params = []
                
                for col_name, _ in feature_columns:
                    if col_name in row and pd.notna(row[col_name]):
                        update_values.append(f"{col_name} = ?")
                        update_params.append(row[col_name])
                
                if update_values:
                    update_params.append(row['id'])
                    update_sql = f"UPDATE combined_dataset SET {', '.join(update_values)} WHERE id = ?"
                    cursor.execute(update_sql, update_params)
        
        conn.commit()
        
        # Generate summary
        print("\n" + "="*60)
        print("FEATURE ENGINEERING SUMMARY")
        print("="*60)
        print(f"Total Records Updated: {len(df):,}")
        print(f"\nTemporal Features:")
        print(f"  Weekend Visits: {df['is_weekend'].sum():,} ({df['is_weekend'].mean()*100:.1f}%)")
        print(f"  Peak Hour Visits: {df['is_peak_hours'].sum():,} ({df['is_peak_hours'].mean()*100:.1f}%)")
        print(f"  Night Entries: {df['is_night_entry'].sum():,} ({df['is_night_entry'].mean()*100:.1f}%)")
        
        print(f"\nDuration Features:")
        print(f"  Overstays: {df['is_overstay'].sum():,} ({df['is_overstay'].mean()*100:.1f}%)")
        print(f"  Average Duration: {df['duration_minutes'].mean():.1f} minutes")
        
        print(f"\nVehicle Features:")
        if 'Vehicle Id' in df.columns:
            print(f"  Unique Vehicles: {df['Vehicle Id'].nunique():,}")
        print(f"  Multi-site Vehicles: {df['is_multi_site_vehicle'].sum():,}")
        
        print(f"\nOrganization Features:")
        if org_col:
            print(f"  Organizations: {df[org_col].nunique():,}")
        print(f"  Average Vehicles per Org: {df['org_vehicle_count'].mean():.1f}")
        
        print(f"\nFinancial Features:")
        if amount_col:
            print(f"  Total Revenue: KSh {df[amount_col].sum():,.2f}")
            print(f"  Average Revenue per Minute: KSh {df['revenue_per_minute'].mean():.2f}")
        print(f"  Digital Payments: {df['is_digital_payment'].sum():,} ({df['is_digital_payment'].mean()*100:.1f}%)")
        
        print(f"\nFeature engineering completed successfully!")
        print(f"Added {len(feature_columns)} engineered features to the combined_dataset table.")
        
    except Exception as e:
        print(f"Error adding engineered features: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """Main execution function"""
    print("Vehicle Intelligence System - Add Engineered Features")
    print("="*60)
    
    # Inspect existing table
    result = inspect_combined_dataset()
    
    if result:
        # Add engineered features
        add_engineered_features()
    else:
        print("Cannot proceed without existing combined_dataset table.")

if __name__ == "__main__":
    main()