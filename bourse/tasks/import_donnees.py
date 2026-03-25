from celery import shared_task
from ..models import Action
from ..services.donnees_service import importer_historique


@shared_task(name='bourse.tasks.import_donnees.importer_toutes_actions')
def importer_toutes_actions():
    """Importe les 5 derniers jours pour toutes les actions actives."""
    actions = Action.objects.filter(actif=True)
    resultats = {}
    for action in actions:
        try:
            nb = importer_historique(action.symbole, periode='5d')
            resultats[action.symbole] = f'{nb} nouvelles lignes'
        except Exception as e:
            resultats[action.symbole] = f'Erreur: {str(e)}'
    return resultats


@shared_task(name='bourse.tasks.import_donnees.importer_action')
def importer_action(symbole, periode='1y'):
    """Importe l'historique d'une seule action (lancement manuel)."""
    try:
        nb = importer_historique(symbole, periode)
        return f'{symbole}: {nb} lignes importées'
    except Exception as e:
        return f'{symbole}: Erreur — {str(e)}'
