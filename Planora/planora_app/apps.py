from django.apps import AppConfig


class PlanoraAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'planora_app'

class ProjectManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'planora_app'

    def ready(self):
        import planora_app.signals  # Import the signals
