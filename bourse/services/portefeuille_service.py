import numpy as np
from .donnees_service import get_prix_actuel


def mettre_a_jour_positions(portefeuille):
    """Met à jour valeur_actuelle et plus_moins_value de chaque position."""
    for pos in portefeuille.positions.select_related('action').all():
        if float(pos.quantite_detenue) <= 0:
            continue
        prix = get_prix_actuel(pos.action.symbole)
        if prix:
            valeur           = prix * float(pos.quantite_detenue)
            pmu              = float(pos.prix_moyen_achat)
            pos.valeur_actuelle  = round(valeur, 2)
            pos.plus_moins_value = round((prix - pmu) * float(pos.quantite_detenue), 2)
            pos.save(update_fields=['valeur_actuelle', 'plus_moins_value', 'mis_a_jour'])


def calculer_metriques(portefeuille):
    """Calcule rendement, volatilité et ratio de Sharpe du portefeuille."""
    positions = portefeuille.positions.filter(quantite_detenue__gt=0).select_related('action')

    valeur_totale   = float(portefeuille.solde_cash)
    valeur_investie = 0
    rendements      = []

    for pos in positions:
        prix = get_prix_actuel(pos.action.symbole)
        if not prix:
            continue
        valeur        = prix * float(pos.quantite_detenue)
        pmu           = float(pos.prix_moyen_achat)
        investissement= pmu * float(pos.quantite_detenue)
        rend          = ((prix - pmu) / pmu) * 100 if pmu > 0 else 0

        valeur_totale   += valeur
        valeur_investie += investissement
        rendements.append(rend)

    if not rendements:
        return {
            'valeur_totale':    round(valeur_totale, 2),
            'valeur_investie':  0,
            'plus_value_totale':0,
            'rendement_moyen':  0,
            'volatilite':       0,
            'ratio_sharpe':     0,
            'nb_positions':     0,
        }

    rend_array      = np.array(rendements)
    volatilite      = round(float(np.std(rend_array)), 4)
    rendement_moyen = round(float(np.mean(rend_array)), 4)
    taux_sans_risque= 2.0
    ratio_sharpe    = round((rendement_moyen - taux_sans_risque) / volatilite, 3) if volatilite > 0 else 0
    plus_value      = round(valeur_totale - valeur_investie - float(portefeuille.solde_cash), 2)

    return {
        'valeur_totale':    round(valeur_totale, 2),
        'valeur_investie':  round(valeur_investie, 2),
        'plus_value_totale':plus_value,
        'rendement_moyen':  rendement_moyen,
        'volatilite':       volatilite,
        'ratio_sharpe':     ratio_sharpe,
        'nb_positions':     len(rendements),
    }


def enregistrer_transaction(portefeuille, action, type_op, quantite, prix, frais=0):
    """Enregistre une transaction et met à jour la position et le solde."""
    from ..models import Transaction, Position

    quantite = float(quantite)
    prix     = float(prix)
    frais    = float(frais) if frais else 0

    # Créer la transaction
    Transaction.objects.create(
        portefeuille  = portefeuille,
        action        = action,
        type_op       = type_op,
        quantite      = quantite,
        prix_unitaire = prix,
        frais         = frais,
    )

    # Récupérer ou créer la position
    pos, _ = Position.objects.get_or_create(
        portefeuille = portefeuille,
        action       = action,
        defaults     = {'quantite_detenue': 0, 'prix_moyen_achat': 0}
    )

    q_avant = float(pos.quantite_detenue)
    pmu     = float(pos.prix_moyen_achat)

    if type_op == 'ACHAT':
        # Calculer nouveau PRU
        total_avant = q_avant * pmu
        total_achat = quantite * prix
        nouvelle_qte = q_avant + quantite
        pmu_new = (total_avant + total_achat) / nouvelle_qte if nouvelle_qte > 0 else prix

        pos.quantite_detenue = round(nouvelle_qte, 4)
        pos.prix_moyen_achat = round(pmu_new, 4)

        # Débiter le cash
        montant = quantite * prix + frais
        portefeuille.solde_cash = float(portefeuille.solde_cash) - montant

    elif type_op == 'VENTE':
        nouvelle_qte = max(0, q_avant - quantite)
        pos.quantite_detenue = round(nouvelle_qte, 4)

        # Créditer le cash
        montant = quantite * prix - frais
        portefeuille.solde_cash = float(portefeuille.solde_cash) + montant

    # Sauvegarder
    pos.save()
    portefeuille.save()
    return pos