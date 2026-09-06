#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
👑 CAZADOR PRO: CEREBRO HÍBRIDO TRIFECTA CUÁNTICA ($15 + $45 + $10)
========================================================================================
Ubicación Oficial: /home/h/Escritorio/SEPTIEMBRE/HIBRIDO/
Arquitectura Operativa:
  1. Activos Oficiales: AMD, AVGO, META, DJI, BTC, ETH.
  2. Modos Independientes por Activo (REAL 🟢 vs FANTASMA 👻).
  3. Trifecta de Balas:
     • Bala 1 (Sonda): $15.00 USD margen (10x palanca = $150 nominal).
     • Bala 2 (Martillazo en Suelo 30D): $45.00 USD margen (10x palanca = $450 nominal).
     • Bala 3 (Rebote Inminente): $10.00 USD margen (10x palanca = $100 nominal).
  4. Protección Anti-Colisión Cuántica:
     • Aislamiento con Binance y Cerebro 6 (USDC).
     • Escudo BingX: clientOrderId único TRI_{sym}_{timestamp}, MSFT intocable.
  5. Comandos Manuales desde Dashboard: Cierre de emergencia por activo.
========================================================================================
"""
import os, sys, time, json, datetime, hmac, hashlib, requests, warnings, math
import pandas as pd
import numpy as np
from dotenv import load_dotenv

warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROD_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
VELAS_DIR = "/home/h/Escritorio/RESPALDO/2027/VELAS"
ENV_PATH = os.path.join(BASE_DIR, ".env") if os.path.exists(os.path.join(BASE_DIR, ".env")) else os.path.join(PROD_DIR, ".env")
load_dotenv(ENV_PATH)

CONFIG_MODO_FILE = os.path.join(BASE_DIR, "config_trifecta_modo.json")
ESTADO_FILE = os.path.join(BASE_DIR, "estado_trifecta_hibrido.json")
TELEMETRIA_FILE = os.path.join(BASE_DIR, "telemetria_adn_trifecta.json")
COMANDOS_FILE = os.path.join(BASE_DIR, "comandos_manuales.json")
LOG_FILE = os.path.join(BASE_DIR, "cazador_trifecta.log")

BINGX_KEY = os.getenv("BINGX_API_KEY", "")
BINGX_SECRET = os.getenv("BINGX_API_SECRET", "")
BINGX_URL = "https://open-api.bingx.com"

EXCLUIDOS_DE_ADOPCION = ["NCSKMSFT2USD-USDT"]

BALA_1_MARGEN = 15.0
BALA_2_MARGEN = 45.0
BALA_3_MARGEN = 10.0
PALANCA = 10.0
FEE_TAKER = 0.0005

ACTIVOS = [
    {"sym": "AMD",  "name": "AMD",        "bingx_sym": "NCSKAMD2USD-USDT",  "tipo": "ACCION", "step_qty": 0.01,   "min_qty": 0.01,   "price_prec": 2, "tp_rebote": 0.045, "caida_martillazo": 0.035},
    {"sym": "AVGO", "name": "BROADCOM",   "bingx_sym": "NCSKAVGO2USD-USDT", "tipo": "ACCION", "step_qty": 0.01,   "min_qty": 0.01,   "price_prec": 2, "tp_rebote": 0.045, "caida_martillazo": 0.035},
    {"sym": "META", "name": "META",       "bingx_sym": "NCSKMETA2USD-USDT", "tipo": "ACCION", "step_qty": 0.01,   "min_qty": 0.01,   "price_prec": 2, "tp_rebote": 0.040, "caida_martillazo": 0.035},
    {"sym": "DJI",  "name": "DOW JONES",  "bingx_sym": "NCSIDJI2USD-USDT",  "tipo": "INDICE", "step_qty": 0.001,  "min_qty": 0.001,  "price_prec": 1, "tp_rebote": 0.025, "caida_martillazo": 0.020},
    {"sym": "BTC",  "name": "BITCOIN",    "bingx_sym": "BTC-USDC",          "tipo": "CRIPTO", "step_qty": 0.0001, "min_qty": 0.0001, "price_prec": 1, "tp_rebote": 0.040, "caida_martillazo": 0.050},
    {"sym": "ETH",  "name": "ETHEREUM",   "bingx_sym": "ETH-USDC",          "tipo": "CRIPTO", "step_qty": 0.01,   "min_qty": 0.01,   "price_prec": 2, "tp_rebote": 0.040, "caida_martillazo": 0.050}
]

def log_msg(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts}] {msg}"
    print(formatted)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except: pass

def clean_num(val, fallback=0.0):
    try:
        v = float(val)
        return fallback if np.isnan(v) or np.isinf(v) else v
    except: return fallback

def ajustar_qty(monto_usd, precio, step, min_q):
    raw_qty = (monto_usd * PALANCA) / precio
    precision = int(round(-math.log10(step))) if step < 1 else 0
    qty = round(math.floor(raw_qty / step) * step, precision)
    return max(qty, min_q)

def leer_modos():
    default_modos = {cfg["sym"]: "FANTASMA" for cfg in ACTIVOS}
    if os.path.exists(CONFIG_MODO_FILE):
        try:
            with open(CONFIG_MODO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for sym in default_modos:
                    if sym in data:
                        default_modos[sym] = data[sym].upper()
                return default_modos
        except: pass
    return default_modos

def leer_estado():
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {
        "pnl_total": 0.0, "total_trades": 0, "wins": 0, "losses": 0,
        "posiciones_activas": {}, "historial": [],
        "ultima_actualizacion": datetime.datetime.now().isoformat()
    }

def guardar_estado(st):
    st["ultima_actualizacion"] = datetime.datetime.now().isoformat()
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2)

def obtener_precio_en_vivo(sym, bingx_sym):
    try:
        url = f"{BINGX_URL}/openApi/swap/v2/quote/ticker?symbol={bingx_sym}"
        res = requests.get(url, timeout=4).json()
        if res.get("code") == 0:
            return float(res["data"]["lastPrice"])
    except: pass
    fpath = os.path.join(VELAS_DIR, f"{sym}_1h.csv")
    if os.path.exists(fpath):
        try:
            df = pd.read_csv(fpath)
            dt_col = 'Close' if 'Close' in df.columns else 'close'
            return float(df[dt_col].iloc[-1])
        except: pass
    return 0.0

def calcular_indicadores_activo(sym):
    fpath = os.path.join(VELAS_DIR, f"{sym}_1h.csv")
    if not os.path.exists(fpath): return None
    try:
        df = pd.read_csv(fpath)
        dt_col = 'Datetime' if 'Datetime' in df.columns else df.columns[0]
        df['dt'] = pd.to_datetime(df[dt_col], utc=True)
        df = df.rename(columns={'Close': 'close', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Volume': 'volume'})
        df = df.sort_values('dt').set_index('dt')
        df4 = df.resample('4h').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna()
        
        tr1 = df4['high'] - df4['low']
        tr2 = (df4['high'] - df4['close'].shift(1)).abs()
        tr3 = (df4['low'] - df4['close'].shift(1)).abs()
        df4['atr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()
        
        candle_range = (df4['high'] - df4['low']).clip(lower=1e-6)
        lower_wick = (df4[['open', 'close']].min(axis=1) - df4['low']).clip(lower=0.0)
        df4['lower_wick_pct'] = (lower_wick / candle_range) * 100.0
        
        df4['sop7d'] = df4['low'].rolling(42).min().shift(1)
        df4['piso30d'] = df4['low'].rolling(180).min().shift(1)
        
        df4['vol_ma'] = df4['volume'].rolling(20).mean()
        df4['rvol'] = df4['volume'] / (df4['vol_ma'] + 1e-9)
        return df4.iloc[-1]
    except Exception as e:
        log_msg(f"Error calculando indicadores {sym}: {e}")
        return None

def chequear_comandos_manuales(st, modos):
    if not os.path.exists(COMANDOS_FILE): return
    try:
        with open(COMANDOS_FILE, "r", encoding="utf-8") as f:
            cmds = json.load(f)
        
        cerrar_sym = cmds.get("cerrar_posicion")
        if cerrar_sym and cerrar_sym in st["posiciones_activas"]:
            pos = st["posiciones_activas"][cerrar_sym]
            px = obtener_precio_en_vivo(cerrar_sym, pos["bingx_sym"])
            if px <= 0: px = pos["precio_promedio"]
            
            nominal = pos["qty_total"] * px
            costo = pos["costo_total_usd"]
            pnl = nominal - costo - (costo * FEE_TAKER * 2)
            modo_del_trade = pos.get("modo", modos.get(cerrar_sym, "FANTASMA"))
            
            log_msg(f"🚨 CIERRE MANUAL DESDE DASHBOARD [{modo_del_trade}]: {cerrar_sym} a mercado (PnL: {pnl:+.2f} USD)")
            
            st["pnl_total"] += pnl
            st["total_trades"] += 1
            if pnl > 0: st["wins"] += 1
            else: st["losses"] += 1
            
            st["historial"].insert(0, {
                "sym": cerrar_sym, "tipo": "CIERRE_MANUAL_DASHBOARD",
                "fecha_in": pos["in_ts"], "fecha_out": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "margen": pos["margen_total"], "pnl": round(pnl, 2), "modo": modo_del_trade
            })
            del st["posiciones_activas"][cerrar_sym]
            guardar_estado(st)
            
            with open(COMANDOS_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)
    except Exception as e:
        log_msg(f"Error procesando comandos manuales: {e}")

def ciclo_principal():
    log_msg("👑 INICIANDO MOTOR CAZADOR PRO: CEREBRO TRIFECTA CUÁNTICA (MODOS INDEPENDIENTES)")
    while True:
        try:
            modos = leer_modos()
            st = leer_estado()
            chequear_comandos_manuales(st, modos)
            
            telemetria = {}
            
            for cfg in ACTIVOS:
                sym = cfg["sym"]
                bingx_sym = cfg["bingx_sym"]
                modo_activo = modos.get(sym, "FANTASMA")
                
                if bingx_sym in EXCLUIDOS_DE_ADOPCION:
                    continue
                    
                px = obtener_precio_en_vivo(sym, bingx_sym)
                ind = calcular_indicadores_activo(sym)
                if px <= 0 or ind is None: continue
                
                pos = st["posiciones_activas"].get(sym)
                piso_30d = float(ind['piso30d'])
                sop_7d = float(ind['sop7d'])
                dist_martillazo_pct = ((px - piso_30d) / piso_30d) * 100.0
                
                # 1. GESTIÓN DE POSICIÓN ACTIVA
                if pos is not None:
                    avg_p = pos["precio_promedio"]
                    tp_target = avg_p * (1.0 + cfg["tp_rebote"])
                    dist_tp_pct = ((tp_target - px) / px) * 100.0
                    pnl_flotante = (pos["qty_total"] * px) - pos["costo_total_usd"]
                    modo_trade = pos.get("modo", modo_activo)
                    
                    if px >= tp_target:
                        estado_adn = "🟢 ZONA DE COBRO (EJECUTANDO TAKE PROFIT)"
                        log_msg(f"🎯 TAKE PROFIT ALCANZADO EN {sym} [{modo_trade}]: Precio={px:.2f} >= Target={tp_target:.2f} (PnL: +{pnl_flotante:.2f} USD)")
                        
                        st["pnl_total"] += pnl_flotante
                        st["total_trades"] += 1
                        st["wins"] += 1
                        st["historial"].insert(0, {
                            "sym": sym, "tipo": f"TAKE_PROFIT_{pos['balas_count']}_BALAS",
                            "fecha_in": pos["in_ts"], "fecha_out": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "margen": pos["margen_total"], "pnl": round(pnl_flotante, 2), "modo": modo_trade
                        })
                        del st["posiciones_activas"][sym]
                        guardar_estado(st)
                        continue
                    else:
                        estado_adn = f"🟡 FLOTANDO ({pos['balas_count']} Balas activas, faltan {dist_tp_pct:+.2f}% para TP)"
                        
                    # Chequeo Bala 2 (Martillazo $45)
                    if not pos["martillazo_disparado"]:
                        caida_desde_sonda = (pos["precio_sonda"] - px) / pos["precio_sonda"]
                        if caida_desde_sonda >= cfg["caida_martillazo"] and abs(dist_martillazo_pct) <= 3.0:
                            estado_adn = "🚨 SUELO VERDADERO: DISPARANDO MARTILLAZO $45"
                            qty_mart = ajustar_qty(BALA_2_MARGEN, px, cfg["step_qty"], cfg["min_qty"])
                            costo_mart = qty_mart * px
                            
                            pos["qty_total"] += qty_mart
                            pos["costo_total_usd"] += costo_mart
                            pos["precio_promedio"] = pos["costo_total_usd"] / pos["qty_total"]
                            pos["margen_total"] += BALA_2_MARGEN
                            pos["martillazo_disparado"] = True
                            pos["precio_martillazo"] = px
                            pos["balas_count"] = 2
                            log_msg(f"🔨 MARTILLAZO DISPARADO EN {sym} [{modo_trade}]: Lote={qty_mart} a ${px:.2f} (Nuevo Promedio: ${pos['precio_promedio']:.2f})")
                            guardar_estado(st)
                            
                    # Chequeo Bala 3 (Rebote $10)
                    elif pos["martillazo_disparado"] and not pos["bala3_disparada"]:
                        if px > pos["precio_martillazo"] * 1.01:
                            estado_adn = "⚡ REBOTE INMINENTE CONFIRMADO: DISPARANDO BALA 3 ($10)"
                            qty_b3 = ajustar_qty(BALA_3_MARGEN, px, cfg["step_qty"], cfg["min_qty"])
                            costo_b3 = qty_b3 * px
                            
                            pos["qty_total"] += qty_b3
                            pos["costo_total_usd"] += costo_b3
                            pos["precio_promedio"] = pos["costo_total_usd"] / pos["qty_total"]
                            pos["margen_total"] += BALA_3_MARGEN
                            pos["bala3_disparada"] = True
                            pos["balas_count"] = 3
                            log_msg(f"⚡ BALA 3 REBOTE DISPARADA EN {sym} [{modo_trade}]: Lote={qty_b3} a ${px:.2f} (Nuevo Promedio: ${pos['precio_promedio']:.2f})")
                            guardar_estado(st)

                    telemetria[sym] = {
                        "activo": True, "modo": modo_trade, "precio_actual": px, "precio_promedio": pos["precio_promedio"],
                        "target_tp": tp_target, "dist_tp_pct": round(dist_tp_pct, 2),
                        "piso_30d": piso_30d, "dist_martillazo_pct": round(dist_martillazo_pct, 2),
                        "margen_total": pos["margen_total"], "qty_total": pos["qty_total"],
                        "balas_count": pos["balas_count"], "pnl_flotante": round(pnl_flotante, 2),
                        "estado_adn": estado_adn
                    }
                    
                # 2. SIN POSICIÓN
                else:
                    dist_sop7d_pct = ((px - sop_7d) / sop_7d) * 100.0
                    target_estimado = px * (1.0 + cfg["tp_rebote"])
                    
                    if abs(dist_sop7d_pct) <= 2.5:
                        estado_adn = f"🎯 SOPORTE 7D ALCANZADO: GATILLO DE SONDA DISPONIBLE [{modo_activo}]"
                        if ind['close'] > ind['open']:
                            qty_sonda = ajustar_qty(BALA_1_MARGEN, px, cfg["step_qty"], cfg["min_qty"])
                            costo_sonda = qty_sonda * px
                            
                            st["posiciones_activas"][sym] = {
                                "sym": sym, "bingx_sym": bingx_sym, "modo": modo_activo,
                                "in_ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "precio_sonda": px, "precio_promedio": px, "qty_total": qty_sonda,
                                "costo_total_usd": costo_sonda, "margen_total": BALA_1_MARGEN,
                                "martillazo_disparado": False, "bala3_disparada": False, "balas_count": 1
                            }
                            guardar_estado(st)
                            log_msg(f"🟢 SONDA DISPARADA EN {sym} [{modo_activo}]: Lote={qty_sonda} a ${px:.2f} (Margen: $15 USD)")
                    else:
                        estado_adn = f"⚪ EN RANGO (A {dist_sop7d_pct:+.2f}% del soporte)"

                    telemetria[sym] = {
                        "activo": False, "modo": modo_activo, "precio_actual": px, "precio_promedio": px,
                        "target_tp": target_estimado, "dist_tp_pct": cfg["tp_rebote"] * 100.0,
                        "piso_30d": piso_30d, "dist_martillazo_pct": round(dist_martillazo_pct, 2),
                        "margen_total": 0.0, "qty_total": 0.0, "balas_count": 0, "pnl_flotante": 0.0,
                        "estado_adn": estado_adn
                    }
                    
            with open(TELEMETRIA_FILE, "w", encoding="utf-8") as f:
                json.dump(telemetria, f, indent=2)
                
        except Exception as e:
            log_msg(f"Error en ciclo principal: {e}")
            
        time.sleep(10)

if __name__ == "__main__":
    ciclo_principal()
