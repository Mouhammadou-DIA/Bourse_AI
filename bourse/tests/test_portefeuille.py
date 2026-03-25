from django.test import TestCase
from django.contrib.auth.models import User
from bourse.models import Action, Portefeuille, Position, Transaction
from bourse.services.portefeuille_service import enregistrer_transaction


class TestTransaction(TestCase):

    def setUp(self):
        self.user    = User.objects.create_user(username='u', password='p')
        self.action  = Action.objects.create(symbole='AAPL', nom='Apple')
        self.pf      = Portefeuille.objects.create(
            user=self.user, nom='Test', solde_cash=10000
        )

    def test_achat_cree_position(self):
        enregistrer_transaction(self.pf, self.action, 'ACHAT', 10, 150)
        pos = Position.objects.get(portefeuille=self.pf, action=self.action)
        self.assertEqual(float(pos.quantite_detenue), 10)
        self.assertEqual(float(pos.prix_moyen_achat), 150)

    def test_achat_debite_cash(self):
        enregistrer_transaction(self.pf, self.action, 'ACHAT', 10, 150)
        self.pf.refresh_from_db()
        self.assertAlmostEqual(float(self.pf.solde_cash), 10000 - 10 * 150)

    def test_pru_moyen_deux_achats(self):
        enregistrer_transaction(self.pf, self.action, 'ACHAT', 10, 100)
        # Recréer le pf car solde_cash a changé
        self.pf.refresh_from_db()
        enregistrer_transaction(self.pf, self.action, 'ACHAT', 10, 200)
        pos = Position.objects.get(portefeuille=self.pf, action=self.action)
        # PRU attendu : (10*100 + 10*200) / 20 = 150
        self.assertAlmostEqual(float(pos.prix_moyen_achat), 150, places=2)

    def test_vente_reduit_position(self):
        enregistrer_transaction(self.pf, self.action, 'ACHAT', 10, 150)
        self.pf.refresh_from_db()
        enregistrer_transaction(self.pf, self.action, 'VENTE', 4, 160)
        pos = Position.objects.get(portefeuille=self.pf, action=self.action)
        self.assertAlmostEqual(float(pos.quantite_detenue), 6, places=4)

    def test_vente_credite_cash(self):
        enregistrer_transaction(self.pf, self.action, 'ACHAT', 10, 150)
        self.pf.refresh_from_db()
        cash_avant = float(self.pf.solde_cash)
        enregistrer_transaction(self.pf, self.action, 'VENTE', 5, 160)
        self.pf.refresh_from_db()
        self.assertAlmostEqual(float(self.pf.solde_cash), cash_avant + 5 * 160)

    def test_transaction_enregistree(self):
        enregistrer_transaction(self.pf, self.action, 'ACHAT', 10, 150, frais=5)
        self.assertEqual(Transaction.objects.filter(portefeuille=self.pf).count(), 1)
        tx = Transaction.objects.first()
        self.assertEqual(tx.type_op, 'ACHAT')
        self.assertEqual(float(tx.frais), 5)
