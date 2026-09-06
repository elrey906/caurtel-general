# -*- coding: utf-8 -*-
"""
=============================================================================
RADAR DE ORDER BLOCKS INSTITUCIONALES & CONFLUENCIA CUÁNTICA
=============================================================================
Jerarquía Institucional: 1W > 1D > 4H > 1H
Score Cuantitativo por Order Block (0 a 100 pts)
Arsenal: RSI Normal, Stoch RSI (%K/%D), Giros MACD, ADX > 23,
         Golden Pocket (0.618 - 0.65), POC de Volumen y EMAs (10, 55, 200).
=============================================================================
"""

import os
import json
import time
import requests
import numpy as np
import pandas as pd

# Jerarquía institucional de ponderación
JERARQUIA_TF = {
    "1W": {"nombre": "Macro Semanal", "peso": 1.00, "mando": "MÁXIMO PODER INSTITUCIONAL (Manda sobre todos)"},
    "1D": {"nombre": "Estructural Diario", "peso": 0.85, "mando": "ALTO IMPACTO ESTRUCTURAL"},
    "4H": {"nombre": "Intermedio Táctico", "peso": 0.65, "mando": "CONFIRMACIÓN DE RUTA SWING"},
    "1H": {"nombre": "Sniper Gatillo", "peso": 0.50, "mando": "GATILLO DE PRECISIÓN (Afinación)"}
}

def clean_num(val, fallback=0.0):
    if val is None:
        return float(fallback)
    try:
        v = float(val)
        return v if v == v else float(fallback)
    except Exception:
        return float(fallback)

# ── CÁLCULO DE INDICADORES TÉCNICOS PUROS (Anti-NaN / Sin dependencias rotas) ──

def calcular_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def calcular_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
    rs = gain / (loss.replace(0, 1e-9))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)

def calcular_stoch_rsi(series, rsi_period=14, stoch_period=14, k_period=3, d_period=3):
    rsi = calcular_rsi(series, period=rsi_period)
    min_rsi = rsi.rolling(window=stoch_period, min_periods=1).min()
    max_rsi = rsi.rolling(window=stoch_period, min_periods=1).max()
    denom = max_rsi - min_rsi
    stoch = ((rsi - min_rsi) / denom.replace(0, 1e-9)) * 100
    stoch_k = stoch.rolling(window=k_period, min_periods=1).mean()
    stoch_d = stoch_k.rolling(window=d_period, min_periods=1).mean()
    return stoch_k.fillna(50.0), stoch_d.fillna(50.0)

def calcular_macd(series, fast=12, slow=26, signal=9):
    ema_fast = calcular_ema(series, fast)
    ema_slow = calcular_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calcular_ema(macd_line, signal)
    macd_hist = macd_line - signal_line
    giro_valle = (macd_hist < 0) & (macd_hist > macd_hist.shift(1))
    giro_alcista = (macd_hist > 0) & (macd_hist.shift(1) <= 0)
    return macd_line, signal_line, macd_hist, giro_valle, giro_alcista

def calcular_adx(df, period=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=1).mean()
    
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(window=period, min_periods=1).mean() / (atr.replace(0, 1e-9)))
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(window=period, min_periods=1).mean() / (atr.replace(0, 1e-9)))
    
    dx = 100 * ((plus_di - minus_di).abs() / ((plus_di + minus_di).replace(0, 1e-9)))
    adx = dx.rolling(window=period, min_periods=1).mean()
    return adx.fillna(20.0), plus_di.fillna(20.0), minus_di.fillna(20.0)

def calcular_poc_volumen(df, bins=25):
    """Calcula el Point of Control (precio con mayor volumen agrupado)"""
    if len(df) < 10:
        return float(df["close"].iloc[-1])
    
    min_p = df["low"].min()
    max_p = df["high"].max()
    if max_p <= min_p:
        return float(df["close"].iloc[-1])
    
    vol = df["vol"] if "vol" in df.columns else (df["volume"] if "volume" in df.columns else pd.Series(1, index=df.index))
    counts, bin_edges = np.histogram(df["close"], bins=bins, weights=vol)
    max_bin_idx = np.argmax(counts)
    poc = (bin_edges[max_bin_idx] + bin_edges[max_bin_idx + 1]) / 2.0
    return float(poc)

def calcular_fibonacci_golden_pocket(df, lookback=50):
    """Calcula el Golden Pocket de Fibonacci (0.618 - 0.65)"""
    recent = df.tail(lookback)
    swing_high = float(recent["high"].max())
    swing_low = float(recent["low"].min())
    diff = swing_high - swing_low
    
    gp_618 = swing_high - (diff * 0.618)
    gp_650 = swing_high - (diff * 0.650)
    
    return swing_high, swing_low, min(gp_618, gp_650), max(gp_618, gp_650)

