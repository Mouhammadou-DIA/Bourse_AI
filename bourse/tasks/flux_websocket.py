from celery import shared_task
from ..services.websocket_finnhub import demarrer_flux


@shared_task(
    bind=True,
    max_retries=None,
    name='bourse.tasks.flux_websocket.demarrer_flux_finnhub',
    ignore_result=True,
)
def demarrer_flux_finnhub(self, symboles=None):
    """
    Tâche Celery longue durée.
    Lance le flux WebSocket Finnhub et tourne indéfiniment.
    Reconnexion automatique intégrée dans demarrer_flux().

    Lancement : from bourse.tasks.flux_websocket import demarrer_flux_finnhub
                demarrer_flux_finnhub.delay()
    """
    demarrer_flux(symboles=symboles)
