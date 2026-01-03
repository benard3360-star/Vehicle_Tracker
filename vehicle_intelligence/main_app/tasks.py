from celery import shared_task
from django.core.management import call_command

@shared_task
def update_parking_data():
    """Scheduled task to update parking data every 5 minutes"""
    call_command('load_excel_data')
    return "Data updated successfully"

# Add to settings.py:
# CELERY_BEAT_SCHEDULE = {
#     'update-parking-data': {
#         'task': 'main_app.tasks.update_parking_data',
#         'schedule': 300.0,  # Every 5 minutes
#     },
# }