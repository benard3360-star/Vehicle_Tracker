from django.core.management.base import BaseCommand
from main_app.models import CustomUser
import secrets
import string

class Command(BaseCommand):
    help = 'Set passwords for existing vehicle users'

    def generate_password(self, length=8):
        """Generate a simple password"""
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))

    def handle(self, *args, **options):
        try:
            # Get all employee users without temp_password
            users_without_password = CustomUser.objects.filter(
                role='employee',
                temp_password__isnull=True
            ) | CustomUser.objects.filter(
                role='employee',
                temp_password=''
            )
            
            count = users_without_password.count()
            self.stdout.write(f"Found {count} users without passwords")
            
            updated_count = 0
            for user in users_without_password:
                password = self.generate_password()
                user.temp_password = password
                user.set_password(password)
                user.force_password_change = True
                user.save()
                updated_count += 1
                
                if updated_count % 100 == 0:
                    self.stdout.write(f"Updated {updated_count}/{count} users... ({updated_count/count*100:.1f}%)")
                    self.stdout.flush()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully set passwords for {updated_count} users'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error setting passwords: {str(e)}')
            )