# BourseAI — Plateforme d'Analyse Boursière
**Groupe 2 · Django + Channels + Celery + WebSocket Finnhub**

---

## Structure du projet

```
plateforme_bourse/
├── config/
│   ├── __init__.py          ← importe celery_app
│   ├── settings.py          ← configuration principale
│   ├── urls.py              ← routes racine
│   ├── asgi.py              ← ASGI + Django Channels
│   └── celery.py            ← configuration Celery
│
├── bourse/
│   ├── models.py            ← Action, Portefeuille, Alerte, etc.
│   ├── views.py             ← toutes les vues + API JSON
│   ├── urls.py              ← routes de l'application
│   ├── forms.py             ← formulaires Django
│   ├── admin.py             ← interface admin
│   ├── consumers.py         ← WebSocket consumers (Channels)
│   ├── routing.py           ← routes WebSocket
│   ├── apps.py              ← AppConfig + signaux
│   │
│   ├── services/
│   │   ├── donnees_service.py       ← import yfinance, prix actuel
│   │   ├── indicateurs_service.py   ← RSI, MACD, Bollinger, ATR
│   │   ├── portefeuille_service.py  ← métriques, transactions
│   │   ├── telegram_service.py      ← envoi alertes Telegram
│   │   └── websocket_finnhub.py     ← flux WebSocket Finnhub
│   │
│   ├── tasks/
│   │   ├── import_donnees.py        ← Celery : import historique
│   │   ├── calcul_indicateurs.py    ← Celery : recalcul RSI/MACD
│   │   ├── check_alertes.py         ← Celery : vérification alertes
│   │   └── flux_websocket.py        ← Celery : tâche WS longue durée
│   │
│   ├── templates/bourse/
│   │   ├── base.html            ← layout + WebSocket global
│   │   ├── dashboard.html
│   │   ├── action_detail.html   ← graphiques Plotly
│   │   ├── portefeuille.html
│   │   ├── alertes.html
│   │   ├── transaction.html
│   │   ├── telegram.html
│   │   ├── liste_actions.html
│   │   └── login.html
│   │
│   ├── static/bourse/
│   │   ├── css/style.css        ← thème dark complet
│   │   └── js/main.js           ← WebSocket fallback + utils
│   │
│   └── tests/
│       ├── test_indicateurs.py  ← tests RSI, MACD, Bollinger
│       ├── test_alertes.py      ← tests logique alertes
│       └── test_portefeuille.py ← tests transactions
│
├── docker/
│   └── docker-compose.yml       ← PostgreSQL + Redis + tous les services
├── Dockerfile
├── manage.py
├── requirements.txt
└── .env.example
```

---

## Installation rapide

### 1. Cloner et configurer l'environnement

```bash
git clone <url-du-repo>
cd plateforme_bourse

python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
# Éditer .env avec vos vraies valeurs :
# - SECRET_KEY, DB_PASSWORD
# - FINNHUB_API_KEY  (sur finnhub.io → gratuit)
# - TELEGRAM_BOT_TOKEN (via @BotFather sur Telegram)
```

### 3. Créer la base de données

```bash
createdb bourse_db        # PostgreSQL doit être installé
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 4. Lancer tous les services (4 terminaux)

```bash
# Terminal 1 — Serveur ASGI (obligatoire pour WebSocket)
daphne config.asgi:application --port 8000

# Terminal 2 — Worker Celery
celery -A config worker --loglevel=info

# Terminal 3 — Scheduler Celery Beat
celery -A config beat --loglevel=info

# Terminal 4 — Flux WebSocket Finnhub (temps réel)
python manage.py shell -c "
from bourse.tasks.flux_websocket import demarrer_flux_finnhub
demarrer_flux_finnhub.delay()
"
```

### 5. Importer les premières données

```bash
python manage.py shell
```
```python
from bourse.services.donnees_service import importer_historique
from bourse.services.indicateurs_service import calculer_et_sauvegarder
from bourse.models import Action

# Importer l'historique de plusieurs actions
for sym in ['AAPL', 'GOOGL', 'TSLA', 'NVDA', 'MSFT', 'META']:
    nb = importer_historique(sym, periode='1y')
    print(f'{sym}: {nb} lignes')

# Calculer les indicateurs
for action in Action.objects.all():
    nb = calculer_et_sauvegarder(action)
    print(f'{action.symbole}: {nb} jours calculés')
```

### 6. Configurer Telegram (optionnel)

1. Aller sur Telegram → chercher **@BotFather**
2. Taper `/newbot` → suivre les instructions → copier le token
3. Mettre le token dans `.env` : `TELEGRAM_BOT_TOKEN=...`
4. Dans l'application : **Menu → Telegram** → entrer votre Chat ID

---

## Lancement via Docker (tout-en-un)

```bash
cd docker
docker compose up --build
```

Cela lance automatiquement : PostgreSQL, Redis, Django (daphne), Celery worker, Celery beat, et le flux WebSocket Finnhub.

---

## Lancer les tests

```bash
python manage.py test bourse.tests
```

---

## Architecture WebSocket temps réel

```
Finnhub wss:// ──► Celery Worker ──► Redis Channel Layer ──► Django Channels ──► Navigateur JS
                   (flux continu)    (bus de messages)       (consumers)         (WebSocket)
```

- **Finnhub** envoie les ticks boursiers en continu via WebSocket
- **Celery** reçoit chaque tick, le met en cache Redis (TTL 15s) et le publie dans le Channel Layer
- **Django Channels** redistribue les ticks à tous les navigateurs connectés
- **JavaScript** (base.html) reçoit chaque tick et met à jour les prix à l'écran sans rechargement
- **Fallback** : si le WebSocket n'est pas disponible, un polling AJAX toutes les 30s prend le relais

---

## APIs disponibles

| URL | Méthode | Description |
|-----|---------|-------------|
| `/api/prix/<symbole>/` | GET | Prix actuel d'une action |
| `/api/watchlist/` | GET | Prix de toutes les actions |
| `/api/portefeuille/positions/` | GET | Positions du portefeuille |
| `/ws/prix/<symbole>/` | WS | Flux live pour une action |
| `/ws/watchlist/` | WS | Flux live watchlist complète |
