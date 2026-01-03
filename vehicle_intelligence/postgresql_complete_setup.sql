
-- Vehicle Intelligence System - PostgreSQL Setup
-- Generated automatically with all engineered features

-- 1. Create database (run as postgres superuser)
DROP DATABASE IF EXISTS vehicle_intelligence_db;
CREATE DATABASE vehicle_intelligence_db;

-- 2. Connect to vehicle_intelligence_db and create table
\c vehicle_intelligence_db;

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
) FROM 'c:\Users\user\OneDrive - Strathmore University\Projects\vehicle-intelligence-system\vehicle_intelligence\combined_dataset_with_features.csv' DELIMITER ',' CSV HEADER;

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
