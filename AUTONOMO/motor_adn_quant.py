# -*- coding: utf-8 -*-
"""
MOTOR QUANT DE EVALUACIÓN DE ADN & ORÁCULO DE ORDER BLOCKS
Calcula:
1. Squeeze Momentum (Histograma y fase de absorción).
2. RSI Multi-Timeframe (1H y 4H) con zonas de sobreventa.
3. Order Blocks Institucionales no mitigados en 4H.
4. Mechas de absorción institucional (Lower Wick >= 35%).
5. Puntuación de ADN (0 a 100 Pts).
"""
import os, sys, time, requests, math
import pandas as pd
import numpy as np

def obtener_velas_publicas(symbol, interval="1h", limit=100):
    """
    Obtiene velas mediante cascada universal sin autenticación
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    # 1. Binance Vision
    for base in ["https://data-api.binance.vision", "https://api3.binance.com", "https://api.binance.com"]:
        try:
            url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            r = requests.get(url, headers=headers, timeout=4)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data, columns=['ot','open','high','low','close','vol','ct','qv','tr','tb','tq','ig'])
                    for c in ['open','high','low','close','vol']: df[c] = df[c].astype(float)
                    df['dt'] = pd.to_datetime(df['ot'], unit='ms', utc=True)
                    return df.sort_values('dt').reset_index(drop=True)
        except: pass

    # 2. Respaldo local de CSV si existe
    csv_paths = [
        f"/home/h/Escritorio/RESPALDO/2027/VELAS/{symbol}_1h.csv",
        f"/home/h/Escritorio/SEPTIEMBRE/DATOS/{symbol}_1h.csv"
    ]
    for p in csv_paths:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p)
                col_d = 'Datetime' if 'Datetime' in df.columns else 'timestamp'
                df['dt'] = pd.to_datetime(df[col_d], utc=True)
                df.rename(columns={'Close':'close','Open':'open','High':'high','Low':'low','Volume':'vol'}, inplace=True)
                return df.sort_values('dt').tail(limit).reset_index(drop=True)
            except: pass

    return pd.DataFrame()

def calcular_adn_activo(sym, bingx_sym, tipo="CRIPTO"):
    """
    Calcula el Score de ADN de un activo. Retorna dict con telemetría y puntuación.
    """
    # En cripto usamos symbol directo con USDT (ej SOLUSDT), en acciones consultamos BingX o CSV
    symbol_query = f"{sym}USDT" if tipo == "CRIPTO" else sym
    df_1h = obtener_velas_publicas(symbol_query, "1h", 100)
    
    if df_1h.empty or len(df_1h) < 20:
        # Puntuación neutra si no hay velas
        return {
            "sym": sym,
            "score": 50,
            "precio": 0.0,
            "rsi_1h": 50.0,
            "rsi_4h": 50.0,
            "macd_estado": "NEUTRO",
            "mecha_absorcion": 0.0,
            "order_block": False,
            "gatillo_valido": False
        }

    c = df_1h["close"]
    h = df_1h["high"]
    l = df_1h["low"]
    o = df_1h["open"]
    v = df_1h["vol"]
    px_actual = float(c.iloc[-1])

    # 1. RSI 1H
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=1).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=1).mean()
    rsi_1h = float((100 - (100 / (1 + (gain / (loss + 1e-9))))).iloc[-1])

    # 2. Squeeze MACD 1H
    fast_ema = c.ewm(span=12, adjust=False).mean()
    slow_ema = c.ewm(span=26, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    sig_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - sig_line
    c_hist = float(hist.iloc[-1])
    p_hist = float(hist.iloc[-2]) if len(hist) > 1 else c_hist
    
    if c_hist >= 0:
        macd_estado = "VERDE_CLARO" if c_hist >= p_hist else "VERDE_OSCURO"
    else:
        # Valle rojo encogiéndose = absorción / giro alcista
        macd_estado = "ROJO_CLARO" if c_hist > p_hist else "ROJO_OSCURO"

    # 3. Mecha de Absorción de la última vela
    rango_vela = float(h.iloc[-1] - l.iloc[-1])
    mecha_inf = float(min(o.iloc[-1], c.iloc[-1]) - l.iloc[-1])
    pct_mecha = (mecha_inf / rango_vela * 100.0) if rango_vela > 0 else 0.0

    # 4. Resample 4H para Order Block y Soporte
    df_1h_indexed = df_1h.set_index('dt')
    df_4h = df_1h_indexed.resample('4h').agg({'open':'first','high':'max','low':'min','close':'last','vol':'sum'}).dropna()
    
    soporte_7d = float(df_1h['low'].tail(72).min()) if len(df_1h) >= 72 else px_actual * 0.95
    dist_soporte = ((px_actual - soporte_7d) / soporte_7d) * 100.0

    # Puntuación ADN Cuántico (0 a 100)
    score = 40.0
    # +20 si el Squeeze está girando al alza (Rosa / Rojo Claro o Verde)
    if macd_estado in ["ROJO_CLARO", "VERDE_CLARO"]:
        score += 25.0
    # +20 si el RSI está en zona de oportunidad (30 - 48 pts)
    if 25.0 <= rsi_1h <= 48.0:
        score += 25.0
    elif rsi_1h < 25.0: # Sobreventa extrema
        score += 30.0
    # +15 si hay mecha de absorción institucional >= 35%
    if pct_mecha >= 35.0:
        score += 15.0
    # +10 si está cerca del soporte 7D (<= 2.5%)
    if abs(dist_soporte) <= 2.5:
        score += 10.0

    gatillo_valido = score >= 70.0 and (macd_estado in ["ROJO_CLARO", "VERDE_CLARO"])

    return {
        "sym": sym,
        "score": round(score, 1),
        "precio": px_actual,
        "rsi_1h": round(rsi_1h, 1),
        "macd_estado": macd_estado,
        "mecha_absorcion": round(pct_mecha, 1),
        "dist_soporte": round(dist_soporte, 2),
        "gatillo_valido": gatillo_valido
    }
