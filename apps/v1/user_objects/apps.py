from django.apps import AppConfig


class UserObjectsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.v1.user_objects'
    
    def ready(self):
        print(f"[DEBUG] ========== UserObjectsConfig.ready() called ==========")
        print(f"[DEBUG] Importing signals...")
        import apps.v1.user_objects.signals
        print(f"[DEBUG] Signals imported successfully")
        print(f"[DEBUG] ========== UserObjectsConfig.ready() finished ==========")