# ── DETECCIÓN DE ORDER BLOCKS INSTITUCIONALES ─────────────────────────────────

def detectar_order_blocks(df, tf_name="1D", max_blocks=3):
    """
    Detecta Bullish Order Blocks (Demanda) y Bearish Order Blocks (Oferta).
    Verifica estado: Virgen (Fresco) vs Mitigado.
    """
    if len(df) < 15:
        return []
    
    obs = []
    close = df["close"].values
    open_p = df["open"].values
    high = df["high"].values
    low = df["low"].values
    current_price = close[-1]
    
    # Recorrer desde las velas recientes hacia atrás
    for i in range(len(df) - 3, max(2, len(df) - 40), -1):
        # Bullish OB: Vela bajista previa a rompimiento alcista
        if close[i] < open_p[i]:
            if close[i+1] > high[i] or (i+2 < len(df) and close[i+2] > high[i]):
                ob_top = float(high[i])
                ob_bot = float(low[i])
                
                # Chequeo de mitigación
                precios_posteriores = low[i+1:]
                mitigado = np.any(precios_posteriores < ob_bot) if len(precios_posteriores) > 0 else False
                tocado = np.any((precios_posteriores <= ob_top) & (precios_posteriores >= ob_bot)) if len(precios_posteriores) > 0 else False
                
                estado = "Mitigado" if mitigado else ("En Testeo" if tocado else "Virgen (Fresco)")
                
                obs.append({
                    "tipo": "BULLISH_OB",
                    "direccion": "COMPRA (Demanda)",
                    "tf": tf_name,
                    "top": ob_top,
                    "bot": ob_bot,
                    "mid": (ob_top + ob_bot) / 2.0,
                    "estado": estado,
                    "es_virgen": estado == "Virgen (Fresco)",
                    "dist_pct": ((ob_top - current_price) / current_price) * 100,
                    "indice_vela": i
                })
                if len(obs) >= max_blocks:
                    break
                    
    return obs

# ── SISTEMA DE SCORING CUANTITATIVO POR ORDER BLOCK (0 a 100 PTS) ─────────────

def puntuar_order_block(ob, current_price, ema55, ema200, gp_low, gp_high, poc, stoch_k, adx, macd_giro):
    score = 0
    razones = []
    mid_ob = ob["mid"]
    
    # 1. Estado Virgen
    if ob["es_virgen"]:
        score += 25
        razones.append("Bloque Virgen Fresco (+25 pts)")
    elif ob["estado"] == "En Testeo":
        score += 12
        razones.append("En Primer Testeo (+12 pts)")
        
    # 2. Confluencia con Golden Pocket o POC
    en_gp = (mid_ob >= gp_low * 0.985) and (mid_ob <= gp_high * 1.015)
    cerca_poc = abs(mid_ob - poc) / (poc + 1e-9) <= 0.02
    if en_gp:
        score += 25
        razones.append("Confluencia Golden Pocket Fib 0.618-0.65 (+25 pts)")
    elif cerca_poc:
        score += 20
        razones.append("Confluencia con POC de Volumen (+20 pts)")
        
    # 3. Confluencia con EMAs institucionales
    cerca_ema55 = abs(mid_ob - ema55) / (ema55 + 1e-9) <= 0.025
    cerca_ema200 = abs(mid_ob - ema200) / (ema200 + 1e-9) <= 0.03
    if cerca_ema200:
        score += 20
        razones.append("Confluencia con EMA 200 Institucional (+20 pts)")
    elif cerca_ema55:
        score += 15
        razones.append("Confluencia con EMA 55 de Tendencia (+15 pts)")
        
    # 4. Stoch RSI en sobreventa
    if stoch_k <= 25:
        score += 15
        razones.append("Stoch RSI Sobreventa Extrema %K <= 25 (+15 pts)")
    elif stoch_k <= 35:
        score += 8
        razones.append("Stoch RSI en Zona Baja (+8 pts)")
        
    # 5. Fuerza ADX > 23 y Giros MACD
    if adx >= 23.0 and macd_giro:
        score += 15
        razones.append("ADX > 23 con Giro de Valle MACD (+15 pts)")
    elif adx >= 23.0:
        score += 10
        razones.append("Fuerza Institucional ADX > 23 (+10 pts)")
    elif macd_giro:
        score += 8
        razones.append("Giro de Valle MACD Activo (+8 pts)")
        
    # Bonus de Jerarquía Institucional
    tf = ob["tf"]
    if tf == "1W":
        score = min(100, score + 15)
        razones.append("🏛️ Macro Semanal 1W (MÁXIMO PODER INSTITUCIONAL)")
    elif tf == "1D":
        score = min(100, score + 10)
        razones.append("📊 Estructural Diario 1D (ALTO IMPACTO)")
        
    ob["score"] = min(100, int(score))
    ob["razones"] = razones
    ob["mando_jerarquia"] = JERARQUIA_TF.get(tf, {}).get("mando", "")
    return ob

