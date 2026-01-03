from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.core.management import call_command
from django.db import connection
import logging

logger = logging.getLogger(__name__)

@receiver(post_migrate)
def create_vehicle_users_on_startup(sender, **kwargs):
    """Automatically create users from vehicle data on server startup"""
    if sender.name == 'main_app':
        try:
            logger.info("Auto-creating vehicle users on startup...")
            call_command('create_vehicle_users')
            logger.info("Vehicle users creation completed")
        except Exception as e:
            logger.error(f"Error creating vehicle users: {e}")

def sync_vehicle_users():
    """Function to sync vehicle users - can be called anytime"""
    try:
        from django.core.management import call_command
        call_command('create_vehicle_users')
        return True
    except Exception as e:
        logger.error(f"Error syncing vehicle users: {e}")
        return False