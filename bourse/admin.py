from django.contrib import admin
from .models import (Action, DonneeHistorique, Portefeuille,
                     Transaction, Position, Alerte, IndicateurCache, UserProfile)

@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display  = ['symbole', 'nom', 'secteur', 'place_bourse', 'actif']
    search_fields = ['symbole', 'nom']
    list_filter   = ['actif', 'place_bourse', 'secteur']

@admin.register(DonneeHistorique)
class DonneeHistoriqueAdmin(admin.ModelAdmin):
    list_display  = ['action', 'date', 'cloture', 'volume']
    list_filter   = ['action']
    date_hierarchy = 'date'

@admin.register(Portefeuille)
class PortefeuilleAdmin(admin.ModelAdmin):
    list_display = ['nom', 'user', 'solde_cash', 'date_creation']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['portefeuille', 'action', 'type_op', 'quantite', 'prix_unitaire', 'date_transaction']
    list_filter  = ['type_op', 'action']

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['action', 'portefeuille', 'quantite_detenue', 'prix_moyen_achat', 'valeur_actuelle']

@admin.register(Alerte)
class AlerteAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'type_alerte', 'seuil', 'active', 'date_creation']
    list_filter  = ['active', 'type_alerte', 'notif_telegram']

@admin.register(IndicateurCache)
class IndicateurCacheAdmin(admin.ModelAdmin):
    list_display = ['action', 'date', 'rsi_14', 'macd', 'sma_20']
    list_filter  = ['action']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'telegram_actif', 'telegram_chat_id', 'devise_affichage']
