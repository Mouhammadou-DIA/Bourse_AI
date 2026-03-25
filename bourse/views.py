import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import JsonResponse
from django.core.cache import cache
from django.views.decorators.http import require_POST

from .models import Action, DonneeHistorique, Portefeuille, Alerte, IndicateurCache, Position, UserProfile
from .forms import AlerteForm, TransactionForm, ActionRechercheForm, TelegramLiaisonForm
from .services import donnees_service, indicateurs_service, portefeuille_service
from .services.telegram_service import recuperer_chat_id
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm

def accueil(request):
    """Page d'accueil publique — redirige vers dashboard si déjà connecté."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'bourse/accueil.html')


def inscription(request):
    """Page d'inscription."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    from .forms import InscriptionForm
    form = InscriptionForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        # Connecter automatiquement après inscription
        login(request, user)
        messages.success(request, f'Bienvenue {user.username} ! Votre compte a été créé.')
        return redirect('dashboard')

    return render(request, 'bourse/inscription.html', {'form': form})

# ── DASHBOARD ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    # S'assurer que le profil existe (pour les anciens utilisateurs)
    if not hasattr(request.user, 'profile'):
        UserProfile.objects.create(user=request.user)
        request.user.refresh_from_db()

    portefeuille   = Portefeuille.objects.filter(user=request.user).first()
    actions        = Action.objects.filter(actif=True).order_by('symbole')
    alertes_actives= Alerte.objects.filter(user=request.user, active=True)[:5]

    metriques = {}
    if portefeuille:
        metriques = portefeuille_service.calculer_metriques(portefeuille)

    # Watchlist avec prix, variation et signal
    watchlist = []
    for action in actions[:10]:
        prix = cache.get(f'prix_{action.symbole}')
        if not prix:
            prix = donnees_service.get_prix_actuel(action.symbole)

        # Variation vs clôture précédente
        variation = None
        try:
            historique = DonneeHistorique.objects.filter(
                action=action
            ).order_by('-date')[:2]
            if len(historique) >= 2 and prix:
                cloture_hier = float(historique[1].cloture)
                if cloture_hier > 0:
                    variation = round(
                        ((float(prix) - cloture_hier) / cloture_hier) * 100, 2
                    )
        except Exception:
            pass

        # Signal depuis le cache des indicateurs
        indic = IndicateurCache.objects.filter(
            action=action
        ).order_by('-date').first()
        signal = indicateurs_service.get_signal_global(indic)

        watchlist.append({
            'action':    action,
            'prix':      prix,
            'variation': variation,
            'signal':    signal,
            'indic':     indic,
        })

    context = {
        'portefeuille':    portefeuille,
        'metriques':       metriques,
        'watchlist':       watchlist,
        'alertes_actives': alertes_actives,
        'nb_alertes':      alertes_actives.count(),
        'form_recherche':  ActionRechercheForm(),
    }
    return render(request, 'bourse/dashboard.html', context)



@login_required
def profil(request):
    profile = request.user.profile
    pf      = Portefeuille.objects.filter(user=request.user).first()
    metriques = {}
    if pf:
        metriques = portefeuille_service.calculer_metriques(pf)

    from .forms import UserProfileForm
    form = UserProfileForm(request.POST or None, request.FILES or None, instance=profile)

    if request.method == 'POST' and form.is_valid():
        form.save()
        # Mettre à jour l'email si fourni
        email = request.POST.get('email', '').strip()
        if email:
            request.user.email = email
            request.user.save(update_fields=['email'])
        messages.success(request, 'Profil mis à jour avec succès !')
        return redirect('profil')

    context = {
        'profile':   profile,
        'form':      form,
        'pf':        pf,
        'metriques': metriques,
        'nb_alertes': Alerte.objects.filter(user=request.user, active=True).count(),
        'nb_transactions': pf.transactions.count() if pf else 0,
        'nb_actions': Action.objects.filter(actif=True).count(),
    }
    return render(request, 'bourse/profil.html', context)

# ── ACTIONS ───────────────────────────────────────────────────────────────────

