from django.apps import AppConfig
from django.apps import AppConfig

class MainAppConfig(AppConfig):
    name = 'main_app'

# apps.py


class YourAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'your_app'
    
    def ready(self):
        import main_app.signals