from django.core.management.base import BaseCommand
from main_app.models import CustomUser, Organization

class Command(BaseCommand):
    help = 'Create JKIA admin for the correct JKIA organization'

    def handle(self, *args, **options):
        try:
            # Get JKIA organization (not JKIA Airport)
            jkia_org = Organization.objects.get(name='JKIA')
            
            # Create JKIA admin
            username = 'jkia_admin_new'
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
                force_password_change=False
            )
            
            # Update organization admin reference
            jkia_org.admin_user = admin_user
            jkia_org.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created JKIA admin:\n'
                    f'Username: {username}\n'
                    f'Password: {password}\n'
                    f'Organization: {jkia_org.name}\n'
                    f'Vehicle Users: {CustomUser.objects.filter(organization=jkia_org, role="employee").count()}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating JKIA admin: {str(e)}')
            )