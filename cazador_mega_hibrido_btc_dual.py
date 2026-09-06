#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
👑 CEREBRO SUPREMO: MEGA HÍBRIDO QUANTUM BTC DUAL (BINANCE CROSS MARGIN 5X)
=============================================================================
Reemplazo Oficial de Septiembre 2027 para Binance Margin 5X.
Cero Sentimientos, Puro ADN Matemático Cuántico Institucional.

ARQUITECTURA OPERATIVA:
1. Exchange: BINANCE CROSS MARGIN 5X (Pares BTCUSDT & BTCUSDC).
2. Capital Base: $200.00 USD + $10.00 USD cada 15 días (10X Apalancamiento).
3. Reglas de Entrada Cuantitativas:
   - BALA 1: Solo se activa en el Piso de 7 Días (Cero ruido de mechas 4H).
   - PISO INMINENTE / REBOTE INMINENTE: Keltner 2.5 ATR, RSI 1D <= 28 o Giro de Valle 1D (Squeeze Momentum).
     • Exige distancia >= $4,000 USD de las compras previas o mitigación de Order Block.
     • Dispara BALA DOBLE ($12.00 USD) SI Y SOLO SI Margin Level >= 1.50x.
     • Si ML proyectado < 1.50x, modula a BALA SIMPLE ($6.00 USD).
   - BLINDAJE DE SEGURIDAD BTC $85,000: Bloquea compras si BTC >= $85k USD (configurable via Dashboard).
   - COMANDOS MANUALES DESDE DASHBOARD: Cierre 100% inmediato o venta parcial manual.
   - CONEXIÓN EN VIVO EN TIEMPO REAL CON BINANCE CROSS MARGIN 5X (serverTime API3).
