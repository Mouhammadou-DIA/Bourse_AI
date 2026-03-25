import json
import time
import websocket
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.conf import settings

channel_layer = get_channel_layer()

SYMBOLES_PAR_DEFAUT = ['AAPL', 'GOOGL', 'TSLA', 'NVDA', 'MSFT', 'META', 'AMZN', 'BTC-USD']


def on_message(ws, message):
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return

    if data.get('type') != 'trade':
        return

    for trade in data.get('data', []):
        symbole = trade.get('s', '').replace('BINANCE:', '')
        prix    = trade.get('p')
        volume  = trade.get('v', 0)

        if not symbole or not prix:
            continue

        prix = round(float(prix), 2)

        # Calculer la variation vs prix précédent
        ancien = cache.get(f'prix_{symbole}')
        variation = 0
        if ancien:
            try:
                ancien_float = float(ancien)
                if ancien_float > 0:
                    variation = round(((prix - ancien_float) / ancien_float) * 100, 4)
            except (ValueError, TypeError):
                pass

        # Stocker dans Redis
        cache.set(f'prix_{symbole}', prix, timeout=15)

        payload = {
            'type':      'prix_update',
            'symbole':   symbole,
            'prix':      prix,
            'variation': variation,
            'volume':    int(volume),
            'timestamp': trade.get('t'),
        }

        try:
            # Publier aux abonnés de ce symbole
            async_to_sync(channel_layer.group_send)(f'prix_{symbole}', payload)
            # Publier à la watchlist globale
            async_to_sync(channel_layer.group_send)('watchlist', payload)
        except Exception as e:
            print(f'[WS] Erreur channel_layer : {e}')


def on_error(ws, error):
    print(f'[Finnhub WS] Erreur : {error}')


def on_close(ws, close_status_code, close_msg):
    print(f'[Finnhub WS] Connexion fermée ({close_status_code}) — reconnexion dans 5s')


def on_open(ws, symboles=None):
    symboles = symboles or SYMBOLES_PAR_DEFAUT
    print(f'[Finnhub WS] Connexion ouverte — abonnement à {symboles}')
    for sym in symboles:
        ws.send(json.dumps({'type': 'subscribe', 'symbol': sym}))


def demarrer_flux(symboles=None):
    """Lance le WebSocket Finnhub avec reconnexion automatique."""
    token = settings.FINNHUB_API_KEY
    if not token:
        print('[Finnhub WS] FINNHUB_API_KEY manquante dans .env !')
        return

    url = f'wss://ws.finnhub.io?token={token}'

    while True:
        try:
            ws = websocket.WebSocketApp(
                url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=lambda ws_inst: on_open(ws_inst, symboles),
            )
            ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as e:
            print(f'[Finnhub WS] Exception : {e}')
        print('[Finnhub WS] Reconnexion dans 5s...')
        time.sleep(5)
