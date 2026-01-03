# Generated migration to rename Location column to Organization

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0002_add_feature_engineering_fields'),
    ]

    operations = [
        # Rename Location column to Organization if it exists
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'parking_records' 
                    AND column_name = 'location'
                ) THEN
                    ALTER TABLE parking_records RENAME COLUMN location TO organization;
                END IF;
            END $$;
            """,
            reverse_sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'parking_records' 
                    AND column_name = 'organization'
                ) THEN
                    ALTER TABLE parking_records RENAME COLUMN organization TO location;
                END IF;
            END $$;
            """
        ),
        
        # Update any existing data that might have 'Location' references
        migrations.RunSQL(
            """
            -- Update any location references in other tables if they exist
            UPDATE parking_records 
            SET organization = COALESCE(organization, 'Unknown Organization')
            WHERE organization IS NULL OR organization = '';
            """,
            reverse_sql="-- No reverse operation needed"
        ),
    ]