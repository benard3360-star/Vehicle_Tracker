from django.core.management.base import BaseCommand
from main_app.models import CustomUser, Organization

class Command(BaseCommand):
    help = 'Delete JKIA Airport organization'

    def handle(self, *args, **options):
        try:
            org = Organization.objects.get(name='JKIA Airport')
            
            # First, reassign or delete users
            users = CustomUser.objects.filter(organization=org)
            self.stdout.write(f'Found {users.count()} users in JKIA Airport')
            
            # Get JKIA organization to reassign users
            jkia_org = Organization.objects.get(name='JKIA')
            
            for user in users:
                if user.role == 'employee':
                    # Reassign vehicle users to JKIA
                    user.organization = jkia_org
                    user.save()
                    self.stdout.write(f'Reassigned {user.username} to JKIA')
                else:
                    # Delete admin users
                    user.delete()
                    self.stdout.write(f'Deleted admin user {user.username}')
            
            # Now delete the organization
            org.delete()
            self.stdout.write('Successfully deleted JKIA Airport organization')
            
            # Show final organizations
            self.stdout.write('\nFinal organizations:')
            for org in Organization.objects.all():
                user_count = CustomUser.objects.filter(organization=org, role='employee').count()
                self.stdout.write(f'- {org.name}: {user_count} users')
                
        except Exception as e:
            self.stdout.write(f'Error: {str(e)}')