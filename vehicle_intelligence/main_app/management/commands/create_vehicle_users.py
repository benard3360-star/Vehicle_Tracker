from django.core.management.base import BaseCommand
from django.db import connection
from main_app.models import CustomUser, Organization
import secrets
import string

class Command(BaseCommand):
    help = 'Create users from vehicle plates in real_movement_analytics table'

    def generate_password(self, length=8):
        """Generate a simple password"""
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                # Get distinct plate numbers and their organizations
                cursor.execute("""
                    SELECT DISTINCT plate_number, organization 
                    FROM real_movement_analytics 
                    WHERE plate_number IS NOT NULL 
                    AND organization IS NOT NULL
                    ORDER BY organization, plate_number
                """)
                
                vehicles = cursor.fetchall()
                
                created_count = 0
                
                for plate_number, org_name in vehicles:
                    # Clean plate number for username
                    username = plate_number.replace(' ', '').replace('-', '').upper()
                    
                    # Get or create organization
                    organization, org_created = Organization.objects.get_or_create(
                        name=org_name,
                        defaults={
                            'slug': org_name.lower().replace(' ', '-').replace('_', '-'),
                            'email': f'admin@{org_name.lower().replace(" ", "").replace("_", "")}.com',
                            'is_active': True
                        }
                    )
                    
                    # Check if user already exists
                    if CustomUser.objects.filter(username=username).exists():
                        continue
                    
                    # Generate password
                    password = self.generate_password()
                    
                    # Create user
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
                
                if created_count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully created {created_count} new vehicle users'
                        )
                    )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating users: {str(e)}')
            )