@login_required
def liste_actions(request):
    form    = ActionRechercheForm(request.GET or None)
    actions = Action.objects.filter(actif=True).order_by('symbole')

    if form.is_valid():
        symbole = form.cleaned_data['symbole']
        if not Action.objects.filter(symbole=symbole).exists():
            try:
                donnees_service.importer_historique(symbole, periode='3mo')
                messages.success(request, f'{symbole} ajouté avec succès.')
            except Exception as e:
                messages.error(request, f'Impossible d\'importer {symbole} : {e}')
        return redirect('detail_action', symbole=symbole)

    # Charger les prix et variations pour chaque action
    watchlist = []
    for action in actions:
        prix = cache.get(f'prix_{action.symbole}')
        if not prix:
            prix = donnees_service.get_prix_actuel(action.symbole)

        variation = None
        try:
            historique = DonneeHistorique.objects.filter(
                action=action
            ).order_by('-date')[:2]
            if len(historique) >= 2 and prix:
                cloture_hier = float(historique[1].cloture)
                if cloture_hier > 0:
                    variation = round(
                        ((float(prix) - cloture_hier) / cloture_hier) * 100, 2
                    )
        except Exception:
            pass

        watchlist.append({
            'action':    action,
            'prix':      prix,
            'variation': variation,
        })

    context = {'actions': actions, 'form': form, 'watchlist': watchlist}
    return render(request, 'bourse/liste_actions.html', context)

@login_required
def detail_action(request, symbole):
    action      = get_object_or_404(Action, symbole=symbole.upper())
    indicateurs = IndicateurCache.objects.filter(action=action).order_by('-date').first()
    infos       = donnees_service.get_infos_action(symbole)
    prix_actuel = donnees_service.get_prix_actuel(symbole) or 0
    signal      = indicateurs_service.get_signal_global(indicateurs)

    # Période demandée (défaut 3 mois)
    periode = request.GET.get('periode', '3mo')

    # Mapping période → paramètres yfinance
    PERIODES = {
        '1h':  {'period': '1d',  'interval': '1m'},
        '1d':  {'period': '5d',  'interval': '5m'},
        '1w':  {'period': '1mo', 'interval': '1h'},
        '1mo': {'period': '1mo', 'interval': '1d'},
        '3mo': {'period': '3mo', 'interval': '1d'},
        '6mo': {'period': '6mo', 'interval': '1d'},
        '1y':  {'period': '1y',  'interval': '1d'},
        'max': {'period': 'max', 'interval': '1wk'},
    }

    params = PERIODES.get(periode, PERIODES['3mo'])

    # Récupérer les données depuis yfinance directement
    import yfinance as yf
    from django.core.cache import cache

    cache_key = f'ohlcv_{symbole}_{periode}'
    ohlcv = cache.get(cache_key)

    if not ohlcv:
        try:
            ticker = yf.Ticker(symbole)
            df = ticker.history(
                period=params['period'],
                interval=params['interval']
            )
            if not df.empty:
                ohlcv = {
                    'dates':  [d.tz_convert('Africa/Dakar').strftime('%Y-%m-%d %H:%M') if hasattr(d, 'tz_convert') and d.tzinfo else str(d) for d in df.index],
                    'open':   [round(float(v), 2) for v in df['Open']],
                    'high':   [round(float(v), 2) for v in df['High']],
                    'low':    [round(float(v), 2) for v in df['Low']],
                    'close':  [round(float(v), 2) for v in df['Close']],
                    'volume': [int(v) for v in df['Volume']],
                }
                # Cache plus court pour les périodes courtes
                ttl = 60 if periode in ('1h', '1d') else 3600
                cache.set(cache_key, ohlcv, timeout=ttl)
        except Exception as e:
            ohlcv = {'dates': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}

    if not ohlcv:
        ohlcv = {'dates': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}

    # Indicateurs depuis la base (pour les périodes journalières)
    indic_data = {}
    if periode not in ('1h', '1d', '1w'):
        indic_qs = IndicateurCache.objects.filter(action=action).order_by('date')
        indic_data = {
            'dates':     [str(i.date) for i in indic_qs],
            'rsi':       [float(i.rsi_14)         if i.rsi_14         else None for i in indic_qs],
            'macd':      [float(i.macd)            if i.macd           else None for i in indic_qs],
            'macd_sig':  [float(i.macd_signal)     if i.macd_signal    else None for i in indic_qs],
            'macd_hist': [float(i.macd_hist)       if i.macd_hist      else None for i in indic_qs],
            'boll_h':    [float(i.bollinger_haut)  if i.bollinger_haut else None for i in indic_qs],
            'boll_b':    [float(i.bollinger_bas)   if i.bollinger_bas  else None for i in indic_qs],
            'sma20':     [float(i.sma_20)          if i.sma_20         else None for i in indic_qs],
            'ema50':     [float(i.ema_50)          if i.ema_50         else None for i in indic_qs],
            'stoch_k':   [float(i.stoch_k)         if i.stoch_k        else None for i in indic_qs],
            'stoch_d':   [float(i.stoch_d)         if i.stoch_d        else None for i in indic_qs],
            'obv':       [int(i.obv)               if i.obv            else None for i in indic_qs],
        }

    alerte_form = AlerteForm(initial={'action': action})

    context = {
        'action':      action,
        'indicateurs': indicateurs,
        'infos':       infos,
        'prix_actuel': prix_actuel,
        'signal':      signal,
        'periode':     periode,
        'ohlcv_json':  json.dumps(ohlcv),
        'indic_json':  json.dumps(indic_data),
        'alerte_form': alerte_form,
    }
    return render(request, 'bourse/action_detail.html', context)

