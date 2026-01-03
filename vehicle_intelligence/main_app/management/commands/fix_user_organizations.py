from django.core.management.base import BaseCommand
from django.db import connection
from main_app.models import CustomUser, Organization
import secrets
import string

class Command(BaseCommand):
    help = 'Fix vehicle user organization assignments'

    def generate_password(self, length=8):
        """Generate a simple password"""
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))

    def handle(self, *args, **options):
        try:
            # First, get all organizations from real_movement_analytics
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT organization, COUNT(*) as vehicle_count
                    FROM real_movement_analytics 
                    WHERE organization IS NOT NULL 
                    GROUP BY organization
                    ORDER BY vehicle_count DESC
                """)
                
                db_organizations = cursor.fetchall()
                
                self.stdout.write(f"Found {len(db_organizations)} organizations in database:")
                for org_name, count in db_organizations:
                    self.stdout.write(f"  - {org_name}: {count} records")
                
                # Create or update organizations
                org_mapping = {}
                for org_name, count in db_organizations:
                    # Create organization if it doesn't exist
                    organization, created = Organization.objects.get_or_create(
                        name=org_name,
                        defaults={
                            'slug': org_name.lower().replace(' ', '-').replace('_', '-'),
                            'email': f'admin@{org_name.lower().replace(" ", "").replace("_", "")}.com',
                            'is_active': True
                        }
                    )
                    org_mapping[org_name] = organization
                    
                    if created:
                        self.stdout.write(f"Created organization: {org_name}")
                
                # Now get all vehicle plates and their organizations
                cursor.execute("""
                    SELECT DISTINCT plate_number, organization 
                    FROM real_movement_analytics 
                    WHERE plate_number IS NOT NULL 
                    AND organization IS NOT NULL
                    ORDER BY organization, plate_number
                """)
                
                vehicles = cursor.fetchall()
                
                updated_count = 0
                created_count = 0
                
                for plate_number, org_name in vehicles:
                    # Clean plate number for username
                    username = plate_number.replace(' ', '').replace('-', '').upper()
                    
                    # Get the organization
                    organization = org_mapping.get(org_name)
                    if not organization:
                        continue
                    
                    # Check if user exists
                    try:
                        user = CustomUser.objects.get(username=username)
                        # Update organization if different
                        if user.organization != organization:
                            user.organization = organization
                            user.save()
                            updated_count += 1
                    except CustomUser.DoesNotExist:
                        # Create new user
                        password = self.generate_password()
                        
                        user = CustomUser.objects.create_user(
                            username=username,
                            email=f'{username.lower()}@{org_name.lower().replace(" ", "").replace("_", "")}.com',
                            password=password,
                            first_name=plate_number,
                            last_name='Driver',
                            role='employee',
                            organization=organization,
                            is_active=True,
                            temp_password=password,
                            force_password_change=True
                        )
                        created_count += 1
                
                # Print summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nSummary:\n'
                        f'- Created {created_count} new users\n'
                        f'- Updated {updated_count} existing users\n'
                        f'- Total organizations: {len(org_mapping)}\n'
                    )
                )
                
                # Print user counts per organization
                self.stdout.write("\nUser counts per organization:")
                for org_name, organization in org_mapping.items():
                    user_count = CustomUser.objects.filter(organization=organization, role='employee').count()
                    self.stdout.write(f"  - {org_name}: {user_count} users")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error fixing user assignments: {str(e)}')
            )