=============================================================================
"""

import os
import sys
import time
import json
import hmac
import hashlib
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROD_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
ENV_PATH = os.path.join(BASE_DIR, ".env") if os.path.exists(os.path.join(BASE_DIR, ".env")) else os.path.join(PROD_DIR, ".env")
load_dotenv(ENV_PATH)

CONFIG_MODO_FILE = os.path.join(BASE_DIR, "config_MEGA_HIBRIDO_BTC_modo.json")
STATE_FILE = os.path.join(BASE_DIR, "estado_mega_hibrido_btc_dual.json")
LOG_FILE = os.path.join(BASE_DIR, "cazador_mega_hibrido_btc_dual.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("MEGA_HIBRIDO_BTC")

BINANCE_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET = os.getenv("BINANCE_API_SECRET", os.getenv("BINANCE_SECRET_KEY", ""))

def clean_num(val, fallback=0.0):
    try:
        v = float(val)
        return fallback if (np.isnan(v) or np.isinf(v)) else v
    except Exception:
        return fallback

def obtener_saldo_real_binance_margin():
    if not BINANCE_KEY or not BINANCE_SECRET:
        return None
    for base_url in ["https://api3.binance.com", "https://api.binance.com", "https://api1.binance.com"]:
        try:
            s_time = requests.get(f"{base_url}/api/v3/time", timeout=5).json().get("serverTime", int(time.time()*1000))
            qs = f"recvWindow=60000&timestamp={s_time}"
            sig = hmac.new(BINANCE_SECRET.encode('utf-8'), qs.encode('utf-8'), hashlib.sha256).hexdigest()
            url = f"{base_url}/sapi/v1/margin/account?{qs}&signature={sig}"
            headers = {"X-MBX-APIKEY": BINANCE_KEY}
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200:
                res = r.json()
                if "marginLevel" in res:
                    ml = float(res.get("marginLevel", 999.0))
                    tot_asset_btc = float(res.get("totalAssetOfBtc", 0.0))
                    tot_net_btc = float(res.get("totalNetAssetOfBtc", 0.0))
                    tot_liab_btc = float(res.get("totalLiabilityOfBtc", 0.0))
                    
                    usdt_free = 0.0
                    for a in res.get("userAssets", []):
                        if a.get("asset") == "USDT":
                            usdt_free = clean_num(a.get("free", 0.0))
                            break
                            
                    return {
                        "margin_level": ml,
                        "total_asset_btc": tot_asset_btc,
                        "total_net_btc": tot_net_btc,
                        "total_liab_btc": tot_liab_btc,
                        "usdt_free": usdt_free,
                        "raw": res
                    }
        except Exception as e:
            pass
    return None

def firmar_query_binance(query_string):
    return hmac.new(BINANCE_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def enviar_orden_binance_margin(symbol="BTCUSDT", side="BUY", quote_qty=None, qty=None, side_effect="NO_SIDE_EFFECT"):
    if not BINANCE_KEY or not BINANCE_SECRET:
        log.error("❌ [BINANCE API] Sin credenciales configuradas para orden real.")
        return None
        
    for base_url in ["https://api3.binance.com", "https://api.binance.com"]:
        try:
            s_time = requests.get(f"{base_url}/api/v3/time", timeout=5).json().get("serverTime", int(time.time()*1000))
            
            params = [
                f"symbol={symbol}",
                "isIsolated=FALSE",
                f"side={side}",
                "type=MARKET",
                f"sideEffectType={side_effect}",
                "recvWindow=60000",
                f"timestamp={s_time}"
            ]
            if side == "BUY" and quote_qty is not None:
                params.append(f"quoteOrderQty={quote_qty:.2f}")
            elif side == "SELL" and qty is not None:
                # Precisión de paso para BTC en Binance Margin es 0.00001 (5 decimales)
                params.append(f"quantity={qty:.5f}")
                
            qs = "&".join(params)
            sig = firmar_query_binance(qs)
            url = f"{base_url}/sapi/v1/margin/order?{qs}&signature={sig}"
            headers = {"X-MBX-APIKEY": BINANCE_KEY}
            
            r = requests.post(url, headers=headers, timeout=12)
            data = r.json()
            
            if "orderId" in data and data.get("status") in ["FILLED", "NEW", "PARTIALLY_FILLED"]:
                log.info(f"✅ [BINANCE MARGIN ORDER FILLED] ID: {data.get('orderId')} | Status: {data.get('status')}")
                return data
            else:
                log.error(f"❌ [BINANCE MARGIN ORDER ERROR] Code: {data.get('code')} | Msg: {data.get('msg')}")
                return None
        except Exception as e:
            log.error(f"❌ [BINANCE NETWORK EXCEPTION] Error enviando orden: {e}")
            continue
    return None


def obtener_velas_binance(symbol="BTCUSDT", interval="1h", limit=200):
    for base_url in ["https://api3.binance.com", "https://api.binance.com", "https://data-api.binance.vision"]:
        try:
            url = f"{base_url}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data, columns=['ot','open','high','low','close','vol','ct','qv','tr','tb','tq','ig'])
                    for c in ['open','high','low','close','vol']:
                        df[c] = df[c].astype(float)
                    df['dt'] = pd.to_datetime(df['ot'], unit='ms', utc=True)
                    return df.sort_values('dt').reset_index(drop=True)
        except Exception:
            continue
            
    local_csv = os.path.join(PROD_DIR, "VELAS", "BTC_1h.csv")
    if os.path.exists(local_csv):
        try:
            df = pd.read_csv(local_csv).tail(limit).copy()
            df.rename(columns={"Datetime":"dt","Open":"open","High":"high","Low":"low","Close":"close","Volume":"vol"}, inplace=True)
            df["dt"] = pd.to_datetime(df["dt"].str.split("+").str[0].str.strip(), utc=True)
            for c in ["open", "high", "low", "close", "vol"]:
                df[c] = df[c].astype(float)
            return df.sort_values("dt").reset_index(drop=True)
        except: pass
    return pd.DataFrame()

def calcular_indicadores(df_1h: pd.DataFrame):
    if df_1h.empty or len(df_1h) < 60:
        return None
    df = df_1h.copy()
    df.set_index("dt", inplace=True)
    
    # 4H
    df_4h = df.resample("4h").agg({"open":"first","high":"max","low":"min","close":"last","vol":"sum"}).dropna()
    df_4h["tr0"] = abs(df_4h["high"] - df_4h["low"])
    df_4h["tr1"] = abs(df_4h["high"] - df_4h["close"].shift(1))
    df_4h["tr2"] = abs(df_4h["low"] - df_4h["close"].shift(1))
    df_4h["atr_4h"] = df_4h[["tr0", "tr1", "tr2"]].max(axis=1).rolling(14).mean()
    df_4h["rvol_4h"] = df_4h["vol"] / df_4h["vol"].rolling(20).mean()
    
    d_4h = df_4h["close"].diff()
    g_4h = d_4h.clip(lower=0).rolling(14, min_periods=1).mean()
    l_4h = (-d_4h.clip(upper=0)).rolling(14, min_periods=1).mean()
    df_4h["rsi_4h"] = 100 - (100 / (1 + (g_4h / (l_4h + 1e-9))))
    
    rango_4h = df_4h["high"] - df_4h["low"]
    cuerpo_menor = np.minimum(df_4h["open"], df_4h["close"])
    df_4h["mecha_inf_pct"] = np.where(rango_4h > 0, (cuerpo_menor - df_4h["low"]) / rango_4h, 0.0)
    df_4h["es_vela_verde"] = df_4h["close"] > df_4h["open"]
    
    # Order Blocks 4H
    df_4h["es_ob"] = (df_4h["close"] < df_4h["open"]) & (df_4h["close"].shift(-1) > df_4h["high"])
    df_4h["ob_top"] = np.where(df_4h["es_ob"], df_4h["high"], np.nan)
    df_4h["ob_bot"] = np.where(df_4h["es_ob"], df_4h["low"], np.nan)
    df_4h["ob_top"] = df_4h["ob_top"].ffill()
    df_4h["ob_bot"] = df_4h["ob_bot"].ffill()
    
    # 1D
    df_1d = df.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last","vol":"sum"}).dropna()
    df_1d["tr0"] = abs(df_1d["high"] - df_1d["low"])
    df_1d["tr1"] = abs(df_1d["high"] - df_1d["close"].shift(1))
    df_1d["tr2"] = abs(df_1d["low"] - df_1d["close"].shift(1))
    df_1d["atr_1d"] = df_1d[["tr0", "tr1", "tr2"]].max(axis=1).rolling(14).mean()
    df_1d["ema20_1d"] = df_1d["close"].ewm(span=20, adjust=False).mean()
    df_1d["ema55_1d"] = df_1d["close"].ewm(span=55, adjust=False).mean()
    df_1d["ema10_1d"] = df_1d["close"].ewm(span=10, adjust=False).mean()
    df_1d["keltner_piso_extremo"] = df_1d["ema20_1d"] - (2.5 * df_1d["atr_1d"])
    df_1d["soporte_7d"] = df_1d["low"].shift(1).rolling(7).min()
    
    d_1d = df_1d["close"].diff()
    g_1d = d_1d.clip(lower=0).rolling(14, min_periods=1).mean()
    l_1d = (-d_1d.clip(upper=0)).rolling(14, min_periods=1).mean()
    df_1d["rsi_1d"] = 100 - (100 / (1 + (g_1d / (l_1d + 1e-9))))
    
    # Squeeze Momentum 1D (LazyBear)
    sqz_len_kc = 20
    hh = df_1d["high"].rolling(sqz_len_kc).max()
    ll = df_1d["low"].rolling(sqz_len_kc).min()
    donchian_mid = (hh + ll) / 2.0
    sma_close = df_1d["close"].rolling(sqz_len_kc).mean()
    base_val = (donchian_mid + sma_close) / 2.0
    delta = df_1d["close"] - base_val

    def linreg_series(s, length=20):
        x = np.arange(length)
        x_mean = x.mean()
        x_var = ((x - x_mean)**2).sum()
        res = np.full(len(s), np.nan)
        vals = s.values
        for i in range(length - 1, len(s)):
            y = vals[i - length + 1 : i + 1]
            if np.isnan(y).any(): continue
            y_mean = y.mean()
            slope = ((x - x_mean) * (y - y_mean)).sum() / x_var
            intercept = y_mean - slope * x_mean
            res[i] = intercept + slope * (length - 1)
        return pd.Series(res, index=s.index)

    df_1d["sqz_val_1d"] = linreg_series(delta, 20)
    df_1d["giro_valle_1d"] = (df_1d["sqz_val_1d"] < 0) & (df_1d["sqz_val_1d"] > df_1d["sqz_val_1d"].shift(1))

    df.reset_index(inplace=True)
    df_4h.reset_index(inplace=True)
    df_1d.reset_index(inplace=True)
    
    cols_4h = ["dt", "atr_4h", "rvol_4h", "rsi_4h", "mecha_inf_pct", "es_vela_verde", "ob_top", "ob_bot"]
    cols_1d = ["dt", "atr_1d", "ema10_1d", "ema55_1d", "keltner_piso_extremo", "soporte_7d", "rsi_1d", "sqz_val_1d", "giro_valle_1d"]
    
    merged = pd.merge_asof(df.sort_values("dt"), df_4h[cols_4h].sort_values("dt"), on="dt", direction="backward")
    merged = pd.merge_asof(merged.sort_values("dt"), df_1d[cols_1d].sort_values("dt"), on="dt", direction="backward")
    merged.ffill(inplace=True)
    return merged

def cargar_config():
    if os.path.exists(CONFIG_MODO_FILE):
        try:
            with open(CONFIG_MODO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {
        "modo_general": "REAL",
        "modo_btc_usdt": "REAL",
        "modo_btc_usdc": "REAL",
        "capital_inicial_usd": 200.0,
        "inyeccion_quincenal_usd": 10.0,
        "leverage": 10,
        "base_bullet_usd": 6.0,
        "double_bullet_usd": 12.0,
        "min_ml_allowed": 1.50,
        "blindaje_ml_bloqueo": 1.80,
        "bloqueo_precio_max": True,
        "precio_max_compras": 85000.0,
        "orden_manual_pendiente": None
    }

def guardar_config(cfg):
    try:
        with open(CONFIG_MODO_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        log.error(f"Error guardando config: {e}")

def cargar_estado():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {
        "capital_depositado_usd": 200.0,
        "cash_balance_usd": 200.0,
        "equity_total_usd": 200.0,
        "deuda_total_usd": 0.0,
        "margin_level_actual": 999.0,
        "posiciones": {
            "BTC-USDT": {
                "btc_pos": 0.0,
                "costo_prom": 0.0,
                "compras_realizadas": [],
                "ventas_realizadas": [],
                "stop_breakeven_activo": False,
                "stop_be_px": 0.0,
                "last_buy_dt": "",
                "last_sell_dt": ""
            },
            "BTC-USDC": {
                "btc_pos": 0.0,
                "costo_prom": 0.0,
                "compras_realizadas": [],
                "ventas_realizadas": [],
                "stop_breakeven_activo": False,
                "stop_be_px": 0.0,
                "last_buy_dt": "",
                "last_sell_dt": ""
            }
        },
        "historial_cerradas": [],
        "pnl_acumulado_usd": 0.0,
        "total_fees_usd": 0.0,
        "total_trades": 0,
        "victorias": 0
    }

def guardar_estado(st):
    st["ultima_actualizacion"] = datetime.now(timezone.utc).isoformat()
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2)
    except Exception as e:
        log.error(f"Error guardando estado: {e}")

def procesar_ordenes_manuales(cfg, st, px_ref):
    orden = cfg.get("orden_manual_pendiente")
    if not orden:
        return
    
    log.info(f"⚡ [ORDEN MANUAL DETECTADA EN DASHBOARD]: {orden}")
    symbol = orden.get("symbol", "TODOS")
    accion = orden.get("accion", "")
    pct = float(orden.get("pct", 1.0))
    
    pares_afectados = ["BTC-USDT", "BTC-USDC"] if symbol == "TODOS" else [symbol]
    
    for s in pares_afectados:
        if s in st["posiciones"] and st["posiciones"][s]["btc_pos"] > 0.00005:
            pos = st["posiciones"][s]
            sym_k = s.lower().replace("-", "_")
            modo_p = cfg.get(f"modo_{sym_k}", cfg.get("modo_general", "REAL"))
            s_bin = s.replace("-", "")
            
            btc_v = pos["btc_pos"] * pct
            costo_p = pos["costo_prom"]
            px_v = px_ref.get(s, costo_p)
            
            if modo_p == "REAL":
                res_ord = enviar_orden_binance_margin(symbol=s_bin, side="SELL", qty=btc_v, side_effect="AUTO_REPAY")
                if not res_ord:
                    log.error(f"❌ [{s}] Falló la ejecución de la orden manual REAL en Binance. Se omite actualización local.")
                    continue
                fills = res_ord.get("fills", [])
                tot_q = sum(float(f.get("qty", 0)) for f in fills)
                tot_c = sum(float(f.get("price", 0)) * float(f.get("qty", 0)) for f in fills)
                if tot_q > 0:
                    px_v = tot_c / tot_q
                    btc_v = tot_q

            noc_v = btc_v * px_v
            fee_v = noc_v * 0.0005
            pnl_op = (px_v - costo_p) * btc_v - fee_v
            
            st["cash_balance_usd"] += (noc_v - fee_v)
            deuda_p = min(st["deuda_total_usd"], btc_v * costo_p * 0.9)
            st["deuda_total_usd"] = max(0.0, st["deuda_total_usd"] - deuda_p)
            st["cash_balance_usd"] -= deuda_p
            pos["btc_pos"] -= btc_v
            
            st["pnl_acumulado_usd"] += pnl_op
            st["total_fees_usd"] += fee_v
            st["total_trades"] += 1
            if pnl_op > 0: st["victorias"] += 1
            
            log.info(f"🚨 [ORDEN MANUAL EJECUTADA] {accion} ({pct*100:.0f}%) en {s} @ ${px_v:,.1f} | PnL: +${pnl_op:.2f} USD")
            
            if pos["btc_pos"] <= 0.00005:
                pos["btc_pos"] = 0.0
                pos["costo_prom"] = 0.0
                pos["compras_realizadas"] = []
                pos["ventas_realizadas"] = []
                pos["stop_breakeven_activo"] = False
                
    cfg["orden_manual_pendiente"] = None
    guardar_config(cfg)
    guardar_estado(st)

def ejecutar_ciclo():
    cfg = cargar_config()
    st = cargar_estado()
    
    modo_gen = cfg.get("modo_general", "REAL")
    
    # 0. Actualizar Saldo Real en Vivo desde BINANCE CROSS MARGIN 5X
    if modo_gen == "REAL":
        saldo_binance = obtener_saldo_real_binance_margin()
        if saldo_binance:
            st["margin_level_actual"] = saldo_binance["margin_level"]
            st["cash_balance_usd"] = saldo_binance["usdt_free"]
            
            # Obtener precio aproximado de BTC
            df_curr = obtener_velas_binance("BTCUSDT", interval="1h", limit=5)
            px_curr = float(df_curr.iloc[-1]["close"]) if not df_curr.empty else 64000.0
            
            st["equity_total_usd"] = saldo_binance["total_net_btc"] * px_curr
            st["deuda_total_usd"] = saldo_binance["total_liab_btc"] * px_curr
            log.info(f"🟡 [BINANCE MARGIN EN VIVO]: ML: {st['margin_level_actual']:.2f}x | Equity: ${st['equity_total_usd']:,.2f} | USDT Libre: ${st['cash_balance_usd']:,.2f}")
            guardar_estado(st)

    # 1. Inyección quincenal automática
    ahora_dt = datetime.now(timezone.utc)
    ult_iny_str = st.get("ultima_inyeccion_dt")
    if ult_iny_str:
        ult_iny = datetime.fromisoformat(ult_iny_str)
        if (ahora_dt - ult_iny).total_seconds() >= 15 * 86400:
            iny = float(cfg.get("inyeccion_quincenal_usd", 10.0))
            st["capital_depositado_usd"] += iny
            st["cash_balance_usd"] += iny
            st["ultima_inyeccion_dt"] = ahora_dt.isoformat()
            log.info(f"💵 [INYECCIÓN QUINCENAL] Recibidos +${iny:.2f} USD. Capital Total: ${st['capital_depositado_usd']:.2f}")
            guardar_estado(st)

    # 2. Evaluar cada par (BTC-USDT y BTC-USDC)
    pares = ["BTC-USDT", "BTC-USDC"]
    base_bullet = float(cfg.get("base_bullet_usd", 6.0))
    lev = float(cfg.get("leverage", 10.0))
    min_ml_allowed = float(cfg.get("min_ml_allowed", 1.50))
    bloqueo_max = cfg.get("bloqueo_precio_max", True)
    px_max_allowed = float(cfg.get("precio_max_compras", 85000.0))
    
    precios_ref = {}
    for symbol in pares:
        symbol_bin = symbol.replace("-", "")
        df_ind = calcular_indicadores(obtener_velas_binance(symbol_bin, interval="1h", limit=200))
        if df_ind is not None and not df_ind.empty:
            precios_ref[symbol] = float(df_ind.iloc[-1]["close"])
            
    # Procesar orden manual si la enviaron desde Streamlit
    procesar_ordenes_manuales(cfg, st, precios_ref)
    
    for symbol in pares:
        symbol_bin = symbol.replace("-", "")
        df_ind = calcular_indicadores(obtener_velas_binance(symbol_bin, interval="1h", limit=200))
        if df_ind is None or len(df_ind) < 2:
            continue
            
        row = df_ind.iloc[-1]
        px = float(row["close"])
        precios_ref[symbol] = px
        dt_str = row["dt"].strftime("%Y-%m-%d %H:%M")
        
        pos = st["posiciones"][symbol]
        sym_key = symbol.lower().replace("-", "_")
        modo_par = cfg.get(f"modo_{sym_key}", cfg.get("modo_general", "REAL"))
        
        # ── GESTIÓN DE VENTAS SEMÁFORO 30/30/40 COOLDOWN 24H ──
        if pos["btc_pos"] > 0.0001:
            costo_p = pos["costo_prom"]
            pnl_flot_pct = ((px - costo_p) / costo_p) * 100.0
            
            # Protección Break-Even Post Venta 1
            if pos["stop_breakeven_activo"] and px <= pos["stop_be_px"]:
                log.info(f"🛡️ [{symbol}] SALIDA POR BREAK-EVEN PROTEGIDO @ ${px:,.1f} (Cero Pérdidas)")
                btc_v = pos["btc_pos"]
                px_be = px
                if modo_par == "REAL":
                    res_ord = enviar_orden_binance_margin(symbol=symbol_bin, side="SELL", qty=btc_v, side_effect="AUTO_REPAY")
                    if not res_ord:
                        log.error(f"❌ [{symbol}] Falló la ejecución de orden BE REAL en Binance. Se omite actualización local.")
                        continue
                    fills = res_ord.get("fills", [])
                    tot_q = sum(float(f.get("qty", 0)) for f in fills)
                    tot_c = sum(float(f.get("price", 0)) * float(f.get("qty", 0)) for f in fills)
                    if tot_q > 0:
                        px_be = tot_c / tot_q
                        btc_v = tot_q

                noc_c = btc_v * px_be
                fee_c = noc_c * 0.0005
                pnl_op = (px_be - costo_p) * btc_v - fee_c
                st["cash_balance_usd"] += (noc_c - fee_c)
                deuda_p = min(st["deuda_total_usd"], btc_v * costo_p * 0.9)
                st["deuda_total_usd"] = max(0.0, st["deuda_total_usd"] - deuda_p)
                st["cash_balance_usd"] -= deuda_p
                st["pnl_acumulado_usd"] += pnl_op
                st["total_fees_usd"] += fee_c
                
                pos["btc_pos"] = 0.0
                pos["costo_prom"] = 0.0
                pos["compras_realizadas"] = []
                pos["ventas_realizadas"] = []
                pos["stop_breakeven_activo"] = False
                guardar_estado(st)
                continue
                
            last_sell_dt = datetime.fromisoformat(pos["last_sell_dt"]) if pos.get("last_sell_dt") else None
            cd_v_ok = (last_sell_dt is None) or ((datetime.now(timezone.utc) - last_sell_dt).total_seconds() >= 24 * 3600)
            
            cond_f1 = ((row["rsi_1d"] >= 68.0 and pnl_flot_pct >= 8.0) or (pnl_flot_pct >= 12.0)) and len(pos["ventas_realizadas"]) == 0
            cond_f2 = (row["rsi_4h"] >= 70.0) and cd_v_ok and len(pos["ventas_realizadas"]) == 1
            cond_f3 = (px < row["ema10_1d"]) and cd_v_ok and len(pos["ventas_realizadas"]) == 2
            
            v_pct = 0.0
            fase = ""
            if cond_f1: v_pct, fase = 0.30, "Fase 1 (30% + BE)"
            elif cond_f2: v_pct, fase = 0.42857, "Fase 2 (30% Cooldown 24h)"
            elif cond_f3: v_pct, fase = 1.0, "Fase 3 (40% Runner)"
            
            if v_pct > 0.0:
                btc_v = pos["btc_pos"] * v_pct
                px_s = px
                if modo_par == "REAL":
                    res_ord = enviar_orden_binance_margin(symbol=symbol_bin, side="SELL", qty=btc_v, side_effect="AUTO_REPAY")
                    if not res_ord:
                        log.error(f"❌ [{symbol}] Falló la ejecución de orden {fase} REAL en Binance. Se omite actualización local.")
                        continue
                    fills = res_ord.get("fills", [])
                    tot_q = sum(float(f.get("qty", 0)) for f in fills)
                    tot_c = sum(float(f.get("price", 0)) * float(f.get("qty", 0)) for f in fills)
                    if tot_q > 0:
                        px_s = tot_c / tot_q
                        btc_v = tot_q

                noc_v = btc_v * px_s
                fee_v = noc_v * 0.0005
                pnl_op = (px_s - costo_p) * btc_v - fee_v
                
                st["cash_balance_usd"] += (noc_v - fee_v)
                deuda_p = min(st["deuda_total_usd"], btc_v * costo_p * 0.9)
                st["deuda_total_usd"] = max(0.0, st["deuda_total_usd"] - deuda_p)
                st["cash_balance_usd"] -= deuda_p
                pos["btc_pos"] -= btc_v
                pos["last_sell_dt"] = datetime.now(timezone.utc).isoformat()
                
                if len(pos["ventas_realizadas"]) == 0:
                    pos["stop_breakeven_activo"] = True
                    pos["stop_be_px"] = costo_p * 1.005
                    
                pos["ventas_realizadas"].append({"dt": dt_str, "fase": fase, "px": px_s, "pnl": pnl_op})
                st["pnl_acumulado_usd"] += pnl_op
                st["total_fees_usd"] += fee_v
                st["total_trades"] += 1
                if pnl_op > 0: st["victorias"] += 1
                
                log.info(f"🔵 [{symbol}] VENTA {fase} @ ${px_s:,.1f} | PnL: +${pnl_op:.2f} USD")
                if len(pos["ventas_realizadas"]) >= 3 or pos["btc_pos"] <= 0.00005:
                    pos["btc_pos"] = 0.0
                    pos["costo_prom"] = 0.0
                    pos["compras_realizadas"] = []
                    pos["ventas_realizadas"] = []
                    pos["stop_breakeven_activo"] = False
                guardar_estado(st)

        # ── GESTIÓN DE COMPRAS CUANTITATIVAS INSTITUCIONALES ──
        # Filtro de techo máximo (Bloqueo $85,000 USD)
        if bloqueo_max and px >= px_max_allowed:
            log.info(f"🛑 [{symbol}] COMPRAS BLOQUEADAS POR REGLA DE SEGURIDAD: BTC (${px:,.1f}) >= ${px_max_allowed:,.1f} USD")
            continue
            
        sop7 = row["soporte_7d"]
        en_desc = (px <= row["ema55_1d"] * 0.98) and (row["rsi_1d"] < 55.0)
        toca_soporte_7d = (sop7 > 0) and (px <= sop7 * 1.005) and en_desc
        
        keltner_floor = row["keltner_piso_extremo"]
        ob_top = row["ob_top"]
        ob_bot = row["ob_bot"]
        en_zona_ob = (ob_bot <= px <= ob_top) if ob_top > 0 else False
        giro_1d = bool(row.get("giro_valle_1d", False))
        
        cond_piso_inminente_tecnica = (px <= keltner_floor) or (row["rsi_1d"] <= 28.0) or giro_1d
        
        precios_prev = [c["px"] for c in pos["compras_realizadas"]]
        min_compra_ant = min(precios_prev) if precios_prev else None
        dist_a_compras = (min_compra_ant - px) if min_compra_ant else 99999.0
        
        disparar_compra = False
        tipo_c = ""
        m_intento = base_bullet
        
        if len(pos["compras_realizadas"]) == 0:
            # BALA 1: Solo se activa en Piso de 7 Días
            if toca_soporte_7d:
                disparar_compra = True
                tipo_c = "BALA 1 (Piso 7 Días - Cero Ruido 4H)"
                m_intento = base_bullet
        else:
            # PISO INMINENTE: Exige distancia >= $4,000, OB o Giro de Valle 1D
            if cond_piso_inminente_tecnica:
                if dist_a_compras >= 4000.0 or (giro_1d and dist_a_compras >= 2000.0):
                    disparar_compra = True
                    tipo_c = f"PISO INMINENTE / GIRO 1D (Distancia ${dist_a_compras:,.0f})"
                    m_intento = base_bullet * 2.0
                else:
                    proy_piso = min_compra_ant - max(4000.0, 1.5 * row["atr_1d"])
                    if px <= proy_piso or (en_zona_ob and dist_a_compras >= 2500.0):
                        disparar_compra = True
                        tipo_c = f"PISO INMINENTE EN OB INSTITUCIONAL (@ ${px:,.1f})"
                        m_intento = base_bullet * 2.0
            else:
                # Reversión intermedia (al menos $3,500 o 1.2 ATR_1D)
                reversion_mecha = (row["mecha_inf_pct"] >= 0.40) and bool(row["es_vela_verde"]) and (row["rsi_4h"] <= 38.0)
                if reversion_mecha and dist_a_compras >= max(3500.0, 1.2 * row["atr_1d"]):
                    disparar_compra = True
                    tipo_c = f"BALA ESCALONADA (Reversión 4H con Descuento ${dist_a_compras:,.0f})"
                    m_intento = base_bullet
                    
        if disparar_compra:
            tot_btc_global = sum(st["posiciones"][p]["btc_pos"] for p in pares)
            noc_i = m_intento * lev
            deuda_pot = st["deuda_total_usd"] + (noc_i - m_intento)
            assets_pot = (st["cash_balance_usd"] - m_intento) + (((tot_btc_global + (noc_i / px))) * px)
            ml_pot = assets_pot / deuda_pot if deuda_pot > 0 else 999.0
            
            # Filtro SI Y SOLO SI ML >= 1.50
            if ml_pot < min_ml_allowed and m_intento > base_bullet:
                m_intento = base_bullet
                noc_i = m_intento * lev
                deuda_pot = st["deuda_total_usd"] + (noc_i - m_intento)
                assets_pot = (st["cash_balance_usd"] - m_intento) + (((tot_btc_global + (noc_i / px))) * px)
                ml_pot = assets_pot / deuda_pot if deuda_pot > 0 else 999.0
                tipo_c += " -> Modulado a 1x por filtro ML 1.50"
                
            if ml_pot >= min_ml_allowed and st["cash_balance_usd"] >= m_intento:
                m = m_intento
                noc = m * lev
                px_c = px
                
                if modo_par == "REAL":
                    res_ord = enviar_orden_binance_margin(symbol=symbol_bin, side="BUY", quote_qty=noc, side_effect="MARGIN_BUY")
                    if not res_ord:
                        log.error(f"❌ [{symbol}] Falló la ejecución de la compra REAL en Binance. Se omite actualización local.")
                        continue
                    fills = res_ord.get("fills", [])
                    tot_q = sum(float(f.get("qty", 0)) for f in fills)
                    tot_c = sum(float(f.get("price", 0)) * float(f.get("qty", 0)) for f in fills)
                    if tot_q > 0:
                        px_c = tot_c / tot_q
                        btc_c = tot_q
                    else:
                        btc_c = (noc * 0.9995) / px_c
                    fee = noc * 0.0005
                else:
                    fee = noc * 0.0005
                    btc_c = (noc - fee) / px_c

                pos["costo_prom"] = ((pos["costo_prom"] * pos["btc_pos"]) + (px_c * btc_c)) / (pos["btc_pos"] + btc_c)
                pos["btc_pos"] += btc_c
                st["deuda_total_usd"] += (noc - m)
                st["cash_balance_usd"] -= m
                st["total_fees_usd"] += fee
                pos["last_buy_dt"] = datetime.now(timezone.utc).isoformat()
                pos["compras_realizadas"].append({"dt": dt_str, "tipo": tipo_c, "px": px_c, "margen": m, "ml": ml_pot})
                
                log.info(f"🟢 [{symbol} - {modo_par}] COMPRA {tipo_c} @ ${px_c:,.1f} | Margen: ${m:.1f} | ML Post: {ml_pot:.2f}x")
                guardar_estado(st)

    guardar_estado(st)

if __name__ == "__main__":
    log.info("🚀 [INICIANDO] Motor Cuántico Mega Híbrido BTC Dual (Binance Cross Margin 5X)...")
    while True:
        try:
            ejecutar_ciclo()
        except Exception as err:
            log.error(f"Error en ciclo operativo: {err}")
        time.sleep(15)
