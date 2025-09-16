from django.apps import AppConfig


class AdminSectionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_section'

    def ready(self):
        import admin_section.signals  # Import signals to register them
