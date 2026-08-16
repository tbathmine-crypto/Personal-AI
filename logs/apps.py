from django.apps import AppConfig
import sys

class LogsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'logs'

    def ready(self):
        # Only start background scheduler when running web server (avoiding duplicate triggers during migrations/commands)
        if 'runserver' in sys.argv:
            try:
                from logs.utils.scheduler import start_scheduler_thread
                start_scheduler_thread()
            except Exception as e:
                print(f"Scheduler startup warning: {e}")

