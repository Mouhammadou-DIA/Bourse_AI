from django.db import models
from decimal import Decimal
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Action(models.Model):
    symbole      = models.CharField(max_length=10,  unique=True)
    nom          = models.CharField(max_length=200)
    secteur      = models.CharField(max_length=100, blank=True)
    place_bourse = models.CharField(max_length=20,  default='NASDAQ')
    devise       = models.CharField(max_length=3,   default='USD')
    actif        = models.BooleanField(default=True)
    date_ajout   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.symbole} — {self.nom}'

    class Meta:
        ordering = ['symbole']
        verbose_name        = 'Action'
        verbose_name_plural = 'Actions'


class DonneeHistorique(models.Model):
    action          = models.ForeignKey(Action, on_delete=models.CASCADE, related_name='historique')
    date            = models.DateField()
    ouverture       = models.DecimalField(max_digits=12, decimal_places=4)
    plus_haut       = models.DecimalField(max_digits=12, decimal_places=4)
    plus_bas        = models.DecimalField(max_digits=12, decimal_places=4)
    cloture         = models.DecimalField(max_digits=12, decimal_places=4)
    volume          = models.BigIntegerField()
    cloture_ajustee = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)

    class Meta:
        unique_together = ['action', 'date']
        ordering        = ['-date']
        verbose_name    = 'Donnée historique'

    def __str__(self):
        return f'{self.action.symbole} — {self.date}'


class Portefeuille(models.Model):
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portefeuilles')
    nom           = models.CharField(max_length=100)
    solde_cash    = models.DecimalField(max_digits=15, decimal_places=2, default=10000)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.nom} ({self.user.username})'

    class Meta:
        verbose_name = 'Portefeuille'


class Transaction(models.Model):
    ACHAT = 'ACHAT'
    VENTE = 'VENTE'
    TYPE_CHOICES = [(ACHAT, 'Achat'), (VENTE, 'Vente')]

    portefeuille     = models.ForeignKey(Portefeuille, on_delete=models.CASCADE, related_name='transactions')
    action           = models.ForeignKey(Action,       on_delete=models.CASCADE)
    type_op          = models.CharField(max_length=5,  choices=TYPE_CHOICES)
    quantite         = models.DecimalField(max_digits=10, decimal_places=4)
    prix_unitaire    = models.DecimalField(max_digits=12, decimal_places=4)
    frais            = models.DecimalField(max_digits=8,  decimal_places=2, default=0)
    date_transaction = models.DateTimeField(auto_now_add=True)

    def montant_total(self):
        return (self.quantite * self.prix_unitaire) + self.frais

    def __str__(self):
        return f'{self.type_op} {self.quantite} {self.action.symbole}'

    class Meta:
        ordering     = ['-date_transaction']
        verbose_name = 'Transaction'


class Position(models.Model):
    portefeuille     = models.ForeignKey(Portefeuille, on_delete=models.CASCADE, related_name='positions')
    action           = models.ForeignKey(Action,       on_delete=models.CASCADE)
    quantite_detenue = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    prix_moyen_achat = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    valeur_actuelle  = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    plus_moins_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    mis_a_jour       = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['portefeuille', 'action']
        verbose_name    = 'Position'

    def __str__(self):
        return f'{self.action.symbole} × {self.quantite_detenue}'

    def rendement_pct(self):
        if self.prix_moyen_achat and self.prix_moyen_achat > 0 and self.valeur_actuelle and self.quantite_detenue > 0:
            prix_actuel = self.valeur_actuelle / self.quantite_detenue
            return ((prix_actuel - self.prix_moyen_achat) / self.prix_moyen_achat) * 100
        return 0


class Alerte(models.Model):
    TYPE_PRIX_HAUT  = 'PRIX_HAUT'
    TYPE_PRIX_BAS   = 'PRIX_BAS'
    TYPE_RSI_HAUT   = 'RSI_HAUT'
    TYPE_RSI_BAS    = 'RSI_BAS'
    TYPE_MACD       = 'MACD'
    TYPE_CHOICES = [
        (TYPE_PRIX_HAUT, 'Prix ≥ seuil'),
        (TYPE_PRIX_BAS,  'Prix ≤ seuil'),
        (TYPE_RSI_HAUT,  'RSI > 70'),
        (TYPE_RSI_BAS,   'RSI < 30'),
        (TYPE_MACD,      'Croisement MACD'),
    ]

    user            = models.ForeignKey(User,   on_delete=models.CASCADE, related_name='alertes')
    action          = models.ForeignKey(Action, on_delete=models.CASCADE)
    type_alerte     = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_PRIX_HAUT)
    seuil           = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    active          = models.BooleanField(default=True)
    notif_telegram  = models.BooleanField(default=True)
    notif_email     = models.BooleanField(default=False)
    desactiver_apres= models.BooleanField(default=True)
    message_perso   = models.CharField(max_length=200, blank=True)
    date_creation   = models.DateTimeField(auto_now_add=True)
    date_declenchement = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering     = ['-date_creation']
        verbose_name = 'Alerte'

    def __str__(self):
        return f'Alerte {self.action.symbole} — {self.get_type_alerte_display()}'


class IndicateurCache(models.Model):
    action         = models.ForeignKey(Action, on_delete=models.CASCADE, related_name='indicateurs')
    date           = models.DateField()
    rsi_14         = models.DecimalField(max_digits=8,  decimal_places=4, null=True)
    macd           = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    macd_signal    = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    macd_hist      = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    bollinger_haut = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    bollinger_bas  = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    bollinger_mid  = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    sma_20         = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    sma_50         = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    ema_50         = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    atr            = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    stoch_k        = models.DecimalField(max_digits=8,  decimal_places=4, null=True)
    stoch_d        = models.DecimalField(max_digits=8,  decimal_places=4, null=True)
    obv            = models.BigIntegerField(null=True)
    mis_a_jour     = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['action', 'date']
        ordering        = ['-date']
        verbose_name    = 'Indicateur (cache)'

    def signal_rsi(self):
        if not self.rsi_14:
            return 'inconnu'
        v = float(self.rsi_14)
        if v > 70: return 'suracheté'
        if v < 30: return 'survendu'
        return 'neutre'

    def signal_macd(self):
        if self.macd is None or self.macd_signal is None:
            return 'inconnu'
        return 'haussier' if float(self.macd) > float(self.macd_signal) else 'baissier'


class UserProfile(models.Model):
    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    telegram_chat_id = models.CharField(max_length=50, blank=True)
    telegram_actif   = models.BooleanField(default=False)
    devise_affichage = models.CharField(max_length=3, default='USD')
    theme_pref       = models.CharField(max_length=10, default='dark', choices=[('dark', 'Sombre'), ('light', 'Clair')])
    photo            = models.ImageField(upload_to='profiles/', null=True, blank=True)
    bio              = models.TextField(blank=True)

    def __str__(self):
        return f'Profil de {self.user.username}'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        Portefeuille.objects.create(user=instance, nom='Mon portefeuille', solde_cash=10000)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
