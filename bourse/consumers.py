import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache


class PrixConsumer(AsyncWebsocketConsumer):
    """
    WebSocket par action individuelle.
    URL : ws://<host>/ws/prix/AAPL/
    """

    async def connect(self):
        self.symbole    = self.scope['url_route']['kwargs']['symbole'].upper()
        self.group_name = f'prix_{self.symbole}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Envoyer le dernier prix connu immédiatement depuis Redis
        prix = cache.get(f'prix_{self.symbole}')
        if prix:
            await self.send(text_data=json.dumps({
                'type':    'prix',
                'symbole': self.symbole,
                'prix':    prix,
                'source':  'cache',
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Le client peut demander un refresh manuel
        data = json.loads(text_data)
        if data.get('action') == 'refresh':
            prix = cache.get(f'prix_{self.symbole}')
            if prix:
                await self.send(text_data=json.dumps({
                    'type':    'prix',
                    'symbole': self.symbole,
                    'prix':    prix,
                }))

    async def prix_update(self, event):
        """Reçoit un message du Channel Layer publié par Celery."""
        await self.send(text_data=json.dumps({
            'type':      'prix',
            'symbole':   event['symbole'],
            'prix':      event['prix'],
            'variation': event.get('variation', 0),
            'volume':    event.get('volume', 0),
            'timestamp': event.get('timestamp'),
        }))


class WatchlistConsumer(AsyncWebsocketConsumer):
    """
    WebSocket global pour la watchlist complète.
    URL : ws://<host>/ws/watchlist/
    Un seul WebSocket suffit pour toutes les actions de la watchlist.
    """

    async def connect(self):
        await self.channel_layer.group_add('watchlist', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('watchlist', self.channel_name)

    async def prix_update(self, event):
        await self.send(text_data=json.dumps({
            'type':      'prix',
            'symbole':   event['symbole'],
            'prix':      event['prix'],
            'variation': event.get('variation', 0),
            'volume':    event.get('volume', 0),
            'timestamp': event.get('timestamp'),
        }))
