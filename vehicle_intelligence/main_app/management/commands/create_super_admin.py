from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from main_app.models import Organization

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a super admin user'

    def handle(self, *args, **options):
        # Create a default organization if none exists
        organization, created = Organization.objects.get_or_create(
            name='System Administration',
            defaults={
                'slug': 'system-admin',
                'email': 'admin@system.local',
                'is_active': True
            }
        )
        
        # Create super admin user
        if not User.objects.filter(username='superadmin').exists():
            user = User.objects.create_superuser(
                username='superadmin',
                email='admin@vehicleintelligence.com',
                password='Admin@123',
                role='super_admin',
                organization=organization,
                first_name='Super',
                last_name='Admin',
                is_verified=True,
                force_password_change=True
            )
            self.stdout.write(self.style.SUCCESS('Super admin user created successfully!'))
            self.stdout.write(f'Username: superadmin')
            self.stdout.write(f'Password: Admin@123')
            self.stdout.write(self.style.WARNING('Please change the password after first login!'))
        else:
            self.stdout.write(self.style.WARNING('Super admin user already exists!'))