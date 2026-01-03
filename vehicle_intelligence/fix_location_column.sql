-- SQL Script to rename Location column to Organization
-- Run this directly in PostgreSQL if needed

-- Check if Location column exists and rename it
DO $$
BEGIN
    -- Check if 'location' column exists in parking_records table
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'parking_records' 
        AND column_name = 'location'
    ) THEN
        -- Rename location column to organization
        ALTER TABLE parking_records RENAME COLUMN location TO organization;
        RAISE NOTICE 'Column "location" renamed to "organization" successfully';
    ELSE
        RAISE NOTICE 'Column "location" does not exist, no action needed';
    END IF;
    
    -- Also check if we need to update any null/empty organization values
    UPDATE parking_records 
    SET organization = COALESCE(NULLIF(organization, ''), 'Unknown Organization')
    WHERE organization IS NULL OR organization = '';
    
    -- Get count of updated records
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % records with missing organization values', updated_count;
    
END $$;

-- Verify the change
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'parking_records' 
AND column_name IN ('location', 'organization')
ORDER BY column_name;

-- Show sample data to verify
SELECT 
    plate_number,
    organization,
    entry_time,
    amount_paid
FROM parking_records 
LIMIT 5;