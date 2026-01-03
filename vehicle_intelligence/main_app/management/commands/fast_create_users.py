from django.core.management.base import BaseCommand
from django.db import connection, transaction
from main_app.models import CustomUser, Organization
from django.contrib.auth.hashers import make_password
from django.utils import timezone

class Command(BaseCommand):
    help = 'Fast bulk creation of vehicle users using raw SQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        with connection.cursor() as cursor:
            # First, create organizations if they don't exist
            self.stdout.write("Creating organizations...")
            
            if not dry_run:
                cursor.execute("""
                    INSERT INTO organizations (name, slug, email, is_active, created_at, updated_at)
                    SELECT DISTINCT 
                        organization,
                        LOWER(REPLACE(REPLACE(organization, ' ', '-'), '.', '-')),
                        CONCAT('admin@', LOWER(REPLACE(REPLACE(organization, ' ', ''), '.', '')), '.com'),
                        true,
                        NOW(),
                        NOW()
                    FROM real_movement_analytics 
                    WHERE organization IS NOT NULL
                    AND organization NOT IN (SELECT name FROM organizations)
                """)
                orgs_created = cursor.rowcount
                self.stdout.write(f"  Created {orgs_created} organizations")
            
            # Get organization counts
            cursor.execute("""
                SELECT organization, COUNT(DISTINCT plate_number) as plate_count
                FROM real_movement_analytics 
                WHERE organization IS NOT NULL AND plate_number IS NOT NULL
                GROUP BY organization
                ORDER BY plate_count DESC
            """)
            
            org_data = cursor.fetchall()
            total_plates = sum(count for _, count in org_data)
            
            self.stdout.write(f"\nFound {len(org_data)} organizations with {total_plates} total unique plates")
            for org_name, count in org_data:
                self.stdout.write(f"  - {org_name}: {count} plates")
            
            if dry_run:
                self.stdout.write(f"\nWould create {total_plates} vehicle users")
                return
            
            # Now create users in one massive SQL operation
            self.stdout.write(f"\nCreating {total_plates} vehicle users...")
            
            # Use ON CONFLICT to handle duplicates
            cursor.execute("""
                INSERT INTO users (
                    username, email, password, first_name, last_name, 
                    role, is_active, is_staff, is_superuser, date_joined,
                    organization_id, force_password_change
                )
                SELECT DISTINCT
                    rma.plate_number,
                    CONCAT(LOWER(rma.plate_number), '@', LOWER(REPLACE(REPLACE(rma.organization, ' ', ''), '.', '')), '.com'),
                    %s,  -- Default hashed password
                    'Vehicle',
                    rma.plate_number,
                    'employee',
                    true,
                    false,
                    false,
                    NOW(),
                    org.id,
                    false
                FROM real_movement_analytics rma
                JOIN organizations org ON org.name = rma.organization
                WHERE rma.plate_number IS NOT NULL 
                AND rma.organization IS NOT NULL
                AND rma.plate_number NOT IN (SELECT username FROM users)
                ON CONFLICT (username) DO NOTHING
            """, [make_password('default123')])  # Simple default password for all
            
            users_created = cursor.rowcount
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n[SUCCESS] Created {users_created} vehicle users in bulk!"
                )
            )
            
            if users_created > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"\n[INFO] All vehicle users created with default password: 'default123'\n"
                        f"Users can change their password after first login."
                    )
                )
                
                # Show some sample users created
                cursor.execute("""
                    SELECT u.username, o.name 
                    FROM users u 
                    JOIN organizations o ON u.organization_id = o.id 
                    WHERE u.role = 'employee' 
                    ORDER BY u.date_joined DESC 
                    LIMIT 10
                """)
                
                sample_users = cursor.fetchall()
                self.stdout.write("\nSample users created:")
                for username, org_name in sample_users:
                    self.stdout.write(f"  - {username} ({org_name})")