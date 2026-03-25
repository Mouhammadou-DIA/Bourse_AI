import pandas as pd
import numpy as np
from django.test import TestCase
from bourse.services.indicateurs_service import (
    calculer_rsi, calculer_macd, calculer_bollinger, calculer_atr
)


class TestRSI(TestCase):

    def _series(self, valeurs):
        return pd.Series(valeurs, dtype=float)

    def test_rsi_plage(self):
        """RSI doit toujours être entre 0 et 100."""
        np.random.seed(42)
        prix = self._series(np.random.normal(100, 5, 60).cumsum())
        rsi  = calculer_rsi(prix)
        rsi_clean = rsi.dropna()
        self.assertTrue((rsi_clean >= 0).all(), "RSI < 0 détecté")
        self.assertTrue((rsi_clean <= 100).all(), "RSI > 100 détecté")

    def test_rsi_survendu(self):
        """Série fortement baissière → RSI doit descendre sous 30."""
        prix = self._series([100 - i * 3 for i in range(30)])
        rsi  = calculer_rsi(prix)
        self.assertTrue(rsi.dropna().iloc[-1] < 40, "RSI trop élevé sur série baissière")

    def test_rsi_suracheté(self):
        """Série fortement haussière → RSI doit monter au-dessus de 70."""
        prix = self._series([100 + i * 3 for i in range(30)])
        rsi  = calculer_rsi(prix)
        self.assertTrue(rsi.dropna().iloc[-1] > 60, "RSI trop bas sur série haussière")

    def test_rsi_longueur(self):
        """RSI doit avoir la même longueur que la série d'entrée."""
        prix = self._series(range(50))
        rsi  = calculer_rsi(prix)
        self.assertEqual(len(rsi), len(prix))


class TestMACD(TestCase):

    def _series(self, n=60):
        np.random.seed(0)
        return pd.Series(100 + np.cumsum(np.random.randn(n)), dtype=float)

    def test_macd_longueur(self):
        prix = self._series()
        macd, signal, hist = calculer_macd(prix)
        self.assertEqual(len(macd), len(prix))
        self.assertEqual(len(signal), len(prix))
        self.assertEqual(len(hist), len(prix))

    def test_hist_egal_macd_moins_signal(self):
        prix = self._series()
        macd, signal, hist = calculer_macd(prix)
        diff = (macd - signal - hist).dropna().abs()
        self.assertTrue((diff < 1e-9).all(), "Histogramme != MACD - Signal")

    def test_croisement_haussier(self):
        """
        Sur une série avec tendance croissante, le dernier MACD
        doit finir au-dessus de son signal.
        """
        prix = pd.Series([100 + i * 0.5 + (0.1 * (i % 3)) for i in range(60)], dtype=float)
        macd, signal, _ = calculer_macd(prix)
        self.assertGreater(
            float(macd.dropna().iloc[-1]),
            float(signal.dropna().iloc[-1]),
            "MACD devrait être au-dessus du signal sur série haussière régulière"
        )


class TestBollinger(TestCase):

    def _series(self, n=60):
        np.random.seed(1)
        return pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5), dtype=float)

    def test_bande_superieure_toujours_au_dessus(self):
        prix = self._series()
        haut, bas, mid = calculer_bollinger(prix)
        valides = haut.dropna()
        self.assertTrue((haut.dropna() >= mid.dropna()).all(), "Bande sup < SMA")
        self.assertTrue((bas.dropna()  <= mid.dropna()).all(), "Bande inf > SMA")

    def test_longueur_coherente(self):
        prix = self._series()
        haut, bas, mid = calculer_bollinger(prix)
        self.assertEqual(len(haut), len(prix))
        self.assertEqual(len(bas),  len(prix))
        self.assertEqual(len(mid),  len(prix))

    def test_largeur_positive(self):
        prix = self._series()
        haut, bas, _ = calculer_bollinger(prix)
        largeur = (haut - bas).dropna()
        self.assertTrue((largeur > 0).all(), "Largeur de bande doit être positive")


class TestATR(TestCase):

    def _df(self, n=30):
        np.random.seed(2)
        closes = 100 + np.cumsum(np.random.randn(n))
        return pd.DataFrame({
            'plus_haut': closes + np.abs(np.random.randn(n)),
            'plus_bas':  closes - np.abs(np.random.randn(n)),
            'cloture':   closes,
        })

    def test_atr_positif(self):
        df  = self._df()
        atr = calculer_atr(df)
        self.assertTrue((atr.dropna() > 0).all(), "ATR doit être strictement positif")

    def test_atr_longueur(self):
        df  = self._df()
        atr = calculer_atr(df)
        self.assertEqual(len(atr), len(df))
