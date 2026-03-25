from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/prix/(?P<symbole>[A-Z0-9\-\.]+)/$', consumers.PrixConsumer.as_asgi()),
    re_path(r'ws/watchlist/$',                        consumers.WatchlistConsumer.as_asgi()),
]
