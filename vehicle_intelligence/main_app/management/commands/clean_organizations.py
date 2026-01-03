from django.core.management.base import BaseCommand
from main_app.models import CustomUser, Organization

class Command(BaseCommand):
    help = 'Delete unwanted organizations'

    def handle(self, *args, **options):
        try:
            # Organizations to delete
            orgs_to_delete = ['KNH Hospital', 'JKIA Airport']
            
            for org_name in orgs_to_delete:
                try:
                    org = Organization.objects.get(name=org_name)
                    users = CustomUser.objects.filter(organization=org)
                    user_count = users.count()
                    
                    self.stdout.write(f'Deleting {org_name}: {user_count} users')
                    users.delete()
                    org.delete()
                    self.stdout.write(f'Deleted {org_name}')
                    
                except Organization.DoesNotExist:
                    self.stdout.write(f'{org_name} not found')
            
            # Show remaining organizations
            self.stdout.write('\nRemaining organizations:')
            for org in Organization.objects.all():
                user_count = CustomUser.objects.filter(organization=org, role='employee').count()
                self.stdout.write(f'- {org.name}: {user_count} users')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error cleaning organizations: {str(e)}')
            )