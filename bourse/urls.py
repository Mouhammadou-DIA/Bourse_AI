from django.urls import path
from . import views

urlpatterns = [
    # Page d'accueil publique — DOIT être en premier
    path('', views.accueil, name='accueil'),

    # Auth
    path('inscription/', views.inscription, name='inscription'),

    # Dashboard (après connexion)
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profil/', views.profil, name='profil'),

    # Actions
    path('actions/', views.liste_actions, name='liste_actions'),
    path('actions/comparer/', views.comparer_actions, name='comparer'),
    path('actions/<str:symbole>/', views.detail_action, name='detail_action'),

    # Portefeuille
    path('portefeuille/', views.portefeuille, name='portefeuille'),
    path('portefeuille/transaction/', views.ajouter_transaction, name='transaction'),

    # Alertes
    path('alertes/', views.mes_alertes, name='alertes'),
    path('alertes/creer/', views.creer_alerte, name='creer_alerte'),
    path('alertes/<int:pk>/supprimer/', views.supprimer_alerte, name='suppr_alerte'),
    path('alertes/<int:pk>/toggle/', views.toggle_alerte, name='toggle_alerte'),

    # Telegram
    path('telegram/', views.lier_telegram, name='lier_telegram'),

    # API JSON
    path('api/prix/<str:symbole>/', views.api_prix, name='api_prix'),
    path('api/watchlist/', views.api_watchlist, name='api_watchlist'),
    path('api/portefeuille/positions/', views.api_portefeuille_positions, name='api_positions'),
    path('api/switch_theme/', views.switch_theme, name='switch_theme'),
]