from django.core.management.base import BaseCommand
from main_app.models import CustomUser, Organization

class Command(BaseCommand):
    help = 'Create KNH admin for testing'

    def handle(self, *args, **options):
        try:
            # Get KNH organization
            knh_org = Organization.objects.get(name='KNH')
            
            # Create KNH admin
            username = 'knh_admin'
            password = 'admin123'
            
            # Delete existing user if exists
            CustomUser.objects.filter(username=username).delete()
            
            # Create new admin
            admin_user = CustomUser.objects.create_user(
                username=username,
                email='knh_admin@knh.com',
                password=password,
                first_name='KNH',
                last_name='Administrator',
                role='organization_admin',
                organization=knh_org,
                is_active=True,
                temp_password=password,
                force_password_change=False
            )
            
            # Update organization admin reference
            knh_org.admin_user = admin_user
            knh_org.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created KNH admin:\n'
                    f'Username: {username}\n'
                    f'Password: {password}\n'
                    f'Organization: {knh_org.name}\n'
                    f'Vehicle Users: {CustomUser.objects.filter(organization=knh_org, role="employee").count()}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating KNH admin: {str(e)}')
            )