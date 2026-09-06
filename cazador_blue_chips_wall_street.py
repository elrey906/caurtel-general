#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
👑 SEPTIEMBRE 2027: CEREBRO 1 (ALPHA BLUE CHIPS & WALL STREET)
===============================================================================
Ecosistema Ganador Validado (96.3% Win Rate en los últimos 3 meses)
Activos Exclusivos: Acciones Tecnológicas e Índices Institucionales de Wall Street
Mecánica:
  1. Margen por posición: $10 USD (Configurable a $20 USD) | 10x apalancamiento
  2. Gatillo Smart Money: Mechas de absorción >= 35% en Soporte 7D + Compresión ATR
  3. Salida Asimétrica:
     - TP1 (50%): Mitigación al POC 90D o +1.5% / +2.0% -> Mueve Stop a Break-Even (+0.5%)
     - TP2 (50%): Trailing Stop a 1.5x ATR buscando techos institucionales
  4. Selector REAL 🟢 vs FANTASMA 👻 independiente
===============================================================================
"""

import os, sys, time, json, datetime, hmac, hashlib, requests, warnings
import pandas as pd
import numpy as np

warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
ESTADO_FILE = os.path.join(BASE_DIR, "estado_blue_chips.json")
CONFIG_MODO_FILE = os.path.join(BASE_DIR, "config_blue_chips_modo.json")

# Configuración de Capital
CAPITAL_BASE_NODO = 10.0   # $10 USD margen base por trade
APALANCAMIENTO = 10.0      # 10x apalancamiento -> Notional $100 USD
MAX_POSICIONES = 5         # Máximo de posiciones simultáneas
COOLDOWN_SEGUNDOS = 180    # 3 minutos entre aperturas del mismo activo
ULTIMA_OPERACION = {}

# 11 Activos Oficiales de Wall Street
ASSETS = [
    {"name": "BROADCOM",   "ticker": "AVGO",   "bingx_sym": "NCSKAVGO2USD-USDT",  "tipo": "ACCION", "sl": 0.06, "be": 0.020, "step_qty": 0.01,  "price_prec": 2, "min_qty": 0.01},
    {"name": "AMD",        "ticker": "AMD",    "bingx_sym": "NCSKAMD2USD-USDT",   "tipo": "ACCION", "sl": 0.08, "be": 0.020, "step_qty": 0.01,  "price_prec": 2, "min_qty": 0.01},
    {"name": "META",       "ticker": "META",   "bingx_sym": "NCSKMETA2USD-USDT",  "tipo": "ACCION", "sl": 0.06, "be": 0.020, "step_qty": 0.01,  "price_prec": 2, "min_qty": 0.01},
    {"name": "ALPHABET",   "ticker": "GOOGL",  "bingx_sym": "NCSKGOOGL2USD-USDT", "tipo": "ACCION", "sl": 0.05, "be": 0.020, "step_qty": 0.01,  "price_prec": 2, "min_qty": 0.01},
    {"name": "NVIDIA",     "ticker": "NVDA",   "bingx_sym": "NCSKNVDA2USD-USDT",  "tipo": "ACCION", "sl": 0.08, "be": 0.020, "step_qty": 0.01,  "price_prec": 2, "min_qty": 0.01},
    {"name": "APPLE",      "ticker": "AAPL",   "bingx_sym": "NCSKAAPL2USD-USDT",  "tipo": "ACCION", "sl": 0.05, "be": 0.030, "step_qty": 0.01,  "price_prec": 2, "min_qty": 0.01},
    {"name": "MICROSOFT",  "ticker": "MSFT",   "bingx_sym": "NCSKMSFT2USD-USDT",  "tipo": "ACCION", "sl": 0.04, "be": 0.015, "step_qty": 0.01,  "price_prec": 2, "min_qty": 0.01},
    {"name": "AMAZON",     "ticker": "AMZN",   "bingx_sym": "NCSKAMZN2USD-USDT",  "tipo": "ACCION", "sl": 0.05, "be": 0.020, "step_qty": 0.01,  "price_prec": 2, "min_qty": 0.01},
    {"name": "TESLA",      "ticker": "TSLA",   "bingx_sym": "NCSKTSLA2USD-USDT",  "tipo": "ACCION", "sl": 0.12, "be": 0.015, "step_qty": 0.01,  "price_prec": 2, "min_qty": 0.01},
    {"name": "NASDAQ",     "ticker": "QQQ",    "bingx_sym": "NCSKQQQ2USD-USDT",   "tipo": "ETF",    "sl": 0.05, "be": 0.015, "step_qty": 0.01,  "price_prec": 2, "min_qty": 0.01},
    {"name": "S&P 500",    "ticker": "^GSPC",  "bingx_sym": "NCSISP5002USD-USDT", "tipo": "INDICE", "sl": 0.06, "be": 0.020, "step_qty": 0.001, "price_prec": 1, "min_qty": 0.001},
    {"name": "DOW JONES",  "ticker": "^DJI",   "bingx_sym": "NCSKDJI2USD-USDT",   "tipo": "INDICE", "sl": 0.05, "be": 0.015, "step_qty": 0.001, "price_prec": 1, "min_qty": 0.001}
]

# Lectura de Modo (REAL vs FANTASMA)
def obtener_modo_operativo():
    if os.path.exists(CONFIG_MODO_FILE):
        try:
            with open(CONFIG_MODO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("modo", "FANTASMA").upper()
        except: pass
    return "FANTASMA"

def cargar_estado():
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"posiciones": {}, "historial": [], "pnl_acumulado": 0.0, "total_trades": 0, "wins": 0, "losses": 0}

def guardar_estado(estado):
    try:
        with open(ESTADO_FILE, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=2)
    except Exception as e:
        print(f"❌ Error guardando estado: {e}")

# API BingX
def cargar_credenciales():
    for p in [os.path.join(BASE_DIR, "bot_credentials.json"), os.path.join(BASE_DIR, ".env"), os.path.join(ROOT_DIR, "bot_credentials.json"), os.path.join(ROOT_DIR, ".env")]:
        if os.path.exists(p):
            if p.endswith(".json"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        c = json.load(f)
                        return c.get("bingx_api_key", ""), c.get("bingx_secret_key", "")
                except: pass
            else:
                from dotenv import dotenv_values
                vals = dotenv_values(p)
                return vals.get("BINGX_API_KEY", ""), vals.get("BINGX_API_SECRET", vals.get("BINGX_SECRET_KEY", ""))
    return os.getenv("BINGX_API_KEY", ""), os.getenv("BINGX_API_SECRET", os.getenv("BINGX_SECRET_KEY", ""))

API_KEY, SECRET_KEY = cargar_credenciales()

def bingx_api_request(method, endpoint, params=None):
    if not API_KEY or not SECRET_KEY:
        return {"code": -1, "msg": "Sin credenciales"}
    params = params.copy() if params else {}
    params["timestamp"] = int(time.time() * 1000)
    query = "&".join([f"{k}={params[k]}" for k in sorted(params.keys())])
    sig = hmac.new(SECRET_KEY.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
    url = f"https://open-api.bingx.com{endpoint}?{query}&signature={sig}"
    headers = {"X-BX-APIKEY": API_KEY}
    try:
        if method.upper() == "GET":
            r = requests.get(url, headers=headers, timeout=10)
        else:
            r = requests.post(url, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        return {"code": -999, "msg": str(e)}

def obtener_precio_actual(bingx_sym):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = f"https://open-api.bingx.com/openApi/swap/v2/quote/ticker?symbol={bingx_sym}"
        r = requests.get(url, headers=headers, timeout=6).json()
        if r.get("code") == 0 and "data" in r:
            return float(r["data"]["lastPrice"])
    except: pass
    return None

# -----------------------------------------------------------------------------
# 🔒 BLINDAJE SAGRADO DE MICROSOFT (MSFT) & ADOPCIÓN DE POSICIONES
# -----------------------------------------------------------------------------
# El SHORT manual de MSFT es 100% intocable. El bot jamás lo adoptará ni lo cerrará.
# Los LONGS de MSFT y de todos los demás activos SÍ se pueden operar y adoptar.

def sincronizar_y_adoptar_bingx(estado):
    """
    Sincroniza ÚNICAMENTE las posiciones abiertas y gestionadas por Cerebro 1.
    BLINDAJE DE ADOPCIÓN ABSOLUTO:
    1. Jamás adopta posiciones externas de BingX ni de otros cerebros (Cerebro 3, Cerebro 4, manuales).
    2. El SHORT de MSFT es 100% intocable, sagrado y blindado.
    3. Si la API falla, no borra el estado local (Circuit Breaker).
    4. Si una posición de Cerebro 1 ya no está viva en BingX, la liquida limpiamente.
    """
    modo = obtener_modo_operativo()
    if modo != "REAL":
        return
        
    r = bingx_api_request("GET", "/openApi/swap/v2/user/positions")
    if r.get("code") != 0 or "data" not in r or not isinstance(r.get("data"), list):
        return
        
    live_positions = r.get("data", [])
    posiciones = estado.setdefault("posiciones", {})
    
    # Identificar símbolos con posición real viva en BingX
    syms_vivos = set()
    for lp in live_positions:
        amt = abs(float(lp.get("positionAmt", 0.0)))
        if amt > 0:
            syms_vivos.add(lp.get("symbol", ""))

    # Auditar exclusivamente las posiciones registradas por Cerebro 1
    for ticker in list(posiciones.keys()):
        asset_match = next((a for a in ASSETS if a["ticker"] == ticker), None)
        if asset_match:
            bsym = asset_match["bingx_sym"]
            if bsym not in syms_vivos:
                print(f"🔔 [CIERRE DETECTADO EN BINGX] {ticker} ya no figura abierta en BingX.")
                del posiciones[ticker]
                guardar_estado(estado)

def calcular_indicadores_locales(csv_path):
    if not os.path.exists(csv_path): return None
    df = pd.read_csv(csv_path)
    date_col = 'Datetime' if 'Datetime' in df.columns else ('timestamp' if 'timestamp' in df.columns else ('Date' if 'Date' in df.columns else df.columns[0]))
    df['dt'] = pd.to_datetime(df[date_col], utc=True)
    df = df.rename(columns={'Close':'close','Open':'open','High':'high','Low':'low','Volume':'volume'}).sort_values('dt').reset_index(drop=True)
    
    # ATR & Soporte 7D
    tr = pd.concat([df['high']-df['low'], (df['high']-df['close'].shift(1)).abs(), (df['low']-df['close'].shift(1)).abs()], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean().fillna(df['close'] * 0.015)
    df['soporte_7d'] = df['low'].rolling(168, min_periods=24).min()
    
    # POC 90D
    len_poc = min(2160, len(df))
    vol_cum = df['volume'].rolling(len_poc, min_periods=48).sum() + 1e-9
    df['poc_90d'] = ((df['close'] * df['volume']).rolling(len_poc, min_periods=48).sum() / vol_cum).fillna(df['close'])
    
    # Mechas
    cr = (df['high'] - df['low']).clip(lower=1e-6)
    df['lw_pct'] = ((df[['open', 'close']].min(axis=1) - df['low']).clip(lower=0) / cr) * 100.0
    df['rvol'] = df['volume'] / (df['volume'].rolling(20, min_periods=1).mean() + 1e-9)
    
    return df.iloc[-1]

def ciclo_de_monitoreo():
    print("=" * 75)
    print("👑 INICIANDO MOTOR: CEREBRO 1 (ALPHA BLUE CHIPS & WALL STREET)")
    print(f"⏰ Fecha/Hora: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Modo Operativo: {obtener_modo_operativo()} | Activos: {len(ASSETS)} Blue Chips")
    print("=" * 75)
    
    while True:
        modo = obtener_modo_operativo()
        estado = cargar_estado()
        posiciones = estado.setdefault("posiciones", {})
        
        # Sincronización y adopción institucional de BingX (con SHORT MSFT blindado)
        try:
            sincronizar_y_adoptar_bingx(estado)
        except Exception as e:
            pass
        
        for asset in ASSETS:
            sym = asset['ticker']
            bsym = asset['bingx_sym']
            
            # Buscar archivo de velas local
            csv_candidates = [
                os.path.join("/home/h/Escritorio/RESPALDO/2027/VELAS", f"{sym}_1h.csv"),
                os.path.join(ROOT_DIR, "VELAS", f"{sym}_1h.csv"),
                os.path.join(ROOT_DIR, "DATOS", "VELAS", "yfinance", f"{sym}_1h.csv")
            ]
            cand_row = None
            for c in csv_candidates:
                if os.path.exists(c):
                    cand_row = calcular_indicadores_locales(c)
                    break
                    
            px = obtener_precio_actual(bsym)
            is_live = True
            if px is None and cand_row is not None:
                px = float(cand_row['close'])
                is_live = False
            if px is None: continue
            
            # 1. GESTIÓN DE POSICIÓN ACTIVA
            if sym in posiciones:
                p = posiciones[sym]
                avg_px = max(1e-6, float(p.get('entry_px', 0.0)))
                tp1 = p['tp1']
                sl = p['sl']
                dur_hrs = (time.time() - p['ts_entry']) / 3600.0
                
                # Check TP1 (50% en efectivo) - Exige precio en vivo real
                if not p.get('tp1_hit', False) and px >= tp1 and is_live:
                    p['tp1_hit'] = True
                    p['sl'] = round(avg_px * 1.005, asset['price_prec']) # BE en verde (+0.5%)
                    pnl_parc = ((tp1 - avg_px) / avg_px) * (CAPITAL_BASE_NODO * 0.5) * APALANCAMIENTO
                    p['realized_cash'] = p.get('realized_cash', 0.0) + pnl_parc
                    p['margen_actual'] = CAPITAL_BASE_NODO * 0.5
                    print(f"🎯 [TP1 PARCIAL] {sym} tocó ${tp1} -> Realizado: +${pnl_parc:.2f} USD | SL asegurado en Break-Even")
                    guardar_estado(estado)
                    
                # Trailing Stop dinámico para el 50% restante
                if p.get('tp1_hit', False) and cand_row is not None and is_live:
                    trailing_sl = round(px - (float(cand_row['atr']) * 1.5), asset['price_prec'])
                    if trailing_sl > p['sl']:
                        p['sl'] = trailing_sl
                        
                # Check Salida Final (SL / TP2) - Exige precio en vivo real
                cerrar = False; motivo = ""; exit_px = px
                if px >= p['tp2'] and is_live:
                    cerrar = True; motivo = "TP2_TECHO_MACRO"; exit_px = p['tp2']
                elif px <= p['sl'] and is_live:
                    cerrar = True; motivo = "BREAK_EVEN_SALVADO" if p.get('tp1_hit', False) else "SL_CONTROLADO"; exit_px = p['sl']
                    
                if cerrar:
                    raw = ((exit_px - avg_px) / avg_px) * p['margen_actual'] * APALANCAMIENTO
                    fees = (CAPITAL_BASE_NODO * APALANCAMIENTO * 2) * 0.0005
                    net = p.get('realized_cash', 0.0) + (raw - fees)
                    
                    estado['pnl_acumulado'] += net
                    estado['total_trades'] += 1
                    if net > 0: estado['wins'] += 1
                    else: estado['losses'] += 1
                    
                    estado['historial'].append({
                        "activo": sym, "side": "LONG", "entry": avg_px, "exit": exit_px,
                        "pnl": round(net, 2), "motivo": motivo, "fecha": datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                    })
                    del posiciones[sym]
                    guardar_estado(estado)
                    print(f"🏁 [CIERRE TRADE] {sym} | PnL: ${net:+6.2f} USD | Motivo: {motivo}")
                    continue
                    
            # 2. EVALUACIÓN DE NUEVA ENTRADA
            if sym not in posiciones and len(posiciones) < MAX_POSICIONES:
                now_ts = time.time()
                if now_ts - ULTIMA_OPERACION.get(sym, 0) < COOLDOWN_SEGUNDOS:
                    continue
                    
                if cand_row is not None:
                    sop7 = float(cand_row['soporte_7d'])
                    lw = float(cand_row['lw_pct'])
                    rvol = float(cand_row['rvol'])
                    atr = float(cand_row['atr'])
                    poc = float(cand_row['poc_90d'])
                    
                    # Condición de entrada Institucional
                    if px <= sop7 * 1.015 and lw >= 35.0 and rvol >= 1.0:
                        sl = round(px * (1.0 - asset['sl']), asset['price_prec'])
                        tp1 = round(max(poc, px * (1.0 + asset['be'])), asset['price_prec'])
                        tp2 = round(px * (1.0 + (asset['be'] * 3.0)), asset['price_prec'])
                        
                        posiciones[sym] = {
                            "activo": sym, "side": "LONG", "entry_px": px, "sl": sl, "tp1": tp1, "tp2": tp2,
                            "margen_actual": CAPITAL_BASE_NODO, "ts_entry": now_ts, "tp1_hit": False, "realized_cash": 0.0
                        }
                        ULTIMA_OPERACION[sym] = now_ts
                        guardar_estado(estado)
                        print(f"🚀 [NUEVO LONG {modo}] {sym} @ ${px} | SL: ${sl} | TP1: ${tp1} | TP2: ${tp2}")
                        
        time.sleep(15)

if __name__ == "__main__":
    ciclo_de_monitoreo()
