from django.core.management.base import BaseCommand
from main_app.models import CustomUser

class Command(BaseCommand):
    help = 'Check password assignment progress'

    def handle(self, *args, **options):
        try:
            total_users = CustomUser.objects.filter(role='employee').count()
            users_with_password = CustomUser.objects.filter(
                role='employee'
            ).exclude(temp_password__isnull=True).exclude(temp_password='').count()
            
            percentage = (users_with_password / total_users * 100) if total_users > 0 else 0
            remaining = total_users - users_with_password
            
            self.stdout.write(f"Password Assignment Progress:")
            self.stdout.write(f"✅ Completed: {users_with_password:,} users")
            self.stdout.write(f"⏳ Remaining: {remaining:,} users")
            self.stdout.write(f"📊 Progress: {percentage:.1f}%")
            
            if percentage >= 100:
                self.stdout.write(self.style.SUCCESS("🎉 All passwords have been set!"))
            else:
                self.stdout.write(f"⏱️  Estimated remaining: ~{remaining//100} minutes")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error checking progress: {str(e)}')
            )