@login_required
def comparer_actions(request):
    symboles = request.GET.getlist('s')[:4]
    data     = []

    for sym in symboles:
        action = Action.objects.filter(symbole=sym).first()
        if not action:
            continue
        hist   = DonneeHistorique.objects.filter(action=action).order_by('date')
        closes = [float(d.cloture)   for d in hist]
        hauts  = [float(d.plus_haut) for d in hist]
        bas    = [float(d.plus_bas)  for d in hist]
        dates  = [str(d.date)        for d in hist]

        variation  = None
        plus_haut  = None
        plus_bas   = None
        volatilite = None

        if len(closes) >= 2:
            import numpy as np
            variation  = round(((closes[-1] - closes[0]) / closes[0]) * 100, 2)
            plus_haut  = round(max(hauts), 2)
            plus_bas   = round(min(bas),   2)
            # Volatilité = écart-type des rendements journaliers annualisé
            rendements = [
                (closes[i] - closes[i-1]) / closes[i-1]
                for i in range(1, len(closes))
            ]
            volatilite = round(float(np.std(rendements)) * (252 ** 0.5) * 100, 2)

        data.append({
            'action':    action,
            'dates':     dates,
            'close':     closes,
            'variation': variation,
            'plus_haut': plus_haut,
            'plus_bas':  plus_bas,
            'volatilite':volatilite,
        })

    data_json = json.dumps([{
        'action': item['action'].symbole,
        'dates':  item['dates'],
        'close':  item['close'],
    } for item in data])

    context = {
        'data':           data,
        'data_json':      data_json,
        'symboles':       symboles,
        'toutes_actions': Action.objects.filter(actif=True).order_by('symbole'),
    }
    return render(request, 'bourse/comparer.html', context)

# ── PORTEFEUILLE ──────────────────────────────────────────────────────────────

@login_required
def portefeuille(request):
    pf = get_object_or_404(Portefeuille, user=request.user)
    portefeuille_service.mettre_a_jour_positions(pf)
    positions  = pf.positions.filter(quantite_detenue__gt=0).select_related('action')
    metriques  = portefeuille_service.calculer_metriques(pf)
    historique = pf.transactions.select_related('action').order_by('-date_transaction')[:20]

    context = {
        'portefeuille': pf,
        'positions':    positions,
        'metriques':    metriques,
        'historique':   historique,
    }
    return render(request, 'bourse/portefeuille.html', context)


@login_required
def ajouter_transaction(request):
    pf   = get_object_or_404(Portefeuille, user=request.user)
    
    # Pré-remplir l'action si passée en GET
    action_symbole = request.GET.get('action', '')
    action_initiale = None
    if action_symbole:
        action_initiale = Action.objects.filter(symbole=action_symbole).first()

    # Pré-remplir le type si passé en GET
    type_op = request.GET.get('type', 'ACHAT')

    form = TransactionForm(
        request.POST or None,
        initial={
            'action':  action_initiale,
            'type_op': type_op,
        }
    )

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        try:
            # Vérifier solde suffisant pour un achat
            if data['type_op'] == 'ACHAT':
                cout = float(data['quantite']) * float(data['prix_unitaire'])
                frais = float(data.get('frais') or 0)
                if cout + frais > float(pf.solde_cash):
                    messages.error(request, f'Solde insuffisant. Disponible : {pf.solde_cash:.2f} $')
                    return render(request, 'bourse/transaction.html', {'form': form, 'portefeuille': pf})

            portefeuille_service.enregistrer_transaction(
                portefeuille = pf,
                action       = data['action'],
                type_op      = data['type_op'],
                quantite     = data['quantite'],
                prix         = data['prix_unitaire'],
                frais        = data.get('frais') or 0,
            )
            messages.success(request, f'Transaction enregistrée avec succès !')
            return redirect('portefeuille')
        except Exception as e:
            messages.error(request, f'Erreur : {e}')

    # Prix actuel pour pré-remplir
    prix_actuel = None
    if action_initiale:
        prix_actuel = donnees_service.get_prix_actuel(action_initiale.symbole)

    context = {
        'form':         form,
        'portefeuille': pf,
        'prix_actuel':  prix_actuel,
        'action_pre':   action_initiale,
    }
    return render(request, 'bourse/transaction.html', context)

# ── ALERTES ───────────────────────────────────────────────────────────────────

