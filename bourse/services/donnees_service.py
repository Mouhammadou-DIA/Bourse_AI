import yfinance as yf
from django.core.cache import cache
from ..models import Action, DonneeHistorique


def importer_historique(symbole, periode='1y'):
    """Télécharge l'historique OHLCV et sauvegarde en base."""
    ticker = yf.Ticker(symbole)
    info   = ticker.info
    df     = ticker.history(period=periode)

    if df.empty:
        return 0

    action, _ = Action.objects.get_or_create(
        symbole=symbole.upper(),
        defaults={
            'nom':          info.get('longName',      symbole),
            'secteur':      info.get('sector',        ''),
            'place_bourse': info.get('exchange',      'NASDAQ'),
            'devise':       info.get('currency',      'USD'),
        }
    )

    created = 0
    for date, row in df.iterrows():
        _, is_new = DonneeHistorique.objects.update_or_create(
            action=action,
            date=date.date(),
            defaults={
                'ouverture':       round(float(row['Open']),   4),
                'plus_haut':       round(float(row['High']),   4),
                'plus_bas':        round(float(row['Low']),    4),
                'cloture':         round(float(row['Close']),  4),
                'volume':          int(row['Volume']),
                'cloture_ajustee': round(float(row['Close']),  4),
            }
        )
        if is_new:
            created += 1

    return created


def get_prix_actuel(symbole):
    """Retourne le prix actuel — yfinance en priorité, fallback base de données."""
    # Essayer yfinance directement (plus fiable qu'Upstash pour les petites données)
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbole)
        prix   = ticker.fast_info.last_price
        if prix and float(prix) > 0:
            return round(float(prix), 2)
    except Exception:
        pass

    # Fallback : dernière clôture en base
    try:
        from ..models import DonneeHistorique
        derniere = DonneeHistorique.objects.filter(
            action__symbole=symbole
        ).order_by('-date').first()
        if derniere:
            return round(float(derniere.cloture), 2)
    except Exception:
        pass

    return None

def get_infos_action(symbole):
    """Retourne les données fondamentales d'une action."""
    cle    = f'infos_{symbole}'
    cached = cache.get(cle)
    if cached:
        return cached

    try:
        ticker = yf.Ticker(symbole)
        info   = ticker.info
        data   = {
            'nom':             info.get('longName', symbole),
            'secteur':         info.get('sector', ''),
            'capitalisation':  info.get('marketCap', 0),
            'pe_ratio':        info.get('trailingPE', None),
            'eps':             info.get('trailingEps', None),
            'dividende':       info.get('dividendYield', None),
            'semaine_haut':    info.get('fiftyTwoWeekHigh', None),
            'semaine_bas':     info.get('fiftyTwoWeekLow', None),
            'volume_moyen':    info.get('averageVolume', None),
            'beta':            info.get('beta', None),
        }
        cache.set(cle, data, timeout=3600)  # 1h
        return data
    except Exception:
        return {}
