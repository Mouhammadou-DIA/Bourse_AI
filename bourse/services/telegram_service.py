import requests
from django.conf import settings

TELEGRAM_API = f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}'


def send_alert(chat_id, message):
    """Envoie un message Telegram formaté en HTML."""
    if not chat_id or not settings.TELEGRAM_BOT_TOKEN:
        return False
    try:
        resp = requests.post(
            f'{TELEGRAM_API}/sendMessage',
            json={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'},
            timeout=10
        )
        return resp.ok
    except Exception as e:
        print(f'[Telegram] Erreur envoi : {e}')
        return False


def get_updates():
    """Récupère les derniers messages reçus par le bot."""
    try:
        resp = requests.get(f'{TELEGRAM_API}/getUpdates', timeout=10)
        return resp.json().get('result', [])
    except Exception:
        return []


def recuperer_chat_id(username_ou_token):
    """
    Récupère le chat_id d'un utilisateur qui a envoyé /start au bot.
    À appeler depuis la vue de liaison Telegram.
    """
    updates = get_updates()
    for update in reversed(updates):
        msg = update.get('message', {})
        if msg.get('text') == '/start':
            return str(msg['chat']['id'])
    return None


def formater_alerte(symbole, prix, type_alerte, seuil=None, message_perso=''):
    """Construit le message Telegram d'une alerte."""
    direction = '▲' if 'HAUT' in type_alerte or type_alerte == 'MACD' else '▼'
    msg = (
        f'{direction} <b>Alerte BourseAI — {symbole}</b>\n'
        f'Prix actuel : <b>{prix:.2f} USD</b>\n'
    )
    if seuil:
        msg += f'Seuil atteint : {float(seuil):.2f} USD\n'
    if message_perso:
        msg += f'\n{message_perso}'
    return msg
