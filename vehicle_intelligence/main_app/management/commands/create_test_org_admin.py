from django.core.management.base import BaseCommand
from main_app.models import CustomUser, Organization
import secrets
import string

class Command(BaseCommand):
    help = 'Create a test organization admin for JKIA'

    def generate_password(self, length=8):
        """Generate a simple password"""
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))

    def handle(self, *args, **options):
        try:
            # Get or create JKIA organization
            jkia_org, created = Organization.objects.get_or_create(
                name='JKIA Airport',
                defaults={
                    'slug': 'jkia-airport',
                    'email': 'admin@jkia.com',
                    'is_active': True
                }
            )
            
            # Create or update organization admin
            username = 'jkia_admin'
            password = 'admin123'
            
            # Delete existing user if exists
            CustomUser.objects.filter(username=username).delete()
            
            # Create new admin
            admin_user = CustomUser.objects.create_user(
                username=username,
                email='jkia_admin@jkia.com',
                password=password,
                first_name='JKIA',
                last_name='Administrator',
                role='organization_admin',
                organization=jkia_org,
                is_active=True,
                temp_password=password,
                force_password_change=False  # Don't force password change for testing
            )
            
            # Update organization admin reference
            jkia_org.admin_user = admin_user
            jkia_org.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created organization admin:\n'
                    f'Username: {username}\n'
                    f'Password: {password}\n'
                    f'Organization: {jkia_org.name}\n'
                    f'URL: /org-admin/user-credentials/'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating admin: {str(e)}')
            )