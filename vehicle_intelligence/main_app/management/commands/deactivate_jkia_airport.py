from django.core.management.base import BaseCommand
from main_app.models import Organization

class Command(BaseCommand):
    help = 'Deactivate JKIA Airport organization'

    def handle(self, *args, **options):
        try:
            org = Organization.objects.get(name='JKIA Airport')
            org.is_active = False
            org.save()
            self.stdout.write('Deactivated JKIA Airport organization')
            
            # Show active organizations only
            self.stdout.write('\nActive organizations:')
            for org in Organization.objects.filter(is_active=True):
                from main_app.models import CustomUser
                user_count = CustomUser.objects.filter(organization=org, role='employee').count()
                self.stdout.write(f'- {org.name}: {user_count} users')
                
        except Exception as e:
            self.stdout.write(f'Error: {str(e)}')