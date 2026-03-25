import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('plateforme_bourse')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Déclarer les tâches explicitement
app.autodiscover_tasks([
    'bourse.tasks.import_donnees',
    'bourse.tasks.calcul_indicateurs',
    'bourse.tasks.check_alertes',
    'bourse.tasks.flux_websocket',
])