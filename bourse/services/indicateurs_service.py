import pandas as pd
import numpy as np
from ..models import DonneeHistorique, IndicateurCache


def calculer_rsi(series, periode=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(periode).mean()
    perte = (-delta.clip(upper=0)).rolling(periode).mean()
    rs    = gain / perte
    return 100 - (100 / (1 + rs))


def calculer_macd(series, rapide=12, lent=26, signal_period=9):
    ema_r  = series.ewm(span=rapide, adjust=False).mean()
    ema_l  = series.ewm(span=lent,   adjust=False).mean()
    macd   = ema_r - ema_l
    signal = macd.ewm(span=signal_period, adjust=False).mean()
    hist   = macd - signal
    return macd, signal, hist


def calculer_bollinger(series, periode=20, nb_std=2):
    sma  = series.rolling(periode).mean()
    std  = series.rolling(periode).std()
    haut = sma + nb_std * std
    bas  = sma - nb_std * std
    return haut, bas, sma

def calculer_stochastique(df, k_window=14, d_window=3):
    # Plus bas des 14 derniers jours
    low_min  = df['plus_bas'].rolling(window=k_window).min()
    # Plus haut des 14 derniers jours
    high_max = df['plus_haut'].rolling(window=k_window).max()
    
    # Fast Stochastic %K
    k = 100 * ((df['cloture'] - low_min) / (high_max - low_min))
    # Slow Stochastic %D (SMA de %K)
    d = k.rolling(window=d_window).mean()
    return k, d

def calculer_obv(df):
    # Si Cloture > Cloture_prev => +Volume, sinon -Volume
    direction = np.where(df['cloture'] > df['cloture'].shift(1), 1, -1)
    direction[df['cloture'] == df['cloture'].shift(1)] = 0
    obv = (direction * df['volume']).cumsum()
    return pd.Series(obv, index=df.index)

def calculer_atr(df, periode=14):
    high  = df['plus_haut'].astype(float)
    low   = df['plus_bas'].astype(float)
    close = df['cloture'].astype(float)
    tr    = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(periode).mean()


def calculer_et_sauvegarder(action):
    """Calcule tous les indicateurs pour une action et les persiste."""
    qs = DonneeHistorique.objects.filter(action=action).order_by('date')
    if qs.count() < 60:
        return 0

    df = pd.DataFrame(list(qs.values('date', 'ouverture', 'plus_haut', 'plus_bas', 'cloture', 'volume')))
    df.set_index('date', inplace=True)
    closes = df['cloture'].astype(float)
    df['cloture']   = df['cloture'].astype(float)
    df['plus_haut'] = df['plus_haut'].astype(float)
    df['plus_bas']  = df['plus_bas'].astype(float)
    df['volume']    = df['volume'].astype(float)

    rsi                   = calculer_rsi(closes)
    macd, macd_sig, hist  = calculer_macd(closes)
    boll_h, boll_b, sma20 = calculer_bollinger(closes)
    sma50 = closes.rolling(50).mean()
    ema50 = closes.ewm(span=50, adjust=False).mean()
    atr   = calculer_atr(df)
    stoch_k, stoch_d      = calculer_stochastique(df)
    obv                   = calculer_obv(df)

    saved = 0
    for date in df.index[-60:]:
        def safe(series):
            v = series.get(date)
            return round(float(v), 6) if v is not None and not pd.isna(v) else None

        IndicateurCache.objects.update_or_create(
            action=action, date=date,
            defaults={
                'rsi_14':         safe(rsi),
                'macd':           safe(macd),
                'macd_signal':    safe(macd_sig),
                'macd_hist':      safe(hist),
                'bollinger_haut': safe(boll_h),
                'bollinger_bas':  safe(boll_b),
                'bollinger_mid':  safe(sma20),
                'sma_20':         safe(sma20),
                'sma_50':         safe(sma50),
                'ema_50':         safe(ema50),
                'atr':            safe(atr),
                'stoch_k':        safe(stoch_k),
                'stoch_d':        safe(stoch_d),
                'obv':            int(obv.get(date)) if not pd.isna(obv.get(date)) else 0,
            }
        )
        saved += 1

    return saved


def get_signal_global(indicateur):
    """Calcule un signal global (achat/vente/neutre) à partir des indicateurs."""
    if not indicateur:
        return 'inconnu'

    signaux = []

    if indicateur.rsi_14:
        rsi = float(indicateur.rsi_14)
        if rsi > 70: signaux.append(-1)
        elif rsi < 30: signaux.append(1)
        else: signaux.append(0)

    if indicateur.macd and indicateur.macd_signal:
        signaux.append(1 if float(indicateur.macd) > float(indicateur.macd_signal) else -1)

    if indicateur.bollinger_mid and indicateur.bollinger_haut:
        signaux.append(0)

    # Signal Stochastique
    if indicateur.stoch_k and indicateur.stoch_d:
        k, d = float(indicateur.stoch_k), float(indicateur.stoch_d)
        if k < 20 and k > d: signaux.append(1)   # Croisement haussier zone survente
        if k > 80 and k < d: signaux.append(-1)  # Croisement baissier zone surachat

    if not signaux:
        return 'neutre'

    score = sum(signaux) / len(signaux)
    if score > 0.3:   return 'achat'
    if score < -0.3:  return 'vente'
    return 'neutre'
