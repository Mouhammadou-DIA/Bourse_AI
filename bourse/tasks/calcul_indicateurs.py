from celery import shared_task
from ..models import Action
from ..services.indicateurs_service import calculer_et_sauvegarder


@shared_task(name='bourse.tasks.calcul_indicateurs.calculer_tous_indicateurs')
def calculer_tous_indicateurs():
    """Recalcule RSI, MACD, Bollinger pour toutes les actions actives."""
    actions = Action.objects.filter(actif=True)
    resultats = {}
    for action in actions:
        try:
            nb = calculer_et_sauvegarder(action)
            resultats[action.symbole] = f'{nb} jours calculés'
        except Exception as e:
            resultats[action.symbole] = f'Erreur: {str(e)}'
    return resultats


@shared_task(name='bourse.tasks.calcul_indicateurs.calculer_indicateurs_action')
def calculer_indicateurs_action(symbole):
    """Calcule les indicateurs pour une seule action."""
    try:
        action = Action.objects.get(symbole=symbole)
        nb = calculer_et_sauvegarder(action)
        return f'{symbole}: {nb} jours calculés'
    except Action.DoesNotExist:
        return f'{symbole}: action introuvable'
    except Exception as e:
        return f'{symbole}: Erreur — {str(e)}'
