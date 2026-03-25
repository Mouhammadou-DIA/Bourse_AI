from django.apps import AppConfig


class BourseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name  = 'bourse'
    label = 'bourse'

    def ready(self):
        import bourse.models  # noqa — active les signaux