# ── FUNCIÓN MAESTRA: ANÁLISIS COMPLETO MULTI-TIMEFRAME DE UN ACTIVO ───────────

def analizar_activo_multitimeframe(simbolo, df_1h=None, df_4h=None, df_1d=None, df_1w=None):
    resultado = {
        "simbolo": simbolo,
        "precio_actual": 0.0,
        "indicadores": {},
        "order_blocks": [],
        "top_3_obs": [],
        "golden_pocket": {},
        "poc": 0.0,
        "score_general": 0
    }
    
    if df_1d is None or len(df_1d) < 15:
        return resultado
        
    precio = float(df_1d["close"].iloc[-1])
    resultado["precio_actual"] = precio
    
    # 1. Indicadores en 1D
    ema10_1d = float(calcular_ema(df_1d["close"], 10).iloc[-1])
    ema55_1d = float(calcular_ema(df_1d["close"], 55).iloc[-1])
    ema200_1d = float(calcular_ema(df_1d["close"], 200).iloc[-1]) if len(df_1d) >= 200 else float(calcular_ema(df_1d["close"], len(df_1d)).iloc[-1])
    rsi_1d = float(calcular_rsi(df_1d["close"], 14).iloc[-1])
    stoch_k_1d, stoch_d_1d = calcular_stoch_rsi(df_1d["close"])
    stoch_k_1d_val = float(stoch_k_1d.iloc[-1])
    stoch_d_1d_val = float(stoch_d_1d.iloc[-1])
    _, _, macd_hist_1d, giro_valle_1d, _ = calcular_macd(df_1d["close"])
    macd_giro_1d = bool(giro_valle_1d.iloc[-1])
    adx_1d, _, _ = calcular_adx(df_1d)
    adx_1d_val = float(adx_1d.iloc[-1])
    
    # 2. Golden Pocket y POC
    sw_high, sw_low, gp_low, gp_high = calcular_fibonacci_golden_pocket(df_1d, lookback=min(60, len(df_1d)))
    poc_val = calcular_poc_volumen(df_1d, bins=25)
    
    resultado["golden_pocket"] = {
        "swing_high": sw_high,
        "swing_low": sw_low,
        "gp_low": gp_low,
        "gp_high": gp_high,
        "en_rango_gp": (precio >= gp_low * 0.99) and (precio <= gp_high * 1.01)
    }
    resultado["poc"] = poc_val
    
    # 3. Indicadores en 4H si existe
    if df_4h is not None and len(df_4h) >= 15:
        rsi_4h = float(calcular_rsi(df_4h["close"], 14).iloc[-1])
        stoch_k_4h, stoch_d_4h = calcular_stoch_rsi(df_4h["close"])
        stoch_k_4h_val = float(stoch_k_4h.iloc[-1])
        stoch_d_4h_val = float(stoch_d_4h.iloc[-1])
        _, _, _, giro_valle_4h, _ = calcular_macd(df_4h["close"])
        macd_giro_4h = bool(giro_valle_4h.iloc[-1])
        adx_4h, _, _ = calcular_adx(df_4h)
        adx_4h_val = float(adx_4h.iloc[-1])
    else:
        rsi_4h, stoch_k_4h_val, stoch_d_4h_val, macd_giro_4h, adx_4h_val = rsi_1d, stoch_k_1d_val, stoch_d_1d_val, macd_giro_1d, adx_1d_val
        
    # 4. Indicadores en 1H si existe
    if df_1h is not None and len(df_1h) >= 15:
        rsi_1h = float(calcular_rsi(df_1h["close"], 14).iloc[-1])
        stoch_k_1h, stoch_d_1h = calcular_stoch_rsi(df_1h["close"])
        stoch_k_1h_val = float(stoch_k_1h.iloc[-1])
        stoch_d_1h_val = float(stoch_d_1h.iloc[-1])
        _, _, _, giro_valle_1h, _ = calcular_macd(df_1h["close"])
        macd_giro_1h = bool(giro_valle_1h.iloc[-1])
    else:
        rsi_1h, stoch_k_1h_val, stoch_d_1h_val, macd_giro_1h = rsi_4h, stoch_k_4h_val, stoch_d_4h_val, macd_giro_4h
        
    # 5. Indicadores en 1W si existe
    if df_1w is not None and len(df_1w) >= 10:
        rsi_1w = float(calcular_rsi(df_1w["close"], 14).iloc[-1])
        stoch_k_1w, stoch_d_1w = calcular_stoch_rsi(df_1w["close"])
        stoch_k_1w_val = float(stoch_k_1w.iloc[-1])
        stoch_d_1w_val = float(stoch_d_1w.iloc[-1])
        _, _, _, giro_valle_1w, _ = calcular_macd(df_1w["close"])
        macd_giro_1w = bool(giro_valle_1w.iloc[-1])
        adx_1w, _, _ = calcular_adx(df_1w)
        adx_1w_val = float(adx_1w.iloc[-1])
    else:
        rsi_1w, stoch_k_1w_val, stoch_d_1w_val, macd_giro_1w, adx_1w_val = rsi_1d, stoch_k_1d_val, stoch_d_1d_val, macd_giro_1d, adx_1d_val

    resultado["indicadores"] = {
        "precio": precio,
        "ema10_1d": ema10_1d,
        "ema55_1d": ema55_1d,
        "ema200_1d": ema200_1d,
        "dist_ema55_pct": ((precio - ema55_1d) / ema55_1d) * 100,
        "rsi_1w": rsi_1w,
        "stoch_k_1w": stoch_k_1w_val,
        "stoch_d_1w": stoch_d_1w_val,
        "macd_giro_1w": macd_giro_1w,
        "adx_1w": adx_1w_val,
        "rsi_1d": rsi_1d,
        "stoch_k_1d": stoch_k_1d_val,
        "stoch_d_1d": stoch_d_1d_val,
        "macd_giro_1d": macd_giro_1d,
        "adx_1d": adx_1d_val,
        "adx_fuerte_1d": adx_1d_val >= 23.0,
        "rsi_4h": rsi_4h,
        "stoch_k_4h": stoch_k_4h_val,
        "stoch_d_4h": stoch_d_4h_val,
        "macd_giro_4h": macd_giro_4h,
        "adx_4h": adx_4h_val,
        "rsi_1h": rsi_1h,
        "stoch_k_1h": stoch_k_1h_val,
        "stoch_d_1h": stoch_d_1h_val,
        "macd_giro_1h": macd_giro_1h
    }
    
    # 6. Detección de Order Blocks en cada TF
    todos_obs = []
    
    if df_1w is not None and len(df_1w) >= 10:
        obs_1w = detectar_order_blocks(df_1w, tf_name="1W", max_blocks=2)
        for ob in obs_1w:
            puntuar_order_block(ob, precio, ema55_1d, ema200_1d, gp_low, gp_high, poc_val, stoch_k_1w_val, adx_1w_val, macd_giro_1w)
            todos_obs.append(ob)
            
    obs_1d = detectar_order_blocks(df_1d, tf_name="1D", max_blocks=2)
    for ob in obs_1d:
        puntuar_order_block(ob, precio, ema55_1d, ema200_1d, gp_low, gp_high, poc_val, stoch_k_1d_val, adx_1d_val, macd_giro_1d)
        todos_obs.append(ob)
        
    if df_4h is not None and len(df_4h) >= 15:
        obs_4h = detectar_order_blocks(df_4h, tf_name="4H", max_blocks=2)
        for ob in obs_4h:
            puntuar_order_block(ob, precio, ema55_1d, ema200_1d, gp_low, gp_high, poc_val, stoch_k_4h_val, adx_4h_val, macd_giro_4h)
            todos_obs.append(ob)
            
    if df_1h is not None and len(df_1h) >= 15:
        obs_1h = detectar_order_blocks(df_1h, tf_name="1H", max_blocks=2)
        for ob in obs_1h:
            puntuar_order_block(ob, precio, ema55_1d, ema200_1d, gp_low, gp_high, poc_val, stoch_k_1h_val, adx_4h_val, macd_giro_1h)
            todos_obs.append(ob)
            
    resultado["order_blocks"] = todos_obs
    
    # Ordenar por Score descendente y tomar Top 3
    sorted_obs = sorted(todos_obs, key=lambda x: x["score"], reverse=True)
    resultado["top_3_obs"] = sorted_obs[:3]
    
    # Score de Confluencia General
    best_ob_score = sorted_obs[0]["score"] if sorted_obs else 30
    desc_score = 20 if resultado["indicadores"]["dist_ema55_pct"] <= -2.5 else 10
    stoch_score = 15 if stoch_k_1d_val <= 25 else (8 if stoch_k_1d_val <= 40 else 0)
    macd_score = 15 if macd_giro_1d else (10 if macd_giro_4h else 0)
    adx_score = 15 if adx_1d_val >= 23.0 else 5
    
    total_confluencia = int((best_ob_score * 0.35) + desc_score + stoch_score + macd_score + adx_score)
    resultado["score_general"] = min(100, max(0, total_confluencia))
    
    return resultado