@login_required
def mes_alertes(request):
    alertes = Alerte.objects.filter(user=request.user).select_related('action').order_by('-date_creation')
    form    = AlerteForm()

    nb_actives     = alertes.filter(active=True).count()
    nb_declenchees = alertes.filter(active=False, date_declenchement__isnull=False).count()

    context = {
        'alertes':        alertes,
        'form':           form,
        'nb_actives':     nb_actives,
        'nb_declenchees': nb_declenchees,
    }
    return render(request, 'bourse/alertes.html', context)


@login_required
@require_POST
def creer_alerte(request):
    form = AlerteForm(request.POST)
    if form.is_valid():
        alerte      = form.save(commit=False)
        alerte.user = request.user
        alerte.save()
        messages.success(request, f'Alerte créée pour {alerte.action.symbole}.')
    else:
        messages.error(request, 'Formulaire invalide.')
    return redirect('alertes')


@login_required
@require_POST
def supprimer_alerte(request, pk):
    alerte = get_object_or_404(Alerte, pk=pk, user=request.user)
    sym    = alerte.action.symbole
    alerte.delete()
    messages.success(request, f'Alerte {sym} supprimée.')
    return redirect('alertes')


@login_required
@require_POST
def toggle_alerte(request, pk):
    alerte        = get_object_or_404(Alerte, pk=pk, user=request.user)
    alerte.active = not alerte.active
    alerte.save(update_fields=['active'])
    return JsonResponse({'active': alerte.active})


# ── TELEGRAM ──────────────────────────────────────────────────────────────────

@login_required
def lier_telegram(request):
    profile = request.user.profile
    form    = TelegramLiaisonForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        chat_id = form.cleaned_data['chat_id'].strip()
        profile.telegram_chat_id = chat_id
        profile.telegram_actif   = True
        profile.save()

        # Test d'envoi
        from .services.telegram_service import send_alert
        ok = send_alert(chat_id, '✅ <b>BourseAI</b> — Liaison Telegram réussie !')
        if ok:
            messages.success(request, 'Telegram lié avec succès ! Message de test envoyé.')
        else:
            messages.warning(request, 'Chat ID enregistré mais le message de test a échoué. Vérifiez le Chat ID.')
        return redirect('lier_telegram')

    context = {
        'form':    form,
        'profile': profile,
        'bot_name': 'BourseAIBot',
    }
    return render(request, 'bourse/telegram.html', context)


# ── APIs JSON (pour AJAX et WebSocket fallback) ───────────────────────────────

@login_required
def api_prix(request, symbole):
    symbole = symbole.upper()
    prix    = donnees_service.get_prix_actuel(symbole)
    return JsonResponse({
        'symbole': symbole,
        'prix':    round(float(prix), 2) if prix else 0
    })


@login_required
def api_watchlist(request):
    """Retourne les prix de toutes les actions suivies."""
    actions = Action.objects.filter(actif=True)
    data = []
    for action in actions:
        prix = cache.get(f'prix_{action.symbole}', 0)
        data.append({'symbole': action.symbole, 'prix': prix or 0})
    return JsonResponse({'watchlist': data})


@login_required
def api_portefeuille_positions(request):
    """Retourne les positions du portefeuille en JSON."""
    pf = get_object_or_404(Portefeuille, user=request.user)
    positions = []
    for pos in pf.positions.filter(quantite_detenue__gt=0).select_related('action'):
        prix = cache.get(f'prix_{pos.action.symbole}', float(pos.prix_moyen_achat))
        positions.append({
            'symbole':    pos.action.symbole,
            'quantite':   float(pos.quantite_detenue),
            'pru':        float(pos.prix_moyen_achat),
            'prix_actuel':float(prix),
            'valeur':     float(prix) * float(pos.quantite_detenue),
            'pnl':        (float(prix) - float(pos.prix_moyen_achat)) * float(pos.quantite_detenue),
        })
    return JsonResponse({'positions': positions, 'solde_cash': float(pf.solde_cash)})


@login_required
@require_POST
def switch_theme(request):
    """Bascule le thème (clair/sombre) sans recharger la page."""
    profile = request.user.profile
    try:
        # Essayer de lire le thème envoyé par le JS pour être synchro
        data = json.loads(request.body)
        target_theme = data.get('theme')
        if target_theme in ['light', 'dark']:
            profile.theme_pref = target_theme
        else:
            raise ValueError
    except (json.JSONDecodeError, ValueError, AttributeError):
        # Fallback : bascule simple si pas de données JSON
        profile.theme_pref = 'light' if profile.theme_pref == 'dark' else 'dark'

    profile.save(update_fields=['theme_pref'])
    return JsonResponse({'theme': profile.theme_pref})
