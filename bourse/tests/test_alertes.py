from django.test import TestCase
from django.contrib.auth.models import User
from bourse.models import Action, Alerte, IndicateurCache, UserProfile
from bourse.tasks.check_alertes import evaluer_alerte
import datetime


def creer_action(symbole='TEST'):
    return Action.objects.create(symbole=symbole, nom='Test Action')


def creer_user():
    user = User.objects.create_user(username='trader', password='pass')
    return user


class TestEvaluerAlerte(TestCase):

    def setUp(self):
        self.action = creer_action()
        self.user   = creer_user()

    def test_prix_haut_franchi(self):
        alerte = Alerte(action=self.action, user=self.user,
                        type_alerte=Alerte.TYPE_PRIX_HAUT, seuil=200)
        self.assertTrue(evaluer_alerte(alerte, 205))
        self.assertFalse(evaluer_alerte(alerte, 195))

    def test_prix_haut_exact(self):
        alerte = Alerte(action=self.action, user=self.user,
                        type_alerte=Alerte.TYPE_PRIX_HAUT, seuil=200)
        self.assertTrue(evaluer_alerte(alerte, 200))

    def test_prix_bas_franchi(self):
        alerte = Alerte(action=self.action, user=self.user,
                        type_alerte=Alerte.TYPE_PRIX_BAS, seuil=150)
        self.assertTrue(evaluer_alerte(alerte, 145))
        self.assertFalse(evaluer_alerte(alerte, 155))

    def test_prix_bas_exact(self):
        alerte = Alerte(action=self.action, user=self.user,
                        type_alerte=Alerte.TYPE_PRIX_BAS, seuil=150)
        self.assertTrue(evaluer_alerte(alerte, 150))

    def test_rsi_haut_déclenché(self):
        IndicateurCache.objects.create(
            action=self.action, date=datetime.date.today(), rsi_14=75
        )
        alerte = Alerte(action=self.action, user=self.user,
                        type_alerte=Alerte.TYPE_RSI_HAUT)
        self.assertTrue(evaluer_alerte(alerte, 200))

    def test_rsi_haut_non_déclenché(self):
        IndicateurCache.objects.create(
            action=self.action, date=datetime.date.today(), rsi_14=55
        )
        alerte = Alerte(action=self.action, user=self.user,
                        type_alerte=Alerte.TYPE_RSI_HAUT)
        self.assertFalse(evaluer_alerte(alerte, 200))

    def test_rsi_bas_déclenché(self):
        IndicateurCache.objects.create(
            action=self.action, date=datetime.date.today(), rsi_14=25
        )
        alerte = Alerte(action=self.action, user=self.user,
                        type_alerte=Alerte.TYPE_RSI_BAS)
        self.assertTrue(evaluer_alerte(alerte, 100))

    def test_macd_haussier(self):
        IndicateurCache.objects.create(
            action=self.action, date=datetime.date.today(),
            macd=1.5, macd_signal=0.8
        )
        alerte = Alerte(action=self.action, user=self.user,
                        type_alerte=Alerte.TYPE_MACD)
        self.assertTrue(evaluer_alerte(alerte, 100))

    def test_macd_baissier(self):
        IndicateurCache.objects.create(
            action=self.action, date=datetime.date.today(),
            macd=0.5, macd_signal=1.2
        )
        alerte = Alerte(action=self.action, user=self.user,
                        type_alerte=Alerte.TYPE_MACD)
        self.assertFalse(evaluer_alerte(alerte, 100))

    def test_sans_seuil_prix_haut(self):
        """Une alerte PRIX_HAUT sans seuil ne doit pas déclencher."""
        alerte = Alerte(action=self.action, user=self.user,
                        type_alerte=Alerte.TYPE_PRIX_HAUT, seuil=None)
        self.assertFalse(evaluer_alerte(alerte, 999))
