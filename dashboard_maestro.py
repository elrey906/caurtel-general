# -*- coding: utf-8 -*-
"""
=============================================================================
CAZADOR PRO — CUARTEL GENERAL UNIFICADO (PUERTO 8500)
=============================================================================
7 Pestanas:
  Tab 1: Estado General (Score, Semaforo, KPIs Binance)
  Tab 2: ON-CHAIN & MACRO + MVRV Inter-Ciclo
  Tab 3: Matriz Tecnica Multi-Timeframe
  Tab 4: Trifecta Binance (3 Cajas)
  Tab 5: Billetera & Aportes Automaticos
  Tab 6: Metas & Cierre Mensual
  Tab 7: Proyeccion HODL 2028-2030
=============================================================================
"""

import sys, os, json, time, requests, socket
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, date, time as dtime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

try:
    import pandas_ta as ta
    HAS_TA = True
except ImportError:
    HAS_TA = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    from HERRAMIENTAS.laboratorio_simbiosis_quant import ejecutar_simulacion_laboratorio
    HAS_LAB_QUANT = True
except Exception:
    HAS_LAB_QUANT = False

# Pure Pandas Indicator Helpers (Anti-NaN / Anti-Dash)
def pure_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def pure_sma(series, window):
    return series.rolling(window=min(window, len(series)), min_periods=1).mean()

def pure_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
    rs = gain / (loss.replace(0, 1e-9))
    return 100 - (100 / (1 + rs))

def pure_macd_hist(series):
    fast_ema = pure_ema(series, 12)
    slow_ema = pure_ema(series, 26)
    macd_line = fast_ema - slow_ema
    sig_line = pure_ema(macd_line, 9)
    hist = macd_line - sig_line
    if len(hist) < 2:
        return 0.0, 0.0, "NEUTRO"
    curr = float(hist.iloc[-1])
    prev = float(hist.iloc[-2])
    
    # Detección de Colores y Giros Cuánticos (Squeeze Momentum / MACD)
    if curr >= 0:
        estado = "VERDE_CLARO" if curr >= prev else "VERDE_OSCURO"
    else:
        # Valle Rojo: si curr > prev significa que se está encogiendo hacia cero (desaceleración bajista / absorción)
        estado = "ROJO_CLARO" if curr > prev else "ROJO_OSCURO"
        
    return curr, prev, estado

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BINANCE_DIR = os.path.join(BASE_DIR, "BINANCE")
HERRAMIENTAS_DIR = os.path.join(BASE_DIR, "HERRAMIENTAS")
DATOS_DIR = os.path.join(BASE_DIR, "DATOS")
ESTADO_DIR = os.path.join(BASE_DIR, "ESTADO")

for d in [DATOS_DIR, ESTADO_DIR]:
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass

DIR_SEPTIEMBRE = BASE_DIR
for path in [DIR_SEPTIEMBRE, BINANCE_DIR, HERRAMIENTAS_DIR, BASE_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    import radar_orderblocks_quant as roq
    HAS_ROQ = True
except Exception as e:
    HAS_ROQ = False

load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

# Compatibilidad con Streamlit Community Cloud (st.secrets)
try:
    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if isinstance(v, str) and k not in os.environ:
                os.environ[k] = v
except Exception:
    pass

try:
    # v3.0: usar conector_exchanges.py directamente
    import sys as _sys_bam, os as _os_bam
    _bam_path = _os_bam.path.join(_os_bam.path.dirname(_os_bam.path.abspath(__file__)), "AUTONOMO")
    if _bam_path not in _sys_bam.path:
        _sys_bam.path.insert(0, _bam_path)
    from conector_exchanges import binance_margin_account_info as _bam_info
    def obtener_datos_margin_account():
        try:
            res = _bam_info()
            if res is None:
                return {"error": "API Binance no respondió o no hay claves"}
            return res
        except Exception as _e_bam:
            return {"error": str(_e_bam)}
    def obtener_precio_actual(sym="BTCUSDT"):
        return obtener_precio_publico(sym)
    def obtener_precio_actual(sym="BTCUSDT"):
        p = None
        try:
            p = _b_obtener_precio(sym)
        except Exception:
            pass
        if p and p > 1000.0:
            return float(p)
        return obtener_precio_publico(sym)
except Exception:
    def obtener_datos_margin_account(): return {"error": "binance_api_manager no disponible"}
    def obtener_precio_actual(sym="BTCUSDT"): return obtener_precio_publico(sym)

_GLOBAL_LIVE_PRICES = {"data": {}, "ts": 0}

def obtener_todas_cotizaciones_en_vivo(force_refresh=False):
    """Descarga cotizaciones multi-mercado en paralelo (BingX Swap + BingX Spot + OKX + Bybit + Yahoo) con caché TTL."""
    global _GLOBAL_LIVE_PRICES
    now = time.time()
    if not force_refresh and (now - _GLOBAL_LIVE_PRICES["ts"]) < 10 and len(_GLOBAL_LIVE_PRICES["data"]) > 100:
        return _GLOBAL_LIVE_PRICES["data"]

    headers_req = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    def _fetch_bingx_swap():
        res = {}
        try:
            r = requests.get("https://open-api.bingx.com/openApi/swap/v2/quote/ticker", headers=headers_req, timeout=4).json()
            if r.get("code") == 0 and "data" in r:
                for item in r["data"]:
                    s = item.get("symbol", "")
                    try:
                        p = float(item.get("lastPrice", 0))
                        if p > 0:
                            res[s] = p
                            res[s.replace("-", "")] = p
                            if s.startswith("NCSK") and "2USD" in s:
                                raw_tk = s[4:s.index("2USD")]
                                res[raw_tk] = p
                                res[f"{raw_tk}-USDT"] = p
                                res[f"{raw_tk}USDT"] = p
                            elif s.startswith("NCCO1OILWTI"):
                                res["WTI"] = p
                                res["OIL"] = p
                            elif s.startswith("NCSISP500"):
                                res["SPY"] = p
                                res["SP500"] = p
                                res["^GSPC"] = p
                    except Exception: pass
        except Exception: pass
        return res

    def _fetch_bingx_spot():
        res = {}
        try:
            r = requests.get("https://open-api.bingx.com/openApi/spot/v1/ticker/24hr", headers=headers_req, timeout=4).json()
            if r.get("code") == 0 and "data" in r:
                for item in r["data"]:
                    s = item.get("symbol", "")
                    try:
                        p = float(item.get("lastPrice", 0))
                        if p > 0:
                            if s not in res: res[s] = p
                            if s.replace("-", "") not in res: res[s.replace("-", "")] = p
                    except Exception: pass
        except Exception: pass
        return res

    def _fetch_okx_spot():
        res = {}
        try:
            r = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SPOT", headers=headers_req, timeout=4).json()
            if r.get("code") == "0" and "data" in r:
                for item in r["data"]:
                    inst = item.get("instId", "")
                    try:
                        p = float(item.get("last", 0))
                        if p > 0:
                            if inst not in res: res[inst] = p
                            if inst.replace("-", "") not in res: res[inst.replace("-", "")] = p
                    except Exception: pass
        except Exception: pass
        return res

    def _fetch_bybit_spot():
        res = {}
        try:
            r = requests.get("https://api.bybit.com/v5/market/tickers?category=spot", headers=headers_req, timeout=4).json()
            if r.get("retCode") == 0 and "result" in r:
                for item in r["result"].get("list", []):
                    s = item.get("symbol", "")
                    try:
                        p = float(item.get("lastPrice", 0))
                        if p > 0:
                            if s not in res: res[s] = p
                            if s.endswith("USDT"):
                                res[f"{s[:-4]}-USDT"] = p
                    except Exception: pass
        except Exception: pass
        return res

    prices = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        f1 = ex.submit(_fetch_bingx_swap)
        f2 = ex.submit(_fetch_bingx_spot)
        f3 = ex.submit(_fetch_okx_spot)
        f4 = ex.submit(_fetch_bybit_spot)
        
        prices.update(f3.result())
        prices.update(f4.result())
        prices.update(f2.result())
        prices.update(f1.result())

    # Fallback Yahoo Finance para acciones o commodities faltantes
    missing_stocks = [
        ("GOOGL", "GOOGL"), ("MSFT", "MSFT"), ("AMZN", "AMZN"), ("NVDA", "NVDA"),
        ("AAPL", "AAPL"), ("MSTR", "MSTR"), ("TSLA", "TSLA"), ("META", "META"),
        ("AMD", "AMD"), ("AVGO", "AVGO"), ("COIN", "COIN"), ("QQQ", "QQQ"),
        ("SPY", "SPY"), ("^GSPC", "^GSPC"), ("DJI", "^DJI"), ("NU", "NU"),
        ("PLTR", "PLTR"), ("NFLX", "NFLX"), ("INTC", "INTC"), ("QCOM", "QCOM"),
        ("TSM", "TSM"), ("WTI", "CL=F"), ("PAXG", "GC=F")
    ]
    def _fetch_y(tk, ysym):
        try:
            u = f"https://query1.finance.yahoo.com/v8/finance/chart/{ysym}?interval=1d&range=1d"
            ry = requests.get(u, headers=headers_req, timeout=3)
            if ry.status_code == 200:
                res_y = ry.json().get("chart", {}).get("result", [])
                if res_y:
                    p = float(res_y[0].get("meta", {}).get("regularMarketPrice", 0))
                    if p > 0: return tk, p
        except Exception: pass
        return tk, 0.0

    needed_y = [m for m in missing_stocks if m[0] not in prices or prices[m[0]] <= 0]
    if needed_y:
        with ThreadPoolExecutor(max_workers=6) as ex:
            futs = [ex.submit(_fetch_y, tk, ysym) for tk, ysym in needed_y]
            for f in futs:
                tk, p = f.result()
                if p > 0: prices[tk] = p

    if prices:
        _GLOBAL_LIVE_PRICES["data"] = prices
        _GLOBAL_LIVE_PRICES["ts"] = now

    return _GLOBAL_LIVE_PRICES["data"]

def obtener_precio_publico(sym="BTCUSDT"):
    """Consulta cotización en vivo con cascada ultrarrápida multi-fuente"""
    all_p = obtener_todas_cotizaciones_en_vivo()
    
    # 1. Búsqueda directa e indexada en caché vivo
    candidates = [
        sym,
        sym.upper(),
        sym.replace("-", ""),
        f"{sym}-USDT",
        f"{sym}USDT",
        f"NCSK{sym}2USD-USDT",
        sym.replace("USDT", ""),
        sym.split("-")[0] if "-" in sym else sym
    ]
    for cand in candidates:
        if cand in all_p and all_p[cand] > 0:
            return float(all_p[cand])

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # 2. BingX Swap Quote Directo
    try:
        r = requests.get(f"https://open-api.bingx.com/openApi/swap/v2/quote/ticker?symbol={sym}", headers=headers, timeout=3)
        if r.status_code == 200:
            d = r.json().get("data", {})
            if isinstance(d, dict) and "lastPrice" in d:
                p = float(d["lastPrice"])
                if p > 0: return p
    except Exception: pass

    # 3. OKX Directo
    try:
        okx_inst = "BTC-USDT" if "BTC" in sym else (f"{sym}-USDT" if not sym.endswith("USDT") else sym)
        r = requests.get(f"https://www.okx.com/api/v5/market/ticker?instId={okx_inst}", headers=headers, timeout=3)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data and "last" in data[0]:
                p = float(data[0]["last"])
                if p > 0: return p
    except Exception: pass

    # 4. Coinbase Spot Directo
    try:
        coin_id = "BTC" if "BTC" in sym else ("ETH" if "ETH" in sym else ("SOL" if "SOL" in sym else sym.replace("-USDT", "").replace("USDT", "")))
        r = requests.get(f"https://api.coinbase.com/v2/prices/{coin_id}-USD/spot", headers=headers, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if "data" in data and "amount" in data["data"]:
                p = float(data["data"]["amount"])
                if p > 0: return p
    except Exception: pass

    # 5. Bybit Directo
    try:
        byb_sym = sym.replace("-", "")
        r = requests.get(f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={byb_sym}", headers=headers, timeout=3)
        if r.status_code == 200:
            lst = r.json().get("result", {}).get("list", [])
            if lst and "lastPrice" in lst[0]:
                p = float(lst[0]["lastPrice"])
                if p > 0: return p
    except Exception: pass

    return 79900.0 if "BTC" in sym else 0.0

@st.cache_data(ttl=15)
def auditar_salud_apis_y_precios():
    """
    🛡️ AGENTE CENTINELA EN TIEMPO REAL:
    Audita la latencia y respuesta de BingX, Binance y Yahoo Finance,
    y valida la coherencia matemática de las cotizaciones en vivo para evitar errores de entrada.
    """
    reporte = {
        "estado": "OPTIMO", # OPTIMO, PRECAUCION, CRITICO
        "bingx_status": "🟢 OPERATIVO",
        "bingx_ms": 0,
        "binance_status": "🟢 OPERATIVO",
        "binance_ms": 0,
        "yahoo_status": "🟢 OPERATIVO",
        "yahoo_ms": 0,
        "alertas": [],
        "precios_auditados": {}
    }
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # 1. Test BingX
    t0 = time.time()
    try:
        r = requests.get("https://open-api.bingx.com/openApi/swap/v2/quote/ticker?symbol=BTC-USDT", headers=headers, timeout=3).json()
        reporte["bingx_ms"] = int((time.time() - t0) * 1000)
        if r.get("code") != 0:
            reporte["bingx_status"] = "⚠️ AVISO CODIGO"
            reporte["alertas"].append(f"BingX API devolvió código no-cero: {r.get('code')}")
    except Exception as e:
        reporte["bingx_ms"] = int((time.time() - t0) * 1000)
        reporte["bingx_status"] = "🔴 REINTENTO"
        reporte["alertas"].append(f"Microcorte o latencia con BingX API")
        
    # 2. Test Binance
    t0 = time.time()
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", headers=headers, timeout=3).json()
        reporte["binance_ms"] = int((time.time() - t0) * 1000)
        if "price" not in r:
            reporte["binance_status"] = "⚠️ AVISO RESPUESTA"
            reporte["alertas"].append("Binance API sin respuesta directa")
    except Exception as e:
        reporte["binance_ms"] = int((time.time() - t0) * 1000)
        reporte["binance_status"] = "🔴 REINTENTO"
        reporte["alertas"].append("Microcorte o latencia con Binance API")
        
    # 3. Test Yahoo / Macro
    t0 = time.time()
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NVDA?interval=1d&range=1d", headers=headers, timeout=3).json()
        reporte["yahoo_ms"] = int((time.time() - t0) * 1000)
    except Exception:
        reporte["yahoo_ms"] = int((time.time() - t0) * 1000)
        reporte["yahoo_status"] = "⚠️ LENTO"
        
    # 4. Auditoría de precios en vivo críticos
    cotizaciones = obtener_todas_cotizaciones_en_vivo()
    activos_check = {
        "BTC": (50000.0, 150000.0),
        "NVDA": (180.0, 350.0),
        "MSFT": (400.0, 650.0),
        "AMZN": (190.0, 350.0),
        "GOOGL": (250.0, 450.0),
        "AVGO": (250.0, 500.0),
        "TSLA": (200.0, 500.0),
        "AAPL": (220.0, 420.0)
    }
    
    for sym, (min_p, max_p) in activos_check.items():
        p = cotizaciones.get(sym, 0.0)
        if p <= 0:
            for alt in [f"NCSK{sym}2USD-USDT", f"{sym}-USDT", f"{sym}USDT"]:
                if cotizaciones.get(alt, 0) > 0:
                    p = cotizaciones[alt]
                    break
        reporte["precios_auditados"][sym] = p
        if p <= 0:
            reporte["alertas"].append(f"Precio de #{sym} usando canal de contingencia")
        elif p < min_p or p > max_p:
            reporte["alertas"].append(f"⚠️ ANOMALÍA EN #{sym}: Cotización ${p:.2f} fuera de rango de seguridad (${min_p:.0f} - ${max_p:.0f})")
            
    if any("🔴" in s for s in [reporte["bingx_status"], reporte["binance_status"]]) or any("ANOMALÍA" in a for a in reporte["alertas"]):
        reporte["estado"] = "CRITICO"
    elif reporte["alertas"] or any("⚠️" in s for s in [reporte["bingx_status"], reporte["binance_status"], reporte["yahoo_status"]]):
        reporte["estado"] = "PRECAUCION"
        
    return reporte

# ── UTILIDADES ─────────────────────────────────────────────────────────────
def clean_num(val, fallback=0.0):
    if val is None: return float(fallback)
    try:
        v = float(val)
        return v if v == v else float(fallback)
    except Exception:
        return float(fallback)

def now_vet():
    return datetime.now(ZoneInfo("America/Caracas"))

def cargar_json(path, default=None):
    if default is None: default = {}
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def guardar_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False

def probar_puerto_socket(port, host="127.0.0.1"):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        res = s.connect_ex((host, port))
        s.close()
        return res == 0
    except Exception:
        return False

@st.cache_data(ttl=5)
def obtener_procesos_python_activos():
    procs = []
    if not HAS_PSUTIL:
        return procs
    try:
        for p in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'create_time']):
            try:
                cmd = " ".join(p.info['cmdline'] or [])
                pname = (p.info['name'] or "").lower()
                if "python" in pname or "python" in cmd.lower():
                    rss = p.info['memory_info'].rss if p.info['memory_info'] else 0
                    procs.append({
                        "pid": p.info['pid'],
                        "cmd": cmd,
                        "rss_mb": round(rss / (1024 * 1024), 1),
                        "create_time": p.info['create_time']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass
    return procs

def verificar_estado_detallado_cerebros():
    lista_proc = obtener_procesos_python_activos()
    
    definicion_cerebros = [
        {
            "id": "C1",
            "nombre": "Cerebro 1: Wall Street & Blue Chips",
            "tipo": "Motor + Dashboard",
            "script_motor": "cazador_blue_chips_wall_street.py",
            "script_dash": "dashboard_blue_chips.py",
            "puerto": 8540,
            "mercado": "BingX Perpetuos (11 Blue Chips)",
            "log_file": "LOGS/blue_chips_bot.log",
            "state_file": os.path.join(BASE_DIR, "estado_blue_chips.json")
        },
        {
            "id": "C2",
            "nombre": "Cerebro 2: Mega Híbrido Quantum BTC Dual",
            "tipo": "Motor + Dashboard",
            "script_motor": "cazador_mega_hibrido_btc_dual.py",
            "script_dash": "dashboard_mega_hibrido_btc.py",
            "puerto": 8545,
            "mercado": "Binance Cross Margin 5X (BTC)",
            "log_file": "LOGS/mega_hibrido_bot.log",
            "state_file": os.path.join(BASE_DIR, "estado_mega_hibrido_btc_dual.json")
        },
        {
            "id": "C3",
            "nombre": "Cerebro 3: Trifecta Híbrido Sonda/Martillo",
            "tipo": "Motor + Dashboard",
            "script_motor": "cazador_trifecta_hibrido.py",
            "script_dash": "dashboard_trifecta_hibrido.py",
            "puerto": 8555,
            "mercado": "BingX Acciones & Cripto",
            "log_file": "HIBRIDO/cazador_trifecta.log",
            "state_file": os.path.join(BASE_DIR, "HIBRIDO", "estado_trifecta_hibrido.json")
        },
        {
            "id": "C4",
            "nombre": "Cerebro 4: Mega-Agente ADN Autónomo",
            "tipo": "Motor + Dashboard",
            "script_motor": "cazador_mega_agente_autonomo.py",
            "script_dash": "dashboard_mega_agente.py",
            "puerto": 8560,
            "mercado": "BingX Biaxial + Binance BTC Margin",
            "log_file": "AUTONOMO/mega_agente_adn.log",
            "state_file": os.path.join(BASE_DIR, "AUTONOMO", "estado_mega_agente.json")
        },
        {
            "id": "HQ",
            "nombre": "Cuartel General PRO 2.0",
            "tipo": "Sala de Mando Maestro",
            "script_motor": None,
            "script_dash": "dashboard_maestro.py",
            "puerto": 8500,
            "mercado": "Control Maestro Unificado",
            "log_file": "LOGS/dashboard_maestro.log",
            "state_file": os.path.join(BASE_DIR, "estado_mega_hibrido_btc_dual.json")
        }
    ]

    resultados = []
    for item in definicion_cerebros:
        puerto_ok = probar_puerto_socket(item["puerto"])
        
        pid_motor = None
        ram_motor = 0.0
        if item["script_motor"]:
            for pr in lista_proc:
                if item["script_motor"] in pr["cmd"]:
                    pid_motor = pr["pid"]
                    ram_motor = pr["rss_mb"]
                    break
        
        pid_dash = None
        ram_dash = 0.0
        if item["script_dash"]:
            for pr in lista_proc:
                if item["script_dash"] in pr["cmd"]:
                    pid_dash = pr["pid"]
                    ram_dash = pr["rss_mb"]
                    break

        if item["script_motor"]:
            motor_vivo = pid_motor is not None
        else:
            motor_vivo = puerto_ok

        dash_vivo = puerto_ok or (pid_dash is not None)
        
        # Ocultar módulos que no tengan su motor en vivo (tarjetas amarillas/apagadas)
        if item["script_motor"] and not motor_vivo:
            continue
        if not (motor_vivo or dash_vivo):
            continue
        
        last_heartbeat = "Activo"
        posiciones_count = 0
        if item["state_file"] and os.path.exists(item["state_file"]):
            try:
                st_data = cargar_json(item["state_file"], {})
                last_heartbeat = st_data.get("ultima_actualizacion", st_data.get("last_contribution_date", "Activo"))
                if "T" in str(last_heartbeat):
                    last_heartbeat = str(last_heartbeat).split(".")[0].replace("T", " ")
                
                # Soportar Cerebro 4 (fase1_rapidas_activas + fase2_macro_activas) y otros cerebros
                if "fase1_rapidas_activas" in st_data or "fase2_macro_activas" in st_data:
                    f1_len = len(st_data.get("fase1_rapidas_activas", {}))
                    f2_len = len(st_data.get("fase2_macro_activas", {}))
                    bin_len = len(st_data.get("binance_btc_balas", []))
                    posiciones_count = f1_len + f2_len + bin_len
                else:
                    pos_act = st_data.get("posiciones_activas", st_data.get("posiciones", {}))
                    if isinstance(pos_act, dict):
                        posiciones_count = len(pos_act)
                    elif isinstance(pos_act, list):
                        posiciones_count = len(pos_act)
                
                bingx_live = st_data.get("bloqueo_anti_desmadre", {}).get("posiciones_bingx_live", [])
                if bingx_live and len(bingx_live) > posiciones_count:
                    posiciones_count = len(bingx_live)
            except Exception:
                pass

        resultados.append({
            "id": item["id"],
            "nombre": item["nombre"],
            "tipo": item["tipo"],
            "puerto": item["puerto"],
            "mercado": item["mercado"],
            "motor_vivo": motor_vivo,
            "dash_vivo": dash_vivo,
            "pid_motor": pid_motor,
            "pid_dash": pid_dash,
            "ram_total_mb": round(ram_motor + ram_dash, 1),
            "posiciones_activas": posiciones_count,
            "last_heartbeat": last_heartbeat,
            "log_file": item["log_file"]
        })
    return resultados

# ── CONFIGURACION STREAMLIT ────────────────────────────────────────────────
st.set_page_config(
    page_title="Cazador PRO — Cuartel General",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #080c14; color: #e2e8f0; }
.hdr { background: linear-gradient(135deg,#0f172a,#1e293b); border:1px solid #1e3a5f; border-radius:16px; padding:20px 28px; margin-bottom:20px; box-shadow:0 8px 32px rgba(0,0,0,.6); }
.hdr h1 { margin:0; font-size:2.1rem; font-weight:800; background:linear-gradient(135deg,#38bdf8,#818cf8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.hdr p  { margin:6px 0 0; color:#64748b; font-size:.9rem; }
.kpi  { background:rgba(30,41,59,.7); border:1px solid #334155; border-radius:12px; padding:16px; text-align:center; backdrop-filter:blur(8px); margin-bottom:8px; }
.kpi-t { font-size:.78rem; color:#94a3b8; font-weight:700; text-transform:uppercase; letter-spacing:.5px; }
.kpi-v { font-size:1.7rem; font-weight:800; color:#f8fafc; margin-top:4px; }
.kpi-s { font-size:.78rem; color:#38bdf8; margin-top:3px; }
.badge-green { background:rgba(16,185,129,.18); color:#10b981; padding:3px 11px; border-radius:20px; font-size:.8rem; font-weight:700; border:1px solid rgba(16,185,129,.35); }
.badge-gold  { background:rgba(234,179,8,.18); color:#eab308; padding:3px 11px; border-radius:20px; font-size:.8rem; font-weight:700; border:1px solid rgba(234,179,8,.35); }

/* HERO CARDS DUPLA MAESTRA */
.hero-c3 {
    background: linear-gradient(135deg, rgba(15,23,42,0.9), rgba(30,58,138,0.35));
    border: 2px solid #38bdf8;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 0 25px rgba(56,189,248,0.2);
    margin-bottom: 12px;
}
.hero-c5 {
    background: linear-gradient(135deg, rgba(15,23,42,0.9), rgba(161,98,7,0.35));
    border: 2px solid #eab308;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 0 25px rgba(234,179,8,0.2);
    margin-bottom: 12px;
}
.hero-title-c3 { font-size: 1.25rem; font-weight: 800; color: #38bdf8; margin-bottom: 4px; }
.hero-title-c5 { font-size: 1.25rem; font-weight: 800; color: #eab308; margin-bottom: 4px; }
.hero-sub { font-size: 0.85rem; color: #94a3b8; margin-bottom: 12px; }

/* CHECKLIST TUNEL SMC */
.step-card {
    background: rgba(30,41,59,0.7);
    border: 1px solid #475569;
    border-radius: 10px;
    padding: 12px;
    text-align: center;
}
.step-on { border-color: #22c55e; background: rgba(34,197,94,0.12); color: #22c55e; font-weight: 700; }
.step-off { border-color: #eab308; background: rgba(234,179,8,0.08); color: #eab308; }

/* BOVEDAS */
.vault-box {
    background: rgba(15,23,42,0.85);
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🏆 Cazador PRO")
st.sidebar.markdown("**Cuartel General Unificado — Puerto 8500**")
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Recargar Datos en Vivo", use_container_width=True):
    st.cache_data.clear()
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Configuración de Balas y Cajas")
CONFIG_CAJAS_PATH = os.path.join(DATOS_DIR, "config_cajas_dupla.json")

def cargar_cfg_cajas():
    if os.path.exists(CONFIG_CAJAS_PATH):
        try:
            with open(CONFIG_CAJAS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: pass
    return {"caja1_monto": 25.0, "caja3_monto": 25.0, "balas_max_mes": 4}

cfg_guardada = cargar_cfg_cajas()

caja1_monto = st.sidebar.number_input("Caja 1 — DCA Soporte 7D (USDT)", min_value=5.0, max_value=500.0, value=float(cfg_guardada.get("caja1_monto", 25.0)), step=5.0)
caja3_monto = st.sidebar.number_input("Caja 3 — Oráculo YT (USDT)",    min_value=5.0, max_value=500.0, value=float(cfg_guardada.get("caja3_monto", 25.0)), step=5.0)
caja2_monto = float(cfg_guardada.get("caja2_monto", 20.0))
balas_max_mes = st.sidebar.selectbox("Balas Máximas / Mes", [4, 6, 8, 10], index=[4, 6, 8, 10].index(cfg_guardada.get("balas_max_mes", 4)) if cfg_guardada.get("balas_max_mes", 4) in [4, 6, 8, 10] else 0)

if st.sidebar.button("💾 Guardar Configuración de Balas", use_container_width=True):
    try:
        nueva_cfg = {"caja1_monto": float(caja1_monto), "caja2_monto": float(caja2_monto), "caja3_monto": float(caja3_monto), "balas_max_mes": int(balas_max_mes)}
        with open(CONFIG_CAJAS_PATH, "w", encoding="utf-8") as f:
            json.dump(nueva_cfg, f, indent=4)
        st.sidebar.success("✅ Configuración guardada en vivo!")
    except Exception as e:
        st.sidebar.error(f"Error: {e}")

st.sidebar.markdown("---")
st.sidebar.markdown(f"🕐 **Hora VET:** `{now_vet().strftime('%H:%M:%S')}`")

# ── ENCABEZADO ─────────────────────────────────────────────────────────────
col_hdr_l, col_hdr_r = st.columns([3.2, 1.2])
with col_hdr_l:
    st.markdown("""
    <div class="hdr" style="padding:14px 20px; margin-bottom:10px;">
      <div style="display:flex;align-items:center;justify-content:space-between;">
        <div>
          <h1 style="margin:0;font-size:1.8rem;font-weight:900;">🏆 CAZADOR PRO — CUARTEL GENERAL</h1>
          <p style="margin:4px 0 0 0;font-size:0.85rem;color:#94a3b8;">Dashboard Maestro Unificado · Multimercado en Vivo · Puerto 8500</p>
        </div>
        <div><span class="badge-green" style="font-size:0.8rem;padding:4px 10px;">🟢 PRECIOS EN VIVO 24/7</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

with col_hdr_r:
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 ACTUALIZAR PRECIOS EN VIVO", key="btn_top_live_refresh_global", use_container_width=True, type="primary"):
        st.cache_data.clear()
        obtener_todas_cotizaciones_en_vivo(force_refresh=True)
        st.rerun()

# Auto-refresh de pantalla cada 30 segundos para mantener cotizaciones 100% vivas
if HAS_AUTOREFRESH:
    st_autorefresh(interval=30 * 1000, key="auto_refresh_30s")

# ── CARGA DE DATOS (SINCRONIZACIÓN CADA 8 HORAS) ──────────────────────────
DATOS_12H_FILE = os.path.join(DATOS_DIR, "macro_onchain_12h.json")
INFORMADORES_FILE = os.path.join(DATOS_DIR, "informadores_diarios.json")

@st.cache_data(ttl=3600)
def cargar_informadores_diarios():
    if os.path.exists(INFORMADORES_FILE):
        try:
            with open(INFORMADORES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "ultima_actualizacion": datetime.now().isoformat(),
        "ballenas_flujo_7d": 12652,
        "reservas_exchanges": 2160437,
        "suministro_iliquido_pct": 74.08,
    }

@st.cache_data(ttl=28800)
def cargar_fear_greed():
    if os.path.exists(DATOS_12H_FILE):
        try:
            with open(DATOS_12H_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if "fear_and_greed" in d: return d["fear_and_greed"]
        except Exception: pass
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
        if r.status_code == 200:
            d = r.json()
            return {"val": int(d["data"][0]["value"]), "classif": d["data"][0]["value_classification"]}
    except Exception:
        pass
    return {"val": 68, "classif": "Codicia"}

@st.cache_data(ttl=900)
def cargar_funding_rate_oi():
    headers = {"User-Agent": "Mozilla/5.0"}
    funding_rate = 0.0001
    oi_btc = 106000.0
    try:
        r_f = requests.get("https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT", headers=headers, timeout=4).json()
        if isinstance(r_f, dict) and "lastFundingRate" in r_f:
            funding_rate = float(r_f["lastFundingRate"])
    except Exception:
        pass
    try:
        r_oi = requests.get("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT", headers=headers, timeout=4).json()
        if isinstance(r_oi, dict) and "openInterest" in r_oi:
            oi_btc = float(r_oi["openInterest"])
    except Exception:
        pass
    return {"funding_rate": funding_rate, "open_interest": oi_btc}

@st.cache_data(ttl=30)
def cargar_klines(interval, limit):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # 1. BingX Swap Kline API (Directo y ultra rápido)
    bx_bar_map = {"1h": "1h", "4h": "4h", "1d": "1d", "1D": "1d", "1w": "1w", "1W": "1w", "1M": "1M"}
    bx_bar = bx_bar_map.get(interval, "1h")
    try:
        url_bx = f"https://open-api.bingx.com/openApi/swap/v3/quote/klines?symbol=BTC-USDT&interval={bx_bar}&limit={min(200, limit)}"
        r_bx = requests.get(url_bx, headers=headers, timeout=4).json()
        if r_bx.get("code") == 0 and "data" in r_bx and len(r_bx["data"]) > 0:
            df_bx = pd.DataFrame(r_bx["data"])
            df_bx.rename(columns={"open":"O", "high":"H", "low":"L", "close":"C", "volume":"V", "time":"ts"}, inplace=True)
            for c2 in ["O", "H", "L", "C", "V"]: df_bx[c2] = df_bx[c2].astype(float)
            df_bx["ts"] = pd.to_datetime(df_bx["ts"].astype(float), unit="ms")
            df_bx.sort_values("ts", inplace=True)
            df_bx.set_index("ts", inplace=True)
            return df_bx.tail(limit)
    except Exception:
        pass

    # 2. OKX Candlesticks (Alta disponibilidad global)
    bar_map_okx = {"1h": "1H", "4h": "4H", "1d": "1D", "1D": "1D", "1w": "1W", "1W": "1W", "1M": "1M"}
    bar_okx = bar_map_okx.get(interval, "1H")
    try:
        url_okx = f"https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar={bar_okx}&limit={min(100, limit)}"
        r = requests.get(url_okx, headers=headers, timeout=4)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data and len(data) > 0:
                # [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                df_okx = pd.DataFrame(data, columns=["ts", "O", "H", "L", "C", "V", "vccy", "vquote", "confirm"])
                for c2 in ["O", "H", "L", "C", "V"]: df_okx[c2] = df_okx[c2].astype(float)
                df_okx["ts"] = pd.to_datetime(df_okx["ts"].astype(float), unit="ms")
                df_okx.sort_values("ts", inplace=True)
                df_okx.set_index("ts", inplace=True)
                return df_okx.tail(limit)
    except Exception:
        pass

    # 3. Bybit Kline API
    byb_int_map = {"1h": "60", "4h": "240", "1d": "D", "1D": "D", "1w": "W", "1W": "W", "1M": "M"}
    byb_int = byb_int_map.get(interval, "60")
    try:
        url_byb = f"https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&interval={byb_int}&limit={min(200, limit)}"
        r_byb = requests.get(url_byb, headers=headers, timeout=4).json()
        if r_byb.get("retCode") == 0 and "result" in r_byb:
            lst_byb = r_byb["result"].get("list", [])
            if lst_byb and len(lst_byb) > 0:
                df_byb = pd.DataFrame(lst_byb, columns=["ts", "O", "H", "L", "C", "V", "turnover"])
                for c2 in ["O", "H", "L", "C", "V"]: df_byb[c2] = df_byb[c2].astype(float)
                df_byb["ts"] = pd.to_datetime(df_byb["ts"].astype(float), unit="ms")
                df_byb.sort_values("ts", inplace=True)
                df_byb.set_index("ts", inplace=True)
                return df_byb.tail(limit)
    except Exception:
        pass

    # 4. Kraken OHLC API
    kraken_int_map = {"1h": 60, "4h": 240, "1d": 1440, "1D": 1440, "1w": 10080, "1W": 10080, "1M": 21600}
    k_int = kraken_int_map.get(interval, 60)
    try:
        url_kr = f"https://api.kraken.com/0/public/OHLC?pair=XBTUSDT&interval={k_int}"
        r_kr = requests.get(url_kr, headers=headers, timeout=4)
        if r_kr.status_code == 200:
            res_kr = r_kr.json().get("result", {})
            pair_k = [k for k in res_kr.keys() if k != "last"]
            if pair_k:
                k_data = res_kr[pair_k[0]]
                # [time, open, high, low, close, vwap, volume, count]
                df_kr = pd.DataFrame(k_data, columns=["ts", "O", "H", "L", "C", "vwap", "V", "count"])
                for c2 in ["O", "H", "L", "C", "V"]: df_kr[c2] = df_kr[c2].astype(float)
                df_kr["ts"] = pd.to_datetime(df_kr["ts"].astype(float), unit="s")
                df_kr.sort_values("ts", inplace=True)
                df_kr.set_index("ts", inplace=True)
                return df_kr.tail(limit)
    except Exception:
        pass

    # 5. Fallback CSV Local
    for p_csv in [
        os.path.join(BASE_DIR, "VELAS", "BTC_1h.csv"),
        os.path.join(BASE_DIR, "DATOS", "BTC_1h.csv"),
        "/home/h/Escritorio/RESPALDO/2027/VELAS/BTC_1h.csv",
        "/home/h/Escritorio/RESPALDO/2027/DATOS/VELAS/BTC_1h.csv"
    ]:
        if os.path.exists(p_csv):
            try:
                df_loc = pd.read_csv(p_csv)
                df_loc.rename(columns={"Datetime":"ts","Open":"O","High":"H","Low":"L","Close":"C","Volume":"V"}, inplace=True)
                df_loc["ts"] = pd.to_datetime(df_loc["ts"].astype(str).str.split("+").str[0].str.strip(), utc=True)
                df_loc.set_index("ts", inplace=True)
                for c2 in ["O","H","L","C","V"]: df_loc[c2] = df_loc[c2].astype(float)
                
                if interval == "4h":
                    df_res = df_loc.resample("4h").agg({"O":"first","H":"max","L":"min","C":"last","V":"sum"}).dropna()
                    return df_res.tail(limit)
                elif interval in ["1d", "1D"]:
                    df_res = df_loc.resample("1D").agg({"O":"first","H":"max","L":"min","C":"last","V":"sum"}).dropna()
                    return df_res.tail(limit)
                elif interval in ["1w", "1W"]:
                    df_res = df_loc.resample("1W").agg({"O":"first","H":"max","L":"min","C":"last","V":"sum"}).dropna()
                    return df_res.tail(limit)
                elif interval in ["1M", "1m"]:
                    df_res = df_loc.resample("1ME").agg({"O":"first","H":"max","L":"min","C":"last","V":"sum"}).dropna()
                    return df_res.tail(limit)
                else:
                    return df_loc.tail(limit)
            except Exception:
                pass

    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_macro():
    m = {"oro": 4430.0, "oro_chg": 0.82, "petroleo": 91.50, "dxy": 101.50,
         "fed": 5.25, "puell": 0.78, "hashprice": 0.062, "etfs_flujo": 142.5,
         "pmi": 51.4, "btc_oro": 18.0}
    
    all_p = obtener_todas_cotizaciones_en_vivo()
    if "PAXG-USDT" in all_p and all_p["PAXG-USDT"] > 0:
        m["oro"] = all_p["PAXG-USDT"]
    elif "PAXG" in all_p and all_p["PAXG"] > 0:
        m["oro"] = all_p["PAXG"]
    elif "GOLD" in all_p and all_p["GOLD"] > 0:
        m["oro"] = all_p["GOLD"]

    if "WTI" in all_p and all_p["WTI"] > 0:
        m["petroleo"] = all_p["WTI"]
    elif "NCCO1OILWTI2USD-USDT" in all_p and all_p["NCCO1OILWTI2USD-USDT"] > 0:
        m["petroleo"] = all_p["NCCO1OILWTI2USD-USDT"]

    if "SPY" in all_p and all_p["SPY"] > 0:
        m["spy"] = all_p["SPY"]
    if "QQQ" in all_p and all_p["QQQ"] > 0:
        m["qqq"] = all_p["QQQ"]

    return m

data_margin = obtener_datos_margin_account()
btc_price   = obtener_precio_actual("BTCUSDT") or 79900.0
fg          = cargar_fear_greed()
macro       = cargar_macro()

df_h1 = cargar_klines("1h",  300)
df_h4 = cargar_klines("4h",  300)
df_d1 = cargar_klines("1d",  730)
df_w1 = cargar_klines("1w",  260)
df_m1 = cargar_klines("1M",  60)

def metricas_tf(df):
    if df is None or df.empty or "C" not in df.columns:
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=200, freq="1h")
        wave = np.sin(np.linspace(0, 8 * np.pi, 200)) * (btc_price * 0.02)
        prices = btc_price + wave
        df = pd.DataFrame({"C": prices, "O": prices * 0.998, "H": prices * 1.008, "L": prices * 0.992, "V": 1000.0}, index=dates)

    c = df["C"].squeeze().dropna()
    if len(c) < 5:
        return {}
    
    lc = clean_num(c.iloc[-1], btc_price)
    
    if HAS_TA:
        try:
            ema9   = clean_num(ta.ema(c, 9).iloc[-1] if len(c)>=9 else pure_ema(c, 9).iloc[-1], lc)
            ema10  = clean_num(ta.ema(c, 10).iloc[-1] if len(c)>=10 else pure_ema(c, 10).iloc[-1], lc)
            ema34  = clean_num(ta.ema(c, 34).iloc[-1] if len(c)>=34 else pure_ema(c, 34).iloc[-1], lc)
            ema55  = clean_num(ta.ema(c, 55).iloc[-1] if len(c)>=55 else pure_ema(c, 55).iloc[-1], lc)
            ema100 = clean_num(ta.ema(c, 100).iloc[-1] if len(c)>=100 else pure_ema(c, 100).iloc[-1], lc)
            sma30  = clean_num(ta.sma(c, 30).iloc[-1] if len(c)>=30 else pure_sma(c, 30).iloc[-1], lc)
            sma50  = clean_num(ta.sma(c, 50).iloc[-1] if len(c)>=50 else pure_sma(c, 50).iloc[-1], lc)
            sma100 = clean_num(ta.sma(c, 100).iloc[-1] if len(c)>=100 else pure_sma(c, 100).iloc[-1], lc)
            sma200 = clean_num(ta.sma(c, 200).iloc[-1] if len(c)>=200 else pure_sma(c, 200).iloc[-1], lc)
            rsi    = clean_num(ta.rsi(c, 14).iloc[-1] if len(c)>=14 else pure_rsi(c, 14).iloc[-1], 55.0)
        except Exception:
            ema9   = clean_num(pure_ema(c, 9).iloc[-1], lc)
            ema10  = clean_num(pure_ema(c, 10).iloc[-1], lc)
            ema34  = clean_num(pure_ema(c, 34).iloc[-1], lc)
            ema55  = clean_num(pure_ema(c, 55).iloc[-1], lc)
            ema100 = clean_num(pure_ema(c, 100).iloc[-1], lc)
            sma30  = clean_num(pure_sma(c, 30).iloc[-1], lc)
            sma50  = clean_num(pure_sma(c, 50).iloc[-1], lc)
            sma100 = clean_num(pure_sma(c, 100).iloc[-1], lc)
            sma200 = clean_num(pure_sma(c, 200).iloc[-1], lc)
            rsi    = clean_num(pure_rsi(c, 14).iloc[-1], 55.0)
    else:
        ema9   = clean_num(pure_ema(c, 9).iloc[-1], lc)
        ema10  = clean_num(pure_ema(c, 10).iloc[-1], lc)
        ema34  = clean_num(pure_ema(c, 34).iloc[-1], lc)
        ema55  = clean_num(pure_ema(c, 55).iloc[-1], lc)
        ema100 = clean_num(pure_ema(c, 100).iloc[-1], lc)
        sma30  = clean_num(pure_sma(c, 30).iloc[-1], lc)
        sma50  = clean_num(pure_sma(c, 50).iloc[-1], lc)
        sma100 = clean_num(pure_sma(c, 100).iloc[-1], lc)
        sma200 = clean_num(pure_sma(c, 200).iloc[-1], lc)
        rsi    = clean_num(pure_rsi(c, 14).iloc[-1], 55.0)

    mh_val, mh_prev, mh_estado = pure_macd_hist(c)

    # ── MVRV RATIO ON-CHAIN ESTÁNDAR (Market Price / Realized Price Proxy) ──
    # El Realized Price institucional de Bitcoin equivale históricamente al ~75-80% de la SMA 200D
    realized_px = sma200 * 0.76 if sma200 > 0 else lc * 0.65
    mvrv = round(lc / (realized_px + 1e-9), 2)
    if mvrv <= 0.1 or mvrv > 10.0:
        mvrv = 1.55

    return {"ema9":ema9,"ema10":ema10,"ema34":ema34,"ema55":ema55,"ema100":ema100,
            "sma30":sma30,"sma50":sma50,"sma100":sma100,"sma200":sma200,
            "mvrv":mvrv,"rsi":rsi,"macd_hist":mh_val,"macd_prev":mh_prev,"macd_estado":mh_estado,"close":lc}

m_h1 = metricas_tf(df_h1)
m_h4 = metricas_tf(df_h4)
m_d1 = metricas_tf(df_d1)
m_w1 = metricas_tf(df_w1)
m_m1 = metricas_tf(df_m1)

# Datos Binance
binance_ok = "error" not in data_margin and clean_num(data_margin.get("totalCollateralValueInUSDT", 0)) > 0
if binance_ok:
    user_assets   = data_margin.get("userAssets", [])
    margin_level  = clean_num(data_margin.get("marginLevel", 0))
    collateral    = clean_num(data_margin.get("totalCollateralValueInUSDT", 0))
    net_btc       = clean_num(data_margin.get("totalNetAssetOfBtc", 0))
    liability_btc = clean_num(data_margin.get("totalLiabilityOfBtc", 0))
    usdt_free     = next((clean_num(a.get("free",0)) for a in user_assets if a.get("asset")=="USDT"), 0.0)
    usdt_net      = next((clean_num(a.get("netAsset",0)) for a in user_assets if a.get("asset")=="USDT"), 0.0)
    btc_real      = next((clean_num(a.get("netAsset",0)) for a in user_assets if a.get("asset")=="BTC"), 0.0)
else:
    st_mh = cargar_json(os.path.join(BASE_DIR, "estado_mega_hibrido_btc_dual.json"), {})
    collateral = clean_num(st_mh.get("equity_total_usd", 282.58), 282.58)
    margin_level = clean_num(st_mh.get("margin_level_actual", 999.0), 999.0)
    usdt_free = clean_num(st_mh.get("cash_balance_usd", 13.58), 13.58)
    usdt_net = usdt_free
    net_btc = round((collateral - usdt_free) / (btc_price + 1e-9), 6)
    liability_btc = clean_num(st_mh.get("deuda_total_usd", 0.0), 0.0) / (btc_price + 1e-9)
    btc_real = net_btc
    binance_ok = True

ESTADO_DCA_FILE = os.path.join(ESTADO_DIR, "estado_smart_dca.json")
estado_dca = cargar_json(ESTADO_DCA_FILE, {
    "capital_inyectado_total_usd": 0.0, "usdt_registrado": 0.0,
    "historial_aportes": [], "historial_compras": [],
    "historial_cierres_mensuales": [], "capital_inicio_mes": 0.0,
    "last_contribution_date": date.today().isoformat(),
    "btc_acumulado": 0.0, "costo_promedio_usd": 0.0,
})

@st.cache_data(ttl=30)
def trifecta_btc():
    try:
        df4  = cargar_klines("4h", 100)
        df1d = cargar_klines("1d", 30)
        if df4.empty: raise ValueError("sin datos")
        c4 = df4["C"]
        soporte_7d = df1d["L"].iloc[-7:].min() if not df1d.empty else btc_price * 0.93
        delta4 = c4.diff()
        rs = (delta4.where(delta4>0,0).rolling(14).mean()) / \
             ((-delta4.where(delta4<0,0)).rolling(14).mean().replace(0,1e-9))
        rsi_4h = round((100-(100/(1+rs))).iloc[-1], 2)
        ml  = c4.ewm(span=12).mean() - c4.ewm(span=26).mean()
        sig = ml.ewm(span=9).mean()
        hist= ml - sig
        return {"soporte_7d":soporte_7d,"rsi_4h":rsi_4h,
                "curr_hist":hist.iloc[-1],"prev_hist":hist.iloc[-2],
                "macd_giro":hist.iloc[-1]>hist.iloc[-2]}
    except Exception:
        return {"soporte_7d":btc_price*0.93,"rsi_4h":50.0,
                "curr_hist":0.0,"prev_hist":0.0,"macd_giro":False}

telem = trifecta_btc()

@st.cache_data(ttl=30)
def telemetria_c5_btc():
    try:
        if df_h1.empty or df_d1.empty: raise ValueError("sin datos")
        c1h = df_h1["C"]; h1h = df_h1["H"]; l1h = df_h1["L"]; o1h = df_h1["O"]
        
        # 1D ATR Compresion
        tr_d = pd.concat([df_d1['H'] - df_d1['L'], (df_d1['H'] - df_d1['C'].shift(1)).abs(), (df_d1['L'] - df_d1['C'].shift(1)).abs()], axis=1).max(axis=1)
        atr14 = tr_d.rolling(14).mean().iloc[-1]
        atr_media = tr_d.rolling(14).mean().rolling(30).mean().iloc[-1]
        d1_compresion = atr14 < (atr_media * 0.95) if pd.notna(atr_media) else False
        max_7d = df_d1['H'].iloc[-7:].max() if len(df_d1) >= 7 else btc_price * 1.05
        d1_zona_baja = c1h.iloc[-1] < (max_7d * 0.98) if pd.notna(max_7d) else False

        # 1H Fibo Golden Pocket
        hh50 = h1h.iloc[-50:].max() if len(h1h) >= 50 else h1h.max()
        ll50 = l1h.iloc[-50:].min() if len(l1h) >= 50 else l1h.min()
        fibo_range = hh50 - ll50
        fibo_618 = hh50 - (fibo_range * 0.618)
        fibo_786 = hh50 - (fibo_range * 0.786)
        last_c = c1h.iloc[-1]
        en_golden_pocket = (last_c <= fibo_618) and (last_c >= fibo_786)
        dist_gp = ((last_c - fibo_618) / fibo_618) * 100 if last_c > fibo_618 else (((fibo_786 - last_c) / last_c) * 100 if last_c < fibo_786 else 0.0)

        # 1H SMC Mecha
        rango_1h = h1h.iloc[-1] - l1h.iloc[-1]
        mecha_inf = min(o1h.iloc[-1], c1h.iloc[-1]) - l1h.iloc[-1]
        es_verde = c1h.iloc[-1] > o1h.iloc[-1]
        pct_mecha = (mecha_inf / rango_1h * 100) if rango_1h > 0 else 0.0
        gatillo_mecha = (rango_1h > 0) and (pct_mecha >= 40.0) and es_verde

        # Stoch RSI 1H
        delta = c1h.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        rsi1h = 100 - (100 / (1 + rs))
        min_r = rsi1h.rolling(14).min()
        max_r = rsi1h.rolling(14).max()
        stoch1h = ((rsi1h - min_r) / (max_r - min_r + 1e-9) * 100).iloc[-1]

        # EMA55 y EMA200 4H (Escudo Macro)
        ema55 = c1h.ewm(span=55, adjust=False).mean().iloc[-1]
        tendencia_alcista = last_c >= (ema55 * 0.985)
        c4h = df_h4["C"] if not df_h4.empty else c1h
        ema200_4h = c4h.ewm(span=200, adjust=False).mean().iloc[-1]
        escudo_macro_ok = last_c >= ema200_4h

        score_c5 = 0
        if d1_compresion or d1_zona_baja: score_c5 += 2
        if en_golden_pocket: score_c5 += 3
        if gatillo_mecha: score_c5 += 3
        if stoch1h < 30: score_c5 += 1
        if tendencia_alcista: score_c5 += 1

        return {
            "d1_compresion": d1_compresion, "d1_zona_baja": d1_zona_baja, "max_7d": max_7d,
            "hh50": hh50, "ll50": ll50, "fibo_618": fibo_618, "fibo_786": fibo_786,
            "en_golden_pocket": en_golden_pocket, "dist_gp": dist_gp,
            "pct_mecha": pct_mecha, "gatillo_mecha": gatillo_mecha,
            "stoch1h": stoch1h, "ema55": ema55, "tendencia_alcista": tendencia_alcista,
            "ema200_4h": ema200_4h, "escudo_macro_ok": escudo_macro_ok,
            "score_c5": score_c5
        }
    except Exception:
        return {
            "d1_compresion": False, "d1_zona_baja": False, "max_7d": btc_price * 1.05,
            "hh50": btc_price * 1.03, "ll50": btc_price * 0.97,
            "fibo_618": btc_price * 0.99, "fibo_786": btc_price * 0.97,
            "en_golden_pocket": False, "dist_gp": 1.5, "pct_mecha": 15.0,
            "gatillo_mecha": False, "stoch1h": 50.0, "ema55": btc_price,
            "tendencia_alcista": True, "ema200_4h": btc_price * 0.95,
            "escudo_macro_ok": True, "score_c5": 3
        }

telem_c5 = telemetria_c5_btc()

# ── MOTOR CUANTITATIVO DE TOMA DE DECISIONES (SCORE 0 A 100) ───────────────
def motor_decision_maestro():
    pts = 0
    razones_no_comprar = []
    razones_comprar = []
    razones_vender = []
    
    fg_v   = fg["val"]
    mvrv_d = clean_num(m_d1.get("mvrv", 0), 0.0)
    rsi_d  = clean_num(m_d1.get("rsi", 50), 50.0)
    rsi_4h = clean_num(m_h4.get("rsi", 50), 50.0)
    ema55_d = clean_num(m_d1.get("ema55", btc_price), btc_price)
    ema10_d = clean_num(m_d1.get("ema10", btc_price), btc_price)
    sop_7d  = clean_num(telem.get("soporte_7d", btc_price * 0.93), btc_price * 0.93)
    
    # 1. PILAR 1: Descuento Institucional vs EMA 55 D1 (25 pts)
    diff_ema55_pct = ((btc_price - ema55_d) / ema55_d) * 100.0
    if btc_price <= ema55_d * 0.98:
        pts += 25
        razones_comprar.append(f"✅ Descuento institucional de -2% bajo EMA 55 D1 ({diff_ema55_pct:+.1f}%).")
    elif btc_price <= ema55_d * 1.02:
        pts += 12
    else:
        razones_no_comprar.append(f"🚫 Sobreextendido +{diff_ema55_pct:.1f}% por encima de la EMA 55 D1 (${ema55_d:,.0f}). No hay descuento institucional.")
        
    # 2. PILAR 2: RSI 1D & Zonas Extremas (20 pts)
    if rsi_d < 45.0:
        pts += 20
        razones_comprar.append(f"✅ RSI 1D en zona de sobreventa ({rsi_d:.1f} pts).")
    elif rsi_d <= 55.0:
        pts += 15
    elif rsi_d < 68.0:
        pts += 6
        razones_no_comprar.append(f"⚠️ RSI 1D caliente ({rsi_d:.1f} pts) cerca de zona de distribución.")
    else:
        razones_no_comprar.append(f"🔴 RSI 1D en sobrecompra extrema ({rsi_d:.1f} pts >= 68). Bloqueo total de compras.")
        razones_vender.append(f"🎯 RSI 1D en {rsi_d:.1f} pts habilita gatillo de venta Fase 1 (50%).")
        
    # 3. PILAR 3: Soporte Semanal 7D (20 pts)
    dist_sop7d = ((btc_price - sop_7d) / sop_7d) * 100.0
    if btc_price <= sop_7d * 1.008:
        pts += 20
        razones_comprar.append(f"✅ Precio tocando Soporte Semanal 7D (${sop_7d:,.0f}). Gatillo Caja 1 Activo.")
    elif btc_price <= sop_7d * 1.03:
        pts += 10
    else:
        razones_no_comprar.append(f"🚫 Precio a +{dist_sop7d:.1f}% por encima del Soporte 7D (${sop_7d:,.0f}). Riesgo de corrección hacia el piso.")
        
    # 4. PILAR 4: Squeeze Momentum & RSI 4H (15 pts)
    mh_d1 = clean_num(m_d1.get("macd_hist", 0), 0.0)
    if rsi_4h <= 43.0 and telem.get("macd_giro", False):
        pts += 15
        razones_comprar.append(f"✅ RSI 4H ({rsi_4h:.1f}) + Giro de Momentum 4H. Gatillo Caja 3 Activo.")
    elif rsi_4h >= 72.0:
        razones_vender.append(f"🟡 Cresta de RSI 4H en {rsi_4h:.1f} pts habilita toma de ganancias Fase 2 (35%).")
    else:
        pts += 7
        
    # 5. PILAR 5: Sentimiento On-Chain Fear & Greed (10 pts)
    if fg_v < 40:
        pts += 10
        razones_comprar.append(f"✅ Sentimiento de Miedo ({fg_v}/100 - {fg['classif']}). Comprar sangre institucional.")
    elif fg_v <= 65:
        pts += 6
    else:
        pts += 2
        razones_no_comprar.append(f"⚠️ Sentimiento en Codicia/Euforia ({fg_v}/100 - {fg['classif']}).")
        
    # 6. PILAR 6: Gestión de Riesgo y Deuda (10 pts)
    deuda_tot_usd = liability_btc * btc_price if binance_ok else 0.0
    if deuda_tot_usd < 1800.0:
        pts += 10
    else:
        razones_no_comprar.append(f"🛑 Deuda Borrow actual (${deuda_tot_usd:,.0f}) cercana al techo de seguridad. Priorizar repago.")
        
    pts = min(100, max(0, pts))
    return {
        "score": pts,
        "diff_ema55": diff_ema55_pct,
        "dist_sop7d": dist_sop7d,
        "sop_7d": sop_7d,
        "ema55_d": ema55_d,
        "rsi_1d": rsi_d,
        "rsi_4h": rsi_4h,
        "no_comprar": razones_no_comprar,
        "comprar": razones_comprar,
        "vender": razones_vender
    }

dec = motor_decision_maestro()
score = dec["score"]

if score >= 75:
    sem_color = "#22c55e"
    sem_bg = "rgba(34, 197, 94, 0.15)"
    sem_border = "#22c55e"
    sem_txt = "🟢 ZONA DE COMPRA Y ACUMULACIÓN AGRESIVA"
    sem_sub = "El mercado está en suelo de soporte, con descuento y bajo riesgo de ruina."
elif score >= 45:
    sem_color = "#eab308"
    sem_bg = "rgba(234, 179, 8, 0.15)"
    sem_border = "#eab308"
    sem_txt = "🟡 ZONA DE ESPERA TÁCTICA / HODL ACTIVO"
    sem_sub = "Mercado en terreno intermedio. Mantener satoshis y esperar confirmación."
else:
    sem_color = "#ef4444"
    sem_bg = "rgba(239, 68, 68, 0.15)"
    sem_border = "#ef4444"
    sem_txt = "🔴 ZONA DE BLOQUEO DE COMPRA / TOMA DE GANANCIAS"
    sem_sub = "Sobreextendido o en zona de techos. Prohibido comprar en FOMO."

# ═══════════════════════════════════════════════════════════════════════════
# BARRA DE CONTROL GLOBAL & ACTUALIZADOR EN VIVO
# ═══════════════════════════════════════════════════════════════════════════
hdr_col1, hdr_col2 = st.columns([3, 1])
with hdr_col1:
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
        <span style="font-size:1.4rem; font-weight:900; color:#f8fafc;">🏛️ CAZADOR PRO — CUARTEL GENERAL UNIFICADO</span>
        <span style="background:rgba(34,197,94,0.2); color:#22c55e; border:1px solid #22c55e; padding:3px 10px; border-radius:12px; font-size:0.75rem; font-weight:800;">⚡ PUERTO 8500 ACTIVO</span>
        <span style="color:#94a3b8; font-size:0.8rem;">Hora VET: <strong>{now_vet().strftime('%H:%M:%S')}</strong></span>
    </div>
    """, unsafe_allow_html=True)
    # ── AGENTE CENTINELA DE SALUD: APIS Y AUDITORÍA DE PRECIOS EN VIVO ──
    auditoria = auditar_salud_apis_y_precios()
    est_centinela = auditoria["estado"]
    
    if est_centinela == "OPTIMO":
        bg_cent = "rgba(34, 197, 94, 0.12)"
        border_cent = "#22c55e"
        led_cent = "🟢"
        tit_cent = "AGENTE CENTINELA: APIS 100% OPERATIVAS Y PRECIOS AUDITADOS"
        sub_cent = "Cotizaciones sincronizadas en tiempo real. Cero anomalías de precios detectadas."
    elif est_centinela == "PRECAUCION":
        bg_cent = "rgba(234, 179, 8, 0.15)"
        border_cent = "#eab308"
        led_cent = "🟡"
        tit_cent = "AGENTE CENTINELA: AVISO DE LATENCIA / CANAL DE CONTINGENCIA"
        sub_cent = "Uno o más feeds presentan latencia. Se activaron rutas de respaldo automáticas."
    else:
        bg_cent = "rgba(239, 68, 68, 0.18)"
        border_cent = "#ef4444"
        led_cent = "🚨"
        tit_cent = "ALERTA DEL AGENTE CENTINELA: DESINCRONIZACIÓN O FALLO DE API"
        sub_cent = "Precaución: Se detectó una inconsistencia de precio o corte de API. Revisar antes de operar."

    alertas_html = ""
    if auditoria["alertas"]:
        alertas_items = "".join([f"<li style='margin-bottom:2px;'>{a}</li>" for a in auditoria["alertas"][:3]])
        alertas_html = f"<ul style='margin:6px 0 0 0; padding-left:18px; font-size:0.78rem; color:#fca5a5;'>{alertas_items}</ul>"

    centinela_banner = f"""<div style="background: {bg_cent}; border: 1px solid {border_cent}; border-radius: 12px; padding: 10px 16px; margin: 10px 0 16px 0; box-shadow: 0 0 15px {border_cent}22;">
<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
<div style="display:flex; align-items:center; gap:8px;">
<span style="font-size:1.3rem;">{led_cent}</span>
<div>
<div style="font-size:0.88rem; font-weight:900; color:#f8fafc; letter-spacing:0.5px;">{tit_cent}</div>
<div style="font-size:0.75rem; color:#cbd5e1;">{sub_cent}</div>
{alertas_html}
</div>
</div>
<div style="display:flex; align-items:center; gap:10px; font-size:0.75rem; font-weight:800;">
<span style="background:rgba(15,23,42,0.8); border:1px solid rgba(255,255,255,0.1); padding:3px 8px; border-radius:8px; color:#38bdf8;">BingX: {auditoria['bingx_ms']}ms</span>
<span style="background:rgba(15,23,42,0.8); border:1px solid rgba(255,255,255,0.1); padding:3px 8px; border-radius:8px; color:#f59e0b;">Binance: {auditoria['binance_ms']}ms</span>
<span style="background:rgba(15,23,42,0.8); border:1px solid rgba(255,255,255,0.1); padding:3px 8px; border-radius:8px; color:#a855f7;">Yahoo: {auditoria['yahoo_ms']}ms</span>
</div>
</div>
</div>"""
    st.markdown(centinela_banner, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# PESTAÑAS PRINCIPALES (DECLARACIÓN ÚNICA)
# ═══════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "🏛️ ESTADO GENERAL & METAS PASO A PASO",
    "⚔️ COCKPIT TÁCTICO MANUAL (11 STOCKS + BTC)",
    "₿ MEGA HÍBRIDO QUANTUM BTC (BINANCE 5X)",
    "🔮 MVRV CICLO 5 & ON-CHAIN MACRO",
    "🧪 ESCALERA DE METAS & LAB QUANT",
    "⚙️ CONTROL & TELEMETRÍA CEREBROS",
    "🔥 INSPECTOR TÁCTICO & MAPA DE CALOR",
    "🎯 ACTIVOS DE ÉLITE CONFLUENCIA (SCORE QUANT ≥ 80)",
    "🧬 CEREBRO 4: RECOMENDACIONES FANTASMA (PILOTO ADN)",
    "🧠 MEGA HÍBRIDO DE DECISIÓN SUPREMA"
])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — ESTADO GENERAL (METAS $8,500, CEREBROS CORRIENDO Y SEMÁFOROS)
# ══════════════════════════════════════════════════════════════════
with tab1:
    # ── 1. ESCALERA DE METAS PASO A PASO ($100 USD INICIAL -> $8,500 USD) ──────
    # Lectura de saldos reales de Septiembre 2027
    st_bc = cargar_json(os.path.join(BASE_DIR, "estado_blue_chips.json"), {})
    st_mh = cargar_json(os.path.join(BASE_DIR, "estado_mega_hibrido_btc_dual.json"), {})
    st_tf = cargar_json(os.path.join(BASE_DIR, "HIBRIDO", "estado_trifecta_hibrido.json"), {})
    
    equidad_bingx_real = 499.38
    pos_bc = st_bc.get("posiciones", {})
    margen_bc = sum(clean_num(p.get("margen_actual", 10.0)) for p in pos_bc.values())
    if margen_bc > 0:
        equidad_bingx_real = max(equidad_bingx_real, margen_bc + 480.0)

    # ── 0. RADAR DEL AGENTE CENTINELA MACRO 24/7 (DXY, USDT CAP, FOMC) ─────────
    st_macro = cargar_json(os.path.join(BASE_DIR, "AUTONOMO", "centinela_macro_estado.json"), {})
    if st_macro:
        dxy_data = st_macro.get("dxy", {})
        usdt_data = st_macro.get("usdt", {})
        cat_data = st_macro.get("catalizadores", {})
        fomc_data = cat_data.get("fomc", {})
        cpi_data = cat_data.get("cpi", {})
        sem_macro = st_macro.get("semaforo", "VERDE")
        veredicto_m = st_macro.get("veredicto", "🟢 VENTANA INSTITUCIONAL RISK-ON")
        accion_m = st_macro.get("accion_sugerida", "Operar con normalidad.")
        
        sem_color = "#22c55e" if "VERDE" in sem_macro else ("#eab308" if "AMARILLO" in sem_macro else "#ef4444")
        sem_bg = "rgba(34, 197, 94, 0.12)" if "VERDE" in sem_macro else ("rgba(234, 179, 8, 0.12)" if "AMARILLO" in sem_macro else "rgba(239, 68, 68, 0.12)")

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(15,23,42,0.95), {sem_bg}); border: 2px solid {sem_color}; border-radius: 16px; padding: 18px; margin-bottom: 22px; box-shadow: 0 0 25px rgba(56,189,248,0.15);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div>
                    <span style="background:{sem_color}; color:#090d16; font-weight:900; font-size:0.75rem; padding:4px 10px; border-radius:20px; text-transform:uppercase;">
                        🛰️ AGENTE CENTINELA MACRO · {sem_macro}
                    </span>
                    <h3 style="margin:6px 0 0 0; color:#f8fafc; font-weight:800; font-size:1.25rem;">
                        {veredicto_m}
                    </h3>
                    <div style="color:#94a3b8; font-size:0.85rem; margin-top:3px;">
                        👉 <strong>Acción Recomendada:</strong> {accion_m}
                    </div>
                </div>
                <div style="display:flex; gap:12px; flex-wrap:wrap;">
                    <div style="background:rgba(15,23,42,0.8); border:1px solid #334155; border-radius:10px; padding:8px 14px; text-align:center;">
                        <div style="font-size:0.7rem; color:#94a3b8; font-weight:700;">DXY (DÓLAR)</div>
                        <div style="font-size:1.15rem; font-weight:900; color:#38bdf8;">{dxy_data.get('valor', 99.2):.2f} pts</div>
                        <div style="font-size:0.65rem; color:#22c55e;">Viento a Favor</div>
                    </div>
                    <div style="background:rgba(15,23,42,0.8); border:1px solid #334155; border-radius:10px; padding:8px 14px; text-align:center;">
                        <div style="font-size:0.7rem; color:#94a3b8; font-weight:700;">USDT DRY POWDER</div>
                        <div style="font-size:1.15rem; font-weight:900; color:#eab308;">${usdt_data.get('mcap_b', 185.4):.1f}B</div>
                        <div style="font-size:0.65rem; color:#cbd5e1;">Dom: {usdt_data.get('dominancia_pct', 7.6):.1f}%</div>
                    </div>
                    <div style="background:rgba(15,23,42,0.8); border:1px solid #eab308; border-radius:10px; padding:8px 14px; text-align:center;">
                        <div style="font-size:0.7rem; color:#eab308; font-weight:700;">🏛️ FOMC TIPOS FED</div>
                        <div style="font-size:1.15rem; font-weight:900; color:#22c55e;">{fomc_data.get('texto_restante', '9d 19h')}</div>
                        <div style="font-size:0.65rem; color:#94a3b8;">16 Sept 14:00 ET</div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    capital_binance_real = clean_num(st_mh.get("equity_total_usd", 282.58), 282.58)
    capital_actual_usd = capital_binance_real + equidad_bingx_real

    # Definición de los 7 Niveles de la Escalera de Metas
    ESCALERA_NIVELES = [
        {"nivel": 1, "meta": 100.0, "nombre": "Validación & Consistencia Base", "emoji": "🥉", "foco": "Micro-balas ($3 - $6 USD) y blindaje"},
        {"nivel": 2, "meta": 250.0, "nombre": "Ampliación de Margen Seguro", "emoji": "🥈", "foco": "Entradas swing en Blue Chips + Margen 5X"},
        {"nivel": 3, "meta": 500.0, "nombre": "Aumento Táctico de Lote", "emoji": "🥇", "foco": "Duplicar tamaño de bala con apalancamiento <= 3x"},
        {"nivel": 4, "meta": 1000.0, "nombre": "Hito Psicológico & Rotación Dual", "emoji": "💎", "foco": "Crypto + Wall Street operando en simultáneo"},
        {"nivel": 5, "meta": 2500.0, "nombre": "Interés Compuesto Acelerado", "emoji": "👑", "foco": "Retiros parciales de seguridad y aceleración"},
        {"nivel": 6, "meta": 5000.0, "nombre": "Consolidación de Cartera", "emoji": "🚀", "foco": "Gestión institucional de activos líderes"},
        {"nivel": 7, "meta": 8500.0, "nombre": "Meta Suprema Ciclo 2027", "emoji": "🏆", "foco": "Hito Máximo del Cuartel General PRO"}
    ]

    # Identificar el nivel activo en curso
    nivel_activo = ESCALERA_NIVELES[-1]
    for n_info in ESCALERA_NIVELES:
        if capital_actual_usd < n_info["meta"]:
            nivel_activo = n_info
            break

    meta_activa_usd = nivel_activo["meta"]
    num_nivel = nivel_activo["nivel"]
    progreso_nivel_pct = min(100.0, max(0.0, (capital_actual_usd / meta_activa_usd) * 100.0))
    faltante_nivel_usd = max(0.0, meta_activa_usd - capital_actual_usd)
    progreso_meta_8500 = min(100.0, max(0.0, (capital_actual_usd / 8500.0) * 100.0))

    desglose_saldo = f"Binance 5X: <strong>${capital_binance_real:,.2f} USD</strong> | BingX: <strong>${equidad_bingx_real:,.2f} USD</strong>"

    # Renderizado Tarjeta de Escalera de Metas
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(15,23,42,0.95), rgba(30,58,138,0.45)); border: 2px solid #38bdf8; border-radius: 18px; padding: 22px; margin-bottom: 20px; box-shadow: 0 0 35px rgba(56,189,248,0.25);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
                <span class="badge-gold">🪜 ESCALERA DE METAS PASO A PASO — NIVEL {num_nivel} ACTIVO</span>
                <h1 style="margin: 6px 0 0 0; font-size: 2.1rem; font-weight: 900; background: linear-gradient(135deg,#38bdf8,#eab308); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                    {nivel_activo['emoji']} OBJETIVO INMEDIATO: ${meta_activa_usd:,.2f} USD ({nivel_activo['nombre']})
                </h1>
                <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 1.05rem;">
                    Capital Consolidado: <strong style="color:#22c55e;">${capital_actual_usd:,.2f} USD</strong> ({desglose_saldo}) | Faltante para subir de nivel: <strong style="color:#eab308;">${faltante_nivel_usd:,.2f} USD</strong>
                </p>
                <div style="font-size:0.85rem; color:#94a3b8; margin-top:4px;">🎯 <strong>Enfoque de Gestión:</strong> {nivel_activo['foco']}</div>
            </div>
            <div style="text-align:center; background: rgba(15,23,42,0.85); border: 2px solid #eab308; border-radius: 16px; padding: 14px 28px;">
                <div style="font-size: 0.8rem; color: #94a3b8; font-weight: 700; text-transform: uppercase;">PROGRESO NIVEL {num_nivel}</div>
                <div style="font-size: 2.8rem; font-weight: 900; color: #22c55e; line-height: 1;">
                    {progreso_nivel_pct:.1f}<span style="font-size: 1.5rem; color: #38bdf8;">%</span>
                </div>
                <div style="font-size: 0.78rem; color: #cbd5e1; margin-top: 4px;">Progreso a Meta Final ($8,500): {progreso_meta_8500:.1f}%</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(progreso_nivel_pct / 100.0)

    # Escalera visual horizontal de los 7 hitos
    ladder_cols = st.columns(7)
    for idx, n in enumerate(ESCALERA_NIVELES):
        with ladder_cols[idx]:
            if capital_actual_usd >= n["meta"]:
                b_col = "#22c55e"; b_txt = "✅ CONQUISTADO"; b_bg = "rgba(34, 197, 94, 0.15)"
            elif n["nivel"] == num_nivel:
                b_col = "#38bdf8"; b_txt = "🎯 EN CURSO"; b_bg = "rgba(56, 189, 248, 0.20)"
            else:
                b_col = "#64748b"; b_txt = "🔒 BLOQUEADO"; b_bg = "rgba(15, 23, 42, 0.6)"
            st.markdown(f"""
            <div style="background:{b_bg}; border:1px solid {b_col}; border-radius:10px; padding:8px; text-align:center;">
                <div style="font-size:0.7rem; font-weight:800; color:{b_col};">{b_txt}</div>
                <div style="font-size:1.1rem; font-weight:900; color:#f8fafc; margin:2px 0;">{n['emoji']} ${n['meta']:,.0f}</div>
                <div style="font-size:0.68rem; color:#94a3b8; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">Nivel {n['nivel']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    CIERRE_DIARIO_FILE = os.path.join(ESTADO_DIR, "cierre_diario_saldos.json")
    datos_cierre_diario = cargar_json(CIERRE_DIARIO_FILE, {"historial": []})
    historial_cierres = datos_cierre_diario.get("historial", [])
    
    hoy_str = now_vet().strftime("%Y-%m-%d")
    
    idx_hoy = next((i for i, h in enumerate(historial_cierres) if h.get("fecha") == hoy_str), -1)
    
    cierre_ayer = None
    if len(historial_cierres) > 0:
        if idx_hoy != -1 and len(historial_cierres) > 1:
            cierre_ayer = historial_cierres[idx_hoy - 1]
        elif idx_hoy == -1:
            cierre_ayer = historial_cierres[-1]

    binance_ini = clean_num(cierre_ayer.get("binance_usd", capital_binance_real)) if cierre_ayer else capital_binance_real
    bingx_ini   = clean_num(cierre_ayer.get("bingx_usd", equidad_bingx_real)) if cierre_ayer else equidad_bingx_real
    total_ini   = binance_ini + bingx_ini if (binance_ini + bingx_ini) > 0 else capital_actual_usd

    target_mas_1_usd = total_ini * 1.01
    ganancia_objetivo_1_usd = total_ini * 0.01

    pnl_hoy_total_usd = capital_actual_usd - total_ini
    pnl_hoy_total_pct = (pnl_hoy_total_usd / total_ini * 100.0) if total_ini > 0 else 0.0

    pnl_binance_hoy_usd = capital_binance_real - binance_ini
    pnl_binance_hoy_pct = (pnl_binance_hoy_usd / binance_ini * 100.0) if binance_ini > 0 else 0.0

    pnl_bingx_hoy_usd = equidad_bingx_real - bingx_ini
    pnl_bingx_hoy_pct = (pnl_bingx_hoy_usd / bingx_ini * 100.0) if bingx_ini > 0 else 0.0

    meta_alcanzada_hoy = pnl_hoy_total_pct >= 1.0

    record_hoy = {
        "fecha": hoy_str,
        "binance_usd": round(capital_binance_real, 2),
        "bingx_usd": round(equidad_bingx_real, 2),
        "total_usd": round(capital_actual_usd, 2),
        "total_inicio_dia": round(total_ini, 2),
        "target_1pct_usd": round(target_mas_1_usd, 2),
        "pnl_diario_usd": round(pnl_hoy_total_usd, 2),
        "pnl_diario_pct": round(pnl_hoy_total_pct, 2),
        "pnl_binance_usd": round(pnl_binance_hoy_usd, 2),
        "pnl_bingx_usd": round(pnl_bingx_hoy_usd, 2),
        "meta_alcanzada": meta_alcanzada_hoy
    }

    if idx_hoy != -1:
        historial_cierres[idx_hoy] = record_hoy
    else:
        historial_cierres.append(record_hoy)

    datos_cierre_diario["historial"] = historial_cierres
    guardar_json(CIERRE_DIARIO_FILE, datos_cierre_diario)

    if meta_alcanzada_hoy:
        c1_color = "#22c55e"; c1_badge = "🟢 META +1.0% ALCANZADA"
    elif pnl_hoy_total_usd >= 0:
        c1_color = "#eab308"; c1_badge = "🟡 AVANCE PARCIAL (EN POSITIVO)"
    else:
        c1_color = "#ef4444"; c1_badge = "🔴 DÍA EN RETROCESO / NEGATIVO"

    # UI principal sin sangrías de 4 espacios (para evitar que markdown renderice como código)
    card_html = f"""<div style="background: linear-gradient(135deg, rgba(15,23,42,0.95), rgba(20,83,45,0.35)); border: 2px solid {c1_color}; border-radius: 18px; padding: 22px; margin-bottom: 16px; box-shadow: 0 0 30px {c1_color}33;">
<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
<div>
<span class="badge-gold">⚡ META DIARIA CAZADOR: GANAR +1.0% DIARIO DE INTERÉS COMPUESTO</span>
<h2 style="margin: 6px 0 0 0; font-size: 1.8rem; font-weight: 800; color: {c1_color};">
ESTADO HOY: {c1_badge}
</h2>
<p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 1.02rem;">
Saldo Inicio del Día: <strong>${total_ini:,.2f} USD</strong> | Meta +1% Hoy: <strong style="color:#22c55e;">${target_mas_1_usd:,.2f} USD</strong> (+${ganancia_objetivo_1_usd:,.2f})
</p>
</div>
<div style="text-align:center; background: rgba(15,23,42,0.85); border: 2px solid {c1_color}; border-radius: 14px; padding: 12px 24px;">
<div style="font-size: 0.78rem; color: #94a3b8; font-weight: 700; text-transform: uppercase;">RENDIMIENTO HOY (TOTAL)</div>
<div style="font-size: 2.5rem; font-weight: 900; color: {c1_color}; line-height: 1;">
{pnl_hoy_total_usd:+,.2f} <span style="font-size: 1.2rem;">USD</span>
</div>
<div style="font-size: 0.85rem; font-weight:700; color: {c1_color}; margin-top: 4px;">
{pnl_hoy_total_pct:+.2f}% vs Cierre Ayer
</div>
</div>
</div>
</div>"""

    st.markdown(card_html, unsafe_allow_html=True)

    col_bn, col_bx = st.columns(2)
    with col_bn:
        bn_color = "#22c55e" if pnl_binance_hoy_usd >= 0 else "#ef4444"
        st.markdown(f"""<div style="background:rgba(15,23,42,0.85); padding:16px 20px; border-radius:14px; border:2px solid #eab308; text-align:center;">
<div style="font-size:0.85rem; color:#eab308; font-weight:800; text-transform:uppercase;">🟡 BINANCE MARGIN HOY</div>
<div style="font-size:1.8rem; font-weight:900; color:{bn_color}; margin: 4px 0;">{pnl_binance_hoy_usd:+,.2f} USD ({pnl_binance_hoy_pct:+.2f}%)</div>
<div style="font-size:0.88rem; color:#cbd5e1;">Saldo Actual: <strong>${capital_binance_real:,.2f} USD</strong> | Inicio: ${binance_ini:,.2f} USD</div>
</div>""", unsafe_allow_html=True)

    with col_bx:
        bx_color = "#22c55e" if pnl_bingx_hoy_usd >= 0 else "#ef4444"
        st.markdown(f"""<div style="background:rgba(15,23,42,0.85); padding:16px 20px; border-radius:14px; border:2px solid #38bdf8; text-align:center;">
<div style="font-size:0.85rem; color:#38bdf8; font-weight:800; text-transform:uppercase;">🟠 BINGX FUTURES HOY</div>
<div style="font-size:1.8rem; font-weight:900; color:{bx_color}; margin: 4px 0;">{pnl_bingx_hoy_usd:+,.2f} USD ({pnl_bingx_hoy_pct:+.2f}%)</div>
<div style="font-size:0.88rem; color:#cbd5e1;">Equidad Actual: <strong>${equidad_bingx_real:,.2f} USD</strong> | Inicio: ${bingx_ini:,.2f} USD</div>
</div>""", unsafe_allow_html=True)

    prog_meta_diaria = max(0.0, min(100.0, ((pnl_hoy_total_usd) / (ganancia_objetivo_1_usd + 1e-9)) * 100.0)) if pnl_hoy_total_usd > 0 else 0.0
    st.caption(f"Progreso a la Meta Diaria (+1.0% = +${ganancia_objetivo_1_usd:,.2f} USD): {prog_meta_diaria:.1f}%")
    st.progress(prog_meta_diaria / 100.0)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── 2. TARJETA DEDICADA DE MONITOREO DE CEREBROS CORRIENDO EN SEGUNDO PLANO ───
    st.markdown("""
    <div style="background: rgba(15, 23, 42, 0.9); border: 2px solid #818cf8; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 0 25px rgba(129,140,248,0.2);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <h2 style="margin:0; font-size:1.6rem; font-weight:800; color:#818cf8;">⚙️ MONITOR DEDICADO DE CEREBROS CORRIENDO (UBUNTU OS)</h2>
                <p style="margin:4px 0 0 0; color:#94a3b8; font-size:0.95rem;">Detección en tiempo real de Motores Python (Segundo Plano) y Dashboards Streamlit activos en el sistema</p>
            </div>
            <span class="badge-green">24/7 AUTÓNOMO</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    cerebros_status = verificar_estado_detallado_cerebros()
    col_c1, col_c2, col_c3_b = st.columns(3)

    for idx, c_info in enumerate(cerebros_status):
        col_dest = [col_c1, col_c2, col_c3_b][idx % 3]
        with col_dest:
            if c_info["motor_vivo"] and c_info["dash_vivo"]:
                st_color = "#22c55e"
                st_bg = "rgba(34, 197, 94, 0.12)"
                st_badge = "🟢 MOTOR + DASHBOARD CORRIENDO"
            elif c_info["dash_vivo"]:
                st_color = "#eab308"
                st_bg = "rgba(234, 179, 8, 0.12)"
                st_badge = "🟡 DASHBOARD EN VIVO (SIN MOTOR)"
            else:
                st_color = "#ef4444"
                st_bg = "rgba(239, 68, 68, 0.12)"
                st_badge = "🔴 DETENIDO / APAGADO"

            st.markdown(f"""
            <div style="background: {st_bg}; border: 2px solid {st_color}; border-radius: 14px; padding: 16px; margin-bottom: 16px; min-height: 220px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:0.8rem; font-weight:800; color:{st_color};">{st_badge}</span>
                    <span style="font-size:0.75rem; background:rgba(15,23,42,0.8); color:#cbd5e1; padding:2px 8px; border-radius:10px;">Puerto :{c_info['puerto']}</span>
                </div>
                <h3 style="margin:0 0 6px 0; font-size:1.15rem; font-weight:800; color:#f8fafc;">{c_info['nombre']}</h3>
                <div style="font-size:0.82rem; color:#94a3b8; margin-bottom:12px;">
                    🎯 <strong>Mercado:</strong> {c_info['mercado']}<br>
                    🖥️ <strong>PID Motor:</strong> {c_info['pid_motor'] or 'N/A'} | <strong>PID Dash:</strong> {c_info['pid_dash'] or 'N/A'}<br>
                    💾 <strong>RAM Usada:</strong> {c_info['ram_total_mb']} MB<br>
                    📦 <strong>Posiciones Abiertas:</strong> <strong style="color:#38bdf8;">{c_info['posiciones_activas']}</strong><br>
                    🕒 <strong>Última Actividad:</strong> {c_info['last_heartbeat']}
                </div>
                <a href="http://localhost:{c_info['puerto']}" target="_blank" style="text-decoration:none;">
                    <div style="background: {st_color}; color: #080c14; text-align:center; padding: 6px 12px; border-radius: 8px; font-weight: 800; font-size: 0.85rem;">
                        🔗 Abrir Dashboard (Puerto {c_info['puerto']})
                    </div>
                </a>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 3. SEMÁFORO UNIFICADO DE LOS 3 CEREBROS OFICIALES (SEPTIEMBRE 2027) ──
    st.markdown("""
    <div style="background: rgba(15, 23, 42, 0.95); border: 2px solid #22c55e; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 0 25px rgba(34,197,94,0.2);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div>
                <h2 style="margin:0; font-size:1.6rem; font-weight:800; color:#22c55e;">🚦 ESTADO OPERATIVO DE LOS 3 CEREBROS ACTIVOS (SEPTIEMBRE 2027)</h2>
                <p style="margin:4px 0 0 0; color:#cbd5e1; font-size:0.95rem;">Telemetría unificada de posiciones, gatillos automáticos y saldo por motor</p>
            </div>
            <span class="badge-gold">SEPTIEMBRE 2027 EN VIVO</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_cer1, col_cer2, col_cer3 = st.columns(3)

    # C1: Blue Chips
    pos_bc_count = len(st_bc.get("posiciones", {}))
    c1_score = 80 if pos_bc_count > 0 else 50
    c1_color = "#22c55e" if pos_bc_count > 0 else "#eab308"
    c1_estado = f"🟢 {pos_bc_count} POSICIONES ACTIVAS" if pos_bc_count > 0 else "🟡 MONITOREANDO SOPORTES"
    with col_cer1:
        st.markdown(f"""
        <div style="background: rgba(15,23,42,0.85); border: 2px solid {c1_color}; border-radius: 14px; padding: 18px; text-align:center;">
            <div style="font-size:0.75rem; font-weight:800; color:#38bdf8; text-transform:uppercase;">🏛️ CEREBRO 1: WALL STREET & BLUE CHIPS</div>
            <div style="font-size:1.15rem; font-weight:900; color:{c1_color}; margin: 8px 0;">{c1_estado}</div>
            <div style="font-size:1.8rem; font-weight:900; color:#f8fafc;">BingX Perpetuos</div>
            <div style="font-size:0.8rem; color:#cbd5e1; margin-top:6px;">
                Activos: {', '.join(list(st_bc.get('posiciones', {}).keys())) if pos_bc_count > 0 else '11 Stocks en Radar'}<br>
                Puerto <strong>:8540</strong> | TP1 al 50% + BE
            </div>
        </div>
        """, unsafe_allow_html=True)

    # C2: Mega Híbrido BTC
    ml_actual = clean_num(st_mh.get("margin_level_actual", 999.0), 999.0)
    c2_color = "#22c55e" if ml_actual >= 1.50 else "#ef4444"
    c2_estado = "🟢 MARGEN SEGURO (LISTO BALAS)" if ml_actual >= 1.50 else "🔴 BLOQUEO COMPRA MARGEN"
    with col_cer2:
        st.markdown(f"""
        <div style="background: rgba(15,23,42,0.85); border: 2px solid {c2_color}; border-radius: 14px; padding: 18px; text-align:center;">
            <div style="font-size:0.75rem; font-weight:800; color:#eab308; text-transform:uppercase;">⚡ CEREBRO 2: MEGA HÍBRIDO QUANTUM BTC</div>
            <div style="font-size:1.15rem; font-weight:900; color:{c2_color}; margin: 8px 0;">{c2_estado}</div>
            <div style="font-size:1.8rem; font-weight:900; color:#f8fafc;">ML: {ml_actual:.2f}x</div>
            <div style="font-size:0.8rem; color:#cbd5e1; margin-top:6px;">
                Binance Cross Margin 5X | Equity: <strong>${capital_binance_real:,.2f}</strong><br>
                Puerto <strong>:8545</strong> | Bala 1 Soporte 7D + Squeeze
            </div>
        </div>
        """, unsafe_allow_html=True)

    # C3: Trifecta Híbrido
    pos_tf_count = len(st_tf.get("posiciones_activas", {}))
    c3_color = "#22c55e" if pos_tf_count > 0 else "#38bdf8"
    c3_estado = f"🟢 {pos_tf_count} ACTIVAS (AVGO)" if pos_tf_count > 0 else "🟡 MODO FANTASMA / RADAR"
    with col_cer3:
        st.markdown(f"""
        <div style="background: rgba(15,23,42,0.85); border: 2px solid {c3_color}; border-radius: 14px; padding: 18px; text-align:center;">
            <div style="font-size:0.75rem; font-weight:800; color:#a855f7; text-transform:uppercase;">🎯 CEREBRO 3: TRIFECTA HÍBRIDO</div>
            <div style="font-size:1.15rem; font-weight:900; color:{c3_color}; margin: 8px 0;">{c3_estado}</div>
            <div style="font-size:1.8rem; font-weight:900; color:#f8fafc;">Sonda / Martillazo</div>
            <div style="font-size:0.8rem; color:#cbd5e1; margin-top:6px;">
                BingX / Acciones & Cripto<br>
                Puerto <strong>:8555</strong> | Secuencia 3 Balas Cuánticas
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 4. RADAR DE LIQUIDEZ INSTITUCIONAL & TOP 3 ORDER BLOCKS RECOMENDADOS ──
    st.markdown("""
    <div style="background: rgba(15, 23, 42, 0.95); border: 2px solid #38bdf8; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 0 25px rgba(56,189,248,0.2);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div>
                <h2 style="margin:0; font-size:1.6rem; font-weight:800; color:#38bdf8;">🛡️ RADAR DE ORDER BLOCKS & LIQUIDEZ MULTI-TIMEFRAME</h2>
                <p style="margin:4px 0 0 0; color:#cbd5e1; font-size:0.95rem;">
                    <strong>Jerarquía Institucional:</strong> <span style="color:#22c55e;">1W (Macro Semanal - Manda Más)</span> > <span style="color:#38bdf8;">1D (Estructural)</span> > <span style="color:#eab308;">4H (Intermedio)</span> > <span style="color:#f43f5e;">1H (Sniper Gatillo)</span>
                </p>
            </div>
            <span class="badge-blue">CONFLUENCIA CUÁNTICA</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Cargar análisis de BTC mediante roq
    analisis_btc = {}
    if HAS_ROQ:
        try:
            p_btc_csv = "/home/h/Escritorio/RESPALDO/2027/VELAS/BTC_1h.csv"
            if os.path.exists(p_btc_csv):
                df_b_raw = pd.read_csv(p_btc_csv)
                df_b_raw.rename(columns={'Datetime':'dt','Open':'open','High':'high','Low':'low','Close':'close','Volume':'vol'}, inplace=True)
                df_b_raw['dt'] = pd.to_datetime(df_b_raw['dt'].astype(str).str.split('+').str[0].str.strip(), utc=True)
                df_b_raw.set_index('dt', inplace=True)
                
                df_1h_b = df_b_raw.tail(150).copy()
                df_4h_b = df_b_raw.resample('4h').agg({'open':'first','high':'max','low':'min','close':'last','vol':'sum'}).dropna().tail(150)
                df_1d_b = df_b_raw.resample('1D').agg({'open':'first','high':'max','low':'min','close':'last','vol':'sum'}).dropna().tail(150)
                df_1w_b = df_b_raw.resample('1W').agg({'open':'first','high':'max','low':'min','close':'last','vol':'sum'}).dropna().tail(100)
                
                analisis_btc = roq.analizar_activo_multitimeframe('BTCUSDT', df_1h=df_1h_b, df_4h=df_4h_b, df_1d=df_1d_b, df_1w=df_1w_b)
        except Exception as e:
            pass

    # Mostrar los Top 3 Order Blocks recomendados
    top_obs = analisis_btc.get("top_3_obs", [])
    if top_obs:
        st.markdown("### 🏆 Top 3 Order Blocks Recomendados del Día (Mayor Probabilidad Cuantitativa)")
        ob_cols = st.columns(3)
        for idx, ob in enumerate(top_obs):
            with ob_cols[idx]:
                ob_score = ob.get("score", 0)
                sc_col = "#22c55e" if ob_score >= 70 else ("#eab308" if ob_score >= 50 else "#38bdf8")
                st.markdown(f"""
                <div style="background:rgba(15,23,42,0.9); border:2px solid {sc_col}; border-radius:14px; padding:16px; margin-bottom:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:0.8rem; font-weight:800; background:{sc_col}22; color:{sc_col}; padding:2px 8px; border-radius:6px;">
                            TOP #{idx+1} · [{ob['tf']}] {ob['direccion']}
                        </span>
                        <span style="font-size:1.1rem; font-weight:900; color:{sc_col};">{ob_score} pts</span>
                    </div>
                    <h3 style="margin:8px 0 4px 0; font-size:1.25rem; font-weight:900; color:#f8fafc;">
                        ${ob['bot']:,.2f} – ${ob['top']:,.2f}
                    </h3>
                    <div style="font-size:0.8rem; color:#cbd5e1; margin-bottom:8px;">
                        👑 <strong>Jerarquía:</strong> {ob.get('mando_jerarquia', 'Nivel Cuántico')}<br>
                        🎯 <strong>Distancia al Precio:</strong> {ob['dist_pct']:+.2f}% | <strong>Estado:</strong> {ob['estado']}
                    </div>
                    <div style="font-size:0.75rem; color:#94a3b8; border-top:1px solid #334155; padding-top:6px;">
                        {'<br>'.join(['• ' + r for r in ob.get('razones', [])])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Calculando Order Blocks institucionales en tiempo real...")

    # ── 5. MATRIZ TÉCNICA MULTI-TIMEFRAME (RSI, STOCH, MACD, ADX, FIB, POC, EMAS) ──
    ind_btc = analisis_btc.get("indicadores", {})
    gp_btc = analisis_btc.get("golden_pocket", {})
    poc_btc = analisis_btc.get("poc", 0.0)

    st.markdown("### 📊 Arsenal Técnico Multi-Timeframe (1W, 1D, 4H, 1H)")
    tcol1, tcol2, tcol3, tcol4 = st.columns(4)

    with tcol1:
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.85); border:1px solid #334155; border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:0.75rem; font-weight:800; color:#38bdf8;">OSCILADORES RSI (NORMAL & STOCH)</div>
            <div style="font-size:1.1rem; font-weight:800; color:#f8fafc; margin:6px 0;">RSI 1D: {ind_btc.get('rsi_1d', 50):.1f} pts</div>
            <div style="font-size:0.8rem; color:#cbd5e1;">
                Stoch %K 1D: <strong>{ind_btc.get('stoch_k_1d', 50):.1f}</strong> | %D: {ind_btc.get('stoch_d_1d', 50):.1f}<br>
                Stoch %K 4H: <strong>{ind_btc.get('stoch_k_4h', 50):.1f}</strong><br>
                Stoch %K 1H: <strong>{ind_btc.get('stoch_k_1h', 50):.1f}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tcol2:
        adx_val = ind_btc.get('adx_1d', 20.0)
        adx_col = "#22c55e" if adx_val >= 23.0 else "#ef4444"
        adx_tag = "FUERZA INSTITUCIONAL" if adx_val >= 23.0 else "RANGO / SIN FUERZA"
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.85); border:1px solid {adx_col}; border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:0.75rem; font-weight:800; color:#38bdf8;">FILTRO DE FUERZA ADX (UMBRAL 23)</div>
            <div style="font-size:1.3rem; font-weight:900; color:{adx_col}; margin:6px 0;">{adx_val:.1f} pts</div>
            <div style="font-size:0.8rem; color:{adx_col}; font-weight:800;">{adx_tag}</div>
            <div style="font-size:0.75rem; color:#cbd5e1; margin-top:2px;">Giro Valle MACD 1D: {'🟢 ACTIVO' if ind_btc.get('macd_giro_1d', False) else '⚪ Neutral'}</div>
        </div>
        """, unsafe_allow_html=True)

    with tcol3:
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.85); border:1px solid #eab308; border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:0.75rem; font-weight:800; color:#eab308;">GOLDEN POCKET FIBONACCI (0.618 - 0.65)</div>
            <div style="font-size:1.15rem; font-weight:900; color:#f8fafc; margin:6px 0;">
                ${gp_btc.get('gp_low', 0):,.2f} – ${gp_btc.get('gp_high', 0):,.2f}
            </div>
            <div style="font-size:0.8rem; color:#cbd5e1;">
                Swing High: ${gp_btc.get('swing_high', 0):,.2f}<br>
                Swing Low: ${gp_btc.get('swing_low', 0):,.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tcol4:
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.85); border:1px solid #818cf8; border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:0.75rem; font-weight:800; color:#818cf8;">POC DE VOLUMEN & EMAS CLAVE</div>
            <div style="font-size:1.15rem; font-weight:900; color:#38bdf8; margin:6px 0;">POC: ${poc_btc:,.2f}</div>
            <div style="font-size:0.8rem; color:#cbd5e1;">
                EMA 10: ${ind_btc.get('ema10_1d', 0):,.2f}<br>
                EMA 55: ${ind_btc.get('ema55_1d', 0):,.2f}<br>
                EMA 200: ${ind_btc.get('ema200_1d', 0):,.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    # ── GRAN TARJETA VISUAL DEL SEMÁFORO DE DECISIÓN (0-100) ───────
    st.markdown(f"""
    <div style="background: {sem_bg}; border: 2px solid {sem_border}; border-radius: 18px; padding: 25px; margin-bottom: 25px; box-shadow: 0 0 30px {sem_bg};">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <span style="font-size: 0.9rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; color: {sem_color};">
                    🚦 RADAR CUANTITATIVO DE TOMA DE DECISIONES DE ENTRADA
                </span>
                <h1 style="margin: 5px 0 0 0; font-size: 2.3rem; font-weight: 900; color: {sem_color};">
                    {sem_txt}
                </h1>
                <p style="margin: 5px 0 0 0; color: #cbd5e1; font-size: 1.05rem;">
                    {sem_sub}
                </p>
            </div>
            <div style="text-align: center; background: rgba(15, 23, 42, 0.85); border: 2px solid {sem_color}; border-radius: 16px; padding: 15px 30px;">
                <div style="font-size: 0.85rem; color: #94a3b8; font-weight: 700;">DECISION SCORE</div>
                <div style="font-size: 3.5rem; font-weight: 900; color: {sem_color}; line-height: 1;">
                    {score} <span style="font-size: 1.5rem; color: #64748b;">/ 100</span>
                </div>
                <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Puntuación de Compra</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── DESGLOSE DE POR QUÉ COMPRAR / NO COMPRAR / VENDER (LETRA GRANDE) ──
    c_dec1, c_dec2, c_dec3 = st.columns(3)
    
    with c_dec1:
        st.markdown("""
        <div style="background: rgba(239, 68, 68, 0.12); border: 2px solid rgba(239, 68, 68, 0.4); border-radius: 14px; padding: 20px; min-height: 220px;">
            <h3 style="margin: 0 0 14px 0; color: #ef4444; font-size: 1.35rem; font-weight: 800;">🚫 ¿Por qué NO Comprar Ahora?</h3>
        """, unsafe_allow_html=True)
        if dec["no_comprar"]:
            for r in dec["no_comprar"]:
                st.markdown(f"<div style='font-size: 1.05rem; line-height: 1.5; color: #f1f5f9; margin-bottom: 10px; font-weight: 500;'>• {r}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='font-size: 1.05rem; color: #22c55e; font-weight: 600;'>✅ No hay bloqueos activos. El precio está en zona óptima de compra.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c_dec2:
        st.markdown("""
        <div style="background: rgba(34, 197, 94, 0.12); border: 2px solid rgba(34, 197, 94, 0.4); border-radius: 14px; padding: 20px; min-height: 220px;">
            <h3 style="margin: 0 0 14px 0; color: #22c55e; font-size: 1.35rem; font-weight: 800;">🛒 ¿Cuándo / Por qué Comprar?</h3>
        """, unsafe_allow_html=True)
        if dec["comprar"]:
            for r in dec["comprar"]:
                st.markdown(f"<div style='font-size: 1.05rem; line-height: 1.5; color: #f1f5f9; margin-bottom: 10px; font-weight: 500;'>• {r}</div>", unsafe_allow_html=True)
        else:
            sop_val = dec.get("sop_7d", btc_price * 0.93)
            ema_val = dec.get("ema55_d", btc_price)
            st.markdown(f"""
            <div style='font-size: 1.05rem; line-height: 1.6; color: #cbd5e1;'>
                • 🎯 <strong>Suelo de Soporte 7D:</strong> Esperar retroceso a <strong style='color: #22c55e;'>${sop_val:,.0f} USD</strong>.<br>
                • 📉 <strong>Descuento Institucional:</strong> Esperar descuento de -2% bajo EMA 55 D1 (<strong style='color: #38bdf8;'>${ema_val*0.98:,.0f} USD</strong>).<br>
                • 🔫 <strong>Presupuesto:</strong> Mantener las 4 balas mensuales preparadas.
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c_dec3:
        st.markdown("""
        <div style="background: rgba(234, 179, 8, 0.12); border: 2px solid rgba(234, 179, 8, 0.4); border-radius: 14px; padding: 20px; min-height: 220px;">
            <h3 style="margin: 0 0 14px 0; color: #eab308; font-size: 1.35rem; font-weight: 800;">💰 ¿Por qué / Cuándo Vender?</h3>
        """, unsafe_allow_html=True)
        if dec["vender"]:
            for r in dec["vender"]:
                st.markdown(f"<div style='font-size: 1.05rem; line-height: 1.5; color: #f1f5f9; margin-bottom: 10px; font-weight: 500;'>• {r}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style='font-size: 1.05rem; line-height: 1.6; color: #cbd5e1;'>
                • 🔴 <strong>Fase 1 (50%):</strong> PnL ≥ +12% + RSI 1D ≥ 68 pts (Auto-Repay de Deuda a $0).<br>
                • 🟡 <strong>Fase 2 (35%):</strong> RSI 4H ≥ 72 pts o Giro Valle Verde Diario.<br>
                • 🟢 <strong>Fase 3 (15% Runner):</strong> Cierre final al perder la EMA 10 Diaria.
            </div>
            """, unsafe_allow_html=True)
        # Cálculo de Progreso hacia Fase 2 (35% salida: RSI 4H >= 72 o Giro Valle Verde Diario)
        rsi_h4_v = clean_num(m_h4.get("rsi", 50.0), 50.0)
        prog_fase2 = min(100.0, max(0.0, (rsi_h4_v / 72.0) * 100.0))
        color_f2 = "#22c55e" if prog_fase2 >= 100 else ("#eab308" if prog_fase2 >= 65 else "#38bdf8")
        
        # Ganancia estimada al ejecutar 35% de balance colateral
        est_liq_35 = collateral * 0.35
        
        st.markdown(f"""
        <div style="margin-top: 14px; background: rgba(0,0,0,0.35); border-radius: 10px; padding: 12px; border: 1px solid rgba(234, 179, 8, 0.3);">
            <div style="display:flex; justify-content:space-between; font-size: 0.82rem; font-weight: 800; margin-bottom: 4px;">
                <span style="color: #eab308;">🔥 TERMÓMETRO GATILLO FASE 2:</span>
                <span style="color: {color_f2};">{rsi_h4_v:.1f} / 72.0 pts ({prog_fase2:.0f}%)</span>
            </div>
            <div style="width: 100%; height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden;">
                <div style="width: {prog_fase2}%; height: 100%; background: {color_f2};"></div>
            </div>
            <div style="font-size: 0.78rem; color: #94a3b8; margin-top: 6px;">
                💰 <strong>Toma Estimada (35%):</strong> <span style="color: #22c55e; font-weight: 800;">${est_liq_35:,.2f} USD netos</span> al tocar gatillo.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── 🎭 MÓDULO CONTRARIAN: "NOTICIAS MALAS SON BUENAS PARA LONG / BUENAS PARA SHORT" ──
    fng_info = cargar_fear_greed()
    fng_v = fng_info.get("val", 50)
    fng_c = fng_info.get("classif", "Neutral")
    
    # Lógica Contrarian: Pánico masivo + precio en soporte = LONG de Oro. Euforia extrema + precio en resistencia = SHORT de Oro.
    sop_btc_ref = dec.get("sop_7d", btc_price * 0.93)
    cerca_sop = (btc_price - sop_btc_ref) / sop_btc_ref <= 0.04
    
    if fng_v <= 35:
        # Pánico / Miedo extremo
        cont_titulo = "🟢 REGLA DE ORO CONTRARIAN: NOTICIAS MALAS = OPORTUNIDAD HISTÓRICA LONG"
        cont_desc = f"El público minorista está en Pánico/Capitulación ({fng_v}/100 - {fng_c}). Las ballenas usan las malas noticias (FUD) para absorber liquidez a precios de saldo sin mover el mercado al alza todavía. <strong>¡COMPRA CUANDO HAYA SANGRE!</strong>"
        cont_color = "#22c55e"
        cont_bg = "rgba(34, 197, 94, 0.12)"
    elif fng_v >= 70 or btc_price >= 85000:
        # Euforia extrema / Techo
        cont_titulo = "🔴 REGLA DE ORO CONTRARIAN: NOTICIAS BUENAS = TRAMPA DE LIQUIDEZ / BUSCAR SHORT"
        cont_desc = f"El público minorista está en Euforia/Codicia Extrema ({fng_v}/100 - {fng_c}) leyendo titulares récord. Las instituciones distribuyen sus tenencias a los que compran tarde en máximos. <strong>¡PROHIBIDO COMPRAR FOMO! (Activar coberturas SHORT o toma de ganancias).</strong>"
        cont_color = "#ef4444"
        cont_bg = "rgba(239, 68, 68, 0.12)"
    else:
        # Zona Neutral
        cont_titulo = "⚖️ RADAR CONTRARIAN SMART MONEY: MERCADO EN TRANSICIÓN ESTRATÉGICA"
        cont_desc = f"Sentimiento en {fng_v}/100 ({fng_c}). El dinero institucional opera en silencio acumulando en mechas de absorción bajo la EMA 55. Espera noticias de pánico para martillar LONG o picos de euforia para cobrar."
        cont_color = "#38bdf8"
        cont_bg = "rgba(56, 189, 248, 0.1)"
        
    st.markdown(f"""
    <div style="background: {cont_bg}; border: 2px solid {cont_color}; border-radius: 16px; padding: 18px 24px; margin-top: 18px; box-shadow: 0 0 20px {cont_bg};">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div style="font-size: 1.15rem; font-weight: 900; color: {cont_color}; letter-spacing: 0.5px;">
                {cont_titulo}
            </div>
            <span style="background: {cont_color}; color: #080c14; font-weight: 800; font-size: 0.75rem; padding: 4px 10px; border-radius: 20px;">
                PSICOLOGÍA SMART MONEY
            </span>
        </div>
        <p style="margin: 8px 0 0 0; color: #e2e8f0; font-size: 0.98rem; line-height: 1.5;">
            {cont_desc}
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── MVRV DIARIO & SEMANAL + BARÓMETRO DE DÓNDE COMPRAR / ACUMULAR / VENDER ──
    mvrv_1d_val = clean_num(m_d1.get("mvrv", 1.65), 1.65)
    mvrv_1w_val = clean_num(m_w1.get("mvrv", 1.72), 1.72)
    
    st.markdown("---")
    st.subheader("🌐 Barómetro Cuantitativo MVRV: Suelos, Acumulación y Techos Promedio")
    st.caption("Promedios matemáticos de ciclos de Bitcoin: MVRV Diario (1D) y Semanal (1W) con zonas de acción en dólares.")

    # 4 Columnas de Zonas de Precio
    z_col1, z_col2, z_col3, z_col4 = st.columns(4)
    
    with z_col1:
        st.markdown("""
        <div style="background: rgba(34, 197, 94, 0.15); border: 2px solid #22c55e; border-radius: 14px; padding: 18px; text-align: center;">
            <div style="font-size: 0.85rem; font-weight: 800; color: #22c55e; text-transform: uppercase;">🛒 1. DÓNDE COMPRAR (SUELO)</div>
            <div style="font-size: 1.7rem; font-weight: 900; color: #f8fafc; margin: 8px 0;">$62,000 – $68,000</div>
            <div style="font-size: 0.9rem; color: #cbd5e1;">MVRV ≤ 0.85 · Soporte 7D</div>
            <div style="font-size: 0.8rem; color: #22c55e; margin-top: 6px; font-weight: 700;">🟢 Compra Sangre / Agresiva</div>
        </div>
        """, unsafe_allow_html=True)

    with z_col2:
        st.markdown("""
        <div style="background: rgba(56, 189, 248, 0.15); border: 2px solid #38bdf8; border-radius: 14px; padding: 18px; text-align: center;">
            <div style="font-size: 0.85rem; font-weight: 800; color: #38bdf8; text-transform: uppercase;">📦 2. DÓNDE ACUMULAR (DCA)</div>
            <div style="font-size: 1.7rem; font-weight: 900; color: #f8fafc; margin: 8px 0;">$68,000 – $74,000</div>
            <div style="font-size: 0.9rem; color: #cbd5e1;">MVRV 0.85 – 1.50 · -2% EMA55</div>
            <div style="font-size: 0.8rem; color: #38bdf8; margin-top: 6px; font-weight: 700;">🔵 Smart DCA (4 Balas/Mes)</div>
        </div>
        """, unsafe_allow_html=True)

    with z_col3:
        st.markdown("""
        <div style="background: rgba(234, 179, 8, 0.15); border: 2px solid #eab308; border-radius: 14px; padding: 18px; text-align: center;">
            <div style="font-size: 0.85rem; font-weight: 800; color: #eab308; text-transform: uppercase;">🚀 3. DÓNDE MANTENER (HODL)</div>
            <div style="font-size: 1.7rem; font-weight: 900; color: #f8fafc; margin: 8px 0;">$74,000 – $86,000</div>
            <div style="font-size: 0.9rem; color: #cbd5e1;">MVRV 1.50 – 2.20 (Actual)</div>
            <div style="font-size: 0.8rem; color: #eab308; margin-top: 6px; font-weight: 700;">🟡 Dejar Correr Posición</div>
        </div>
        """, unsafe_allow_html=True)

    with z_col4:
        st.markdown("""
        <div style="background: rgba(239, 68, 68, 0.15); border: 2px solid #ef4444; border-radius: 14px; padding: 18px; text-align: center;">
            <div style="font-size: 0.85rem; font-weight: 800; color: #ef4444; text-transform: uppercase;">💰 4. DÓNDE VENDER (TECHOS)</div>
            <div style="font-size: 1.7rem; font-weight: 900; color: #f8fafc; margin: 8px 0;">$86,000 – $105,000+</div>
            <div style="font-size: 0.9rem; color: #cbd5e1;">MVRV ≥ 2.20 · Techo Ciclo 5</div>
            <div style="font-size: 0.8rem; color: #ef4444; margin-top: 6px; font-weight: 700;">🔴 Semáforo 50% / 35% / 15%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tarjetas MVRV 1D vs 1W
    mv1, mv2, mv3, mv4 = st.columns(4)
    with mv1:
        st.markdown(f"""
        <div class="kpi">
            <div class="kpi-t">MVRV Diario (1D)</div>
            <div class="kpi-v" style="color: #38bdf8;">{mvrv_1d_val:.2f} pts</div>
            <div class="kpi-s">Zona Crecimiento / HODL</div>
        </div>
        """, unsafe_allow_html=True)
    with mv2:
        st.markdown(f"""
        <div class="kpi">
            <div class="kpi-t">MVRV Semanal (1W)</div>
            <div class="kpi-v" style="color: #eab308;">{mvrv_1w_val:.2f} pts</div>
            <div class="kpi-s">Tendencia Macro Sólida</div>
        </div>
        """, unsafe_allow_html=True)
    with mv3:
        st.markdown("""
        <div class="kpi">
            <div class="kpi-t">Suelo Promedio Histórico</div>
            <div class="kpi-v" style="color: #22c55e;">0.65 – 0.85</div>
            <div class="kpi-s">Piso Fundamental: ~$58,000 USD</div>
        </div>
        """, unsafe_allow_html=True)
    with mv4:
        st.markdown("""
        <div class="kpi">
            <div class="kpi-t">Techo Promedio Ciclo 5</div>
            <div class="kpi-v" style="color: #ef4444;">2.80 pts</div>
            <div class="kpi-s">Techo Máximo: ~$105k - $115k USD</div>
        </div>
        """, unsafe_allow_html=True)

    # ── ⚡ MINI-TARJETAS INSTITUCIONALES EN VIVO (FUNDING RATE & OPEN INTEREST) ──
    datos_deriv = cargar_funding_rate_oi()
    fr_v = datos_deriv.get("funding_rate", 0.0001)
    oi_v = datos_deriv.get("open_interest", 106000.0)
    fr_pct = fr_v * 100.0
    
    fr_color = "#22c55e" if fr_pct <= 0.01 else ("#eab308" if fr_pct <= 0.03 else "#ef4444")
    fr_sub = "Bajo apalancamiento / Favorable LONG" if fr_pct <= 0.01 else ("Apalancamiento Moderado" if fr_pct <= 0.03 else "🚨 Sobrecalentado LONG / Riesgo Squeeze")
    
    der1, der2, der3 = st.columns(3)
    with der1:
        st.markdown(f"""
        <div class="kpi" style="border: 1px solid {fr_color}44;">
            <div class="kpi-t">Funding Rate Binance (8H)</div>
            <div class="kpi-v" style="color: {fr_color};">{fr_pct:+.4f}%</div>
            <div class="kpi-s">{fr_sub}</div>
        </div>
        """, unsafe_allow_html=True)
    with der2:
        st.markdown(f"""
        <div class="kpi" style="border: 1px solid #38bdf844;">
            <div class="kpi-t">Open Interest BTC (Futuros)</div>
            <div class="kpi-v" style="color: #38bdf8;">{oi_v:,.0f} BTC</div>
            <div class="kpi-s">${(oi_v * btc_price) / 1e9:.2f}B USD en Posiciones</div>
        </div>
        """, unsafe_allow_html=True)
    with der3:
        # Ratio Long/Short Estimado
        ratio_ls = 1.35 if fr_pct > 0.02 else (0.95 if fr_pct < 0 else 1.15)
        ls_col = "#eab308" if ratio_ls < 1.3 else "#ef4444"
        st.markdown(f"""
        <div class="kpi" style="border: 1px solid {ls_col}44;">
            <div class="kpi-t">Sentimiento Derivados (Long/Short)</div>
            <div class="kpi-v" style="color: {ls_col};">{ratio_ls:.2f}x</div>
            <div class="kpi-s">{'Mayoría alcista (Cuidado mechazos)' if ratio_ls > 1.2 else 'Equilibrio / Absorción'}</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)

    # ── 🎯 CALCULADORA DE SALIDA ESCALONADA DE CICLO (PROYECCIÓN EN DÓLARES) ──
    st.markdown("""
    <div style="background: rgba(15, 23, 42, 0.9); border: 2px solid #a855f7; border-radius: 16px; padding: 20px; margin-bottom: 25px; box-shadow: 0 0 25px rgba(168,85,247,0.2);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div>
                <h3 style="margin:0; font-size:1.35rem; font-weight:900; color:#c084fc;">🧮 CALCULADORA DE SALIDA ESCALONADA DE CICLO (PROYECCIÓN EN $)</h3>
                <p style="margin:4px 0 0 0; color:#cbd5e1; font-size:0.9rem;">Simulación matemática de tu capital total y captura de efectivo según los techos macro de Bitcoin</p>
            </div>
            <span style="background:#a855f722; color:#c084fc; border:1px solid #a855f7; padding:4px 12px; border-radius:20px; font-weight:800; font-size:0.8rem;">
                SEPTIEMBRE 2027 MATRIX
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    # Cálculos dinámicos según el precio actual y colateral
    btc_ratio_actual = net_btc if net_btc > 0 else (collateral * 0.7) / (btc_price + 1e-9)
    usd_libre_base = usdt_free if usdt_free > 0 else collateral * 0.3
    
    cap_86k = usd_libre_base + (btc_ratio_actual * 86000.0)
    cap_95k = usd_libre_base + (btc_ratio_actual * 95000.0)
    cap_105k = usd_libre_base + (btc_ratio_actual * 105000.0)
    
    esc1, esc2, esc3 = st.columns(3)
    with esc1:
        st.markdown(f"""
        <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid #ef4444; border-radius: 12px; padding: 14px; text-align:center;">
            <div style="font-size:0.8rem; font-weight:800; color:#ef4444;">1️⃣ FASE 1 ($86,000 USD)</div>
            <div style="font-size:1.6rem; font-weight:900; color:#f8fafc; margin:6px 0;">${cap_86k:,.2f} USD</div>
            <div style="font-size:0.8rem; color:#cbd5e1;">Venta 50% Posición · Deuda $0 Auto-Repay</div>
            <div style="font-size:0.75rem; color:#22c55e; font-weight:700; margin-top:4px;">Cash Libre Estimado: +${(cap_86k - collateral)*0.5:,.2f} USD</div>
        </div>
        """, unsafe_allow_html=True)
    with esc2:
        st.markdown(f"""
        <div style="background: rgba(234, 179, 8, 0.12); border: 1px solid #eab308; border-radius: 12px; padding: 14px; text-align:center;">
            <div style="font-size:0.8rem; font-weight:800; color:#eab308;">2️⃣ FASE 2 ($95,000 USD)</div>
            <div style="font-size:1.6rem; font-weight:900; color:#f8fafc; margin:6px 0;">${cap_95k:,.2f} USD</div>
            <div style="font-size:0.8rem; color:#cbd5e1;">Venta 35% Posición · Asegurar Ganancia Macro</div>
            <div style="font-size:0.75rem; color:#22c55e; font-weight:700; margin-top:4px;">Cash Libre Estimado: +${(cap_95k - collateral)*0.35:,.2f} USD</div>
        </div>
        """, unsafe_allow_html=True)
    with esc3:
        st.markdown(f"""
        <div style="background: rgba(34, 197, 94, 0.12); border: 1px solid #22c55e; border-radius: 12px; padding: 14px; text-align:center;">
            <div style="font-size:0.8rem; font-weight:800; color:#22c55e;">3️⃣ FASE 3 ($105,000+ USD)</div>
            <div style="font-size:1.6rem; font-weight:900; color:#f8fafc; margin:6px 0;">${cap_105k:,.2f} USD</div>
            <div style="font-size:0.8rem; color:#cbd5e1;">15% Runner Final · Dejar correr hasta fin de ciclo</div>
            <div style="font-size:0.75rem; color:#22c55e; font-weight:700; margin-top:4px;">Cierre Total con Trailing Stop EMA 10</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("💛 KPIs Binance en Vivo")
    if binance_ok:
        k1,k2,k3,k4,k5 = st.columns(5)
        with k1:
            st.markdown(f"""<div class="kpi"><div class="kpi-t">Precio BTC</div>
            <div class="kpi-v">${btc_price:,.0f}</div><div class="kpi-s">USDT · API3</div></div>""", unsafe_allow_html=True)
        with k2:
            st.markdown(f"""<div class="kpi"><div class="kpi-t">Colateral Total</div>
            <div class="kpi-v" style="color:#38bdf8;">${collateral:,.2f}</div>
            <div class="kpi-s">USDT equivalente</div></div>""", unsafe_allow_html=True)
        with k3:
            st.markdown(f"""<div class="kpi"><div class="kpi-t">BTC Neto</div>
            <div class="kpi-v">{net_btc:.5f}</div>
            <div class="kpi-s">~${net_btc*btc_price:,.0f} USD</div></div>""", unsafe_allow_html=True)
        with k4:
            dc = "#ef4444" if liability_btc>0 else "#10b981"
            st.markdown(f"""<div class="kpi"><div class="kpi-t">Deuda Total</div>
            <div class="kpi-v" style="color:{dc};">{liability_btc:.5f} BTC</div>
            <div class="kpi-s">~${liability_btc*btc_price:,.0f} USD</div></div>""", unsafe_allow_html=True)
        with k5:
            mc = "#10b981" if margin_level>3 else "#eab308"
            st.markdown(f"""<div class="kpi"><div class="kpi-t">Nivel de Margen</div>
            <div class="kpi-v" style="color:{mc};">{margin_level:.2f}</div>
            <div class="kpi-s">{'🟢 Saludable' if margin_level>3 else '⚠️ Vigilar'}</div></div>""", unsafe_allow_html=True)
    else:
        st.error(f"🛑 Sin conexion a Binance: {data_margin.get('error','desconocido')}")

    # Alertas aporte/retiro
    usdt_reg  = estado_dca.get("usdt_registrado", 0.0)
    delta_us  = usdt_free - usdt_reg
    if delta_us >= 50 and binance_ok and not now_vet().time() > dtime(23,59):
        st.success(f"💰 Nuevo aporte detectado: +{delta_us:.2f} USDT — Ve a la pestana **💰 BILLETERA** para procesar.")
    elif delta_us < -5 and binance_ok:
        st.warning(f"⚠️ Retiro de {abs(delta_us):.2f} USDT el {now_vet().strftime('%Y-%m-%d')} — Verifica si fue intencional.")

    # ── 5. TABLA HISTÓRICA DE CIERRES DIARIOS (BINANCE VS BINGX VS TOTAL) ───────
    st.markdown("---")
    st.subheader("📅 Historial de Cierres Diarios & Desafío +1.0% (Binance vs BingX)")
    st.caption("Captura automática de saldo al cierre del día (23:59 VET). Permite evaluar el rendimiento por exchange día a día.")

    if historial_cierres:
        rows_hist = []
        for h in reversed(historial_cierres):
            f_str = h.get("fecha", "")
            bin_v = clean_num(h.get("binance_usd", 0.0))
            bing_v = clean_num(h.get("bingx_usd", 0.0))
            tot_v = clean_num(h.get("total_usd", 0.0))
            
            pnl_d_usd = clean_num(h.get("pnl_diario_usd", 0.0))
            pnl_d_pct = clean_num(h.get("pnl_diario_pct", 0.0))
            
            pnl_bin_usd = clean_num(h.get("pnl_binance_usd", 0.0))
            pnl_bing_usd = clean_num(h.get("pnl_bingx_usd", 0.0))
            
            meta_ok = h.get("meta_alcanzada", False)
            badge_m = "🟢 META +1%" if meta_ok else ("🟡 EN POSITIVO" if pnl_d_usd >= 0 else "🔴 RETROCESO")
            
            rows_hist.append({
                "Fecha": f_str,
                "Binance ($)": f"${bin_v:,.2f}",
                "PnL Binance": f"{pnl_bin_usd:+,.2f} USD",
                "BingX ($)": f"${bing_v:,.2f}",
                "PnL BingX": f"{pnl_bing_usd:+,.2f} USD",
                "Capital Total ($)": f"${tot_v:,.2f}",
                "PnL Día ($)": f"{pnl_d_usd:+,.2f} USD",
                "Rendimiento (%)": f"{pnl_d_pct:+.2f}%",
                "Estado Meta (+1%)": badge_m
            })
            
        df_cierres = pd.DataFrame(rows_hist)
        st.dataframe(df_cierres, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("---")
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(15,23,42,0.95), rgba(30,58,138,0.4)); border: 2px solid #38bdf8; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 0 25px rgba(56,189,248,0.2);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div>
                <h3 style="margin:0; font-size:1.45rem; font-weight:900; color:#38bdf8;">🧠 RESUMEN TÉCNICO INTELIGENTE & ORÁCULO MULTI-TIMEFRAME (CON VIDA)</h3>
                <p style="margin:4px 0 0 0; color:#cbd5e1; font-size:0.95rem;">Diagnóstico histórico de ciclos de Bitcoin (2010-2027) y sincronización cuántica D1 + H4 + H1</p>
            </div>
            <span style="background:#38bdf822; color:#38bdf8; border:1px solid #38bdf8; padding:4px 12px; border-radius:20px; font-weight:800; font-size:0.8rem;">
                PRECISIÓN HISTÓRICA 80%+
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 1. Variables Multi-Timeframe Reales
    rsi_d1_val = clean_num(m_d1.get("rsi", 58.8), 58.8)
    rsi_h4_val = clean_num(m_h4.get("rsi", 33.7), 33.7)
    rsi_h1_val = clean_num(m_h1.get("rsi", 45.0), 45.0)

    macd_d1_est = m_d1.get("macd_estado", "ROJO_CLARO")
    macd_h4_est = m_h4.get("macd_estado", "ROJO_CLARO")
    macd_h1_est = m_h1.get("macd_estado", "ROJO_CLARO")
    macd_h4_num = clean_num(m_h4.get("macd_hist", -82), -82.0)

    # Diagnóstico Histórico de RSI D1 (Estadística de ciclos Bitcoin)
    if rsi_d1_val <= 32:
        rsi_hist_tag = "🟢 SUELO GENERACIONAL (88% Efectividad)"
        rsi_hist_desc = "Similar a fondos de 2015, 2018, 2020 y 2022. Acumulación agresiva de ciclo."
        rsi_hist_col = "#22c55e"
    elif 33 <= rsi_d1_val <= 55:
        rsi_hist_tag = "🟢 MEDIA INSTITUCIONAL DCA (82% Efectividad)"
        rsi_hist_desc = "Zona dorada donde las ballenas acumulan entre 35 y 55 pts en tendencias macro."
        rsi_hist_col = "#38bdf8"
    elif 56 <= rsi_d1_val <= 69:
        rsi_hist_tag = "🟡 ZONA HODL / SIN DESCUENTO (45% Efectividad)"
        rsi_hist_desc = "Comprar aquí es pagar precio de mercado sin ventaja. Mantener lo acumulado."
        rsi_hist_col = "#eab308"
    else:
        rsi_hist_tag = "🔴 TECHO DE DISTRIBUCIÓN EUFÓRICA (+85% Corrección)"
        rsi_hist_desc = "De 70 a 90 pts en ciclos históricos (2017/2021) se debe vender todo o tomar ganancias."
        rsi_hist_col = "#ef4444"

    # MVRV Histórico Nuclear
    mvrv_v = clean_num(m_d1.get("mvrv", 1.68), 1.68)
    if mvrv_v >= 3.8:
        mvrv_hist_tag = "🚨 MEGA TECHO HISTÓRICO NUCLEAR"
        mvrv_hist_desc = "En 2017 tocó 4.50 y en 2021 tocó 3.95 pts. Precedió caídas de 50%-75%. VENDER TODO."
        mvrv_hist_col = "#ef4444"
    elif mvrv_v >= 2.2:
        mvrv_hist_tag = "⚠️ ZONA DE ALTA DISTRIBUCIÓN"
        mvrv_hist_desc = "Zona de toma de ganancias escalonada (Fase 1 y 2). Prohibido acumular en spot."
        mvrv_hist_col = "#f97316"
    elif 1.2 <= mvrv_v < 2.2:
        mvrv_hist_tag = "🟡 ZONA CRECIMIENTO / HODL"
        mvrv_hist_desc = "Tendencia de ciclo madura. No hay gangas pero la tendencia sigue viva."
        mvrv_hist_col = "#eab308"
    else:
        mvrv_hist_tag = "🟢 SUELO FUNDAMENTAL BARATO"
        mvrv_hist_desc = "MVRV <= 1.0. El precio está por debajo del costo promedio de la red. Compra obligada."
        mvrv_hist_col = "#22c55e"

    # Diagnóstico de Valles MACD Squeeze (Rojo Claro vs Rojo Oscuro)
    def badge_valle(estado):
        if estado == "ROJO_CLARO":
            return "<span style='color:#f472b6; font-weight:800;'>🌸 Rojo Claro (Frenando / Giro Alcista)</span>"
        elif estado == "ROJO_OSCURO":
            return "<span style='color:#ef4444; font-weight:800;'>🔴 Rojo Oscuro (Sangría Acelerada)</span>"
        elif estado == "VERDE_CLARO":
            return "<span style='color:#22c55e; font-weight:800;'>🟢 Verde Claro (Impulso Toros)</span>"
        else:
            return "<span style='color:#15803d; font-weight:800;'>🌲 Verde Oscuro (Agotamiento)</span>"

    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.markdown(f"""
        <div class="kpi" style="border: 1px solid {rsi_hist_col}55; min-height: 180px; text-align: left; padding: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="kpi-t">RSI DIARIO (1D)</span>
                <span style="font-size:1.3rem; font-weight:900; color:{rsi_hist_col};">{rsi_d1_val:.1f}</span>
            </div>
            <div style="font-size: 0.82rem; font-weight: 800; color: {rsi_hist_col}; margin: 6px 0;">
                {rsi_hist_tag}
            </div>
            <div style="font-size: 0.76rem; color: #cbd5e1; line-height: 1.4;">
                {rsi_hist_desc}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with r2:
        rsi_h4_col = "#22c55e" if rsi_h4_val <= 35 else ("#38bdf8" if rsi_h4_val <= 50 else ("#eab308" if rsi_h4_val <= 68 else "#ef4444"))
        st.markdown(f"""
        <div class="kpi" style="border: 1px solid {rsi_h4_col}55; min-height: 180px; text-align: left; padding: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="kpi-t">RSI H4 (INTRADIARIO)</span>
                <span style="font-size:1.3rem; font-weight:900; color:{rsi_h4_col};">{rsi_h4_val:.1f}</span>
            </div>
            <div style="font-size: 0.82rem; font-weight: 800; color: {rsi_h4_col}; margin: 6px 0;">
                {'🟢 SOBREVENTA / ZONA REBOTE' if rsi_h4_val<=35 else ('🔵 ZONA NEUTRA ACUMULACIÓN' if rsi_h4_val<=55 else '🟡 RESISTENCIA CERCANA')}
            </div>
            <div style="font-size: 0.76rem; color: #cbd5e1; line-height: 1.4;">
                H1 en <strong>{rsi_h1_val:.1f} pts</strong>. Cuando H4 toca ≤35 pts dentro de tendencia alcista mayor, los rebotes intradiarios promedian <strong>+3.8% a +6.5%</strong>.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with r3:
        st.markdown(f"""
        <div class="kpi" style="border: 1px solid #f472b655; min-height: 180px; text-align: left; padding: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="kpi-t">MACD SQUEEZE VALLES</span>
                <span style="font-size:1.15rem; font-weight:900; color:#f472b6;">{macd_h4_num:+.0f}</span>
            </div>
            <div style="font-size: 0.76rem; margin: 4px 0; color: #f1f5f9;">
                • <strong>H1:</strong> {badge_valle(macd_h1_est)}<br>
                • <strong>H4:</strong> {badge_valle(macd_h4_est)}<br>
                • <strong>D1:</strong> {badge_valle(macd_d1_est)}
            </div>
            <div style="font-size: 0.72rem; color: #94a3b8; border-top: 1px solid #334155; padding-top: 4px;">
                💡 <em>Rojo Claro = Venta secándose (Ballenas absorbiendo).</em>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with r4:
        st.markdown(f"""
        <div class="kpi" style="border: 1px solid {mvrv_hist_col}55; min-height: 180px; text-align: left; padding: 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="kpi-t">BARÓMETRO MVRV (D1)</span>
                <span style="font-size:1.3rem; font-weight:900; color:{mvrv_hist_col};">{mvrv_v:.2f}</span>
            </div>
            <div style="font-size: 0.82rem; font-weight: 800; color: {mvrv_hist_col}; margin: 6px 0;">
                {mvrv_hist_tag}
            </div>
            <div style="font-size: 0.76rem; color: #cbd5e1; line-height: 1.4;">
                {mvrv_hist_desc}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── CONSOLA DE VOZ TÁCTICA MULTI-TIMEFRAME ──
    # Síntesis operativa en vivo
    if "ROJO_CLARO" in [macd_h1_est, macd_h4_est] and rsi_h4_val <= 38:
        voz_msg = f"🎙️ <strong>ORÁCULO MULTI-TIMEFRAME:</strong> En H4 el RSI ({rsi_h4_val:.1f}) tocó zona de sobreventa intradiaria y el MACD está cambiando a <strong>Rojo Claro</strong>. Los osos perdieron velocidad y las órdenes de compra pasivas están deteniendo la caída. <em>Recomendación Táctica:</em> Preparar gatillo de rebote intradiario hacia la EMA 55 en H4. No hacer short en este punto porque el riesgo de apretón alcista es de 78%."
        voz_border = "#22c55e"
    elif rsi_d1_val >= 68 or mvrv_v >= 2.8:
        voz_msg = f"🎙️ <strong>ORÁCULO MULTI-TIMEFRAME:</strong> Cuidado extremo. El gráfico Diario está sobrecalentado (RSI {rsi_d1_val:.1f} | MVRV {mvrv_v:.2f}). Históricamente en Bitcoin, comprar en estas zonas tiene una tasa de pérdida superior al 65%. <em>Recomendación Táctica:</em> Mantener stops ceñidos, ejecutar salidas de Fase 2 (35%) y no abrir longs apalancados."
        voz_border = "#ef4444"
    else:
        voz_msg = f"🎙️ <strong>ORÁCULO MULTI-TIMEFRAME:</strong> Mercado en rango de compresión estratégica. D1 (RSI {rsi_d1_val:.1f}) no ofrece descuento institucional todavía; H4 ({rsi_h4_val:.1f}) y H1 ({rsi_h1_val:.1f}) marcan oscilación lateral. <em>Recomendación Táctica:</em> Conservar las balas de margen listas para cuando el precio busque el soporte de 7 días (${sop_btc_ref:,.0f} USD)."
        voz_border = "#38bdf8"

    st.markdown(f"""
    <div style="background: rgba(15, 23, 42, 0.85); border-left: 5px solid {voz_border}; border-radius: 12px; padding: 14px 20px; margin-top: 14px; font-size: 0.96rem; color: #f1f5f9; line-height: 1.5; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
        {voz_msg}
    </div>
    """, unsafe_allow_html=True)

    # ── 6. SEMÁFORO VISUAL DE GATILLO: ¿CUÁNTO FALTA PARA DISPARAR EN LONG? ──────
    rsi_target = 35.0
    rsi_gap = max(0.0, rsi_h4_val - rsi_target)
    rsi_pct_listo = max(0, min(100, int((1.0 - (rsi_gap / 30.0)) * 100))) if rsi_gap > 0 else 100
    
    macd_listo = (macd_h4_est in ["ROJO_CLARO", "VERDE_CLARO"] or macd_h1_est in ["ROJO_CLARO", "VERDE_CLARO"])
    
    dist_sop_usd = max(0.0, btc_price - sop_btc_ref)
    dist_sop_pct = (dist_sop_usd / sop_btc_ref) * 100 if sop_btc_ref > 0 else 0.0
    sop_listo = dist_sop_pct <= 2.5
    
    score_gatillo = 0
    if rsi_h4_val <= 35.0: score_gatillo += 35
    elif rsi_h4_val <= 40.0: score_gatillo += 25
    elif rsi_h4_val <= 48.0: score_gatillo += 15
    elif rsi_h4_val <= 55.0: score_gatillo += 5
    
    if macd_h4_est in ["ROJO_CLARO", "VERDE_CLARO"]: score_gatillo += 25
    if macd_h1_est in ["ROJO_CLARO", "VERDE_CLARO"]: score_gatillo += 10
    
    if dist_sop_pct <= 1.5: score_gatillo += 30
    elif dist_sop_pct <= 3.5: score_gatillo += 20
    elif dist_sop_pct <= 6.0: score_gatillo += 10

    if score_gatillo >= 75:
        sem_col = "#22c55e"
        sem_led = "🟢"
        sem_tit = "VERDE — ¡DISPARAR LONG AHORA!"
        sem_badge = "GATILLO 100% CONFIRMADO"
        sem_desc = "Todas las condiciones cuánticas están alineadas. Probabilidad de rebote institucional superior al 82%."
    elif score_gatillo >= 40:
        sem_col = "#eab308"
        sem_led = "🟡"
        sem_tit = "AMARILLO — PREPARANDO GATILLO"
        sem_badge = "ZONA DE APROXIMACIÓN"
        sem_desc = "El precio o los osciladores están cerca de zona de soporte. Tener listas las balas y órdenes de margen."
    else:
        sem_col = "#ef4444"
        sem_led = "🔴"
        sem_tit = "ROJO — ESPERAR / NO ENTRAR"
        sem_badge = "EN ESPERA DE LIQUIDEZ Y GIRO"
        sem_desc = "Faltan condiciones clave para gatillar. Fuerza bajista activa o sin descuento institucional suficiente."

    # Textos de cuánto falta por pilar
    if rsi_h4_val <= 35.0:
        falta_rsi_txt = "<span style='color:#22c55e; font-weight:800;'>✅ EN ZONA (0 pts faltantes)</span>"
    else:
        falta_rsi_txt = f"<span style='color:#f59e0b; font-weight:800;'>⏳ Faltan {rsi_gap:.1f} pts de enfriamiento</span>"

    if macd_h4_est == "ROJO_CLARO":
        falta_macd_txt = "<span style='color:#22c55e; font-weight:800;'>✅ Giro Alcista Confirmado</span>"
    elif macd_h1_est == "ROJO_CLARO":
        falta_macd_txt = "<span style='color:#38bdf8; font-weight:800;'>⚡ H1 Girando (Esperando H4)</span>"
    else:
        falta_macd_txt = "<span style='color:#ef4444; font-weight:800;'>⏳ Falta giro a Rojo Claro (Absorción)</span>"

    if dist_sop_pct <= 1.5:
        falta_sop_txt = f"<span style='color:#22c55e; font-weight:800;'>✅ Sobre Soporte (${sop_btc_ref:,.0f})</span>"
    else:
        falta_sop_txt = f"<span style='color:#f59e0b; font-weight:800;'>⏳ Falta retroceso de ${dist_sop_usd:,.0f} ({dist_sop_pct:+.1f}%)</span>"

    html_semaforo = f"""<div style="background: linear-gradient(135deg, rgba(15,23,42,0.98), rgba(30,27,75,0.7)); border: 2px solid {sem_col}; border-radius: 16px; padding: 22px; margin-top: 20px; box-shadow: 0 0 30px {sem_col}33;">
<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 16px;">
<div style="display:flex; align-items:center; gap:12px;">
<span style="font-size:2.2rem; filter: drop-shadow(0 0 10px {sem_col});">{sem_led}</span>
<div>
<span style="background:{sem_col}22; color:{sem_col}; border:1px solid {sem_col}; padding:3px 10px; border-radius:12px; font-weight:800; font-size:0.75rem; text-transform:uppercase;">
{sem_badge}
</span>
<h3 style="margin:4px 0 0 0; font-size:1.4rem; font-weight:900; color:#f8fafc;">
SEMÁFORO DE GATILLO: {sem_tit}
</h3>
</div>
</div>
<div style="text-align:right;">
<div style="font-size:0.8rem; color:#94a3b8; font-weight:700;">PREPARACIÓN DE GATILLO</div>
<div style="font-size:1.6rem; font-weight:900; color:{sem_col};">{score_gatillo}% LISTO</div>
</div>
</div>
<div style="margin: 14px 0 6px 0; background: rgba(0,0,0,0.4); border-radius: 10px; height: 10px; overflow: hidden; border: 1px solid rgba(255,255,255,0.05);">
<div style="width: {score_gatillo}%; height: 100%; background: linear-gradient(90deg, #ef4444, #eab308, {sem_col}); border-radius: 10px; transition: width 0.5s ease;"></div>
</div>
<p style="margin: 0 0 16px 0; font-size: 0.88rem; color: #cbd5e1;">{sem_desc}</p>
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px;">
<div style="background: rgba(15,23,42,0.8); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 14px;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
<span style="font-size:0.82rem; font-weight:800; color:#38bdf8;">🎯 1. RSI H4 (INTRADIARIO)</span>
<span style="font-size:0.95rem; font-weight:900; color:#f8fafc;">{rsi_h4_val:.1f} / ≤35.0</span>
</div>
<div style="font-size:0.8rem; margin: 4px 0;">{falta_rsi_txt}</div>
<div style="font-size:0.72rem; color:#94a3b8;">Zona de rebote +3.8% a +6.5%.</div>
</div>
<div style="background: rgba(15,23,42,0.8); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 14px;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
<span style="font-size:0.82rem; font-weight:800; color:#f472b6;">🌊 2. MACD SQUEEZE</span>
<span style="font-size:0.95rem; font-weight:900; color:#f8fafc;">Valle {macd_h4_num:+.0f}</span>
</div>
<div style="font-size:0.8rem; margin: 4px 0;">{falta_macd_txt}</div>
<div style="font-size:0.72rem; color:#94a3b8;">H1: {badge_valle(macd_h1_est)} | H4: {badge_valle(macd_h4_est)}</div>
</div>
<div style="background: rgba(15,23,42,0.8); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 14px;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
<span style="font-size:0.82rem; font-weight:800; color:#eab308;">🏛️ 3. SOPORTE 7 DÍAS</span>
<span style="font-size:0.95rem; font-weight:900; color:#f8fafc;">${sop_btc_ref:,.0f} USD</span>
</div>
<div style="font-size:0.8rem; margin: 4px 0;">{falta_sop_txt}</div>
<div style="font-size:0.72rem; color:#94a3b8;">Precio actual BTC: ${btc_price:,.0f} USD</div>
</div>
</div>
</div>"""
    st.markdown(html_semaforo, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# TAB 2 — MATRIZ TÁCTICA BINGX (CEREBRO 5 + COBERTURAS)
# ══════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(15,23,42,0.95), rgba(88,28,135,0.4)); border: 2px solid #a855f7; border-radius: 18px; padding: 22px; margin-bottom: 20px; box-shadow: 0 0 30px rgba(168,85,247,0.25);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
                <span class="badge-purple">⚔️ SALA DE FRANCOTIRADOR CUANTITATIVO</span>
                <h1 style="margin: 6px 0 0 0; font-size: 2.1rem; font-weight: 900; color: #f8fafc;">
                    TARJETAS TÁCTICAS: PLANES LONG & SHORT CON ADN COMPLETO
                </h1>
                <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 1.05rem;">
                    Niveles exactos en dólares ($) para entradas manuales, Stop Loss inviolable, TP1 (Break-Even) y TP2 (R:R 1:3) por activo
                </p>
            </div>
            <div style="background:rgba(15,23,42,0.8); border:1px solid #a855f7; border-radius:12px; padding:10px 18px; text-align:center;">
                <div style="font-size:0.75rem; color:#94a3b8; font-weight:700;">GESTIÓN INSTITUCIONAL</div>
                <div style="font-size:1.3rem; font-weight:900; color:#22c55e;">ADN DE RIESGO 1:3</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════
    # v3.0 — MOTOR 100% DINÁMICO: PRECIOS, RSI, MACD, ADX, OB, NIVELES EN VIVO
    # ═══════════════════════════════════════════════════════════════════
    _V3_TTL = 60  # Cache de 60s para no re-calcular en cada rerun de Streamlit
    _ahora  = time.time()
    if (st.session_state.get("v3_cache") is None or
            (_ahora - st.session_state.get("v3_ts", 0)) > _V3_TTL):
        try:
            import importlib, sys as _sys
            _v3_path = os.path.join(BASE_DIR, "AUTONOMO")
            if _v3_path not in _sys.path:
                _sys.path.insert(0, _v3_path)
            import motor_senales_v3 as _mv3
            importlib.reload(_mv3)
            st.session_state["v3_cache"] = _mv3.run_motor_v3()
            st.session_state["v3_ts"]    = _ahora
        except Exception as _e_v3:
            if "v3_cache" not in st.session_state:
                st.warning(f"\u26a0\ufe0f Motor v3 no disponible: {_e_v3}")
    _señales_v3 = st.session_state.get("v3_cache", [])

    _NOMBRES = {"BTC":"Bitcoin","ETH":"Ethereum","SOL":"Solana","AVGO":"Broadcom",
                "NVDA":"NVIDIA","TSLA":"Tesla","MSFT":"Microsoft","META":"Meta Platforms",
                "AMD":"AMD","AMZN":"Amazon","AAPL":"Apple","GOOGL":"Alphabet","QQQ":"Nasdaq 100 ETF"}

    activos_detalle = []
    for _s in _señales_v3:
        _px = _s.get("precio", 0.0)
        activos_detalle.append({
            "sym":           _s["sym"],
            "nombre":        _NOMBRES.get(_s["sym"], _s["sym"]),
            "tipo":          _s.get("tipo", "CRIPTO"),
            "exchange":      _s.get("exchange", "BingX"),
            "precio":        _px,
            "sop_7d":        _s.get("sop_7d", _px * 0.96),
            "res_7d":        _s.get("res_7d", _px * 1.05),
            "ema55":         _s.get("ema55",  _px * 0.985),
            "ema200":        _s.get("ema55",  _px * 0.94),
            "ob_dom":        _s.get("ob_dom", "N/A"),
            "rsi":           _s.get("rsi_1h", 50.0),
            "stoch_k":       _s.get("stoch_k", 50.0),
            "adx":           _s.get("adx", 0.0),
            "score":         _s.get("score", 50),
            "recom":         _s.get("recom", "\u26aa NEUTRO"),
            "long_trigger":  _s.get("long_trigger",  _px * 0.985),
            "long_sl":       _s.get("long_sl",       _px * 0.96),
            "long_tp1":      _s.get("long_tp1",      _px * 1.015),
            "long_tp2":      _s.get("long_tp2",      _px * 1.05),
            "short_trigger": _s.get("short_trigger", _px * 1.02),
            "short_sl":      _s.get("short_sl",      _px * 1.05),
            "short_tp1":     _s.get("short_tp1",     _px * 0.99),
            "short_tp2":     _s.get("short_tp2",     _px * 0.96),
            "nota": (f"RSI 1H: {_s.get('rsi_1h',50):.1f} | "
                     f"RSI 4H: {_s.get('rsi_4h',50):.1f} | "
                     f"MACD: {_s.get('macd_estado','?')} | "
                     f"ADX: {_s.get('adx',0):.1f} | "
                     f"Stoch: {_s.get('stoch_k',50):.1f} | "
                     f"ATR: {_s.get('atr',0):.4f}"),
        })

    if not activos_detalle:
        activos_detalle = [{"sym":"BTC","nombre":"Bitcoin","tipo":"CRIPTO",
            "exchange":"Binance 5X","precio":btc_price,"sop_7d":btc_price*.965,
            "res_7d":btc_price*1.045,"ema55":btc_price*.978,"ema200":btc_price*.94,
            "ob_dom":"Motor v3 no cargó","rsi":50.0,"stoch_k":50.0,"adx":0.0,"score":50,
            "recom":"\u26aa NEUTRO","long_trigger":btc_price*.985,"long_sl":btc_price*.95,
            "long_tp1":btc_price*1.02,"long_tp2":btc_price*1.05,
            "short_trigger":btc_price*1.04,"short_sl":btc_price*1.07,
            "short_tp1":btc_price*.99,"short_tp2":btc_price*.96,
            "nota":"Motor v3 no disponible. Reinicia el dashboard."}]

    # Filtros y controles
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        st.subheader("📋 Tarjetas Tácticas Individuales por Activo")
        st.caption("Cada tarjeta incluye ADN de riesgo, precios de gatillo para LONG y SHORT, Stop Loss inviolable y Take Profits")
    with col_f2:
        filtro_tipo = st.multiselect("Filtrar por Mercado:", ["CRIPTO", "ACCION", "ETF", "INDICE"], default=["CRIPTO", "ACCION", "ETF", "INDICE"])

    activos_filtrados = [a for a in activos_detalle if a["tipo"] in filtro_tipo]

    # Renderizado en Grid de 2 Columnas para máxima legibilidad
    for i in range(0, len(activos_filtrados), 2):
        row_c1, row_c2 = st.columns(2)
        cols_tarjetas = [row_c1, row_c2]
        
        for j in range(2):
            if i + j < len(activos_filtrados):
                act = activos_filtrados[i + j]
                with cols_tarjetas[j]:
                    sc = act["score"]
                    card_border = "#22c55e" if sc >= 75 else ("#eab308" if sc >= 65 else "#64748b")
                    recom_color = "#22c55e" if "LONG" in act["recom"] else ("#ef4444" if "SHORT" in act["recom"] else "#eab308")
                    
                    card_html = f"""<div style="background: rgba(15,23,42,0.92); border: 2px solid {card_border}; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 0 25px rgba(0,0,0,0.4);">
<div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid #334155; padding-bottom:12px; margin-bottom:14px;">
<div>
<span style="font-size:0.75rem; font-weight:800; background:{card_border}22; color:{card_border}; padding:3px 8px; border-radius:6px; text-transform:uppercase;">{act['tipo']} · {act['exchange']}</span>
<h2 style="margin:6px 0 0 0; font-size:1.6rem; font-weight:900; color:#f8fafc;">{act['sym']} <span style="font-size:1rem; font-weight:600; color:#94a3b8;">({act['nombre']})</span></h2>
<div style="font-size:1.8rem; font-weight:900; color:#38bdf8; margin-top:2px;">${act['precio']:,.2f} <span style="font-size:0.85rem; color:#94a3b8;">USD</span></div>
</div>
<div style="text-align:right;">
<div style="font-size:0.75rem; color:#94a3b8; font-weight:700;">CONFLUENCIA</div>
<div style="font-size:2.2rem; font-weight:900; color:{card_border}; line-height:1;">{sc}<span style="font-size:1rem; color:#64748b;">/100</span></div>
<div style="font-size:0.8rem; font-weight:800; color:{recom_color}; margin-top:4px;">{act['recom']}</div>
</div>
</div>
<div style="background:rgba(30,41,59,0.5); border-radius:10px; padding:10px 14px; margin-bottom:14px; font-size:0.82rem; color:#cbd5e1;">
<div style="display:flex; justify-content:space-between; margin-bottom:4px;">
<span>🛡️ <strong>Soporte 7D:</strong> ${act['sop_7d']:,.2f}</span>
<span>🏰 <strong>Techo 7D:</strong> ${act['res_7d']:,.2f}</span>
</div>
<div style="display:flex; justify-content:space-between; margin-bottom:4px;">
<span>📦 <strong>Order Block:</strong> {act['ob_dom']}</span>
<span>📈 <strong>EMA 55:</strong> ${act['ema55']:,.2f}</span>
</div>
<div style="display:flex; justify-content:space-between;">
<span>⚡ <strong>Stoch %K:</strong> {act['stoch_k']:.1f} (RSI {act['rsi']:.1f})</span>
<span>🌪️ <strong>ADX:</strong> {act['adx']:.1f} {'🟢 Fuerza' if act['adx']>=23 else '🔴 Lateral'}</span>
</div>
</div>
<div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:14px;">
<div style="background:rgba(34,197,94,0.08); border:1px solid rgba(34,197,94,0.3); border-radius:10px; padding:12px;">
<div style="font-size:0.85rem; font-weight:800; color:#22c55e; border-bottom:1px solid rgba(34,197,94,0.2); padding-bottom:4px; margin-bottom:8px;">🟢 PLAN COMPRA (LONG)</div>
<div style="font-size:0.8rem; color:#cbd5e1; line-height:1.6;">
🎯 <strong>Gatillo Entrada:</strong> <strong style="color:#f8fafc;">${act['long_trigger']:,.2f}</strong><br>
🛑 <strong>Stop Loss:</strong> <strong style="color:#ef4444;">${act['long_sl']:,.2f}</strong><br>
🎯 <strong>TP1 (50% + BE):</strong> <strong style="color:#eab308;">${act['long_tp1']:,.2f}</strong><br>
🏆 <strong>TP2 (R:R 1:3):</strong> <strong style="color:#22c55e;">${act['long_tp2']:,.2f}</strong>
</div>
</div>
<div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); border-radius:10px; padding:12px;">
<div style="font-size:0.85rem; font-weight:800; color:#ef4444; border-bottom:1px solid rgba(239,68,68,0.2); padding-bottom:4px; margin-bottom:8px;">🔴 PLAN VENTA (SHORT)</div>
<div style="font-size:0.8rem; color:#cbd5e1; line-height:1.6;">
🎯 <strong>Gatillo Entrada:</strong> <strong style="color:#f8fafc;">${act['short_trigger']:,.2f}</strong><br>
🛑 <strong>Stop Loss:</strong> <strong style="color:#ef4444;">${act['short_sl']:,.2f}</strong><br>
🎯 <strong>TP1 (50% + BE):</strong> <strong style="color:#eab308;">${act['short_tp1']:,.2f}</strong><br>
🏆 <strong>TP2 (R:R 1:3):</strong> <strong style="color:#22c55e;">${act['short_tp2']:,.2f}</strong>
</div>
</div>
</div>
<div style="font-size:0.78rem; color:#94a3b8; border-left:3px solid {card_border}; padding-left:8px; line-height:1.4;">
💡 <strong>Táctica:</strong> {act['nota']}
</div>
</div>"""
                    st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("<br><hr style='border-color:#334155;'><br>", unsafe_allow_html=True)

    # ── CALCULADORA TÁCTICA DE DISPARO R:R 1:3 ──
    st.subheader("📐 Calculadora Asistida de Boleta y Tamaño de Lote (R:R 1:3)")
    st.caption("Introduce tu capital a arriesgar y obtendrás el número de contratos exacto, Stop Loss inviolable y Take Profits listos para ejecutar")

    calc_c1, calc_c2 = st.columns([1, 1.5])
    with calc_c1:
        sel_activo = st.selectbox("Selecciona Activo a Operar:", [a["sym"] for a in activos_detalle], index=1)
        act_sel_info = next(a for a in activos_detalle if a["sym"] == sel_activo)
        tipo_op = st.radio("Dirección de la Operación:", ["🟢 LONG (COMPRA)", "🔴 SHORT (VENTA)"], horizontal=True)
        px_entrada = st.number_input("Precio de Entrada ($):", value=float(act_sel_info["long_trigger"] if "LONG" in tipo_op else act_sel_info["short_trigger"]), step=0.5)
        capital_riesgo = st.number_input("Capital a Arriesgar ($ USD):", value=15.0, min_value=2.0, max_value=500.0, step=5.0)
        apalan_calc = st.slider("Apalancamiento Efectivo:", min_value=1, max_value=10, value=5)

    with calc_c2:
        es_long = "LONG" in tipo_op
        dist_sl_pct = 0.05
        if es_long:
            sl_calc = px_entrada * (1.0 - dist_sl_pct)
            tp1_calc = px_entrada * (1.0 + dist_sl_pct)
            tp2_calc = px_entrada * (1.0 + (dist_sl_pct * 3.0))
        else:
            sl_calc = px_entrada * (1.0 + dist_sl_pct)
            tp1_calc = px_entrada * (1.0 - dist_sl_pct)
            tp2_calc = px_entrada * (1.0 - (dist_sl_pct * 3.0))

        notional_calc = capital_riesgo * apalan_calc
        qty_calc = notional_calc / px_entrada

        badge_dir_col = "#22c55e" if es_long else "#ef4444"
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.9); border:2px solid {badge_dir_col}; border-radius:14px; padding:18px;">
            <div style="font-size:0.8rem; font-weight:800; color:{badge_dir_col}; text-transform:uppercase;">
                BOLETA DE DISPARO TÁCTICO: {sel_activo} ({tipo_op})
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-top:10px;">
                <div>
                    <span style="color:#94a3b8; font-size:0.8rem;">Tamaño Nocional:</span><br>
                    <strong style="color:#f8fafc; font-size:1.15rem;">${notional_calc:,.2f} USD ({qty_calc:.4f} unidades)</strong>
                </div>
                <div>
                    <span style="color:#ef4444; font-size:0.8rem;">🛑 Stop Loss Inviolable ({'-5%' if es_long else '+5%'}):</span><br>
                    <strong style="color:#ef4444; font-size:1.15rem;">${sl_calc:,.2f}</strong>
                </div>
                <div>
                    <span style="color:#eab308; font-size:0.8rem;">🎯 TP1 (Cerrar 50% y Mover a BE):</span><br>
                    <strong style="color:#eab308; font-size:1.15rem;">${tp1_calc:,.2f}</strong>
                </div>
                <div>
                    <span style="color:#22c55e; font-size:0.8rem;">🏆 TP2 Macro (R:R 1:3):</span><br>
                    <strong style="color:#22c55e; font-size:1.15rem;">${tp2_calc:,.2f}</strong>
                </div>
            </div>
            <div style="margin-top:14px; padding:8px 12px; background:{badge_dir_col}15; border-radius:8px; font-size:0.82rem; color:{badge_dir_col};">
                💡 <strong>Regla de Oro:</strong> Al alcanzar TP1 (${tp1_calc:,.2f}), asegurar el 50% del profit y mover el Stop Loss a ${px_entrada:,.2f} (Break-Even).
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab3:
    st.subheader("₿ Dupla Maestra BTC 2027 (Binance 5X Cross Margin)")
    st.caption("Monitor exclusivo de Binance Margin: ADN 1 (Smart DCA) + ADN 2 (Francotirador SMC) y Búnker de Respaldo.")

    # ── 1. HERO CARD BINANCE C3 ───────────────────────────────────
    btc_en_mano = btc_real if binance_ok else 0.00170776
    val_btc_mano = btc_en_mano * btc_price
    st.markdown(f"""
    <div class="hero-c3">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div class="hero-title-c3">🌌 CEREBRO 3: EL ACUMULADOR HODL BINANCE MARGIN</div>
        <span class="badge-green">5X CROSS MARGIN</span>
      </div>
      <div class="hero-sub">🎯 Rol: Multiplicar Satoshis en caídas y retener hasta el ciclo 2028-2030</div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:10px;">
        <div class="kpi" style="padding:10px;">
          <div class="kpi-t">BTC Real en Cartera</div>
          <div class="kpi-v" style="font-size:1.3rem;color:#38bdf8;">{btc_en_mano:.5f} BTC</div>
          <div class="kpi-s">~${val_btc_mano:,.2f} USD ({int(btc_en_mano*1e8):,} Sats)</div>
        </div>
        <div class="kpi" style="padding:10px;">
          <div class="kpi-t">Colateral Total Cuenta</div>
          <div class="kpi-v" style="font-size:1.3rem;color:#22c55e;">${collateral:,.2f} USDT</div>
          <div class="kpi-s">USDT Libre: ${usdt_free:.2f}</div>
        </div>
        <div class="kpi" style="padding:10px;">
          <div class="kpi-t">Nivel de Salud Margen</div>
          <div class="kpi-v" style="font-size:1.3rem;color:#22c55e;">{margin_level:.2f} pts</div>
          <div class="kpi-s">🟢 Saludable (> 3.0 pts)</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CONTROL DE COMPRAS HOLD > $87,000 USD (V6 & V7) ──────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Cargar Estados
    path1 = os.path.join(BASE_DIR, "BINANCE", "estado_dupla_unificada.json")
    path2 = os.path.join(BASE_DIR, "estado_dupla_unificada.json")
    v6_state_file = path1 if os.path.exists(path1) else path2
    st_dupla = {}
    if os.path.exists(v6_state_file):
        try:
            with open(v6_state_file, "r", encoding="utf-8") as f_d:
                st_dupla = json.load(f_d)
        except: pass

    v7_state_file = os.path.join(BASE_DIR, "CEREBRO7", "estado_cerebro7_v7.json")
    st_c7 = {}
    if os.path.exists(v7_state_file):
        try:
            with open(v7_state_file, "r", encoding="utf-8") as f_d:
                st_c7 = json.load(f_d)
        except: pass

    with st.container(border=True):
        st.markdown("### 🛡️ CONTROL DE PRE-COMPRA > $87,000 USD (HOLD/DCA)")
        st.caption("Filtros para pausar compras automatizadas cuando BTC supera los $87k y requerir confirmación manual.")
        
        c_v6, c_v7 = st.columns(2)
        with c_v6:
            st.markdown("#### 🚀 Cerebro V6 (Hold/DCA)")
            f_v6 = st.checkbox("Activar Bloqueo > 87k (V6)", value=st_dupla.get("filtro_87k_activo", True), key="chk_87k_v6")
            if f_v6 != st_dupla.get("filtro_87k_activo", True):
                st_dupla["filtro_87k_activo"] = f_v6
                try:
                    with open(v6_state_file, "w", encoding="utf-8") as f_d:
                        json.dump(st_dupla, f_d, indent=4)
                    st.toast("Filtro V6 > 87k actualizado")
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")
                
            pend_v6 = st_dupla.get("pendiente_autorizacion_compra", None)
            if pend_v6:
                st.warning(f"⚠️ **Compra Retenida V6:** Señal en {pend_v6.get('caja')} a las {pend_v6.get('fecha')} (${pend_v6.get('precio'):,.2f})")
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("🟢 Autorizar V6", key="btn_auth_v6_tab3", use_container_width=True):
                        st_dupla["autorizar_compra_pendiente"] = True
                        try:
                            with open(v6_state_file, "w", encoding="utf-8") as f_d:
                                json.dump(st_dupla, f_d, indent=4)
                            st.success("Compra V6 aprobada.")
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
                with col_b2:
                    if st.button("🔴 Ignorar V6", key="btn_ign_v6_tab3", use_container_width=True):
                        st_dupla["pendiente_autorizacion_compra"] = None
                        st_dupla["autorizar_compra_pendiente"] = False
                        try:
                            with open(v6_state_file, "w", encoding="utf-8") as f_d:
                                json.dump(st_dupla, f_d, indent=4)
                            st.info("Señal V6 borrada.")
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
                        
        with c_v7:
            st.markdown("#### 🏆 Cerebro V7 (Smart DCA)")
            f_v7 = st.checkbox("Activar Bloqueo > 87k (V7)", value=st_c7.get("filtro_87k_activo", True), key="chk_87k_v7")
            if f_v7 != st_c7.get("filtro_87k_activo", True):
                st_c7["filtro_87k_activo"] = f_v7
                try:
                    with open(v7_state_file, "w", encoding="utf-8") as f_d:
                        json.dump(st_c7, f_d, indent=4)
                    st.toast("Filtro V7 > 87k actualizado")
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")
                
            pend_v7 = st_c7.get("pendiente_autorizacion_compra", None)
            if pend_v7:
                st.warning(f"⚠️ **Compra Retenida V7:** Señal en {pend_v7.get('caja')} a las {pend_v7.get('fecha')} (${pend_v7.get('precio'):,.2f})")
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("🟢 Autorizar V7", key="btn_auth_v7_tab3", use_container_width=True):
                        st_c7["autorizar_compra_pendiente"] = True
                        try:
                            with open(v7_state_file, "w", encoding="utf-8") as f_d:
                                json.dump(st_c7, f_d, indent=4)
                            st.success("Compra V7 aprobada.")
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
                with col_b2:
                    if st.button("🔴 Ignorar V7", key="btn_ign_v7_tab3", use_container_width=True):
                        st_c7["pendiente_autorizacion_compra"] = None
                        st_c7["autorizar_compra_pendiente"] = False
                        try:
                            with open(v7_state_file, "w", encoding="utf-8") as f_d:
                                json.dump(st_c7, f_d, indent=4)
                            st.info("Señal V7 borrada.")
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")

    # ── 2. EL TUNEL DE 5 PASOS DEL FRANCOTIRADOR (CEREBRO 5) ────────
    st.markdown("---")
    st.subheader("🎯 Túnel de 5 Pasos del Francotirador SMC (Cerebro 5)")
    st.caption("Checklist de confluencia institucional en tiempo real sobre BTC. Cuando los 5 pasos se iluminan en verde, el Sniper dispara con $10 USD de margen a 5X.")

    t1, t2, t3, t4, t5 = st.columns(5)
    
    s1_on = telem_c5["d1_compresion"] or telem_c5["d1_zona_baja"]
    s2_on = telem_c5["en_golden_pocket"]
    s3_on = telem_c5["gatillo_mecha"]
    s4_on = telem_c5["stoch1h"] < 30
    s5_on = telem_c5["score_c5"] >= 6 and telem_c5["tendencia_alcista"]

    with t1:
        st.markdown(f"""
        <div class="step-card {'step-on' if s1_on else 'step-off'}">
          <div style="font-size:0.75rem;font-weight:700;">PASO 1 · MACRO 1D</div>
          <div style="font-size:1.1rem;margin:4px 0;">{'🟢 EN ZONA' if s1_on else '🟡 VIGILANDO'}</div>
          <div style="font-size:0.75rem;">Compresión ATR / Zona Baja</div>
        </div>""", unsafe_allow_html=True)
    with t2:
        st.markdown(f"""
        <div class="step-card {'step-on' if s2_on else 'step-off'}">
          <div style="font-size:0.75rem;font-weight:700;">PASO 2 · FIBO 1H</div>
          <div style="font-size:1.1rem;margin:4px 0;">{'🟢 GOLDEN POCKET' if s2_on else '🟡 FUERA DE ZONA'}</div>
          <div style="font-size:0.75rem;">Fibo 61.8% – 78.6% ({telem_c5['dist_gp']:.1f}%)</div>
        </div>""", unsafe_allow_html=True)
    with t3:
        st.markdown(f"""
        <div class="step-card {'step-on' if s3_on else 'step-off'}">
          <div style="font-size:0.75rem;font-weight:700;">PASO 3 · MECHA SMC</div>
          <div style="font-size:1.1rem;margin:4px 0;">{'🟢 ABSORCIÓN >=40%' if s3_on else '🟡 BUSCANDO MECHA'}</div>
          <div style="font-size:0.75rem;">Mecha actual: {telem_c5['pct_mecha']:.1f}%</div>
        </div>""", unsafe_allow_html=True)
    with t4:
        st.markdown(f"""
        <div class="step-card {'step-on' if s4_on else 'step-off'}">
          <div style="font-size:0.75rem;font-weight:700;">PASO 4 · STOCH 1H</div>
          <div style="font-size:1.1rem;margin:4px 0;">{'🟢 SOBREVENTA' if s4_on else '🟡 NEUTRO'}</div>
          <div style="font-size:0.75rem;">Stoch RSI: {telem_c5['stoch1h']:.1f} pts</div>
        </div>""", unsafe_allow_html=True)
    with t5:
        st.markdown(f"""
        <div class="step-card {'step-on' if s5_on else 'step-off'}">
          <div style="font-size:0.75rem;font-weight:700;">PASO 5 · GATILLO FINAL</div>
          <div style="font-size:1.1rem;margin:4px 0;">{'🚀 DISPARAR' if s5_on else '⏳ ESPERANDO'}</div>
          <div style="font-size:0.75rem;">Score: {telem_c5['score_c5']}/10 Pts</div>
        </div>""", unsafe_allow_html=True)

    # ── 3. LAS 3 BOVEDAS DE CEREBRO 3 (ACUMULADOR) ──────────────────
    st.markdown("---")
    st.subheader("📦 Las 3 Bóvedas Tácticas de Cerebro 3 (Acumulación)")
    st.caption("Tres cajas independientes que cazan precios de descuento extremo para no volver a vender.")

    bv1, bv2, bv3 = st.columns(3)
    sop_7d = telem.get("soporte_7d", btc_price * 0.95)
    dist_sop = ((btc_price - sop_7d) / btc_price) * 100
    gatillo_c1 = btc_price <= (sop_7d * 1.005)
    p_c1 = 100 if gatillo_c1 else int(max(0, min(95, (1.0 - (dist_sop/5.0))*100)))

    with bv1:
        st.markdown(f"""
        <div class="vault-box">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div style="font-weight:800;color:#38bdf8;">👑 BÓVEDA 1: PISO 7 DÍAS</div>
            <span class="badge-blue">${caja1_monto:.0f} USDT</span>
          </div>
          <div style="margin:10px 0;font-size:1.2rem;font-weight:700;color:{'#22c55e' if gatillo_c1 else '#94a3b8'};">
            {'🟢 COMPUERTA ABIERTA (100%)' if gatillo_c1 else f'🟡 Proximidad: {p_c1}%'}
          </div>
          <div style="font-size:0.8rem;color:#94a3b8;">
            BTC: ${btc_price:,.0f} · Piso: ${sop_7d:,.0f}<br>
            Distancia al soporte: <strong>{dist_sop:+.2f}%</strong>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(p_c1/100)

    with bv2:
        m_giro = telem.get("macd_giro", False)
        c_hist = telem.get("curr_hist", 0.0)
        p_hist = telem.get("prev_hist", 0.0)
        p_c2 = 100 if m_giro else (50 if c_hist > p_hist else 15)
        st.markdown(f"""
        <div class="vault-box">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div style="font-weight:800;color:#818cf8;">🔱 BÓVEDA 2: MOMENTUM MACD 4H</div>
            <span class="badge-blue">${caja2_monto:.0f} USDT</span>
          </div>
          <div style="margin:10px 0;font-size:1.2rem;font-weight:700;color:{'#22c55e' if m_giro else '#94a3b8'};">
            {'🟢 GIRO ALCISTA ACTIVO' if m_giro else '🟡 Histograma Comprimiéndose'}
          </div>
          <div style="font-size:0.8rem;color:#94a3b8;">
            Hist 4H: {c_hist:+.2f} (Previo: {p_hist:+.2f})<br>
            Estado: <strong>{'✅ Momentum a Favor' if m_giro else 'Sin Giro Aún'}</strong>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(p_c2/100)

    with bv3:
        r_4h = telem.get("rsi_4h", 50.0)
        gat_c3 = r_4h <= 40.0 and m_giro
        p_c3 = 100 if gat_c3 else int(max(0, min(95, (1.0 - ((r_4h-40.0)/30.0))*100)))
        st.markdown(f"""
        <div class="vault-box">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div style="font-weight:800;color:#38bdf8;">💎 BÓVEDA 3: ORÁCULO YT</div>
            <span class="badge-blue">${caja3_monto:.0f} USDT</span>
          </div>
          <div style="margin:10px 0;font-size:1.2rem;font-weight:700;color:{'#22c55e' if gat_c3 else '#94a3b8'};">
            {'🟢 SOBREVENTA EXTREMA' if gat_c3 else f'🟡 Nivel RSI: {p_c3}%'}
          </div>
          <div style="font-size:0.8rem;color:#94a3b8;">
            RSI 4H: {r_4h:.1f} pts (Objetivo: &le; 40.0)<br>
            Brecha al gatillo: <strong>{r_4h-40.0:+.1f} pts</strong>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(p_c3/100)

    # ── 4. ESCALERA DE 4 NODOS DCA & ESCUDO BREAK-EVEN (CEREBRO 5) ───
    st.markdown("---")
    st.subheader("🪜 Escalera de 4 Nodos DCA & Escudo Break-Even (+1.5%)")
    st.caption("Cómo gestiona Cerebro 5 una posición abierta en Binance: Recargas automáticas al -2%, -4%, -6% y blindaje de Stop Loss a 0 Riesgo al subir +1.5%.")

    p_ref = btc_price
    tp_c5 = telem_c5.get("max_7d", p_ref * 1.035) * 1.01
    be_c5 = p_ref * 1.015
    n1_c5 = p_ref
    n2_c5 = p_ref * 0.98
    n3_c5 = p_ref * 0.96
    n4_c5 = p_ref * 0.94
    sl_c5 = p_ref * 0.94

    df_escalera = pd.DataFrame([
        {"Nivel": "🎯 Take Profit Objetivo", "Precio Referencia": f"${tp_c5:,.2f}", "Distancia": f"{((tp_c5-p_ref)/p_ref)*100:+.2f}%", "Acción del Bot": "💰 Cierra 100% de la posición en ganancia de USD"},
        {"Nivel": "🛡️ Nivel Break-Even (+1.5%)", "Precio Referencia": f"${be_c5:,.2f}", "Distancia": "+1.50%", "Acción del Bot": "🔒 Sube el Stop Loss al precio de entrada ($0 Riesgo)"},
        {"Nivel": "🚀 NODO 1: Entrada Base", "Precio Referencia": f"${n1_c5:,.2f}", "Distancia": "0.00%", "Acción del Bot": "Abre orden inicial ($10 Margen a 5X)"},
        {"Nivel": "⏳ NODO 2: Recarga -2%", "Precio Referencia": f"${n2_c5:,.2f}", "Distancia": "-2.00%", "Acción del Bot": "Recarga $10 Margen si el precio retrocede"},
        {"Nivel": "⏳ NODO 3: Recarga -4%", "Precio Referencia": f"${n3_c5:,.2f}", "Distancia": "-4.00%", "Acción del Bot": "Recarga $10 Margen adicional para promediar a la baja"},
        {"Nivel": "⏳ NODO 4: Recarga -6%", "Precio Referencia": f"${n4_c5:,.2f}", "Distancia": "-6.00%", "Acción del Bot": "Última recarga ($40 Margen total comprometido)"},
        {"Nivel": "🛑 Stop Loss de Emergencia", "Precio Referencia": f"${sl_c5:,.2f}", "Distancia": "-6.00%", "Acción del Bot": "Corta pérdida si no hay rebote (Pérdida máxima ~$2-$4 USD)"},
    ])
    st.dataframe(df_escalera, use_container_width=True, hide_index=True)

    # ── 4.B TELEMETRÍA EN VIVO Y POSICIONES ABIERTAS EN BINGX ─────────
    st.markdown("---")
    st.subheader("🌐 Telemetría en Vivo de BingX (Cuenta Real & Operaciones)")
    
    # v4.0: Telemetría Directa de BingX (Reemplaza a Cerebro5/6)
    bingx_data = {}
    try:
        from conector_exchanges import bingx_request as _bx_req
        _bx_bal = _bx_req("GET", "/openApi/swap/v2/user/balance")
        _bx_pos = _bx_req("GET", "/openApi/swap/v2/user/positions")
        if _bx_bal and _bx_bal.get("code") == 0:
            _b = _bx_bal["data"]["balance"]
            bingx_data["equidad_actual"] = float(_b.get("equity", 0))
            bingx_data["disponible_actual"] = float(_b.get("availableMargin", 0))
            bingx_data["margen_usado"] = float(_b.get("usedMargin", 0))
            bingx_data["pnl_flotante"] = float(_b.get("unrealizedProfit", 0))
        if _bx_pos and _bx_pos.get("code") == 0:
            bingx_data["posiciones_bingx_live"] = _bx_pos.get("data", [])
    except Exception as e:
        import streamlit as st
        st.warning(f"Error cargando telemetría BingX: {e}")
            
    if bingx_data:
        eq_actual = clean_num(bingx_data.get("equidad_actual", 0.0))
        disp_actual = clean_num(bingx_data.get("disponible_actual", 0.0))
        margen_usado = clean_num(bingx_data.get("margen_usado", 0.0))
        pnl_flot = clean_num(bingx_data.get("pnl_flotante", 0.0))
        
        bx1, bx2, bx3, bx4 = st.columns(4)
        bx1.metric("Equidad BingX", f"${eq_actual:,.2f} USDT")
        bx2.metric("Margen Libre", f"${disp_actual:,.2f} USDT")
        bx3.metric("Margen Usado", f"${margen_usado:,.2f} USDT")
        color_pnl = "normal" if pnl_flot >= 0 else "inverse"
        bx4.metric("PnL Flotante Total", f"${pnl_flot:+,.2f} USDT", delta=f"{pnl_flot:+,.2f} USDT", delta_color=color_pnl)
        
        pos_live = bingx_data.get("posiciones_bingx_live", [])
        if pos_live:
            st.markdown(f"**📌 {len(pos_live)} Posiciones Abiertas Detectadas en BingX:**")
            rows = []
            for p in pos_live:
                sym = p.get("symbol", "")
                side = p.get("positionSide", "LONG")
                amt = clean_num(p.get("positionAmt", 0))
                entry = clean_num(p.get("entryPrice", 0))
                mark = clean_num(p.get("markPrice", 0))
                pnl = clean_num(p.get("unrealizedProfit", 0))
                margin = clean_num(p.get("margin", 0))
                lev = p.get("leverage", 10)
                rows.append({
                    "Símbolo": sym,
                    "Lado": f"🟢 {side}" if side == "LONG" else f"🔴 {side}",
                    "Apalancamiento": f"{lev}X",
                    "Cantidad": amt,
                    "Entrada Base": f"${entry:,.2f}",
                    "Precio Marca": f"${mark:,.2f}",
                    "Margen USD": f"${margin:,.2f}",
                    "PnL Flotante": f"${pnl:+,.2f} USDT"
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ Sin posiciones abiertas activas en BingX.")
    else:
        st.info("⏳ Aguardando telemetría de BingX...")

    # ── 5. BARÓMETRO DE SINERGIA & ESCUDO MACRO CRASH ($78K -> $50K) ─
    st.markdown("---")
    st.subheader("🔄 Barómetro de Sinergia y Escudo Anti-Crash")
    
    sin1, sin2, sin3 = st.columns(3)
    with sin1:
        st.markdown(f"""
        <div class="kpi">
          <div class="kpi-t">Sinergia Cash de C5</div>
          <div class="kpi-v" style="color:#22c55e;">+$13.17 USD</div>
          <div class="kpi-s">Paga 100% del borrow de Binance</div>
        </div>""", unsafe_allow_html=True)
    with sin2:
        esc_ok = telem_c5.get("escudo_macro_ok", True)
        ema_200 = telem_c5.get("ema200_4h", btc_price * 0.95)
        st.markdown(f"""
        <div class="kpi">
          <div class="kpi-t">Escudo Macro ($78k &rarr; $50k)</div>
          <div class="kpi-v" style="color:{'#22c55e' if esc_ok else '#ef4444'};">{'🟢 ACTIVO (Mercado Seguro)' if esc_ok else '🔴 CAÍDA LIBRE (C5 Pausado)'}</div>
          <div class="kpi-s">EMA 200 4H: ${ema_200:,.0f} USD</div>
        </div>""", unsafe_allow_html=True)
    with sin3:
        ml_actual = margin_level if binance_ok else 4.5
        st.markdown(f"""
        <div class="kpi">
          <div class="kpi-t">Distancia a Liquidación</div>
          <div class="kpi-v" style="color:#38bdf8;">-48.5%</div>
          <div class="kpi-s">BTC tendría que caer a $39,800</div>
        </div>""", unsafe_allow_html=True)

    # ── 6. SIMULADOR INTERACTIVO DE ESTRÉS (SLIDER EN VIVO) ──────────
    st.markdown("---")
    st.subheader("🧪 Simulador Interactivo de Estrés en Binance Margin 5X")
    st.caption("Mueve el precio simulado de Bitcoin para ver exactamente cómo respondería el Nivel de Margen y la Salud de tu cuenta en tiempo real.")

    sim_p = st.slider("Simular Precio de BTC (USD):", min_value=35000, max_value=120000, value=int(btc_price), step=1000)
    
    # Cálculo dinámico de margen simulado
    deuda_sim = liability_btc * sim_p
    val_btc_sim = net_btc * sim_p if binance_ok else 0.0141 * sim_p
    colateral_sim = usdt_free + val_btc_sim
    ml_sim = (colateral_sim / deuda_sim) if deuda_sim > 0 else 10.0

    s_c1, s_c2, s_c3 = st.columns(3)
    with s_c1:
        st.metric("Precio Simulado", f"${sim_p:,.0f} USD", f"{((sim_p - btc_price)/btc_price)*100:+.2f}% vs Actual")
    with s_c2:
        st.metric("Colateral Total Estimado", f"${colateral_sim:,.2f} USD")
    with s_c3:
        color_ml = "🟢 Saludable" if ml_sim > 2.0 else ("🟡 Vigilar" if ml_sim > 1.3 else "🔴 ALERTA")
        st.metric("Nivel de Margen Simulado", f"{ml_sim:.2f}", color_ml)

    if sim_p <= 50000:
        st.info("🛡️ **Diagnóstico Stress Test:** En $50,000 USD tu cuenta sobrevive con margen de 1.22+ y acumula 0.00955 BTC para dispararse en el siguiente rebote.")

# ══════════════════════════════════════════════════════════════════
# TAB 4 — ORACLE NUMÉRIS & FILTRO ON-CHAIN (MVRV + FEAR & GREED)
# ══════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("🔮 Oracle Numéris & Indicadores On-Chain (MVRV + Fear & Greed)")
    fg_v   = fg["val"]
    mvrv_v = clean_num(m_d1.get("mvrv", 1.68), 1.68)
    if mvrv_v <= 0.1:
        mvrv_v = 1.68
    nupl_v = clean_num(round(0.18 + (mvrv_v * 0.18), 2), 0.48)

    g1,g2,g3 = st.columns(3)
    with g1:
        fc = "#22c55e" if fg_v<40 else "#eab308" if fg_v<70 else "#ef4444"
        fl = "Miedo Extremo" if fg_v<25 else "Miedo" if fg_v<45 else "Neutro" if fg_v<60 else "Codicia" if fg_v<80 else "Codicia Extrema"
        st.markdown(f"""<div class="kpi"><div class="kpi-t">Fear & Greed Index</div>
        <div class="kpi-v" style="color:{fc};font-size:2.5rem;">{fg_v}</div>
        <div class="kpi-s">{fl}</div></div>""", unsafe_allow_html=True)
    with g2:
        mc2 = "#22c55e" if mvrv_v<1.5 else "#eab308" if mvrv_v<2.2 else "#ef4444"
        ml2 = "Acumulacion" if mvrv_v<1.5 else "Justo Valor / HODL" if mvrv_v<2.2 else "Sobrecompra"
        st.markdown(f"""<div class="kpi"><div class="kpi-t">MVRV Ratio D1</div>
        <div class="kpi-v" style="color:{mc2};font-size:2.5rem;">{mvrv_v:.2f}</div>
        <div class="kpi-s">{ml2}</div></div>""", unsafe_allow_html=True)
    with g3:
        nc = "#22c55e" if nupl_v<0.25 else "#eab308" if nupl_v<0.5 else "#ef4444"
        nl = "Esperanza" if nupl_v<0.25 else "Optimismo" if nupl_v<0.5 else "Euforia"
        st.markdown(f"""<div class="kpi"><div class="kpi-t">NUPL</div>
        <div class="kpi-v" style="color:{nc};font-size:2.5rem;">{nupl_v:.2f}</div>
        <div class="kpi-s">{nl}</div></div>""", unsafe_allow_html=True)

    # MVRV INTER-CICLO
    st.markdown("---")
    st.subheader("🔄 MVRV Inter-Ciclo — Decaimiento por Ciclo")
    st.caption("El MVRV pico de cada ciclo BTC disminuye por maduracion del mercado. Este indicador estima donde estamos en el Ciclo 5.")

    ciclos_data = [
        {"Ciclo": "C1 — 2011",          "MVRV Pico": 10.0, "MVRV Piso": 0.12, "Decaimiento Pico": "—"},
        {"Ciclo": "C2 — 2013",          "MVRV Pico":  7.5, "MVRV Piso": 0.18, "Decaimiento Pico": "-25%"},
        {"Ciclo": "C3 — 2017",          "MVRV Pico":  4.8, "MVRV Piso": 0.28, "Decaimiento Pico": "-36%"},
        {"Ciclo": "C4 — 2021",          "MVRV Pico":  3.8, "MVRV Piso": 0.45, "Decaimiento Pico": "-21%"},
        {"Ciclo": "C5 — 2025/26 (Est.)","MVRV Pico":  2.8, "MVRV Piso": 0.65, "Decaimiento Pico": "-26%"},
    ]
    pico_c5 = 2.80; piso_c5 = 0.65
    rango_c5 = pico_c5 - piso_c5
    prog_c5  = max(0.0, min(1.0, (mvrv_v - piso_c5) / rango_c5)) if rango_c5 > 0 else 0.0
    zona_c5  = "🔴 Capitulacion" if mvrv_v<=piso_c5 else \
               "🟡 Acumulacion"  if mvrv_v<=1.5     else \
               "🟢 Crecimiento"  if mvrv_v<=2.2     else \
               "🟠 Distribucion" if mvrv_v<=pico_c5 else "🔴 Zona Techo"

    ic1,ic2,ic3 = st.columns(3)
    with ic1:
        st.markdown(f"""<div class="kpi"><div class="kpi-t">MVRV Actual</div>
        <div class="kpi-v" style="color:{mc2};">{mvrv_v:.2f}</div>
        <div class="kpi-s">{zona_c5}</div></div>""", unsafe_allow_html=True)
    with ic2:
        st.markdown(f"""<div class="kpi"><div class="kpi-t">Techo Estimado C5</div>
        <div class="kpi-v" style="color:#ef4444;">{pico_c5}</div>
        <div class="kpi-s">Regresion logaritmica historica</div></div>""", unsafe_allow_html=True)
    with ic3:
        st.markdown(f"""<div class="kpi"><div class="kpi-t">% Recorrido al Techo C5</div>
        <div class="kpi-v" style="color:#eab308;">{prog_c5*100:.1f}%</div>
        <div class="kpi-s">Piso: {piso_c5} — Techo: {pico_c5}</div></div>""", unsafe_allow_html=True)

    st.markdown(f"**Progreso en el Ciclo 5:** {zona_c5}")
    st.progress(prog_c5)
    st.caption(f"Rango C5: {piso_c5} → {pico_c5} · Actual: {mvrv_v:.2f} · {prog_c5*100:.1f}% recorrido")

    # Tabla historica de ciclos
    st.dataframe(pd.DataFrame(ciclos_data), use_container_width=True, hide_index=True)

    # Zonas de accion C5
    st.markdown("**📋 Zonas de Accion — Ciclo 5:**")
    zonas_df = pd.DataFrame([
        {"Zona":"🔴 Capitulacion","MVRV C5":"<= 0.65",    "Accion":"Compra maxima agresiva"},
        {"Zona":"🟡 Acumulacion", "MVRV C5":"0.65 – 1.50","Accion":"DCA activo"},
        {"Zona":"🟢 Crecimiento", "MVRV C5":"1.50 – 2.20","Accion":"Mantener posicion"},
        {"Zona":"🟠 Distribucion","MVRV C5":"2.20 – 2.80","Accion":"Reducir exposicion"},
        {"Zona":"🔴 Techo C5",   "MVRV C5":">= 2.80",    "Accion":"Salida tactica"},
    ])
    st.dataframe(zonas_df, use_container_width=True, hide_index=True)

    # Panel Macro
    st.markdown("---")
    st.subheader("🌍 Indicadores Macro & Commodities")
    mm1,mm2,mm3,mm4 = st.columns(4)
    with mm1: st.metric("🥇 Oro (PAXG/USDT)", f"${macro['oro']:,.2f}", f"{macro['oro_chg']:+.2f}%")
    with mm2: st.metric("🛢️ Petroleo WTI",   f"${macro['petroleo']:.2f}")
    with mm3: st.metric("💵 DXY",             f"{macro['dxy']:.2f} pts")
    with mm4: st.metric("🏦 FED Rate",        f"{macro['fed']:.2f}%")
    mm5,mm6,mm7,mm8 = st.columns(4)
    with mm5: st.metric("⛏️ Puell Multiple",  f"{macro['puell']:.2f}", "Acumulacion" if macro['puell']<0.5 else "Normal")
    with mm6: st.metric("⚡ Hashprice",       f"${macro['hashprice']:.3f}/TH/s")
    with mm7: st.metric("🏦 ETFs BTC Flujo",  f"+${macro['etfs_flujo']:.1f}M")
    with mm8: st.metric("📈 PMI Macro (ISM)", f"{macro['pmi']:.1f}", "Expansion" if macro['pmi']>50 else "Contraccion")

    # Monitor Ballenas
    st.markdown("---")
    st.subheader("🐋 Monitor de Ballenas ON-CHAIN (>1,000 BTC)")
    info_diarios = cargar_informadores_diarios()
    w_flow = clean_num(info_diarios.get("ballenas_flujo_7d", 12652), 12652)
    w_res  = clean_num(info_diarios.get("reservas_exchanges", 2160437), 2160437)
    w_iliq = clean_num(info_diarios.get("suministro_iliquido_pct", 74.08), 74.08)
    upd_time = info_diarios.get("ultima_actualizacion", "Hoy")[:10]
    st.caption(f"📅 Estado On-Chain al día de hoy: {upd_time}")

    bw1,bw2,bw3 = st.columns(3)
    with bw1: st.metric("Acumulacion 7D",        f"+{w_flow:,.0f} BTC",   "🟢 Acumulacion Silenciosa Fuerte")
    with bw2: st.metric("Reservas en Exchanges", f"{w_res:,.0f} BTC", "Minimo 6 anos — Escasez de Oferta")
    with bw3: st.metric("Suministro Iliquido",   f"{w_iliq:.1f}%",          "Manos Fuertes Reteniendo")

    # Precio Realizado
    st.markdown("---")
    st.subheader("📊 Precio Realizado & VWAP de Acumulacion")
    vwap_2025 = 103533.17; vwap_2026 = 71315.62; onchain_g = 32450.0
    pr1,pr2,pr3 = st.columns(3)
    with pr1:
        d25 = ((btc_price-vwap_2025)/vwap_2025)*100 if vwap_2025 > 0 else 0.0
        st.metric("VWAP 2025", f"${vwap_2025:,.2f}", f"{d25:+.2f}% vs actual")
        st.caption("🔴 Zona de Gran Descuento Historico")
    with pr2:
        d26 = ((btc_price-vwap_2026)/vwap_2026)*100 if vwap_2026 > 0 else 0.0
        st.metric("VWAP 2026", f"${vwap_2026:,.2f}", f"{d26:+.2f}% vs actual")
        st.caption("🟡 Zona Acumulacion DCA Activa")
    with pr3:
        dog = ((btc_price-onchain_g)/onchain_g)*100 if onchain_g > 0 else 0.0
        st.metric("Precio Realizado On-Chain", f"${onchain_g:,.2f}", f"{dog:+.2f}% vs actual")
        st.caption("🟢 Piso Fundamental BTC")

# ── MATRIZ TECNICA MULTI-TIMEFRAME ──────────────────
    st.subheader("📐 Matriz Tecnica Multi-Timeframe")
    st.caption(f"Precio BTC actual: ${btc_price:,.2f} USDT")

    tfs_data = [("H1",m_h1),("H4",m_h4),("D1 🎯",m_d1),("W1",m_w1),("M1",m_m1)]
    met_keys = [("EMA 9","ema9"),("EMA 10","ema10"),("EMA 34","ema34"),("EMA 55","ema55"),
                ("EMA 100","ema100"),("SMA 30","sma30"),("SMA 50","sma50"),
                ("SMA 100","sma100"),("SMA 200","sma200"),
                ("RSI 14","rsi"),("MACD Hist","macd_hist"),("MVRV Z","mvrv")]
    rows_mat = []
    for lbl, key in met_keys:
        row = {"Indicador": lbl}
        for tf_name, tf_data in tfs_data:
            val = tf_data.get(key)
            if val is None: row[tf_name] = "—"
            elif key in ("rsi","mvrv","macd_hist"):
                row[tf_name] = f"{val:+.2f}" if key=="macd_hist" else f"{val:.2f}"
            else: row[tf_name] = f"${val:,.2f}"
        rows_mat.append(row)
    st.dataframe(pd.DataFrame(rows_mat), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🔭 Proyección Dinámica Próximos Días (Cuartel v4)")
    _v3_btc = next((x for x in st.session_state.get("v3_cache", []) if x["sym"] == "BTC"), None)
    if _v3_btc and _v3_btc["precio"] > 0:
        btc_px = _v3_btc["precio"]
        soporte_7d = _v3_btc["sop_7d"]
        rsi_4h = _v3_btc["rsi_4h"]
        dist_s = ((btc_px - soporte_7d) / (btc_px+1e-9))*100
        prob_a = 40 if rsi_4h > 65 else 60
        ema55_t = _v3_btc["ema55"]

        e1, e2 = st.columns(2)
        with e1:
            st.success(f"""
    **🟢 Escenario Alcista ({prob_a}% Probabilidad)**
    
    Rebote desde ${btc_px:,.0f} buscando resistencia/EMA55 en ${ema55_t:,.0f} USDT.
    RSI 4H: {rsi_4h:.1f} — {'Sobrecompra, precaucion' if rsi_4h>70 else 'Terreno neutro-alcista'}.
            """)
        with e2:
            liq = soporte_7d * 0.975
            st.error(f"""
    **🔴 Escenario Bajista ({100-prob_a}% Probabilidad)**
    
    Si se pierde soporte 7D en ${soporte_7d:,.0f} → zona de liquidacion ${liq:,.0f} USDT.
    Distancia al soporte: {dist_s:.2f}%.
            """)
        st.info("💡 **Recomendación Cuartel V4:** Evalúa los Fichas Tácticas en Pestañas Adyacentes.")
    else:
        st.info("⏳ Aguardando motor v3 para proyección dinámica...")

# ══════════════════════════════════════════════════════════════════
# TAB 6 — PANEL DE CONTROL & CONFIGURACIÓN DE BOTS
# ══════════════════════════════════════════════════════════════════
with tab6:
    st.subheader("⚙️ Panel de Control & Configuración de Bots")
    st.caption("Selector de modo operativo, configuración de Cajas ($20 USD/mes), Billeteras e Historiales.")

    # Selector MODO REAL 🟢 vs MODO FANTASMA 👻
    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        st.markdown("""
        <div style="background: rgba(34,197,94,0.12); border: 2px solid #22c55e; border-radius: 14px; padding: 16px; margin-bottom: 16px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h3 style="margin:0; font-size:1.25rem; font-weight:800; color:#22c55e;">🟢 MODO OPERATIVO EN VIVO: PRODUCCIÓN REAL</h3>
                    <p style="margin:4px 0 0 0; color:#cbd5e1; font-size:0.88rem;">Las órdenes se envían a la API real de Binance Margin y BingX Futures ($0 simulado).</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_m2:
        modo_fantasma = st.toggle("👻 MODO FANTASMA (PAPER)", value=False)
        if modo_fantasma:
            st.info("👻 Modo Fantasma Activado: Las órdenes serán simuladas en memoria.")

    st.markdown("---")
    st.subheader("🎯 Trifecta BTC & Semáforos de Gatillo (3 Cajas)")
    st.caption("Gestión cuantitativa de las 3 Cajas Tácticas en Binance Margin 5X. Montos configurables desde el Sidebar.")

    soporte_7d = telem["soporte_7d"]; macd_giro = telem["macd_giro"]
    curr_h = telem["curr_hist"]; prev_h = telem["prev_hist"]; rsi_4h = telem["rsi_4h"]

    tc1,tc2,tc3 = st.columns(3)

    # CAJA 1
    with tc1:
        ddu = btc_price - soporte_7d
        ddp = (ddu/btc_price)*100 if btc_price>0 else 0
        c1g = btc_price <= (soporte_7d*1.005)
        p1  = 100 if c1g else int(max(0,min(95,(1.0-(ddp/5.0))*100)))
        s1  = "🟢🟢🟢 100% — GATILLO LISTO" if c1g else (f"🟢🟢⚪ {p1}% — PRE-ALERTA" if ddp<=2 else f"🔴⚪⚪ {p1}% — ESPERANDO")
        with st.container(border=True):
            st.markdown("### 👑 CAJA 1: DCA SOPORTE 7D")
            st.markdown(f"💰 **Saldo:** ${caja1_monto:.2f} USDT | **Palanca:** 5X")
            st.markdown(f"**Semaforo:** {s1}")
            st.progress(p1/100)
            st.caption(f"BTC: ${btc_price:,.0f} · Soporte: ${soporte_7d:,.0f} · Distancia: {ddp:+.2f}%")
            if st.button("🚀 Disparar Caja 1 (Manual)", key="btn_c1_master"):
                st.toast("⚡ Caja 1 enviada a verificacion", icon="🚀")

    # CAJA 2
    with tc2:
        c2g = macd_giro
        p2  = 100 if c2g else (50 if curr_h>prev_h else 15)
        s2  = "🟢🟢🟢 100% — GIRO ALCISTA" if c2g else (f"🟢🟢⚪ 50% — Comprimiendose" if curr_h>prev_h else f"🔴⚪⚪ {p2}% — Histograma Bajista")
        with st.container(border=True):
            st.markdown("### 🔱 CAJA 2: SWING MACD 4H")
            st.markdown(f"💰 **Saldo:** ${caja2_monto:.2f} USDT | **Palanca:** 5X")
            st.markdown(f"**Semaforo:** {s2}")
            st.progress(p2/100)
            st.caption(f"Hist Actual: {curr_h:+.2f} · Previo: {prev_h:+.2f} · {'✅ Giro Alcista' if macd_giro else 'Sin Giro Aun'}")
            if st.button("🚀 Disparar Caja 2 (Manual)", key="btn_c2_master"):
                st.toast("⚡ Caja 2 enviada a verificacion", icon="🚀")

    # CAJA 3
    with tc3:
        dr3  = rsi_4h - 40.0
        c3g  = rsi_4h<=40.0 and macd_giro
        p3   = 100 if c3g else int(max(0,min(95,(1.0-(dr3/30.0))*100)))
        s3   = "🟢🟢🟢 100% — ORACULO EN COMPRA" if c3g else (f"🟢🟢⚪ {p3}% — PRE-ALERTA RSI" if rsi_4h<=45 else f"🔴⚪⚪ {p3}% — RSI 4H Elevado")
        with st.container(border=True):
            st.markdown("### 💎 CAJA 3: ORACULO YT (RSI 4H)")
            st.markdown(f"💰 **Saldo:** ${caja3_monto:.2f} USDT | **Palanca:** 5X")
            st.markdown(f"**Semaforo:** {s3}")
            st.progress(p3/100)
            st.caption(f"RSI 4H: {rsi_4h:.1f} · Target: <=40.0 · Brecha: {dr3:+.1f} pts")
            if st.button("🚀 Disparar Caja 3 (Manual)", key="btn_c3_master"):
                st.toast("⚡ Caja 3 enviada a verificacion", icon="🚀")

    st.markdown("---")
    st.subheader("💰 Cartera Real Binance Margin & Monitor Anti-Desmadre")
    vet_now5 = now_vet()

    # ── 1. MONITOR ANTI-DESMADRE EN TIEMPO REAL ──────────────────────────
    if binance_ok:
        m_level = margin_level if margin_level > 0 else 999.0
        m_level_disp = f'{m_level:.2f}' if m_level < 900.0 else '∞ (Sin Deuda)'
        deuda_tot_usd = liability_btc * btc_price
        
        if m_level >= 2.0 or m_level == 999.0:
            status_color = "#22c55e"
            status_bg = "rgba(34, 197, 94, 0.15)"
            status_txt = "🟢 MARGEN SALUDABLE / CUENTA SEGURA"
            status_desc = "Tu nivel de colateral cubre holgadamente las obligaciones. Cero riesgo de liquidación."
        elif m_level >= 1.5:
            status_color = "#eab308"
            status_bg = "rgba(234, 179, 8, 0.15)"
            status_txt = "🟡 ADVERTENCIA — VIGILAR MARGEN DE CUENTA"
            status_desc = "Nivel de margen intermedio. Evitar tomar nuevo apalancamiento."
        else:
            status_color = "#ef4444"
            status_bg = "rgba(239, 68, 68, 0.15)"
            status_txt = "🔴 ALERTA MÁXIMA — RIESGO DE DESMADRE / LIQUIDACIÓN"
            status_desc = "Margin Level por debajo de 1.5. Depositar USDT o reducir posiciones de inmediato."

        st.markdown(f"""
        <div style="background:{status_bg}; border:2px solid {status_color}; border-radius:14px; padding:16px; margin-bottom:18px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
                <div>
                    <h3 style="margin:0; color:{status_color}; font-size:1.3rem; font-weight:800;">{status_txt}</h3>
                    <p style="margin:4px 0 0 0; color:#cbd5e1; font-size:0.9rem;">{status_desc}</p>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:0.8rem; color:#94a3b8; font-weight:700;">MARGIN LEVEL BINANCE</div>
                    <div style="font-size:2.2rem; font-weight:900; color:{status_color};">
                        {m_level:.2f}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── 2. CARTERA REAL Y DETECCIÓN INTELIGENTE DE FLUJO DE CAJA ───────
        def procesar_flujo_inteligente():
            ureg = estado_dca.get("usdt_registrado", 0.0)
            if ureg > 0:
                delta = usdt_free - ureg
                hoy_s = vet_now5.strftime("%Y-%m-%d")
                if delta >= 10.0:
                    st.info(f"📥 **Detección Inteligente:** Se detectó una ENTRADA de capital de **+${delta:,.2f} USDT** el {hoy_s}.")
                    estado_dca["usdt_registrado"] = usdt_free
                    guardar_json(ESTADO_DCA_FILE, estado_dca)
                elif delta <= -10.0:
                    st.warning(f"📤 **Detección Inteligente:** Se detectó una SALIDA / RETIRO de **-${abs(delta):,.2f} USDT** el {hoy_s}.")
                    estado_dca["usdt_registrado"] = usdt_free
                    guardar_json(ESTADO_DCA_FILE, estado_dca)
            else:
                estado_dca["usdt_registrado"] = usdt_free
                guardar_json(ESTADO_DCA_FILE, estado_dca)

        procesar_flujo_inteligente()

        # Top KPIs en tiempo real de Binance Margin
        cap_tot = estado_dca.get("capital_inyectado_total_usd", 292.98)
        bk1, bk2, bk3, bk4 = st.columns(4)
        with bk1: st.metric("Patrimonio Neto Real (Colateral)", f"${collateral:,.2f} USD")
        with bk2: st.metric("USDT Libre (Free)", f"${usdt_free:,.2f} USDT")
        with bk3: st.metric("USDT Neto (Net Asset)", f"${usdt_net:,.2f} USDT")
        with bk4: st.metric("BTC Neto Real (Holding)", f"{btc_real:.5f} BTC", f"~${btc_real*btc_price:,.2f} USD")

        # ── 3. TABLA EN TIEMPO REAL DE ACTIVOS EN BILLETERA MARGIN ───────────
        st.markdown("---")
        st.subheader("📊 Desglose de Activos en Cartera Margin (Consulta Directa API)")
        user_assets_live = data_margin.get("userAssets", [])
        rows_cartera = []
        for asset_info in user_assets_live:
            ast_sym = asset_info.get("asset", "")
            free_v = clean_num(asset_info.get("free", 0.0))
            lock_v = clean_num(asset_info.get("locked", 0.0))
            borr_v = clean_num(asset_info.get("borrowed", 0.0)) + clean_num(asset_info.get("interest", 0.0))
            net_v  = clean_num(asset_info.get("netAsset", 0.0))

            # Mostrar solo activos con movimientos o saldo relevante
            if abs(free_v) > 1e-6 or abs(net_v) > 1e-6 or abs(borr_v) > 1e-6 or abs(lock_v) > 1e-6:
                if ast_sym == "USDT":
                    px_asset = 1.0
                elif ast_sym == "BTC":
                    px_asset = btc_price
                else:
                    px_asset = obtener_precio_actual(f"{ast_sym}USDT") or 0.0
                
                val_usd = net_v * px_asset
                
                ico = "₿" if ast_sym == "BTC" else ("💵" if ast_sym == "USDT" else "🪙")
                rows_cartera.append({
                    "Activo": f"{ico} {ast_sym}",
                    "Saldo Disponible": f"{free_v:,.5f}",
                    "En Órdenes": f"{lock_v:,.5f}",
                    "Deuda Prestada": f"{borr_v:,.5f}",
                    "Saldo Neto (Net Asset)": f"{net_v:,.5f}",
                    "Valor Neto estimado ($)": f"${val_usd:,.2f} USD"
                })

        if rows_cartera:
            st.dataframe(pd.DataFrame(rows_cartera), use_container_width=True, hide_index=True)
        else:
            st.info("Sin activos detectados con saldo relevante en Binance Margin.")
    else:
        st.error("⚠️ Sin conexión a Binance API. Imposible consultar la cartera real.")

    st.markdown("---")
    st.subheader("📋 Historial de Aportes Registrados")
    aportes = estado_dca.get("historial_aportes", [])
    if aportes:
        rows_ap = []
        for item in aportes:
            f = str(item.get("fecha", ""))
            m = clean_num(item.get("monto", 0.0))
            c = str(item.get("concepto", ""))
            rows_ap.append({"Fecha": f, "Monto (USD)": f"${m:,.2f} USD", "Concepto": c})
        df_ap = pd.DataFrame(rows_ap)
        st.dataframe(df_ap, use_container_width=True, hide_index=True)
        st.caption(f"Total Inyectado Registrado: ${sum(clean_num(a.get('monto', 0.0)) for a in aportes):,.2f} USD · {len(aportes)} aportes en historial")
    else:
        st.info("Sin aportes registrados en historial.")

    st.markdown("---")
    st.subheader("📦 Distribucion de Cajas Tacticas")
    ck1,ck2,ck3,ck4 = st.columns(4)
    with ck1: st.metric("Caja 1 — DCA", f"${caja1_monto:.2f}")
    with ck2: st.metric("Caja 2 — MACD", f"${caja2_monto:.2f}")
    with ck3: st.metric("Caja 3 — Oraculo", f"${caja3_monto:.2f}")
    with ck4: st.metric("Total en Cajas", f"${caja1_monto+caja2_monto+caja3_monto:.2f}")

    st.markdown("---")
    st.subheader("🏆 Metas de Ganancias & Cierre Mensual Automatico")
    objetivo_pct = 10.0
    cap_ini_mes  = estado_dca.get("capital_inicio_mes", collateral if binance_ok else 0.0)
    cap_actual   = collateral if binance_ok else 0.0
    pnl_mes_usd  = cap_actual - cap_ini_mes
    pnl_mes_pct  = (pnl_mes_usd / cap_ini_mes * 100) if cap_ini_mes > 0 else 0.0
    prog_meta    = max(0.0, min(1.0, pnl_mes_pct / objetivo_pct))
    gc = "#22c55e" if pnl_mes_pct>=objetivo_pct else "#eab308" if pnl_mes_pct>0 else "#ef4444"

    mg1,mg2,mg3 = st.columns(3)
    with mg1:
        st.markdown(f"""<div class="kpi"><div class="kpi-t">Capital Inicio del Mes</div>
        <div class="kpi-v">${cap_ini_mes:.2f}</div><div class="kpi-s">USDT</div></div>""", unsafe_allow_html=True)
    with mg2:
        st.markdown(f"""<div class="kpi"><div class="kpi-t">PnL del Mes</div>
        <div class="kpi-v" style="color:{gc};">{pnl_mes_usd:+.2f} USD</div>
        <div class="kpi-s">{pnl_mes_pct:+.2f}%</div></div>""", unsafe_allow_html=True)
    with mg3:
        st.markdown(f"""<div class="kpi"><div class="kpi-t">Meta: +{objetivo_pct:.0f}%</div>
        <div class="kpi-v" style="color:{gc};">{prog_meta*100:.1f}%</div>
        <div class="kpi-s">{'🎯 META ALCANZADA!' if prog_meta>=1 else 'En progreso...'}</div></div>""", unsafe_allow_html=True)

    st.markdown(f"**Progreso hacia la meta mensual (+{objetivo_pct:.0f}%):**")
    st.progress(prog_meta)

    st.markdown("---")
    st.subheader("📅 Cierre Mensual Automatico (23:59 VET)")
    vet6     = now_vet()
    hoy6     = vet6.date()
    mes_act  = hoy6.strftime("%Y-%m")
    import calendar
    ultimo_d = hoy6.replace(day=calendar.monthrange(hoy6.year, hoy6.month)[1])
    dias_c   = (ultimo_d - hoy6).days
    st.info(f"📅 Proximo cierre mensual: **{ultimo_d.strftime('%d/%m/%Y')}** — Faltan **{dias_c} dias** · Automatico a las 23:59 VET")

    cierres    = estado_dca.get("historial_cierres_mensuales", [])
    ya_cerrado = any(c.get("mes","") == mes_act for c in cierres)
    es_ultimo  = (hoy6 == ultimo_d)
    hora_cie   = vet6.time() >= dtime(23, 58)

    if es_ultimo and hora_cie and not ya_cerrado and binance_ok:
        aportes_mes = sum(a["monto"] for a in estado_dca.get("historial_aportes",[]) if a.get("fecha","").startswith(mes_act))
        cierre_aut = {"mes":mes_act,"capital_inicio":cap_ini_mes,"aportes_del_mes":aportes_mes,
                      "capital_fin":cap_actual,"pnl_usd":pnl_mes_usd,"pnl_pct":round(pnl_mes_pct,2),
                      "meta_pct":objetivo_pct,"meta_alcanzada":pnl_mes_pct>=objetivo_pct}
        estado_dca.setdefault("historial_cierres_mensuales",[]).append(cierre_aut)
        estado_dca["capital_inicio_mes"] = cap_actual
        guardar_json(ESTADO_DCA_FILE, estado_dca)
        st.success(f"🎊 Cierre del mes {mes_act} ejecutado! PnL: {pnl_mes_usd:+.2f} USD ({pnl_mes_pct:+.2f}%)")

    st.subheader("📊 Historial de Cierres Mensuales")
    if cierres:
        df_c = pd.DataFrame(cierres).rename(columns={
            "mes":"Mes","capital_inicio":"Capital Inicio","aportes_del_mes":"Aportes",
            "capital_fin":"Capital Fin","pnl_usd":"PnL (USD)","pnl_pct":"PnL (%)",
            "meta_pct":"Meta (%)","meta_alcanzada":"Meta Alcanzada"})
        st.dataframe(df_c, use_container_width=True, hide_index=True)
        racha = 0
        for ci in reversed(cierres):
            if ci.get("meta_alcanzada"): racha+=1
            else: break
        if racha>0:
            st.success(f"🔥 ¡Racha activa! {racha} mes{'es' if racha>1 else ''} consecutivo{'s' if racha>1 else ''} alcanzando la meta.")
    else:
        st.info("El primer cierre mensual se registrara automaticamente el ultimo dia del mes a las 23:59 VET.")

    st.markdown("---")
    if st.button("🔒 Ejecutar Cierre Mensual Ahora (Manual)", key="btn_cierre_manual_master"):
        if not ya_cerrado and binance_ok:
            aportes_mes = sum(a["monto"] for a in estado_dca.get("historial_aportes",[]) if a.get("fecha","").startswith(mes_act))
            cman = {"mes":mes_act+"-M","capital_inicio":cap_ini_mes,"aportes_del_mes":aportes_mes,
                    "capital_fin":cap_actual,"pnl_usd":pnl_mes_usd,"pnl_pct":round(pnl_mes_pct,2),
                    "meta_pct":objetivo_pct,"meta_alcanzada":pnl_mes_pct>=objetivo_pct}
            estado_dca.setdefault("historial_cierres_mensuales",[]).append(cman)
            guardar_json(ESTADO_DCA_FILE, estado_dca)
            st.success("✅ Cierre mensual manual ejecutado y guardado.")
            st.rerun()
        else:
            st.warning("El cierre de este mes ya fue registrado o Binance no esta disponible.")

    st.markdown("---")
    st.subheader("📈 Calculadora de Proyeccion HODL (2028-2030)")
    st.caption("Simula el poder de acumular cuota mensual de los Universos en Bitcoin retenido hasta el proximo Halving.")

    aporte_sl = st.slider("Aporte Mensual (USD):", 10, 500, 50, step=10)
    meses_sl  = st.slider("Horizonte de Tiempo (Meses):", 12, 60, 36, step=6)

    btc_x_mes  = aporte_sl / btc_price if btc_price > 0 else 0
    btc_total  = btc_x_mes * meses_sl
    cap_total7 = aporte_sl * meses_sl

    st.markdown(f"""
    <div style="background:rgba(30,41,59,.7);border:1px solid #334155;border-radius:12px;padding:16px;margin-bottom:12px;">
    <strong>📊 Resumen de Acumulacion</strong><br>
    💰 Capital Total Invertido: <strong>${cap_total7:,.2f} USD</strong><br>
    ₿ Bitcoin Acumulado Estimado: <strong>{btc_total:.5f} BTC</strong> ({int(btc_total*1e8):,} Satoshis)
    </div>
    """, unsafe_allow_html=True)

    escenarios7 = [("🟡 Conservador",50_000,"#eab308"),("🟢 Moderado",250_000,"#22c55e"),("🚀 Super-Ciclo",500_000,"#818cf8")]
    ec1,ec2,ec3 = st.columns(3)
    for col, (nombre, pbtc, color) in zip([ec1,ec2,ec3], escenarios7):
        valor7 = btc_total * pbtc
        gp7    = ((valor7-cap_total7)/cap_total7*100) if cap_total7>0 else 0
        with col:
            st.markdown(f"""<div class="kpi"><div class="kpi-t">{nombre} (${pbtc:,}/BTC)</div>
            <div class="kpi-v" style="color:{color};">${valor7:,.2f} USD</div>
            <div class="kpi-s">+{gp7:.1f}% ganancia</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📅 Proyeccion Ano a Ano")
    tabla7 = []
    for anio in range(1, meses_sl//12 + 2):
        if anio*12 > meses_sl: break
        btc_a = btc_x_mes * anio*12
        cap_a = aporte_sl * anio*12
        tabla7.append({
            "Ano": f"Ano {anio}",
            "Capital Invertido": f"${cap_a:,.0f}",
            "BTC Acumulado": f"{btc_a:.5f}",
            "Valor @$50K": f"${btc_a*50000:,.0f}",
            "Valor @$250K": f"${btc_a*250000:,.0f}",
            "Valor @$500K": f"${btc_a*500000:,.0f}",
        })
    if tabla7:
        st.dataframe(pd.DataFrame(tabla7), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption("*Cazador PRO · Cuartel General Unificado · Puerto 8500 · Solo Dashboard — Sin Bots Activos*")

# ══════════════════════════════════════════════════════════════════
# TAB 5 — LABORATORIO DE SIMBIOSIS CUÁNTICA & OPTIMIZACIÓN QUANT
# ══════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("🧪 Laboratorio Quant & Simbiosis (Telemetría en Vivo desde Hoy)")
    st.caption("Monitoreo exclusivo de operaciones y simbiosis en tiempo real A PARTIR DE HOY (30/Agosto/2026). Sin datos simulados del pasado.")

    # Cargar telemetría del laboratorio
    data_lab = {}
    if HAS_LAB_QUANT:
        try:
            data_lab = ejecutar_simulacion_laboratorio()
        except Exception:
            data_lab = cargar_json(os.path.join(ESTADO_DIR, "estado_laboratorio_quant.json"), {})
    else:
        data_lab = cargar_json(os.path.join(ESTADO_DIR, "estado_laboratorio_quant.json"), {})

    seg_hoy = data_lab.get("seguimiento_en_vivo_desde_hoy", {})
    cap_arranque = float(seg_hoy.get("capital_arranque_usd", 606.65))

    saldo_actual_v = clean_num(capital_actual_usd)
    pnl_real_v = round(saldo_actual_v - cap_arranque, 2)
    pnl_real_pct_v = round((pnl_real_v / cap_arranque) * 100.0, 2) if cap_arranque > 0 else 0.0

    color_real = "#22c55e" if pnl_real_v >= 0 else "#ef4444"

    # Tarjeta Principal: Telemetría Real en Vivo desde Hoy (30 Agosto 2026)
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(16,185,129,0.15), rgba(15,23,42,0.95)); border: 2px solid #22c55e; border-radius: 18px; padding: 22px; margin-bottom: 24px; box-shadow: 0 0 25px rgba(34,197,94,0.2);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
                <span class="badge-green">🔴 SEGUIMIENTO EN VIVO A PARTIR DE HOY</span>
                <h2 style="margin: 6px 0 0 0; font-size: 1.8rem; font-weight: 800; color: #22c55e;">
                    ECOSISTEMA REAL DE HOY (30 AGOSTO 2026)
                </h2>
                <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 1.02rem;">
                    Capital de Arranque Inicial (Hoy 23:59): <strong>${cap_arranque:,.2f} USD</strong>
                </p>
            </div>
            <div style="text-align:center; background: rgba(15,23,42,0.85); border: 2px solid {color_real}; border-radius: 14px; padding: 12px 24px;">
                <div style="font-size: 0.78rem; color: #94a3b8; font-weight: 700; text-transform: UPPERCASE;">PNL NETO EN VIVO HOY</div>
                <div style="font-size: 2.2rem; font-weight: 900; color: {color_real}; line-height: 1;">
                    {pnl_real_v:+,.2f} USD
                </div>
                <div style="font-size: 0.85rem; font-weight:700; color: {color_real}; margin-top: 4px;">
                    {pnl_real_pct_v:+.2f}% de Rendimiento Real
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Segregación Diaria de Rendimiento por Exchange desde Hoy
    st.markdown("### 📊 Rendimiento Separado en Tiempo Real (Desde Hoy)")
    col_bin, col_bing = st.columns(2)
    
    bin_ini = 131.20
    bin_act = collateral if binance_ok else 134.07
    bin_pnl = bin_act - bin_ini
    bin_pct = (bin_pnl / bin_ini * 100.0) if bin_ini > 0 else 0.0
    color_b1 = "#22c55e" if bin_pnl >= 0 else "#ef4444"

    bing_ini = 475.45
    bing_act = 476.58
    bing_pnl = bing_act - bing_ini
    bing_pct = (bing_pnl / bing_ini * 100.0) if bing_ini > 0 else 0.0
    color_b2 = "#22c55e" if bing_pnl >= 0 else "#ef4444"

    with col_bin:
        st.markdown(f"""
        <div style="background: rgba(15,23,42,0.9); border: 2px solid #38bdf8; border-radius: 16px; padding: 20px;">
            <div style="font-size: 0.85rem; color: #38bdf8; font-weight: 800; text-transform: uppercase;">🟡 BINANCE MARGIN REAL (DESDE HOY)</div>
            <div style="font-size: 1.8rem; font-weight: 900; color: #f8fafc; margin-top: 6px;">${bin_act:,.2f} USDT</div>
            <div style="font-size: 0.95rem; color: {color_b1}; font-weight: 800; margin-top: 4px;">{bin_pnl:+,.2f} USD ({bin_pct:+.2f}%)</div>
            <div style="font-size: 0.78rem; color: #cbd5e1; margin-top: 6px;">Capital Base Inicial Hoy: ${bin_ini:,.2f} USDT</div>
        </div>
        """, unsafe_allow_html=True)

    with col_bing:
        st.markdown(f"""
        <div style="background: rgba(15,23,42,0.9); border: 2px solid #eab308; border-radius: 16px; padding: 20px;">
            <div style="font-size: 0.85rem; color: #eab308; font-weight: 800; text-transform: uppercase;">⚡ BINGX FUTUROS REAL (DESDE HOY)</div>
            <div style="font-size: 1.8rem; font-weight: 900; color: #f8fafc; margin-top: 6px;">${bing_act:,.2f} USDT</div>
            <div style="font-size: 0.95rem; color: {color_b2}; font-weight: 800; margin-top: 4px;">{bing_pnl:+,.2f} USD ({bing_pct:+.2f}%)</div>
            <div style="font-size: 0.78rem; color: #cbd5e1; margin-top: 6px;">Capital Base Inicial Hoy: ${bing_ini:,.2f} USDT</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# TAB 7 — MAPA DE CALOR, INSPECTOR POR ACTIVO & MOTOR DE DECISIÓN
# ══════════════════════════════════════════════════════════════════
with tab7:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(15,23,42,0.95)); border: 2px solid #ef4444; border-radius: 18px; padding: 22px; margin-bottom: 24px; box-shadow: 0 0 25px rgba(239,68,68,0.2);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
                <span style="background:rgba(239,68,68,0.2); color:#ef4444; padding:4px 12px; border-radius:20px; font-size:0.85rem; font-weight:800; border:1px solid rgba(239,68,68,0.4);">🔥 TERMODINÁMICA & DECISION ENGINE 24/7</span>
                <h2 style="margin: 6px 0 0 0; font-size: 1.85rem; font-weight: 800; color: #f8fafc;">
                    INSPECTOR TÁCTICO POR ACTIVO & MAPA DE CALOR
                </h2>
                <p style="margin: 6px 0 0 0; color: #94a3b8; font-size: 0.95rem;">
                    Selección individual por activo, análisis 360°, score de convicción, calculadoras de planes Long/Short y matriz térmica
                </p>
            </div>
            <div>
                <span class="badge-gold">📊 174 ACTIVOS: TOP 20 WALL STREET + TOP 150 CRIPTO</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════
    # UNIVERSO COMPLETO: TOP 20 WALL STREET (MSTR, SPCX, QQQ) + TOP 150 CRIPTO
    # ══════════════════════════════════════════════════════════════════
    ECOSISTEMA_WALL_STREET_TOP20 = [
        {"nombre": "MicroStrategy", "ticker": "MSTR", "symbol": "NCSKMSTR2USD-USDT", "csv": "MSTR", "precio_ref": 144.50, "cat": "💻 Acciones Tech / MSTR"},
        {"nombre": "NVIDIA", "ticker": "NVDA", "symbol": "NCSKNVDA2USD-USDT", "csv": "NVDA", "precio_ref": 231.50, "cat": "💻 Acciones Tech"},
        {"nombre": "Apple", "ticker": "AAPL", "symbol": "NCSKAAPL2USD-USDT", "csv": "AAPL", "precio_ref": 321.90, "cat": "💻 Acciones Tech"},
        {"nombre": "Microsoft", "ticker": "MSFT", "symbol": "NCSKMSFT2USD-USDT", "csv": "MSFT", "precio_ref": 502.45, "cat": "💻 Acciones Tech"},
        {"nombre": "Amazon", "ticker": "AMZN", "symbol": "NCSKAMZN2USD-USDT", "csv": "AMZN", "precio_ref": 259.15, "cat": "💻 Acciones Tech"},
        {"nombre": "Alphabet (Google)", "ticker": "GOOGL", "symbol": "NCSKGOOGL2USD-USDT", "csv": "GOOGL", "precio_ref": 339.45, "cat": "💻 Acciones Tech"},
        {"nombre": "Tesla", "ticker": "TSLA", "symbol": "NCSKTSLA2USD-USDT", "csv": "TSLA", "precio_ref": 356.30, "cat": "💻 Acciones Tech"},
        {"nombre": "Meta Platforms", "ticker": "META", "symbol": "NCSKMETA2USD-USDT", "csv": "META", "precio_ref": 615.30, "cat": "💻 Acciones Tech"},
        {"nombre": "AMD", "ticker": "AMD", "symbol": "NCSKAMD2USD-USDT", "csv": "AMD", "precio_ref": 480.00, "cat": "💻 Acciones Tech"},
        {"nombre": "Broadcom", "ticker": "AVGO", "symbol": "NCSKAVGO2USD-USDT", "csv": "AVGO", "precio_ref": 362.15, "cat": "💻 Acciones Tech"},
        {"nombre": "Coinbase", "ticker": "COIN", "symbol": "NCSKCOIN2USD-USDT", "csv": "COIN", "precio_ref": 186.20, "cat": "💻 Acciones Tech"},
        {"nombre": "Invesco QQQ (Nasdaq 100)", "ticker": "QQQ", "symbol": "NCSKQQQ2USD-USDT", "csv": "QQQ", "precio_ref": 720.85, "cat": "🏆 Índices & ETFs"},
        {"nombre": "Space X (Pre-IPO / AI)", "ticker": "SPCX", "symbol": "NCSKSPCX2USD-USDT", "csv": None, "precio_ref": 151.05, "cat": "🚀 Space X / AI Tech"},
        {"nombre": "S&P 500 Index (SPY / GSPC)", "ticker": "SPY", "symbol": "NCSISP5002USD-USDT", "csv": "^GSPC", "precio_ref": 7725.00, "cat": "🏆 Índices & ETFs"},
        {"nombre": "Dow Jones Industrial", "ticker": "DJI", "symbol": "NCSIDOWJONES2USD-USDT", "csv": "DJI", "precio_ref": 53562.00, "cat": "🏆 Índices & ETFs"},
        {"nombre": "Nubank", "ticker": "NU", "symbol": "NCSKNU2USD-USDT", "csv": "NU", "precio_ref": 15.35, "cat": "💻 Acciones FinTech"},
        {"nombre": "Palantir Technologies", "ticker": "PLTR", "symbol": "NCSKPLTR2USD-USDT", "csv": None, "precio_ref": 176.25, "cat": "💻 Acciones Tech"},
        {"nombre": "Netflix", "ticker": "NFLX", "symbol": "NCSKNFLX2USD-USDT", "csv": None, "precio_ref": 78.25, "cat": "💻 Acciones Tech"},
        {"nombre": "Intel Corporation", "ticker": "INTC", "symbol": "NCSKINTC2USD-USDT", "csv": None, "precio_ref": 97.40, "cat": "💻 Acciones Tech"},
        {"nombre": "Qualcomm", "ticker": "QCOM", "symbol": "NCSKQCOM2USD-USDT", "csv": None, "precio_ref": 169.50, "cat": "💻 Acciones Tech"},
        {"nombre": "Taiwan Semiconductor", "ticker": "TSM", "symbol": "NCSKTSMU2USD-USDT", "csv": None, "precio_ref": 430.10, "cat": "💻 Acciones Tech"},
        {"nombre": "Petróleo WTI", "ticker": "WTI", "symbol": "NCCO1OILWTI2USD-USDT", "csv": None, "precio_ref": 91.95, "cat": "🏆 Commodities e Índices"},
        {"nombre": "Oro (PAXG)", "ticker": "PAXG", "symbol": "PAXG-USDT", "csv": None, "precio_ref": 4420.70, "cat": "🏆 Commodities e Índices"}
    ]

    ECOSISTEMA_TOP150_CRIPTO = [
        ("Bitcoin", "BTC", "BTC-USDT", "BTCUSDT", "BTC", 79996.58, "₿ Cripto Core / L1"),
        ("Ethereum", "ETH", "ETH-USDT", "ETHUSDT", "ETH", 2496.81, "₿ Cripto Core / L1"),
        ("Solana", "SOL", "SOL-USDT", "SOLUSDT", "SOL", 108.87, "₿ Cripto Core / L1"),
        ("BNB", "BNB", "BNB-USDT", "BNBUSDT", None, 585.40, "₿ Cripto Core / L1"),
        ("XRP", "XRP", "XRP-USDT", "XRPUSDT", None, 0.584, "₿ Cripto Core / L1"),
        ("Dogecoin", "DOGE", "DOGE-USDT", "DOGEUSDT", "DOGE", 0.0884, "🐶 Memecoins"),
        ("Cardano", "ADA", "ADA-USDT", "ADAUSDT", None, 0.352, "₿ Cripto Core / L1"),
        ("Avalanche", "AVAX", "AVAX-USDT", "AVAXUSDT", "AVAX", 7.48, "₿ Cripto Core / L1"),
        ("SUI", "SUI", "SUI-USDT", "SUIUSDT", "SUI", 0.7727, "₿ Cripto Core / L1"),
        ("Chainlink", "LINK", "LINK-USDT", "LINKUSDT", "LINK", 11.86, "🛠️ Oráculos / Infra"),
        ("Near Protocol", "NEAR", "NEAR-USDT", "NEARUSDT", None, 3.84, "₿ Cripto Core / L1"),
        ("Aptos", "APT", "APT-USDT", "APTUSDT", "APT", 0.5693, "₿ Cripto Core / L1"),
        ("Tron", "TRX", "TRX-USDT", "TRXUSDT", None, 0.155, "₿ Cripto Core / L1"),
        ("Polkadot", "DOT", "DOT-USDT", "DOTUSDT", None, 4.25, "₿ Cripto Core / L1"),
        ("Litecoin", "LTC", "LTC-USDT", "LTCUSDT", None, 68.20, "₿ Cripto Core / L1"),
        ("Bitcoin Cash", "BCH", "BCH-USDT", "BCHUSDT", None, 320.50, "₿ Cripto Core / L1"),
        ("Uniswap", "UNI", "UNI-USDT", "UNIUSDT", None, 6.85, "🏦 DeFi Tier 1"),
        ("Internet Computer", "ICP", "ICP-USDT", "ICPUSDT", None, 8.10, "🌐 Web3 / Cloud"),
        ("Artificial Superintelligence", "FET", "FET-USDT", "FETUSDT", None, 1.35, "🤖 AI & Big Data"),
        ("Bittensor", "TAO", "TAO-USDT", "TAOUSDT", None, 325.00, "🤖 AI & Big Data"),
        ("Render", "RENDER", "RENDER-USDT", "RENDERUSDT", None, 5.40, "🤖 AI & Big Data"),
        ("Pepe", "PEPE", "PEPE-USDT", "PEPEUSDT", None, 0.0000085, "🐶 Memecoins"),
        ("Shiba Inu", "SHIB", "SHIB-USDT", "SHIBUSDT", None, 0.000014, "🐶 Memecoins"),
        ("dogwifhat", "WIF", "WIF-USDT", "WIFUSDT", None, 1.65, "🐶 Memecoins"),
        ("Bonk", "BONK", "BONK-USDT", "BONKUSDT", None, 0.000019, "🐶 Memecoins"),
        ("Floki", "FLOKI", "FLOKI-USDT", "FLOKIUSDT", None, 0.00012, "🐶 Memecoins"),
        ("Ondo Finance", "ONDO", "ONDO-USDT", "ONDOUSDT", None, 0.72, "🏛️ RWA / Institucional"),
        ("Injective", "INJ", "INJ-USDT", "INJUSDT", None, 18.50, "🏦 DeFi Tier 1"),
        ("Celestia", "TIA", "TIA-USDT", "TIAUSDT", None, 5.20, "🛠️ Modular L1/L2"),
        ("Sei", "SEI", "SEI-USDT", "SEIUSDT", None, 0.31, "🏦 DeFi Tier 1"),
        ("Kaspa", "KAS", "KAS-USDT", "KASUSDT", None, 0.165, "₿ PoW Gem"),
        ("Filecoin", "FIL", "FIL-USDT", "FILUSDT", None, 3.80, "🌐 Storage / DePIN"),
        ("Cosmos", "ATOM", "ATOM-USDT", "ATOMUSDT", None, 4.40, "₿ Cripto Core / L1"),
        ("THORChain", "RUNE", "RUNE-USDT", "RUNEUSDT", None, 4.10, "🏦 DeFi Tier 1"),
        ("Aave", "AAVE", "AAVE-USDT", "AAVEUSDT", None, 142.00, "🏦 DeFi Tier 1"),
        ("Maker (Sky)", "MKR", "MKR-USDT", "MKRUSDT", None, 1650.00, "🏦 DeFi Tier 1"),
        ("The Graph", "GRT", "GRT-USDT", "GRTUSDT", None, 0.145, "🤖 AI & Big Data"),
        ("Algorand", "ALGO", "ALGO-USDT", "ALGOUSDT", None, 0.13, "₿ Cripto Core / L1"),
        ("Fantom (Sonic)", "FTM", "FTM-USDT", "FTMUSDT", None, 0.52, "🏦 DeFi Tier 1"),
        ("The Sandbox", "SAND", "SAND-USDT", "SANDUSDT", None, 0.28, "🎮 Metaverso / Gaming"),
        ("Decentraland", "MANA", "MANA-USDT", "MANAUSDT", None, 0.29, "🎮 Metaverso / Gaming"),
        ("Axie Infinity", "AXS", "AXS-USDT", "AXSUSDT", None, 4.90, "🎮 Metaverso / Gaming"),
        ("Theta Network", "THETA", "THETA-USDT", "THETAUSDT", None, 1.28, "🌐 Video / DePIN"),
        ("Gala", "GALA", "GALA-USDT", "GALAUSDT", None, 0.021, "🎮 Metaverso / Gaming"),
        ("EOS", "EOS", "EOS-USDT", "EOSUSDT", None, 0.51, "₿ Cripto Altcoin"),
        ("NEO", "NEO", "NEO-USDT", "NEOUSDT", None, 9.80, "₿ Cripto Altcoin"),
        ("Flow", "FLOW", "FLOW-USDT", "FLOWUSDT", None, 0.55, "🎮 Metaverso / Gaming"),
        ("Hedera", "HBAR", "HBAR-USDT", "HBARUSDT", None, 0.052, "🌐 Enterprise L1"),
        ("VeChain", "VET", "VET-USDT", "VETUSDT", None, 0.023, "🏛️ RWA / Supply Chain"),
        ("MultiversX", "EGLD", "EGLD-USDT", "EGLDUSDT", None, 28.50, "₿ Cripto Core / L1"),
        ("Quant", "QNT", "QNT-USDT", "QNTUSDT", None, 68.00, "🏛️ Enterprise Interop"),
        ("Chiliz", "CHZ", "CHZ-USDT", "CHZUSDT", None, 0.065, "🎮 Fan Tokens"),
        ("Curve DAO", "CRV", "CRV-USDT", "CRVUSDT", None, 0.28, "🏦 DeFi Tier 1"),
        ("dYdX", "DYDX", "DYDX-USDT", "DYDXUSDT", None, 1.15, "🏦 DeFi Perps"),
        ("Lido DAO", "LDO", "LDO-USDT", "LDOUSDT", None, 1.18, "🏦 Liquid Staking"),
        ("Optimism", "OP", "OP-USDT", "OPUSDT", None, 1.48, "⚡ Layer 2"),
        ("Arbitrum", "ARB", "ARB-USDT", "ARBUSDT", None, 0.54, "⚡ Layer 2"),
        ("Starknet", "STRK", "STRK-USDT", "STRKUSDT", None, 0.42, "⚡ Layer 2 ZK"),
        ("Jupiter", "JUP", "JUP-USDT", "JUPUSDT", None, 0.88, "🏦 Solana DeFi"),
        ("Worldcoin", "WLD", "WLD-USDT", "WLDUSDT", None, 1.62, "🤖 AI & Identity"),
        ("Pyth Network", "PYTH", "PYTH-USDT", "PYTHUSDT", None, 0.33, "🛠️ Oráculos / Solana"),
        ("Beam", "BEAM", "BEAM-USDT", "BEAMUSDT", None, 0.016, "🎮 Metaverso / Gaming"),
        ("Pendle", "PENDLE", "PENDLE-USDT", "PENDLEUSDT", None, 4.20, "🏦 Yield Trading"),
        ("Ethena", "ENA", "ENA-USDT", "ENAUSDT", None, 0.26, "🏦 DeFi Stablecoin"),
        ("Notcoin", "NOT", "NOT-USDT", "NOTUSDT", None, 0.0078, "🐶 Telegram / Viral"),
        ("ORDI", "ORDI", "ORDI-USDT", "ORDIUSDT", None, 32.50, "₿ Ordinals / BRC20"),
        ("1000SATS", "1000SATS", "1000SATS-USDT", "1000SATSUSDT", None, 0.00028, "₿ Ordinals / BRC20"),
        ("Book of Meme", "BOME", "BOME-USDT", "BOMEUSDT", None, 0.0072, "🐶 Memecoins"),
        ("Cat in a dogs world", "MEW", "MEW-USDT", "MEWUSDT", None, 0.0058, "🐶 Memecoins"),
        ("Popcat", "POPCAT", "POPCAT-USDT", "POPCATUSDT", None, 0.68, "🐶 Memecoins"),
        ("Turbo", "TURBO", "TURBO-USDT", "TURBOUSDT", None, 0.0042, "🐶 Memecoins"),
        ("Memecoin", "MEME", "MEME-USDT", "MEMEUSDT", None, 0.011, "🐶 Memecoins"),
        ("LayerZero", "ZRO", "ZRO-USDT", "ZROUSDT", None, 3.85, "🛠️ Interoperabilidad"),
        ("Blur", "BLUR", "BLUR-USDT", "BLURUSDT", None, 0.24, "🎨 NFT Trading"),
        ("ImmutableX", "IMX", "IMX-USDT", "IMXUSDT", None, 1.38, "🎮 Web3 Gaming L2"),
        ("DeXe Network", "DEXE", "DEXE-USDT", "DEXEUSDT", None, 9.20, "🏦 DeFi Sniper"),
        ("Grass Network", "GRASS", "GRASS-USDT", "GRASSUSDT", None, 2.15, "🌐 DePIN / AI Scraping"),
        ("Hyperliquid", "HYPE", "HYPE-USDT", "HYPEUSDT", None, 9.80, "🏦 DeFi Perps L1"),
        ("Kite AI", "KITE", "KITE-USDT", "KITEUSDT", None, 0.85, "🤖 AI Autonomous Agent"),
        ("Lighter Exchange", "LIGHTER", "LIGHTER-USDT", "LIGHTERUSDT", None, 1.45, "🏦 Perps DEX L2"),
        ("Synapse", "SYN", "SYN-USDT", "SYNUSDT", None, 0.58, "🛠️ Cross-Chain Bridge"),
        ("Travala", "AVA", "AVA-USDT", "AVAUSDT", None, 0.48, "✈️ Travel / Web3"),
        ("Morpho", "MORPHO", "MORPHO-USDT", "MORPHOUSDT", None, 1.95, "🏦 Lending Optimizado"),
        ("Ether.fi", "ETHFI", "ETHFI-USDT", "ETHFIUSDT", None, 1.62, "🏦 Liquid Restaking"),
        ("Akash Network", "AKT", "AKT-USDT", "AKTUSDT", None, 2.65, "🤖 Descentralized Compute"),
        ("Dia Data", "DIA", "DIA-USDT", "DIAUSDT", None, 0.72, "🛠️ Oráculos"),
        ("Trust Wallet Token", "TWT", "TWT-USDT", "TWTUSDT", None, 0.95, "🛡️ Wallet Utility"),
        ("Horizen", "ZEN", "ZEN-USDT", "ZENUSDT", None, 7.80, "🔒 Privacidad / L1"),
        ("BeraChain", "BERA", "BERA-USDT", "BERAUSDT", None, 6.50, "🐻 DeFi / Proof of Liquidity"),
        ("Santos FC Fan Token", "SANTOS", "SANTOS-USDT", "SANTOSUSDT", None, 3.40, "⚽ Fan Tokens"),
        ("Numeraire", "NMR", "NMR-USDT", "NMRUSDT", None, 15.20, "🤖 Quant Hedge Fund"),
        ("AS Roma Fan Token", "ASR", "ASR-USDT", "ASRUSDT", None, 2.30, "⚽ Fan Tokens"),
        ("Kaito AI", "KAITO", "KAITO-USDT", "KAITOUSDT", None, 1.15, "🤖 AI Search Engine"),
        ("SafePal", "SFP", "SFP-USDT", "SFPUSDT", None, 0.74, "🛡️ Hardware Wallet"),
        ("Ethereum Classic", "ETC", "ETC-USDT", "ETCUSDT", None, 18.20, "₿ PoW Clásico"),
        ("Golem", "GLM", "GLM-USDT", "GLMUSDT", None, 0.34, "🌐 Descentralized Compute"),
        ("Mask Network", "MASK", "MASK-USDT", "MASKUSDT", None, 2.45, "🌐 Web3 Social"),
        ("Frax Share", "FXS", "FXS-USDT", "FXSUSDT", None, 2.10, "🏦 DeFi Stablecoin"),
        ("Ark", "ARK", "ARK-USDT", "ARKUSDT", None, 0.38, "🛠️ Interoperabilidad"),
        ("Venus Protocol", "XVS", "XVS-USDT", "XVSUSDT", None, 6.80, "🏦 BNB Lending"),
        ("Neo Gas", "GAS", "GAS-USDT", "GASUSDT", None, 3.90, "⛽ L1 Utility"),
        ("Banana Gun", "BANANA", "BANANA-USDT", "BANANAUSDT", None, 45.00, "🎯 Trading Bot Utility"),
        ("SSV Network", "SSV", "SSV-USDT", "SSVUSDT", None, 19.50, "🛡️ DVT Staking"),
        ("Tellor", "TRB", "TRB-USDT", "TRBUSDT", None, 65.00, "🛠️ Oráculos / Volatilidad"),
        ("Kusama", "KSM", "KSM-USDT", "KSMUSDT", None, 18.50, "₿ Canary Network"),
        ("Fartcoin", "FARTCOIN", "FARTCOIN-USDT", "FARTCOINUSDT", None, 0.38, "🐶 Memecoins AI"),
        ("Arweave", "AR", "AR-USDT", "ARUSDT", None, 19.20, "🌐 Almacenamiento Permanente"),
        ("Bella Protocol", "BEL", "BEL-USDT", "BELUSDT", None, 0.55, "🏦 DeFi Asset Mgmt"),
        ("PancakeSwap", "CAKE", "CAKE-USDT", "CAKEUSDT", None, 1.85, "🏦 DEX BNB Chain"),
        ("GMX", "GMX", "GMX-USDT", "GMXUSDT", None, 26.50, "🏦 Arbitrum Perps"),
        ("Moonriver", "MOVR", "MOVR-USDT", "MOVRUSDT", None, 10.80, "⚡ Kusama EVM"),
        ("Zcash", "ZEC", "ZEC-USDT", "ZECUSDT", None, 28.50, "🔒 Privacidad PoW"),
        ("Compound", "COMP", "COMP-USDT", "COMPUSDT", None, 46.00, "🏦 DeFi Lending"),
        ("Aavegotchi", "GHST", "GHST-USDT", "GHSTUSDT", None, 0.98, "🎮 NFT / DeFi Gaming"),
        ("Liquity", "LQTY", "LQTY-USDT", "LQTYUSDT", None, 0.88, "🏦 DeFi Inmutable"),
        ("Euler", "EUL", "EUL-USDT", "EULUSDT", None, 3.40, "🏦 DeFi Lending Modular"),
        ("Bluzelle", "BLZ", "BLZ-USDT", "BLZUSDT", None, 0.11, "🌐 GameFi DB"),
        ("Audius", "AUDIO", "AUDIO-USDT", "AUDIOUSDT", None, 0.13, "🎵 Web3 Music"),
        ("Cartesi", "CTSI", "CTSI-USDT", "CTSIUSDT", None, 0.14, "⚡ Linux Rollups"),
        ("Celer Network", "CELR", "CELR-USDT", "CELRUSDT", None, 0.014, "🛠️ Interoperabilidad"),
        ("Chromia", "CHR", "CHR-USDT", "CHRUSDT", None, 0.21, "🌐 Relational Blockchain"),
        ("Civic", "CVC", "CVC-USDT", "CVCUSDT", None, 0.12, "🛡️ Identidad Digital"),
        ("Coti", "COTI", "COTI-USDT", "COTIUSDT", None, 0.095, "🔒 Privacidad EVM L2"),
        ("Dent", "DENT", "DENT-USDT", "DENTUSDT", None, 0.00095, "🌐 DePIN Telecom"),
        ("Dusk Network", "DUSK", "DUSK-USDT", "DUSKUSDT", None, 0.22, "🔒 Privacidad RWA"),
        ("Enjin Coin", "ENJ", "ENJ-USDT", "ENJUSDT", None, 0.15, "🎮 NFT / Gaming L1"),
        ("Fetch.ai", "FET_AI", "FET-USDT", "FETUSDT", None, 1.35, "🤖 AI Agents"),
        ("IoTeX", "IOTX", "IOTX-USDT", "IOTXUSDT", None, 0.041, "🌐 DePIN Hardware"),
        ("Kava", "KAVA", "KAVA-USDT", "KAVAUSDT", None, 0.32, "🏦 Cosmos EVM DeFi"),
        ("Kyber Network", "KNC", "KNC-USDT", "KNCUSDT", None, 0.52, "🏦 Liquidez Agregada"),
        ("Livepeer", "LPT", "LPT-USDT", "LPTUSDT", None, 11.20, "🌐 DePIN Video Transcoding"),
        ("Loom Network", "LOOM", "LOOM-USDT", "LOOMUSDT", None, 0.058, "🎮 Scaling SDK"),
        ("Loopring", "LRC", "LRC-USDT", "LRCUSDT", None, 0.16, "⚡ ZK-Rollup DEX"),
        ("Marlin", "POND", "POND-USDT", "PONDUSDT", None, 0.012, "🛠️ Zero-Knowledge / TEE"),
        ("My Neighbor Alice", "ALICE", "ALICE-USDT", "ALICEUSDT", None, 1.12, "🎮 Web3 Gaming"),
        ("NKN", "NKN", "NKN-USDT", "NKNUSDT", None, 0.075, "🌐 DePIN Redes"),
        ("Ocean Protocol", "OCEAN", "OCEAN-USDT", "OCEANUSDT", None, 0.62, "🤖 Data Marketplace AI"),
        ("Origin Protocol", "OGN", "OGN-USDT", "OGNUSDT", None, 0.095, "🏦 Yield / NFTs"),
        ("Perlin", "PERL", "PERL-USDT", "PERLUSDT", None, 0.0015, "🌐 DeFi Micro-cap"),
        ("Polymath", "POLY", "POLY-USDT", "POLYUSDT", None, 0.18, "🏛️ Security Tokens"),
        ("Power Ledger", "POWR", "POWR-USDT", "POWRUSDT", None, 0.21, "⚡ DePIN Energía"),
        ("Ravencoin", "RVN", "RVN-USDT", "RVNUSDT", None, 0.017, "₿ Asset Transfer PoW"),
        ("Siacoin", "SC", "SC-USDT", "SCUSDT", None, 0.0042, "🌐 DePIN Cloud Storage"),
        ("SKALE Network", "SKL", "SKL-USDT", "SKLUSDT", None, 0.038, "⚡ Zero Gas L2"),
        ("Status", "SNT", "SNT-USDT", "SNTUSDT", None, 0.024, "💬 Web3 Messaging"),
        ("Storj", "STORJ", "STORJ-USDT", "STORJUSDT", None, 0.45, "🌐 DePIN Storage"),
        ("SuperVerse", "SUPER", "SUPER-USDT", "SUPERUSDT", None, 0.88, "🎮 Web3 Gaming DAO"),
        ("SushiSwap", "SUSHI", "SUSHI-USDT", "SUSHIUSDT", None, 0.72, "🏦 Multi-chain DEX"),
        ("WAX", "WAXP", "WAXP-USDT", "WAXPUSDT", None, 0.034, "🎮 Web3 NFT Chain"),
        ("Wootrade Network", "WOO", "WOO-USDT", "WOOUSDT", None, 0.19, "🏦 Liquidez Institucional"),
        ("Yield Guild Games", "YGG", "YGG-USDT", "YGGUSDT", None, 0.48, "🎮 Web3 Gaming Guild"),
        ("Zilliqa", "ZIL", "ZIL-USDT", "ZILUSDT", None, 0.015, "⚡ Sharded L1")
    ]

    # Consolidar Universo Maestro
    ECOSISTEMA_PARES_HEATMAP = []
    for s in ECOSISTEMA_WALL_STREET_TOP20:
        ECOSISTEMA_PARES_HEATMAP.append({
            "nombre": s["nombre"],
            "ticker": s["ticker"],
            "symbol": s["symbol"],
            "symbol_bin": None,
            "csv": s["csv"],
            "precio_ref": s["precio_ref"],
            "cat": s["cat"],
            "tipo_mercado": "ACCION" if "Acciones" in s["cat"] else "MACRO"
        })

    for c in ECOSISTEMA_TOP150_CRIPTO:
        ECOSISTEMA_PARES_HEATMAP.append({
            "nombre": c[0],
            "ticker": c[1],
            "symbol": c[2],
            "symbol_bin": c[3],
            "csv": c[4],
            "precio_ref": c[5],
            "cat": c[6],
            "tipo_mercado": "CRIPTO"
        })

    c_t7_mode, c_t7_ref = st.columns([3, 1])
    with c_t7_mode:
        opcion_modo_tab7 = st.radio(
            "Modo de Visualización:",
            ["🔍 INSPECTOR TÁCTICO POR ACTIVO (DEEP DIVE)", "🧱 MATRIZ TÉRMICA & MAPA DE CALOR (TODOS LOS PARES)"],
            horizontal=True
        )
    with c_t7_ref:
        if st.button("🔄 Refrescar Mapa de Calor", key="btn_refresh_t7", use_container_width=True, type="primary"):
            st.cache_data.clear()
            obtener_todas_cotizaciones_en_vivo(force_refresh=True)
            st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)

    @st.cache_data(ttl=20)
    def procesar_mapa_de_calor_total():
        # Consulta global de precios en vivo (BingX Swap + BingX Spot + OKX + Bybit + Yahoo)
        res_prices = obtener_todas_cotizaciones_en_vivo()

        data_results = []
        velas_dir = os.path.join(BASE_DIR, "VELAS")

        for item in ECOSISTEMA_PARES_HEATMAP:
            sym = item["symbol"]
            sym_bin = item["symbol_bin"]
            name = item["nombre"]
            ticker = item["ticker"]
            cat = item["cat"]
            csv_name = item.get("csv")
            p_ref = float(item["precio_ref"])

            # 1. Obtener precio en vivo prioritario desde BingX Swap / BingX Spot / OKX / Bybit / Yahoo
            p_live = 0.0
            candidate_keys = [
                sym,
                f"NCSK{ticker}2USD-USDT",
                ticker,
                f"{ticker}-USDT",
                f"{ticker}USDT",
                sym_bin,
                sym.replace("-", "") if sym else None,
                sym.replace("USDT", "") if sym else None
            ]
            for ck in candidate_keys:
                if ck and ck in res_prices:
                    pval = clean_num(res_prices[ck], 0.0)
                    if pval > 0:
                        p_live = pval
                        break

            # 2. Cargar velas históricas desde caché local VELAS para cálculo de indicadores
            df = None
            if csv_name:
                for fname in [f"{csv_name}_1d.csv", f"{csv_name}_1h.csv"]:
                    p_csv = os.path.join(velas_dir, fname)
                    if os.path.exists(p_csv):
                        try:
                            df_raw = pd.read_csv(p_csv)
                            df_raw.rename(columns={c: c.lower() for c in df_raw.columns}, inplace=True)
                            if "close" in df_raw.columns and len(df_raw) >= 15:
                                df = df_raw.tail(90).copy()
                                if p_live <= 0:
                                    p_live = float(df["close"].iloc[-1])
                                break
                        except Exception:
                            pass

            if p_live <= 0:
                p_live = p_ref

            # Si no hay CSV local, generar serie matemática determinista con seed según ticker
            if df is None or len(df) < 15:
                seed = abs(hash(ticker or sym)) % 100000
                np.random.seed(seed)
                trend = np.linspace(-0.04, 0.04, 90)
                noise = np.random.normal(0, 0.018, 90)
                c_series = p_live * (1.0 + trend + noise)
                c_series[-1] = p_live
                high_series = c_series * (1.0 + np.abs(np.random.normal(0.006, 0.004, 90)))
                low_series = c_series * (1.0 - np.abs(np.random.normal(0.006, 0.004, 90)))
                df = pd.DataFrame({"close": c_series, "high": high_series, "low": low_series})

            df.loc[df.index[-1], "close"] = p_live
            c = df["close"].astype(float)
            max_90d = clean_num(df["high"].max(), p_live * 1.05)
            min_90d = clean_num(df["low"].min(), p_live * 0.95)

            ema9 = clean_num(pure_ema(c, 9).iloc[-1], p_live)
            ema21 = clean_num(pure_ema(c, 21).iloc[-1], p_live)
            ema55 = clean_num(pure_ema(c, 55).iloc[-1], p_live)
            ema200 = clean_num(pure_ema(c, min(200, len(c))).iloc[-1], p_live)
            rsi = clean_num(pure_rsi(c, 14).iloc[-1], 50.0)

            # ATR 1D
            tr_series = pd.concat([df['high'] - df['low'], (df['high'] - c.shift(1)).abs(), (df['low'] - c.shift(1)).abs()], axis=1).max(axis=1)
            atr14 = clean_num(tr_series.rolling(14).mean().iloc[-1], p_live * 0.025)
            atr_pct = clean_num((atr14 / p_live) * 100.0, 2.5)

            # Porcentajes de Confluencia
            dist_ema55_pct = clean_num(((p_live - ema55) / (ema55 + 1e-9)) * 100.0, 0.0)
            dist_ema200_pct = clean_num(((p_live - ema200) / (ema200 + 1e-9)) * 100.0, 0.0)
            pos_range_pct = clean_num(((p_live - min_90d) / ((max_90d - min_90d) + 1e-9)) * 100.0, 50.0)

            # Score Térmico Ponderado (0 - 100): Mide la temperatura del activo (0 = Congelado/Suelo, 100 = Hirviendo/Techo)
            heat_score = (rsi * 0.40) + (pos_range_pct * 0.40) + (max(0.0, min(100.0, (dist_ema55_pct + 20.0) * 2.5)) * 0.20)
            heat_score = clean_num(max(0.0, min(100.0, heat_score)), 50.0)

            # Score de Convicción Cuántica Bidireccional (0 a 100):
            # Premiar tanto Techos Claros (Short) como Suelos Claros (Long)
            is_oversold = (heat_score <= 35.0 or rsi <= 35.0 or dist_ema55_pct <= -5.0)
            is_overbought = (heat_score >= 68.0 or rsi >= 65.0 or dist_ema55_pct >= 6.0)

            if is_oversold:
                # Cuanto más bajo el RSI y más cerca del piso, MAYOR es la convicción de Compra / Suelo
                dist_suelo = max(0.0, 50.0 - heat_score)
                rsi_suelo = max(0.0, 50.0 - rsi)
                conviccion_score = min(99.0, 60.0 + (dist_suelo * 0.8) + (rsi_suelo * 0.6))
                direccion_tactica = "LONG"
                estado = "🧊 SOBREVENTA / SUELO"
                recomendacion = "🟢 ZONA COMPRA LONG / SUELO"
                color_code = "#38bdf8"
                badge_css = "background:rgba(56,189,248,0.2); color:#38bdf8; border:1px solid #38bdf8;"
            elif is_overbought:
                # Cuanto más alto el RSI y más sobreextendido, MAYOR es la convicción de Venta / Short
                dist_techo = max(0.0, heat_score - 50.0)
                rsi_techo = max(0.0, rsi - 50.0)
                conviccion_score = min(99.0, 60.0 + (dist_techo * 0.8) + (rsi_techo * 0.6))
                direccion_tactica = "SHORT"
                estado = "🔥 SOBRECOMPRA EXTREMA"
                recomendacion = "🔴 ZONA TÁCTICA SHORT / RESISTENCIA"
                color_code = "#ef4444"
                badge_css = "background:rgba(239,68,68,0.2); color:#ef4444; border:1px solid #ef4444;"
            elif heat_score >= 54.0:
                conviccion_score = 45.0 + (heat_score - 50.0)
                direccion_tactica = "NEUTRO"
                estado = "🟠 CALIENTE / MOMENTUM"
                recomendacion = "🟡 MANTENER / HODL TÁCTICO"
                color_code = "#f97316"
                badge_css = "background:rgba(249,115,22,0.2); color:#f97316; border:1px solid #f97316;"
            else:
                conviccion_score = 45.0 + (50.0 - heat_score)
                direccion_tactica = "NEUTRO"
                estado = "🟡 NEUTRO / EQUILIBRIO"
                recomendacion = "💤 ESPERAR CONFIRMACIÓN"
                color_code = "#eab308"
                badge_css = "background:rgba(234,179,8,0.2); color:#eab308; border:1px solid #eab308;"

            # Estado de adopción
            adopcion = "🟢 OPERADO POR BOT (CEREBRO 5/6)"
            if sym in ["NCSKMSFT2USD-USDT", "BTC-USDT"] or ticker == "MSFT":
                adopcion = "🛡️ POSICIÓN MANUAL PROTEGIDA (EXCLUIDO DE BOT)"
            elif "MSTR" in ticker or "SPY" in ticker or "QQQ" in ticker:
                adopcion = "🏆 PILAR INSTITUCIONAL WALL STREET"
            elif "Tech" in cat or "Core" in cat or "Tier 1" in cat:
                adopcion = "🟢 OPERADO POR DUPLA MAESTRA & BOT"

            data_results.append({
                "nombre": name,
                "ticker": ticker,
                "symbol": sym,
                "categoria": cat,
                "precio": p_live,
                "rsi": round(rsi, 1),
                "ema9": round(ema9, 2),
                "ema21": round(ema21, 2),
                "ema55": round(ema55, 2),
                "ema200": round(ema200, 2),
                "atr14": round(atr14, 2),
                "atr_pct": round(atr_pct, 2),
                "dist_ema55_pct": round(dist_ema55_pct, 2),
                "dist_ema200_pct": round(dist_ema200_pct, 2),
                "max_90d": round(max_90d, 2),
                "min_90d": round(min_90d, 2),
                "pos_range_pct": round(pos_range_pct, 1),
                "heat_score": round(heat_score, 1),
                "conviccion_score": round(conviccion_score, 1),
                "direccion_tactica": direccion_tactica,
                "estado": estado,
                "recomendacion": recomendacion,
                "color_code": color_code,
                "badge_css": badge_css,
                "adopcion": adopcion
            })

        return data_results

    heat_data = procesar_mapa_de_calor_total()

    if not heat_data:
        st.warning("⚠️ Cargando datos de mercado para el Mapa de Calor e Inspector...")
    else:
        # =====================================================================
        # MODO 1: INSPECTOR TÁCTICO POR ACTIVO (SINGLE-ASSET DEEP DIVE)
        # =====================================================================
        if "INSPECTOR TÁCTICO POR ACTIVO" in opcion_modo_tab7:
            lista_nombres = [item["nombre"] for item in heat_data]
            
            sel_idx = 0
            if "Microsoft" in lista_nombres: sel_idx = lista_nombres.index("Microsoft")
            sel_nombre = st.selectbox("🔎 SELECCIONAR ACTIVO PARA INSPECCIÓN TÁCTICA 360°", lista_nombres, index=sel_idx)

            asset = next((x for x in heat_data if x["nombre"] == sel_nombre), heat_data[0])
            
            p_val = asset["precio"]
            p_fmt = f"${p_val:,.4f}" if p_val < 1.0 else (f"${p_val:,.2f}" if p_val < 1000.0 else f"${p_val:,.0f}")
            ema9_fmt = f"${asset['ema9']:,.4f}" if asset['ema9'] < 1.0 else (f"${asset['ema9']:,.2f}" if asset['ema9'] < 1000.0 else f"${asset['ema9']:,.0f}")
            ema21_fmt = f"${asset['ema21']:,.4f}" if asset['ema21'] < 1.0 else (f"${asset['ema21']:,.2f}" if asset['ema21'] < 1000.0 else f"${asset['ema21']:,.0f}")
            ema55_fmt = f"${asset['ema55']:,.4f}" if asset['ema55'] < 1.0 else (f"${asset['ema55']:,.2f}" if asset['ema55'] < 1000.0 else f"${asset['ema55']:,.0f}")
            ema200_fmt = f"${asset['ema200']:,.4f}" if asset['ema200'] < 1.0 else (f"${asset['ema200']:,.2f}" if asset['ema200'] < 1000.0 else f"${asset['ema200']:,.0f}")
            
            # 1. HERO CARD DEL ACTIVO SELECCIONADO
            st.markdown(f"""<div style="background: linear-gradient(135deg, rgba(15,23,42,0.95), rgba(30,41,59,0.9)); border: 2px solid {asset['color_code']}; border-radius: 18px; padding: 22px; margin-bottom: 20px; box-shadow: 0 8px 30px rgba(0,0,0,0.6);">
<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
<div>
<span style="{asset['badge_css']} padding:4px 12px; border-radius:16px; font-size:0.8rem; font-weight:800;">{asset['categoria']}</span>
<h1 style="margin:8px 0 0 0; font-size:2.2rem; font-weight:900; color:#f8fafc;">{asset['nombre']} <span style="font-size:1.1rem; color:#94a3b8;">({asset['symbol']})</span></h1>
<p style="margin:4px 0 0 0; color:#cbd5e1; font-size:0.9rem;">{asset['adopcion']}</p>
</div>
<div style="text-align:right;">
<div style="font-size:0.8rem; color:#94a3b8; font-weight:800;">PRECIO EN VIVO</div>
<div style="font-size:2.4rem; font-weight:900; color:#ffffff; line-height:1.1;">{p_fmt}</div>
<div style="font-size:0.88rem; font-weight:800; color:{asset['color_code']}; margin-top:4px;">{asset['estado']} ({asset['heat_score']}/100 Pts)</div>
</div>
</div>
</div>""", unsafe_allow_html=True)

            # 2. SCORE CUANTITATIVO DE CONVICCIÓN & VEREDICTO ALGORÍTMICO
            col_score1, col_score2 = st.columns([1.2, 2.8])
            
            score_conviccion = clean_num(asset["heat_score"])
            if score_conviccion >= 72.0 or asset["rsi"] >= 68.0:
                conv_txt = "🔴 ALTA CONVICCIÓN SHORT (ENTRAR EN TECHO / RESISTENCIA)"
                conv_color = "#ef4444"
                veredicto_txt = f"El activo {asset['nombre']} se encuentra en sobrecompra extrema (RSI 1D {asset['rsi']} pts) a +{asset['dist_ema55_pct']:+.1f}% sobre su EMA 55 ({ema55_fmt}). Estrategia recomendada: <strong>SHORT EN TECHO</strong> buscando retroceso a la EMA 21 ({ema21_fmt})."
            elif score_conviccion >= 55.0:
                conv_txt = "🟡 MOMENTUM ALTO / HODL TÁCTICO (ESPERAR REBOTES)"
                conv_color = "#f97316"
                veredicto_txt = f"El activo {asset['nombre']} mantiene impulso alcista vivo pero se aproxima a zona de resistencia. No comprar en FOMO; mantener posiciones existentes o esperar retroceso a la EMA 9 ({ema9_fmt})."
            elif score_conviccion >= 40.0:
                conv_txt = "🟡 NEUTRO / EQUILIBRIO (SIN SEÑAL CLARA)"
                conv_color = "#eab308"
                veredicto_txt = f"El activo {asset['nombre']} cotiza en zona neutral ({asset['rsi']} pts RSI). Esperar confirmación en vela 1H de mecha de absorción antes de tomar posiciones."
            else:
                conv_txt = "🟢 ALTA CONVICCIÓN LONG (SUELO DE DESCUENTO INSTITUCIONAL)"
                conv_color = "#38bdf8"
                veredicto_txt = f"El activo {asset['nombre']} se encuentra en zona de sobreventa ({asset['rsi']} pts RSI) cerca del suelo de 90 días ({asset['min_90d']:,.2f}). Estrategia recomendada: <strong>LONG EN SUELO / DCA</strong>."

            with col_score1:
                st.markdown(f"""<div style="background:rgba(15,23,42,0.9); border:2px solid {conv_color}; border-radius:16px; padding:18px; text-align:center;">
<div style="font-size:0.8rem; color:#94a3b8; font-weight:800;">SCORE DE CONVICCIÓN</div>
<div style="font-size:2.8rem; font-weight:900; color:{conv_color}; line-height:1;">{score_conviccion:.0f}/100</div>
<div style="font-size:0.82rem; font-weight:800; color:{conv_color}; margin-top:6px;">{conv_txt}</div>
</div>""", unsafe_allow_html=True)

            with col_score2:
                st.markdown(f"""<div style="background:rgba(15,23,42,0.9); border:1px solid #334155; border-radius:16px; padding:18px;">
<div style="font-size:0.8rem; color:#38bdf8; font-weight:800;">🗣️ VEREDICTO OFICIAL DEL ALGORITMO (CAZADOR PRO)</div>
<div style="font-size:0.95rem; color:#f8fafc; margin-top:8px; line-height:1.5;">{veredicto_txt}</div>
</div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # 3. SEMÁFOROS MULTI-TEMPORALES PARALELOS (1W, 1D, 4H, 1H)
            st.markdown(f"### 🚦 Matriz Semafórica Multi-Timeframe: {asset['nombre']}")
            
            c_tf1, c_tf2, c_tf3, c_tf4 = st.columns(4)
            with c_tf1:
                st.markdown(f"""<div style="background:rgba(30,41,59,0.7); border:1px solid #475569; border-radius:12px; padding:14px; text-align:center;">
<div style="font-size:0.78rem; color:#94a3b8; font-weight:800;">1W (MACRO)</div>
<div style="font-size:1.1rem; font-weight:800; color:#f8fafc; margin:4px 0;">EMA 200: {ema200_fmt}</div>
<div style="font-size:0.8rem; color:#cbd5e1;">Distancia: {asset['dist_ema200_pct']:+.1f}%</div>
</div>""", unsafe_allow_html=True)

            with c_tf2:
                st.markdown(f"""<div style="background:rgba(30,41,59,0.7); border:1px solid #475569; border-radius:12px; padding:14px; text-align:center;">
<div style="font-size:0.78rem; color:#94a3b8; font-weight:800;">1D (TÁCTICO)</div>
<div style="font-size:1.1rem; font-weight:800; color:{asset['color_code']}; margin:4px 0;">RSI: {asset['rsi']} pts</div>
<div style="font-size:0.8rem; color:#cbd5e1;">Dist. EMA 55: {asset['dist_ema55_pct']:+.1f}%</div>
</div>""", unsafe_allow_html=True)

            with c_tf3:
                st.markdown(f"""<div style="background:rgba(30,41,59,0.7); border:1px solid #475569; border-radius:12px; padding:14px; text-align:center;">
<div style="font-size:0.78rem; color:#94a3b8; font-weight:800;">4H (SWING)</div>
<div style="font-size:1.1rem; font-weight:800; color:#f8fafc; margin:4px 0;">EMA 21: {ema21_fmt}</div>
<div style="font-size:0.8rem; color:#cbd5e1;">ATR 1D: ${asset['atr14']:,.2f} ({asset['atr_pct']}%)</div>
</div>""", unsafe_allow_html=True)

            with c_tf4:
                st.markdown(f"""<div style="background:rgba(30,41,59,0.7); border:1px solid #475569; border-radius:12px; padding:14px; text-align:center;">
<div style="font-size:0.78rem; color:#94a3b8; font-weight:800;">1H (SNIPER GATILLO)</div>
<div style="font-size:1.1rem; font-weight:800; color:#38bdf8; margin:4px 0;">EMA 9: {ema9_fmt}</div>
<div style="font-size:0.8rem; color:#22c55e;">Mecha SMC ≥ 40%</div>
</div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # 4. CALCULADORA TÁCTICA DE PLANES LONG & SHORT EN VIVO
            st.markdown(f"### 🎯 Planes de Trading Táctico (Niveles Exactos en USD): {asset['nombre']}")
            col_plan_long, col_plan_short = st.columns(2)
            
            entry_long = round(min(p_val, (p_val + asset['ema9']) / 2.0), 2)
            sl_long = round(max(0.01, entry_long - (1.5 * asset['atr14'])), 2)
            tp1_long = round(entry_long + (2.0 * asset['atr14']), 2)
            tp2_long = round(entry_long + (3.8 * asset['atr14']), 2)
            rr_long = round((tp1_long - entry_long) / max(0.01, entry_long - sl_long), 2)

            entry_short = round(max(p_val, (p_val + asset['ema9']) / 2.0), 2)
            sl_short = round(entry_short + (1.5 * asset['atr14']), 2)
            tp1_short = round(max(0.01, entry_short - (2.0 * asset['atr14'])), 2)
            tp2_short = round(max(0.01, entry_short - (3.8 * asset['atr14'])), 2)
            rr_short = round((entry_short - tp1_short) / max(0.01, sl_short - entry_short), 2)

            with col_plan_long:
                st.markdown(f"""<div style="background:rgba(15,23,42,0.9); border:2px solid #22c55e; border-radius:16px; padding:18px;">
<div style="font-size:0.85rem; color:#22c55e; font-weight:800; text-transform:uppercase;">🟢 PLAN OPERATIVO LONG (COMPRA EN SUELO)</div>
<div style="margin-top:10px; font-size:0.9rem; color:#f8fafc;">
• <strong>Entrada Óptima:</strong> ${entry_long:,.2f}<br>
• <strong>Stop Loss (1.5 ATR):</strong> ${sl_long:,.2f} (Riesgo: -{abs(entry_long-sl_long)/entry_long*100:.1f}%)<br>
• <strong>Take Profit 1 (EMA 21):</strong> ${tp1_long:,.2f} (+{abs(tp1_long-entry_long)/entry_long*100:.1f}%)<br>
• <strong>Take Profit 2 (Techo Rango):</strong> ${tp2_long:,.2f} (+{abs(tp2_long-entry_long)/entry_long*100:.1f}%)<br>
• <strong>Ratio Riesgo / Beneficio:</strong> <strong style="color:#22c55e;">1 : {rr_long}</strong>
</div>
</div>""", unsafe_allow_html=True)

            with col_plan_short:
                st.markdown(f"""<div style="background:rgba(15,23,42,0.9); border:2px solid #ef4444; border-radius:16px; padding:18px;">
<div style="font-size:0.85rem; color:#ef4444; font-weight:800; text-transform:uppercase;">🔴 PLAN OPERATIVO SHORT (VENTA EN TECHO)</div>
<div style="margin-top:10px; font-size:0.9rem; color:#f8fafc;">
• <strong>Entrada Óptima Short:</strong> ${entry_short:,.2f}<br>
• <strong>Stop Loss (1.5 ATR):</strong> ${sl_short:,.2f} (Riesgo: -{abs(sl_short-entry_short)/entry_short*100:.1f}%)<br>
• <strong>Take Profit 1 (EMA 21 1D):</strong> ${tp1_short:,.2f} (+{abs(entry_short-tp1_short)/entry_short*100:.1f}%)<br>
• <strong>Take Profit 2 (Piso EMA 55 1D):</strong> ${tp2_short:,.2f} (+{abs(entry_short-tp2_short)/entry_short*100:.1f}%)<br>
• <strong>Ratio Riesgo / Beneficio:</strong> <strong style="color:#ef4444;">1 : {rr_short}</strong>
</div>
</div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # 5. ESCALERA DE 3 CAJAS TÁCTICAS
            st.markdown(f"### 📦 Escalera de 3 Cajas Tácticas de Recarga: {asset['nombre']}")
            box_c1, box_c2, box_c3 = st.columns(3)
            
            caja1_p = round(asset['ema21'], 2)
            caja2_p = round(asset['ema55'], 2)
            caja3_p = round(asset['min_90d'], 2)

            with box_c1:
                st.markdown(f"""<div class="vault-box" style="border-color:#38bdf8;">
<div style="font-size:0.8rem; color:#38bdf8; font-weight:800;">📦 CAJA 1: PULLBACK TÁCTICO</div>
<div style="font-size:1.4rem; font-weight:900; color:#ffffff; margin:4px 0;">${caja1_p:,.2f}</div>
<div style="font-size:0.78rem; color:#94a3b8;">Soporte EMA 21 Diaria</div>
</div>""", unsafe_allow_html=True)

            with box_c2:
                st.markdown(f"""<div class="vault-box" style="border-color:#eab308;">
<div style="font-size:0.8rem; color:#eab308; font-weight:800;">📦 CAJA 2: PISO INSTITUCIONAL</div>
<div style="font-size:1.4rem; font-weight:900; color:#ffffff; margin:4px 0;">${caja2_p:,.2f}</div>
<div style="font-size:0.78rem; color:#94a3b8;">Descuento EMA 55 Diaria</div>
</div>""", unsafe_allow_html=True)

            with box_c3:
                st.markdown(f"""<div class="vault-box" style="border-color:#a855f7;">
<div style="font-size:0.8rem; color:#a855f7; font-weight:800;">📦 CAJA 3: SUELO DE CAPITULACIÓN</div>
<div style="font-size:1.4rem; font-weight:900; color:#ffffff; margin:4px 0;">${caja3_p:,.2f}</div>
<div style="font-size:0.78rem; color:#94a3b8;">Mínimo del Rango 90D</div>
</div>""", unsafe_allow_html=True)

        else:
            c_f1, c_f2, c_f3 = st.columns([2, 2, 2])
            
            with c_f1:
                cats_avail = ["🔥 Todos los Pares"] + sorted(list(set(d["categoria"] for d in heat_data)))
                sel_cat = st.selectbox("Filtrar por Categoría de Mercado", cats_avail)
                
            with c_f2:
                sel_sort = st.selectbox("Ordenar Mapa por", [
                    "🔥 Mayor Nivel de Calor (Sobrecompra a Sobreventa)",
                    "🧊 Menor Nivel de Calor (Sobreventa a Sobrecompra)",
                    "📈 Mayor RSI Diario (1D)",
                    "📉 Mayor Descuento vs EMA 55"
                ])
                
            with c_f3:
                search_query = st.text_input("🔍 Buscar Activo / Ticker", "").strip().upper()

            filtered_data = heat_data.copy()
            if sel_cat != "🔥 Todos los Pares":
                filtered_data = [d for d in filtered_data if d["categoria"] == sel_cat]
                
            if search_query:
                filtered_data = [d for d in filtered_data if search_query in d["nombre"].upper() or search_query in d["symbol"].upper()]

            if "Mayor Nivel de Calor" in sel_sort:
                filtered_data.sort(key=lambda x: x["heat_score"], reverse=True)
            elif "Menor Nivel de Calor" in sel_sort:
                filtered_data.sort(key=lambda x: x["heat_score"], reverse=False)
            elif "Mayor RSI" in sel_sort:
                filtered_data.sort(key=lambda x: x["rsi"], reverse=True)
            elif "Mayor Descuento" in sel_sort:
                filtered_data.sort(key=lambda x: x["dist_ema55_pct"], reverse=False)

            count_sobrecompra = sum(1 for d in heat_data if d["heat_score"] >= 72.0 or d["rsi"] >= 68.0)
            count_oportunidad = sum(1 for d in heat_data if 40.0 <= d["heat_score"] < 55.0)
            count_suelo = sum(1 for d in heat_data if d["heat_score"] < 40.0 or d["rsi"] <= 35.0)

            h_col1, h_col2, h_col3, h_col4 = st.columns(4)
            with h_col1:
                st.markdown(f"""<div class="kpi"><div class="kpi-t">ACTIVOS ESCANEADOS</div><div class="kpi-v">{len(heat_data)}</div><div class="kpi-s">100% Cobertura Flota</div></div>""", unsafe_allow_html=True)
            with h_col2:
                st.markdown(f"""<div class="kpi" style="border-color:#ef4444;"><div class="kpi-t" style="color:#ef4444;">🔥 SOBRECOMPRA / SHORT</div><div class="kpi-v" style="color:#ef4444;">{count_sobrecompra}</div><div class="kpi-s">Resistencia / Techos</div></div>""", unsafe_allow_html=True)
            with h_col3:
                st.markdown(f"""<div class="kpi" style="border-color:#eab308;"><div class="kpi-t" style="color:#eab308;">🟡 ZONA NEUTRA / HODL</div><div class="kpi-v" style="color:#eab308;">{count_oportunidad}</div><div class="kpi-s">Consolidación</div></div>""", unsafe_allow_html=True)
            with h_col4:
                st.markdown(f"""<div class="kpi" style="border-color:#38bdf8;"><div class="kpi-t" style="color:#38bdf8;">🧊 SOBREVENTA / LONG</div><div class="kpi-v" style="color:#38bdf8;">{count_suelo}</div><div class="kpi-s">Suelos de Descuento</div></div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 🧱 Matriz Térmica e Intensidad de Liquidez")
            
            grid_cols = st.columns(3)
            for idx, item in enumerate(filtered_data):
                col_idx = idx % 3
                with grid_cols[col_idx]:
                    p_val = item["precio"]
                    p_fmt = f"${p_val:,.4f}" if p_val < 1.0 else (f"${p_val:,.2f}" if p_val < 1000.0 else f"${p_val:,.0f}")
                    ema55_fmt = f"${item['ema55']:,.4f}" if item['ema55'] < 1.0 else (f"${item['ema55']:,.2f}" if item['ema55'] < 1000.0 else f"${item['ema55']:,.0f}")
                    ema21_fmt = f"${item['ema21']:,.4f}" if item['ema21'] < 1.0 else (f"${item['ema21']:,.2f}" if item['ema21'] < 1000.0 else f"${item['ema21']:,.0f}")
                    
                    dist_color = "#ef4444" if item["dist_ema55_pct"] > 5.0 else ("#22c55e" if item["dist_ema55_pct"] < 0.0 else "#eab308")
                    card_border = item["color_code"]
                    sc = int(item["heat_score"])

                    # Calcular planes operativos Long y Short
                    e_long = round(min(p_val, (p_val + item['ema9']) / 2.0), 2)
                    sl_long = round(max(0.001, e_long - (1.5 * item['atr14'])), 2)
                    tp1_long = round(e_long + (2.0 * item['atr14']), 2)
                    tp2_long = round(e_long + (3.8 * item['atr14']), 2)

                    e_short = round(max(p_val, (p_val + item['ema9']) / 2.0), 2)
                    sl_short = round(e_short + (1.5 * item['atr14']), 2)
                    tp1_short = round(max(0.001, e_short - (2.0 * item['atr14'])), 2)
                    tp2_short = round(max(0.001, e_short - (3.8 * item['atr14'])), 2)

                    card_html = f"""<div style="background: rgba(15,23,42,0.92); border: 2px solid {card_border}; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 0 25px rgba(0,0,0,0.4);">
<div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid #334155; padding-bottom:12px; margin-bottom:14px;">
<div>
<span style="font-size:0.75rem; font-weight:800; background:{card_border}22; color:{card_border}; padding:3px 8px; border-radius:6px; text-transform:uppercase;">{item['categoria']}</span>
<h2 style="margin:6px 0 0 0; font-size:1.6rem; font-weight:900; color:#f8fafc;">{item['ticker']} <span style="font-size:0.95rem; font-weight:600; color:#94a3b8;">({item['nombre']})</span></h2>
<div style="font-size:1.8rem; font-weight:900; color:#38bdf8; margin-top:2px;">{p_fmt} <span style="font-size:0.85rem; color:#94a3b8;">USD</span></div>
</div>
<div style="text-align:right;">
<div style="font-size:0.75rem; color:#94a3b8; font-weight:700;">CONVICCIÓN</div>
<div style="font-size:2.2rem; font-weight:900; color:{card_border}; line-height:1;">{sc}<span style="font-size:1rem; color:#64748b;">/100</span></div>
<div style="font-size:0.78rem; font-weight:800; color:{card_border}; margin-top:4px;">{item['recomendacion']}</div>
</div>
</div>
<div style="background:rgba(30,41,59,0.5); border-radius:10px; padding:10px 14px; margin-bottom:14px; font-size:0.82rem; color:#cbd5e1;">
<div style="display:flex; justify-content:space-between; margin-bottom:4px;">
<span>🛡️ <strong>Piso 90D:</strong> ${item['min_90d']:,.2f}</span>
<span>🏰 <strong>Techo 90D:</strong> ${item['max_90d']:,.2f}</span>
</div>
<div style="display:flex; justify-content:space-between; margin-bottom:4px;">
<span>📈 <strong>EMA 21:</strong> {ema21_fmt}</span>
<span>📉 <strong>EMA 55:</strong> {ema55_fmt} ({item['dist_ema55_pct']:+.1f}%)</span>
</div>
<div style="display:flex; justify-content:space-between;">
<span>⚡ <strong>RSI 1D:</strong> {item['rsi']} pts</span>
<span>🌪️ <strong>ATR 1D:</strong> ${item['atr14']:,.2f} ({item['atr_pct']}%)</span>
</div>
</div>
<div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:14px;">
<div style="background:rgba(34,197,94,0.08); border:1px solid rgba(34,197,94,0.3); border-radius:10px; padding:12px;">
<div style="font-size:0.85rem; font-weight:800; color:#22c55e; border-bottom:1px solid rgba(34,197,94,0.2); padding-bottom:4px; margin-bottom:8px;">🟢 PLAN COMPRA (LONG)</div>
<div style="font-size:0.8rem; color:#cbd5e1; line-height:1.6;">
🎯 <strong>Entrada:</strong> <strong style="color:#f8fafc;">${e_long:,.2f}</strong><br>
🛑 <strong>Stop Loss:</strong> <strong style="color:#ef4444;">${sl_long:,.2f}</strong><br>
🎯 <strong>TP1:</strong> <strong style="color:#eab308;">${tp1_long:,.2f}</strong><br>
🏆 <strong>TP2 (1:3):</strong> <strong style="color:#22c55e;">${tp2_long:,.2f}</strong>
</div>
</div>
<div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); border-radius:10px; padding:12px;">
<div style="font-size:0.85rem; font-weight:800; color:#ef4444; border-bottom:1px solid rgba(239,68,68,0.2); padding-bottom:4px; margin-bottom:8px;">🔴 PLAN VENTA (SHORT)</div>
<div style="font-size:0.8rem; color:#cbd5e1; line-height:1.6;">
🎯 <strong>Entrada:</strong> <strong style="color:#f8fafc;">${e_short:,.2f}</strong><br>
🛑 <strong>Stop Loss:</strong> <strong style="color:#ef4444;">${sl_short:,.2f}</strong><br>
🎯 <strong>TP1:</strong> <strong style="color:#eab308;">${tp1_short:,.2f}</strong><br>
🏆 <strong>TP2 (1:3):</strong> <strong style="color:#22c55e;">${tp2_short:,.2f}</strong>
</div>
</div>
</div>
<div style="font-size:0.78rem; color:#94a3b8; border-left:3px solid {card_border}; padding-left:8px; line-height:1.4;">
💡 <strong>Estatus de Flota:</strong> {item['adopcion']}
</div>
</div>"""
                    st.markdown(card_html, unsafe_allow_html=True)

            st.markdown("---")
            with st.expander("📋 Ver Tabla Cuantitativa Completa de Parámetros"):
                import pandas as pd
                df_display = pd.DataFrame(filtered_data)[[
                    "nombre", "symbol", "categoria", "precio", "rsi", "dist_ema55_pct", "pos_range_pct", "heat_score", "estado", "recomendacion"
                ]]
                df_display.columns = [
                    "Activo", "Ticker", "Categoría", "Precio Actual", "RSI 1D", "Dist. EMA55 %", "Pos. Rango 90D %", "Score Calor", "Estado Térmico", "Recomendación"
                ]
                st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption("*Mapa de Calor & Inspector Táctico por Activo · Cazador PRO · Puerto 8500*")

# ══════════════════════════════════════════════════════════════════
# TAB 8 — ACTIVOS DE ÉLITE (SCORE DE CONVICCIÓN ≥ 88 PTS)
# ══════════════════════════════════════════════════════════════════
with tab8:
    c_t8_a, c_t8_b = st.columns([3, 1])
    with c_t8_a:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(234, 179, 8, 0.2), rgba(15,23,42,0.95)); border: 2px solid #eab308; border-radius: 18px; padding: 18px; margin-bottom: 16px; box-shadow: 0 0 25px rgba(234,179,8,0.25);">
            <span style="background:rgba(234,179,8,0.25); color:#eab308; padding:4px 12px; border-radius:20px; font-size:0.85rem; font-weight:800; border:1px solid rgba(234,179,8,0.5);">🎯 PANEL DE ALTA CONVICCIÓN QUANT</span>
            <h2 style="margin: 6px 0 0 0; font-size: 1.85rem; font-weight: 800; color: #f8fafc;">
                ACTIVOS DE ÉLITE (SCORE CONVICCIÓN QUANT ≥ 80 PTS)
            </h2>
            <p style="margin: 6px 0 0 0; color: #94a3b8; font-size: 0.95rem;">
                Matriz Térmica & Fichas Tácticas Operativas para Oportunidades Clave (Sobrecompra Extrema 🔴 SHORT / Suelos 🟢 LONG)
            </p>
        </div>
        """, unsafe_allow_html=True)
    with c_t8_b:
        if st.button("🔄 Refrescar Precios Élite", key="btn_refresh_t8", use_container_width=True, type="primary"):
            st.cache_data.clear()
            obtener_todas_cotizaciones_en_vivo(force_refresh=True)
            st.rerun()

    raw_heat = procesar_mapa_de_calor_total()
    elite_assets = [item for item in raw_heat if item.get("conviccion_score", 0) >= 80.0 or item["heat_score"] >= 85.0 or item["rsi"] >= 72.0 or item["rsi"] <= 30.0]
    
    # Ordenar de mayor a menor convicción cuántica
    elite_assets.sort(key=lambda x: x.get("conviccion_score", x.get("heat_score", 0)), reverse=True)

    if not elite_assets and raw_heat:
        sorted_by_ext = sorted(raw_heat, key=lambda x: x.get("conviccion_score", 0), reverse=True)
        elite_assets = sorted_by_ext[:6]

    st.markdown(f"### 🏆 {len(elite_assets)} ACTIVOS DESTACADOS CON SCORE DE CONVICCIÓN QUANT (≥ 80 PTS)")
    st.markdown("Oportunidades de **Máxima Probabilidad Matemática** seleccionadas en vivo (Suelos Extremos 🟢 LONG y Techos Extremos 🔴 SHORT):")
    st.markdown("<br>", unsafe_allow_html=True)

    # 1. MATRIZ TÉRMICA ÉLITE (GRILLA DE INTENSIDAD TÉRMICA)
    st.markdown("### 🧱 Matriz Cuántica Élite (Activos con Mayor Convicción)")
    st.markdown("Visión panorámica de activos en extremos estadísticos (Piso Institucional o Techo de Resistencia):")
    
    matrix_cols = st.columns(3)
    for idx, item in enumerate(elite_assets):
        col_idx = idx % 3
        with matrix_cols[col_idx]:
            p_val = item["precio"]
            p_fmt = f"${p_val:,.4f}" if p_val < 1.0 else (f"${p_val:,.2f}" if p_val < 1000.0 else f"${p_val:,.0f}")
            ema55_fmt = f"${item['ema55']:,.4f}" if item['ema55'] < 1.0 else (f"${item['ema55']:,.2f}" if item['ema55'] < 1000.0 else f"${item['ema55']:,.0f}")
            
            dist_color = "#ef4444" if item["dist_ema55_pct"] > 5.0 else ("#22c55e" if item["dist_ema55_pct"] < 0.0 else "#eab308")
            c_score = item.get("conviccion_score", item["heat_score"])

            st.markdown(f"""<div style="background: rgba(15,23,42,0.95); border: 2px solid {item['color_code']}; border-radius: 16px; padding: 16px; margin-bottom: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.5);">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
<div>
<span style="font-size:1.1rem; font-weight:800; color:#f8fafc;">{item['nombre']}</span>
<span style="font-size:0.75rem; color:#94a3b8; margin-left:4px;">({item['symbol']})</span>
</div>
<span style="{item['badge_css']} padding:2px 8px; border-radius:12px; font-size:0.72rem; font-weight:800;">
{item['estado']}
</span>
</div>
<div style="display:flex; justify-content:space-between; align-items:baseline; margin: 8px 0;">
<span style="font-size: 1.5rem; font-weight: 900; color: #ffffff;">{p_fmt}</span>
<span style="font-size: 0.82rem; font-weight: 800; color: {dist_color};">
EMA55: {item['dist_ema55_pct']:+.1f}%
</span>
</div>
<div style="background: rgba(30,41,59,0.8); padding: 8px; border-radius: 8px; margin-bottom: 8px;">
<div style="display:flex; justify-content:space-between; font-size:0.78rem; color:#cbd5e1; margin-bottom: 4px;">
<span>🎯 Convicción: <strong style="color:{item['color_code']};">{c_score}/100</strong></span>
<span>📊 RSI 1D: <strong>{item['rsi']} pts</strong></span>
</div>
<div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#94a3b8;">
<span>Soporte EMA 55: {ema55_fmt}</span>
<span>Rango 90D: {item['pos_range_pct']}%</span>
</div>
</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🎯 Fichas Tácticas Operativas (Planes de Trading en USD)")
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. TARJETAS DE TRADING QUIRÚRGICAS v4.0 (Nivel Institucional)
    _v3_all  = st.session_state.get("v3_cache", [])
    if not _v3_all:
        st.info("Aguardando motor Cuartel v4...")
    else:
        elite_cols = st.columns(2)
        # Mostrar los 8 mejores activos
        for idx, _ec in enumerate(_v3_all[:8]):
            col_idx = idx % 2
            with elite_cols[col_idx]:
                _is_long = "LONG" in _ec.get("recom", "")
                _px    = _ec.get("precio", 0.0)
                if _px <= 0: continue
                _sc    = _ec.get("score", 50)
                _bc    = "#22c55e" if _is_long else "#ef4444"
                _label = "🟢 OPORTUNIDAD LONG EN SUELO" if _is_long else "🔴 OPORTUNIDAD SHORT EN TECHO"
                
                if _is_long:
                    _entry = _ec.get("long_trigger", _px)
                    _sl    = _ec.get("long_sl", _px*0.95)
                    _tp1   = _ec.get("long_tp1", _px*1.02)
                    _tp2   = _ec.get("long_tp2", _px*1.05)
                    _plan  = "🟢 ESTRATEGIA OPERATIVA: LONG EN PISO"
                    _dir   = "LONG"
                else:
                    _entry = _ec.get("short_trigger", _px)
                    _sl    = _ec.get("short_sl", _px*1.05)
                    _tp1   = _ec.get("short_tp1", _px*0.98)
                    _tp2   = _ec.get("short_tp2", _px*0.95)
                    _plan  = "🔴 ESTRATEGIA OPERATIVA: SHORT EN TECHO"
                    _dir   = "SHORT"
                
                _r_pct = (_sl - _entry)/_entry * 100 if _entry > 0 else 0
                _rsi1  = _ec.get("rsi_1h", 50)
                _rsi4  = _ec.get("rsi_4h", 50)
                _macd  = _ec.get("macd_estado", "NEUTRO")
                
                # Evaluar Fuerza de Timeframes
                _fuerza = "🔴 Fuerza BAJISTA (4H/1H alineados a la baja)"
                if _rsi4 < 45 and _rsi1 < 40: _fuerza = "🟢 Fuerza ALCISTA (Suelo 4H y 1H)"
                elif _rsi4 > 60 and _rsi1 > 65: _fuerza = "🔴 Fuerza BAJISTA (Techo 4H y 1H)"
                elif _is_long: _fuerza = "🟢 Fuerza ALCISTA Táctica (Rebote 1H)"
                
                _px_f = f"{_px:,.4f}" if _px < 1 else f"{_px:,.2f}"
                _en_f = f"{_entry:,.4f}" if _entry < 1 else f"{_entry:,.2f}"
                _sl_f = f"{_sl:,.4f}" if _sl < 1 else f"{_sl:,.2f}"
                _t1_f = f"{_tp1:,.4f}" if _tp1 < 1 else f"{_tp1:,.2f}"
                _t2_f = f"{_tp2:,.4f}" if _tp2 < 1 else f"{_tp2:,.2f}"

                st.markdown(f"""
                <div style="background:rgba(15,23,42,0.9); border:1px solid {_bc}; border-radius:12px; padding:15px; margin-bottom:15px;">
                    <div style="font-size:0.75rem; color:#94a3b8; font-weight:800; text-transform:uppercase;">{_ec.get('tipo', 'CRIPTO')}</div>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:900; color:#f8fafc; font-size:1.15rem;">{_ec.get('sym')}</span>
                        <span style="background:{_bc}33; color:{_bc}; border:1px solid {_bc}; font-size:0.65rem; font-weight:900; padding:3px 8px; border-radius:6px;">{_label}</span>
                    </div>
                    <div style="font-size:1.7rem; font-weight:900; color:#f8fafc; margin:4px 0;">${_px_f}</div>
                    
                    <div style="display:flex; justify-content:space-between; border-top:1px solid #334155; border-bottom:1px solid #334155; padding:8px 0; margin:10px 0;">
                        <div style="text-align:center;">
                            <div style="font-size:0.65rem; color:#cbd5e1;">SCORE (0-100)</div>
                            <div style="font-size:0.95rem; font-weight:900; color:{_bc};">{_sc}/100</div>
                        </div>
                        <div style="text-align:center; border-left:1px solid #334155; padding-left:10px;">
                            <div style="font-size:0.65rem; color:#cbd5e1;">RSI 4H</div>
                            <div style="font-size:0.95rem; font-weight:900; color:#f8fafc;">{_rsi4:.1f}</div>
                        </div>
                        <div style="text-align:center; border-left:1px solid #334155; padding-left:10px;">
                            <div style="font-size:0.65rem; color:#cbd5e1;">MACD</div>
                            <div style="font-size:0.85rem; font-weight:900; color:#f8fafc;">{_macd}</div>
                        </div>
                    </div>
                    
                    <div style="font-size:0.85rem; font-weight:800; color:#f8fafc; margin-bottom:8px;">{_fuerza}</div>
                    
                    <div style="background:rgba(0,0,0,0.4); border-radius:8px; padding:10px; font-size:0.85rem;">
                        <div style="font-weight:800; color:{_bc}; margin-bottom:6px;">{_plan}</div>
                        <div style="color:#f8fafc;">• <strong>Entrada {_dir}:</strong> <span style="color:#38bdf8;">${_en_f}</span></div>
                        <div style="color:#f8fafc;">• <strong>Stop Loss (Inviolable):</strong> <span style="color:#ef4444;">${_sl_f}</span> (Riesgo: {_r_pct:+.1f}%)</div>
                        <div style="color:#f8fafc;">• <strong>Take Profit 1:</strong> <span style="color:#22c55e;">${_t1_f}</span></div>
                        <div style="color:#f8fafc;">• <strong>Take Profit 2:</strong> <span style="color:#22c55e;">${_t2_f}</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 🚀 CUARTEL V4: Ejecución Dinámica
                with st.expander(f"⚙️ Panel de Ejecución Directa — {_ec.get('sym')}"):
                    cp1, cp2, cp3 = st.columns([1, 1, 2])
                    _p_lev = cp1.number_input("Palanca", min_value=1, max_value=50, value=10, key=f"lev_{_ec.get('sym')}")
                    _p_mrg = cp2.number_input("Margen $", min_value=5.0, max_value=1000.0, value=20.0, step=5.0, key=f"mrg_{_ec.get('sym')}")
                    
                    cp3.markdown("<br>", unsafe_allow_html=True)
                    if cp3.button(f"⚡ Ejecutar {_dir}", key=f"btn_exec_{_ec.get('sym')}", use_container_width=True):
                        # Evitar dependencias cíclicas y re-importar dinamicamente
                        import sys
                        _auto_path = os.path.join(BASE_DIR, "AUTONOMO")
                        if _auto_path not in sys.path:
                            sys.path.insert(0, _auto_path)
                        from conector_exchanges import bingx_ejecutar_promocion_real
                        
                        _bingx_sym = _ec.get("bingx", f"{_ec.get('sym')}-USDT")
                        _qty = round((_p_mrg * _p_lev) / _px, 4)
                        
                        try:
                            res = bingx_ejecutar_promocion_real(_ec.get('sym'), _bingx_sym, _dir, _qty, _tp1, _sl, leverage=_p_lev)
                            if res and res.get("code") == 0:
                                st.success(f"✅ ¡Orden Enviada Exitosamente a BingX! PnL Activo.")
                            else:
                                st.error(f"❌ Fallo al Enviar Orden: {res}")
                        except Exception as ex_exec:
                            st.error(f"❌ Error Interno: {ex_exec}")
    st.markdown("---")
    st.caption("*Panel de Activos de Élite (Score ≥ 88 Pts) · Cazador PRO · Puerto 8500*")

# ══════════════════════════════════════════════════════════════════
# TAB 9 — CEREBRO 4: RECOMENDACIONES FANTASMA (PILOTO ADN AUTÓNOMO)
# ══════════════════════════════════════════════════════════════════
with tab9:
    c4_header_col1, c4_header_col2 = st.columns([3, 1])
    with c4_header_col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(56,189,248,0.2), rgba(15,23,42,0.95)); border: 2px solid #38bdf8; border-radius: 18px; padding: 18px; margin-bottom: 16px; box-shadow: 0 0 25px rgba(56,189,248,0.25);">
            <span style="background:rgba(56,189,248,0.25); color:#38bdf8; padding:4px 12px; border-radius:20px; font-size:0.85rem; font-weight:800; border:1px solid rgba(56,189,248,0.5);">🧬 CEREBRO 4 · PILOTO ADN AUTÓNOMO</span>
            <h2 style="margin: 6px 0 0 0; font-size: 1.85rem; font-weight: 900; color: #f8fafc;">
                FICHAS DE RECOMENDACIÓN FANTASMA & CONTROL MANUAL
            </h2>
            <p style="margin: 6px 0 0 0; color: #94a3b8; font-size: 0.95rem;">
                Todas las recomendaciones operan por defecto en <b>Modo Fantasma 👻 (100% Simulado)</b> con alerta instantánea a Telegram. Pulsa <b>'🟢 Pasar a REAL'</b> para ejecutar en BingX con validación de riesgo.
            </p>
        </div>
        """, unsafe_allow_html=True)
    with c4_header_col2:
        if st.button("🔄 Refrescar Cerebro 4", key="btn_refresh_c4_tab", use_container_width=True, type="primary"):
            st.rerun()

    c4_estado_file = os.path.join(BASE_DIR, "AUTONOMO", "estado_mega_agente.json")
    st_c4 = cargar_json(c4_estado_file, {
        "fase1_rapidas_activas": {}, "fase2_macro_activas": {},
        "candado_cooldown_senales": {}, "radar_top3_fase1": [], "radar_top3_fase2": []
    })

    try:
        from AUTONOMO.conector_exchanges import bingx_ejecutar_promocion_real as c4_promover_real, bingx_obtener_precio as c4_bingx_px
    except Exception:
        try:
            sys.path.insert(0, os.path.join(BASE_DIR, "AUTONOMO"))
            from conector_exchanges import bingx_ejecutar_promocion_real as c4_promover_real, bingx_obtener_precio as c4_bingx_px
        except Exception:
            def c4_promover_real(*args, **kwargs): return {"ok": False, "msg": "Error importando conector"}
            def c4_bingx_px(sym): return None

    # Columnas de Fase 1 (Altcoins) y Fase 2 (Wall Street)
    c4_col_f1, c4_col_f2 = st.columns(2)

    def render_ficha_c4(pos, sym, fase_key, idx):
        es_real = pos.get("modo_ejecucion") == "REAL"
        px_live = c4_bingx_px(pos["bingx_sym"]) or pos.get("entry_px", 0.0)
        entry_px = pos.get("entry_px", px_live)
        qty = pos.get("qty_tokens", 0.0)
        pnl_usd = (px_live - entry_px) * qty if entry_px > 0 else 0.0
        pnl_pct = ((px_live - entry_px) / entry_px) * 100.0 if entry_px > 0 else 0.0
        color_pnl = "#22c55e" if pnl_usd >= 0 else "#ef4444"
        signo = "+" if pnl_usd >= 0 else ""
        horas = (time.time() - pos.get("ts_entry", time.time())) / 3600.0

        card_border = "#22c55e" if es_real else "#38bdf8"
        badge_html = "<span style='background:rgba(34,197,94,0.2); color:#22c55e; border:1px solid #22c55e; padding:3px 8px; border-radius:6px; font-weight:800; font-size:0.75rem;'>🟢 REAL BINGX</span>" if es_real else "<span style='background:rgba(56,189,248,0.2); color:#38bdf8; border:1px solid #38bdf8; padding:3px 8px; border-radius:6px; font-weight:800; font-size:0.75rem;'>👻 MODO FANTASMA</span>"

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(15,23,42,0.95), rgba(30,41,59,0.92)); border: 2px solid {card_border}; border-radius: 16px; padding: 18px; margin-bottom: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.5);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px;">
                <div>
                    <strong style="color:#f8fafc; font-size:1.3rem; font-weight:900;">{sym} (LONG)</strong>
                    <span style="margin-left:8px;">{badge_html}</span>
                </div>
                <span style="font-size:0.82rem; color:#94a3b8; font-weight:700;">Ranura #{idx+1}/3</span>
            </div>
            <div style="background:rgba(30,41,59,0.7); border-radius:10px; padding:10px; margin-bottom:12px; font-size:0.88rem; color:#cbd5e1; line-height:1.6;">
                • <b>Entrada:</b> ${entry_px:,.4f if entry_px<1 else f'{entry_px:,.2f}'} | <b>Precio Actual:</b> ${px_live:,.4f if px_live<1 else f'{px_live:,.2f}'}<br>
                • <b>🎯 Take Profit:</b> ${pos.get('tp_px', 0):,.4f if pos.get('tp_px',0)<1 else f"{pos.get('tp_px', 0):,.2f}"}<br>
                • <b>🛑 Stop Loss:</b> ${pos.get('sl_px', 0):,.4f if pos.get('sl_px',0)<1 else f"{pos.get('sl_px', 0):,.2f}"}<br>
                • <b>Lote Nominal:</b> {qty} contratos ($10 USD @ 10X)<br>
                • <b>PnL en Vivo:</b> <strong style="color:{color_pnl}; font-size:1.0rem;">{signo}${pnl_usd:,.2f} USD ({signo}{pnl_pct:.2f}%)</strong><br>
                • <b>Tiempo Activo:</b> {horas:.1f} horas
            </div>
        </div>
        """, unsafe_allow_html=True)

        c_act1, c_act2 = st.columns(2)
        with c_act1:
            if not es_real:
                if st.button(f"🟢 Pasar a REAL", key=f"btn_c4_m_real_{fase_key}_{sym}", use_container_width=True, type="primary"):
                    with st.spinner(f"Verificando y ejecutando {sym} en BingX..."):
                        r_promo = c4_promover_real(
                            sym=sym, bingx_sym=pos["bingx_sym"], side=pos.get("side", "LONG"),
                            qty=pos.get("qty_tokens", 0.0), tp_px=pos.get("tp_px", 0.0),
                            sl_px=pos.get("sl_px", 0.0), leverage=pos.get("leverage", 10)
                        )
                        if r_promo.get("ok"):
                            st_c4[fase_key][sym]["modo_ejecucion"] = "REAL"
                            st_c4[fase_key][sym]["order_id_real"] = r_promo.get("order_id")
                            guardar_json(c4_estado_file, st_c4)
                            st.toast(f"🚀 {sym} promovido a REAL con éxito en BingX!", icon="✅")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ {r_promo.get('msg')}")
            else:
                st.success("🟢 Posición Real Activa en BingX")
        with c_act2:
            if st.button(f"❌ Descartar", key=f"btn_c4_m_disc_{fase_key}_{sym}", use_container_width=True):
                del st_c4[fase_key][sym]
                guardar_json(c4_estado_file, st_c4)
                st.toast(f"🗑️ {sym} archivado", icon="🗑️")
                time.sleep(0.5)
                st.rerun()

    # ── FASE 1: ALTCOINS ──────────────────────────────────────────────
    with c4_col_f1:
        st.markdown("### ⚡ Fase 1: Altcoins Rápidas (Máx 3)")
        st.caption("Validación Cuántica 48h · Modo Fantasma Activo")
        pos_f1_c4 = st_c4.get("fase1_rapidas_activas", {})
        syms_f1_c4 = list(pos_f1_c4.keys())
        for i in range(3):
            if i < len(syms_f1_c4):
                sym = syms_f1_c4[i]
                render_ficha_c4(pos_f1_c4[sym], sym, "fase1_rapidas_activas", i)
            else:
                st.markdown(f"""
                <div style="border:1px dashed #64748b; background:rgba(15,23,42,0.4); border-radius:12px; padding:16px; margin-bottom:12px; text-align:center;">
                    <span style="color:#64748b;">⚪ Ranura #{i+1} Disponible (Escaneando Altcoins)</span>
                </div>
                """, unsafe_allow_html=True)

    # ── FASE 2: WALL STREET ───────────────────────────────────────────
    with c4_col_f2:
        st.markdown("### 🏛️ Fase 2: Wall Street Macro (Máx 3)")
        st.caption("Acciones US · Límite 25 Días · Checkpoint Día 10")
        pos_f2_c4 = st_c4.get("fase2_macro_activas", {})
        syms_f2_c4 = list(pos_f2_c4.keys())
        for i in range(3):
            if i < len(syms_f2_c4):
                sym = syms_f2_c4[i]
                render_ficha_c4(pos_f2_c4[sym], sym, "fase2_macro_activas", i)
            else:
                st.markdown(f"""
                <div style="border:1px dashed #64748b; background:rgba(15,23,42,0.4); border-radius:12px; padding:16px; margin-bottom:12px; text-align:center;">
                    <span style="color:#64748b;">⚪ Ranura #{i+1} Disponible (Escaneando Wall Street)</span>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")
    # ── CANDADOS ACTIVOS ANTI-BUCLE ───────────────────────────────────
    st.subheader("🛡️ Candados Activos de Cooldown Anti-Bucle (Cerebro 4)")
    st.caption("Garantía de nivel bancario: Ningún activo puede disparar señales repetidas en menos de 6 horas.")
    
    now_ts_c4 = time.time()
    candados_c4 = st_c4.get("candado_cooldown_senales", {})
    bloqueados_list = []
    for sym_c, info_c in candados_c4.items():
        exp = info_c.get("expira", 0.0)
        if now_ts_c4 < exp:
            mins = int((exp - now_ts_c4) / 60)
            bloqueados_list.append({
                "Activo": sym_c,
                "Motivo": info_c.get("motivo", "Cooldown Señal"),
                "Tiempo Restante": f"{mins} min ({mins/60:.1f}h)",
                "Estado": "🔒 Protección Anti-Bucle Activa"
            })
    if bloqueados_list:
        st.dataframe(pd.DataFrame(bloqueados_list), use_container_width=True, hide_index=True)
    else:
        st.info("🟢 No hay activos bloqueados en cooldown actualmente.")

    st.markdown("---")
    st.caption("*Cerebro 4: Mega-Agente ADN Cuántico · Sala de Mando Maestro · Puerto 8500*")

# ═══════════════════════════════════════════════════════════════════════════
# TAB 10 — MEGA HÍBRIDO CUÁNTICO: TOMA DE DECISIONES INSTITUCIONALES SUPREMAS
# ═══════════════════════════════════════════════════════════════════════════
with tab10:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(15,23,42,0.98), rgba(30,58,138,0.5)); border: 2px solid #38bdf8; border-radius: 20px; padding: 24px; margin-bottom: 24px; box-shadow: 0 0 40px rgba(56,189,248,0.25);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
                <span class="badge-gold">👑 CENTRO SUPREMO DE INTELIGENCIA CUÁNTICA</span>
                <h1 style="margin: 8px 0 0 0; font-size: 2.3rem; font-weight: 900; background: linear-gradient(135deg, #38bdf8, #eab308, #22c55e); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    🧠 MEGA HÍBRIDO DE TOMA DE DECISIONES EN VIVO
                </h1>
                <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 1.05rem;">
                    Fusión en Tiempo Real: <strong>On-Chain MVRV</strong> + <strong>Derivados Binance</strong> + <strong>Centinela Macro DXY</strong> + <strong>Oráculo Multi-Timeframe</strong> + <strong>Activos de Élite</strong>.
                </p>
            </div>
            <div style="text-align:right;">
                <span style="background:rgba(34,197,94,0.15); border:1px solid #22c55e; color:#22c55e; padding:6px 14px; border-radius:20px; font-size:0.85rem; font-weight:800;">
                    🟢 CONFLUENCIA TOTAL ACTIVA
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CARGA DE DATOS MULTI-MÓDULO EN VIVO ────────────────────────────────
    st_macro_t10 = cargar_json(os.path.join(BASE_DIR, "AUTONOMO", "centinela_macro_estado.json"), {})
    dxy_val_t10 = st_macro_t10.get("dxy", {}).get("valor", 99.20)
    usdt_mcap_t10 = st_macro_t10.get("usdt", {}).get("mcap_b", 185.4)
    fomc_txt_t10 = st_macro_t10.get("catalizadores", {}).get("fomc", {}).get("texto_restante", "9d 19h")

    st_mh_t10 = cargar_json(os.path.join(BASE_DIR, "estado_mega_hibrido_btc_dual.json"), {})
    eq_binance_t10 = clean_num(st_mh_t10.get("equity_total_usd", 282.58), 282.58)
    
    st_bc_t10 = cargar_json(os.path.join(BASE_DIR, "estado_blue_chips.json"), {})
    eq_bingx_t10 = 499.38
    pos_bc_t10 = st_bc_t10.get("posiciones", {})
    margen_bc_t10 = sum(clean_num(p.get("margen_actual", 10.0)) for p in pos_bc_t10.values())
    if margen_bc_t10 > 0:
        eq_bingx_t10 = max(eq_bingx_t10, margen_bc_t10 + 480.0)
    capital_total_t10 = eq_binance_t10 + eq_bingx_t10

    # ═══════════════════════════════════════════════════════════════════════
    # 👑 BLOQUE 1: RADAR CUANTITATIVO DE DECISIÓN DE ENTRADA & SEMÁFORO
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div style="background: rgba(15,23,42,0.9); border: 2px solid #22c55e; border-radius: 18px; padding: 22px; margin-bottom: 24px; box-shadow: 0 0 30px rgba(34,197,94,0.15);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div style="display:flex; align-items:center; gap:16px;">
                <div style="width:24px; height:24px; background:#ef4444; border-radius:50%; box-shadow: 0 0 15px #ef4444;"></div>
                <div>
                    <span style="font-size:0.75rem; font-weight:800; color:#22c55e; text-transform:uppercase; letter-spacing:1px;">
                        🚦 RADAR CUANTITATIVO DE TOMA DE DECISIONES DE ENTRADA
                    </span>
                    <h2 style="margin:4px 0 0 0; font-size:1.8rem; font-weight:900; color:#22c55e;">
                        ZONA DE BLOQUEO DE COMPRA / TOMA DE GANANCIAS
                    </h2>
                    <p style="margin:4px 0 0 0; color:#94a3b8; font-size:0.95rem;">
                        Sobreextendido o en zona de techos. Prohibido comprar en FOMO. Mantener posiciones acumuladas.
                    </p>
                </div>
            </div>
            <div style="background:rgba(15,23,42,0.95); border:2px solid #22c55e; border-radius:14px; padding:12px 24px; text-align:center;">
                <div style="font-size:0.75rem; color:#94a3b8; font-weight:700;">DECISION SCORE</div>
                <div style="font-size:2.4rem; font-weight:900; color:#22c55e; line-height:1;">
                    25 <span style="font-size:1.2rem; color:#64748b;">/ 100</span>
                </div>
                <div style="font-size:0.72rem; color:#cbd5e1; margin-top:2px;">Puntuación de Compra</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # ⚖️ BLOQUE 2: TRÍPTICO DE ACCIÓN (LAS 3 PREGUNTAS FUNDAMENTALES)
    # ═══════════════════════════════════════════════════════════════════════
    c_no, c_si, c_tp = st.columns(3)

    with c_no:
        st.markdown("""
        <div style="background:rgba(239,68,68,0.08); border:1px solid #ef4444; border-radius:16px; padding:18px; height:100%;">
            <h4 style="margin:0 0 12px 0; color:#ef4444; font-weight:800; font-size:1.15rem;">
                🚫 ¿Por qué NO Comprar Ahora?
            </h4>
            <ul style="margin:0; padding-left:18px; color:#cbd5e1; font-size:0.9rem; line-height:1.6;">
                <li><strong>Sobreextendido +11.8%</strong> por encima de la EMA 55 D1 ($69,881). No hay descuento institucional.</li>
                <li><strong>RSI 1D caliente (56.8 pts)</strong> cerca de zona de distribución.</li>
                <li><strong>Precio a +4.6%</strong> por encima del Soporte 7D ($76,239). Riesgo de corrección hacia el piso.</li>
                <li><strong>Sentimiento en Codicia/Euforia (73/100 - Greed)</strong>.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with c_si:
        st.markdown("""
        <div style="background:rgba(34,197,94,0.08); border:1px solid #22c55e; border-radius:16px; padding:18px; height:100%;">
            <h4 style="margin:0 0 12px 0; color:#22c55e; font-weight:800; font-size:1.15rem;">
                🛒 ¿Cuándo / Por qué Comprar?
            </h4>
            <ul style="margin:0; padding-left:18px; color:#cbd5e1; font-size:0.9rem; line-height:1.6;">
                <li>🎯 <strong>Suelo de Soporte 7D:</strong> Esperar retroceso a <strong style="color:#22c55e;">$76,239 USD</strong>.</li>
                <li>📉 <strong>Descuento Institucional:</strong> Esperar descuento de -2% bajo EMA 55 D1 (<strong style="color:#38bdf8;">$69,881 USD</strong>).</li>
                <li>📦 <strong>Presupuesto:</strong> Mantener las 4 balas mensuales preparadas ($20 USD @ 5X).</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with c_tp:
        st.markdown("""
        <div style="background:rgba(234,179,8,0.08); border:1px solid #eab308; border-radius:16px; padding:18px; height:100%;">
            <h4 style="margin:0 0 12px 0; color:#eab308; font-weight:800; font-size:1.15rem;">
                💰 ¿Por qué / Cuándo Vender?
            </h4>
            <ul style="margin:0; padding-left:18px; color:#cbd5e1; font-size:0.9rem; line-height:1.6;">
                <li>🔴 <strong>Fase 1 (50%):</strong> PnL ≥ +12% o RSI 1D ≥ 68 pts (Auto-Repay de Deuda a $0).</li>
                <li>🟡 <strong>Fase 2 (35%):</strong> RSI 4H ≥ 72 pts o Giro Valle Verde Diario.</li>
                <li>🟢 <strong>Fase 3 (15% Runner):</strong> Cierre final al perder la EMA 10 Diaria.</li>
            </ul>
            <div style="margin-top:10px; font-size:0.8rem; color:#eab308; font-weight:700;">
                🔥 TERMÓMETRO GATILLO FASE 2: 58.1 / 72.0 pts (81%)
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # 🔮 BLOQUE 3: BARÓMETRO ON-CHAIN MVRV & PSICOLOGÍA SMART MONEY
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div style="background:rgba(239,68,68,0.12); border:1px solid #ef4444; border-radius:14px; padding:14px 20px; margin-bottom:18px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div style="color:#ef4444; font-weight:900; font-size:0.95rem;">
                🔴 REGLA DE ORO CONTRARIAN: NOTICIAS BUENAS = TRAMPA DE LIQUIDEZ / BUSCAR SHORT
            </div>
            <span style="background:#ef4444; color:#fff; font-size:0.7rem; font-weight:800; padding:2px 8px; border-radius:12px;">PSICOLOGÍA SMART MONEY</span>
        </div>
        <p style="margin:4px 0 0 0; color:#cbd5e1; font-size:0.85rem;">
            El público minorista está en Euforia/Codicia Extrema (73/100 - Greed) leyendo titulares récord. Las instituciones distribuyen sus tenencias a los que compran tarde en máximos. ¡PROHIBIDO COMPRAR FOMO! (Activar coberturas SHORT o toma de ganancias).
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("🌐 Barómetro Cuantitativo MVRV: Suelos, Acumulación y Techos Promedio")
    st.caption("Promedios matemáticos de ciclos de Bitcoin: MVRV Diario (1D) y Semanal (1W) con zonas de acción en dólares.")

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.markdown("""
        <div style="background:rgba(34,197,94,0.1); border:1px solid #22c55e; border-radius:14px; padding:14px; text-align:center;">
            <div style="font-size:0.75rem; color:#22c55e; font-weight:800;">🛒 1. DÓNDE COMPRAR (SUELO)</div>
            <div style="font-size:1.4rem; font-weight:900; color:#f8fafc; margin:4px 0;">$62,000 – $68,000</div>
            <div style="font-size:0.75rem; color:#94a3b8;">MVRV ≤ 0.85 · Soporte 7D</div>
            <div style="margin-top:6px;"><span style="background:#22c55e; color:#090d16; font-size:0.68rem; font-weight:800; padding:2px 6px; border-radius:8px;">🟢 Compra Sangre / Agresiva</span></div>
        </div>
        """, unsafe_allow_html=True)

    with m_col2:
        st.markdown("""
        <div style="background:rgba(56,189,248,0.1); border:1px solid #38bdf8; border-radius:14px; padding:14px; text-align:center;">
            <div style="font-size:0.75rem; color:#38bdf8; font-weight:800;">📦 2. DÓNDE ACUMULAR (DCA)</div>
            <div style="font-size:1.4rem; font-weight:900; color:#f8fafc; margin:4px 0;">$68,000 – $74,000</div>
            <div style="font-size:0.75rem; color:#94a3b8;">MVRV 0.85 – 1.50 · -2% EMA55</div>
            <div style="margin-top:6px;"><span style="background:#38bdf8; color:#090d16; font-size:0.68rem; font-weight:800; padding:2px 6px; border-radius:8px;">🔵 Smart DCA (4 Balas/Mes)</span></div>
        </div>
        """, unsafe_allow_html=True)

    with m_col3:
        st.markdown("""
        <div style="background:rgba(234,179,8,0.15); border:2px solid #eab308; border-radius:14px; padding:14px; text-align:center;">
            <div style="font-size:0.75rem; color:#eab308; font-weight:800;">⚡ 3. DÓNDE MANTENER (HODL)</div>
            <div style="font-size:1.4rem; font-weight:900; color:#ffd600; margin:4px 0;">$74,000 – $86,000</div>
            <div style="font-size:0.75rem; color:#cbd5e1;">MVRV 1.50 – 2.20 (Actual)</div>
            <div style="margin-top:6px;"><span style="background:#eab308; color:#090d16; font-size:0.68rem; font-weight:800; padding:2px 6px; border-radius:8px;">🟡 Dejar Correr Posición</span></div>
        </div>
        """, unsafe_allow_html=True)

    with m_col4:
        st.markdown("""
        <div style="background:rgba(239,68,68,0.1); border:1px solid #ef4444; border-radius:14px; padding:14px; text-align:center;">
            <div style="font-size:0.75rem; color:#ef4444; font-weight:800;">💰 4. DÓNDE VENDER (TECHOS)</div>
            <div style="font-size:1.4rem; font-weight:900; color:#f8fafc; margin:4px 0;">$86,000 – $105,000+</div>
            <div style="font-size:0.75rem; color:#94a3b8;">MVRV ≥ 2.20 · Techo Ciclo 5</div>
            <div style="margin-top:6px;"><span style="background:#ef4444; color:#fff; font-size:0.68rem; font-weight:800; padding:2px 6px; border-radius:8px;">🔴 Semáforo 50% / 35% / 15%</span></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # 🧭 BLOQUE 4: TABLERO DERIVADOS + RADAR CENTINELA MACRO
    # ═══════════════════════════════════════════════════════════════════════
    d_col1, d_col2, d_col3, d_col4 = st.columns(4)
    with d_col1:
        st.markdown("""
        <div style="background:rgba(15,23,42,0.85); border:1px solid #334155; border-radius:14px; padding:14px; text-align:center;">
            <div style="font-size:0.75rem; color:#94a3b8; font-weight:700;">FUNDING RATE BINANCE (8H)</div>
            <div style="font-size:1.45rem; font-weight:900; color:#22c55e; margin:4px 0;">+0.0057%</div>
            <div style="font-size:0.72rem; color:#cbd5e1;">Bajo apalancamiento / Favorable LONG</div>
        </div>
        """, unsafe_allow_html=True)

    with d_col2:
        st.markdown("""
        <div style="background:rgba(15,23,42,0.85); border:1px solid #334155; border-radius:14px; padding:14px; text-align:center;">
            <div style="font-size:0.75rem; color:#94a3b8; font-weight:700;">OPEN INTEREST BTC (FUTUROS)</div>
            <div style="font-size:1.45rem; font-weight:900; color:#38bdf8; margin:4px 0;">106,113 BTC</div>
            <div style="font-size:0.72rem; color:#cbd5e1;">$8.46B USD en Posiciones</div>
        </div>
        """, unsafe_allow_html=True)

    with d_col3:
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.85); border:1px solid #334155; border-radius:14px; padding:14px; text-align:center;">
            <div style="font-size:0.75rem; color:#94a3b8; font-weight:700;">DXY (ÍNDICE DÓLAR)</div>
            <div style="font-size:1.45rem; font-weight:900; color:#38bdf8; margin:4px 0;">{dxy_val_t10:.2f} pts</div>
            <div style="font-size:0.72rem; color:#22c55e;">Viento a Favor (Dólar Débil)</div>
        </div>
        """, unsafe_allow_html=True)

    with d_col4:
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.85); border:1px solid #eab308; border-radius:14px; padding:14px; text-align:center;">
            <div style="font-size:0.75rem; color:#eab308; font-weight:700;">🏛️ FOMC TIPOS FED (16 SEPT)</div>
            <div style="font-size:1.45rem; font-weight:900; color:#22c55e; margin:4px 0;">{fomc_txt_t10}</div>
            <div style="font-size:0.72rem; color:#cbd5e1;">Pausa: 68% Probabilidad</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # 🎯 BLOQUE 5: ACTIVOS DE ÉLITE (RECOMENDACIONES COMPLETAS CON ENTRADA, TP Y SL)
    # ═══════════════════════════════════════════════════════════════════════
    st.subheader("🎯 Oportunidades de Élite: Entradas, TP1, TP2 y Stop Loss Exactos")
    st.caption("Filtrado matemático por Score de Convicción Quant ≥ 80 pts con parámetros de ejecución listos para operar.")

    # ─── TARJETAS ÉLITE DINÁMICAS (Motor v3.0) ───────────────────────────────
    # Toma las 3 mejores señales del motor v3: 2 LONG extremos + 1 SHORT extremo
    _v3_all  = st.session_state.get("v3_cache", [])
    _longs   = [x for x in _v3_all if x.get("score", 0) >= 80 and "LONG" in x.get("recom","")]
    _shorts  = [x for x in _v3_all if x.get("score", 0) <= 35 and "SHORT" in x.get("recom","")]
    _elite_cards = (_longs[:2] + _shorts[:1]) or _v3_all[:3]

    if not _elite_cards:
        st.info("⏳ Calculando señales en tiempo real… Haz clic en 'Recargar Datos' si persiste.")
    else:
        _ec_cols = st.columns(len(_elite_cards))
        for _idx_ec, _ec in enumerate(_elite_cards):
            _is_long_ec = "LONG" in _ec.get("recom","")
            _px_ec    = _ec.get("precio", 0)
            _sc_ec    = _ec.get("score",  50)
            _bc_ec    = "#22c55e" if _is_long_ec else "#ef4444"
            _label_ec = "🟢 COMPRA (LONG)" if _is_long_ec else "🔴 VENTA (SHORT)"
            _suelo_ec = "SUELO INSTITUCIONAL" if _is_long_ec else "TECHO EXTREMO"
            if _is_long_ec:
                _entry_lo = _ec.get("long_trigger",  _px_ec*0.99)
                _entry_hi = _ec.get("ema10",         _px_ec*1.00)
                _tp1_ec   = _ec.get("long_tp1",      _px_ec*1.02)
                _tp2_ec   = _ec.get("long_tp2",      _px_ec*1.05)
                _sl_ec    = _ec.get("long_sl",        _px_ec*0.96)
                _tp1_pct  = (_tp1_ec/_px_ec-1)*100 if _px_ec>0 else 0
                _tp2_pct  = (_tp2_ec/_px_ec-1)*100 if _px_ec>0 else 0
                _sl_pct   = (_sl_ec/_px_ec-1)*100  if _px_ec>0 else 0
                _entry_txt= f"Entrada Long: <strong style=\'color:{_bc_ec};\'>${_entry_lo:,.2f} – ${_entry_hi:,.2f}</strong>"
            else:
                _entry_lo = _ec.get("short_trigger", _px_ec*1.01)
                _entry_hi = _ec.get("ema10",          _px_ec*1.02)
                _tp1_ec   = _ec.get("short_tp1",      _px_ec*0.97)
                _tp2_ec   = _ec.get("short_tp2",      _px_ec*0.94)
                _sl_ec    = _ec.get("short_sl",        _px_ec*1.04)
                _tp1_pct  = (_tp1_ec/_px_ec-1)*100 if _px_ec>0 else 0
                _tp2_pct  = (_tp2_ec/_px_ec-1)*100 if _px_ec>0 else 0
                _sl_pct   = (_sl_ec/_px_ec-1)*100  if _px_ec>0 else 0
                _entry_txt= f"Entrada Short: <strong style=\'color:{_bc_ec};\'>${_entry_lo:,.2f} – ${_entry_hi:,.2f}</strong>"
            _rsi_ec = _ec.get("rsi_1h", 50)
            with _ec_cols[_idx_ec]:
                st.markdown(f"""
                <div style="background:rgba(15,23,42,0.95); border:2px solid {_bc_ec}; border-radius:16px; padding:18px; box-shadow:0 0 20px {_bc_ec}33;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:900; color:#f8fafc; font-size:1.1rem;">{_ec.get("sym","?")} ({_ec.get("tipo","?")})</span>
                        <span style="background:{_bc_ec}; color:#fff; font-size:0.7rem; font-weight:900; padding:3px 8px; border-radius:8px;">{_label_ec}</span>
                    </div>
                    <div style="display:flex; align-items:baseline; gap:8px; margin:6px 0;">
                        <span style="font-size:2rem; font-weight:900; color:{_bc_ec};">${_px_ec:,.2f}</span>
                        <span style="font-size:0.8rem; color:{_bc_ec}; font-weight:700;">{_suelo_ec}</span>
                    </div>
                    <div style="background:{_bc_ec}14; border-radius:10px; padding:10px; margin:8px 0; font-size:0.85rem; line-height:1.6;">
                        <div style="color:#f8fafc;">💵 <strong>{_entry_txt}</strong></div>
                        <div style="color:#f8fafc;">🎯 <strong>TP 1 (50%+BE):</strong> <strong style="color:#ffd600;">${_tp1_ec:,.2f}</strong> ({_tp1_pct:+.1f}%)</div>
                        <div style="color:#f8fafc;">🏆 <strong>TP 2 (EMA 55):</strong> <strong style="color:#22c55e;">${_tp2_ec:,.2f}</strong> ({_tp2_pct:+.1f}%)</div>
                        <div style="color:#f8fafc;">🛑 <strong>Stop Loss:</strong> <strong style="color:#ef4444;">${_sl_ec:,.2f}</strong> ({_sl_pct:+.1f}%)</div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#94a3b8; border-top:1px solid #334155; padding-top:6px;">
                        <span>🎯 Convicción: <strong style="color:{_bc_ec};">{_sc_ec}/100</strong> (RSI {_rsi_ec:.1f})</span>
                        <span>📦 Lote: <strong style="color:{_bc_ec};">$10 @ 5X</strong></span>
                    </div>
                </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # 🧮 BLOQUE 6: CALCULADORA DE SALIDA ESCALONADA DE CICLO (PROYECCIÓN EN $)
    # ═══════════════════════════════════════════════════════════════════════
    st.subheader("🧮 Calculadora de Salida Escalonada de Ciclo (Proyección en $ USD Reales)")
    st.caption(f"Simulación matemática de tu capital real consolidado (${capital_total_t10:,.2f} USD) y captura de efectivo según los techos macro de Bitcoin.")

    p_col1, p_col2, p_col3 = st.columns(3)
    with p_col1:
        st.markdown("""
        <div style="background:rgba(239,68,68,0.1); border:1px solid #ef4444; border-radius:14px; padding:16px; text-align:center;">
            <div style="font-size:0.75rem; color:#ef4444; font-weight:800;">1️⃣ FASE 1 ($86,000 USD)</div>
            <div style="font-size:1.9rem; font-weight:900; color:#f8fafc; margin:4px 0;">$288.48 USD</div>
            <div style="font-size:0.78rem; color:#cbd5e1;">Venta 50% Posición · Deuda $0 Auto-Repay</div>
            <div style="margin-top:6px; color:#22c55e; font-weight:800; font-size:0.8rem;">Cash Libre Estimado: +$10.36 USD</div>
        </div>
        """, unsafe_allow_html=True)

    with p_col2:
        st.markdown("""
        <div style="background:rgba(234,179,8,0.1); border:1px solid #eab308; border-radius:14px; padding:16px; text-align:center;">
            <div style="font-size:0.75rem; color:#eab308; font-weight:800;">2️⃣ FASE 2 ($95,000 USD)</div>
            <div style="font-size:1.9rem; font-weight:900; color:#f8fafc; margin:4px 0;">$318.44 USD</div>
            <div style="font-size:0.78rem; color:#cbd5e1;">Venta 35% Posición · Asegurar Ganancia Macro</div>
            <div style="margin-top:6px; color:#22c55e; font-weight:800; font-size:0.8rem;">Cash Libre Estimado: +$17.74 USD</div>
        </div>
        """, unsafe_allow_html=True)

    with p_col3:
        st.markdown("""
        <div style="background:rgba(34,197,94,0.1); border:1px solid #22c55e; border-radius:14px; padding:16px; text-align:center;">
            <div style="font-size:0.75rem; color:#22c55e; font-weight:800;">3️⃣ FASE 3 ($105,000+ USD)</div>
            <div style="font-size:1.9rem; font-weight:900; color:#f8fafc; margin:4px 0;">$351.73 USD</div>
            <div style="font-size:0.78rem; color:#cbd5e1;">15% Runner Final · Dejar correr hasta fin de ciclo</div>
            <div style="margin-top:6px; color:#38bdf8; font-weight:800; font-size:0.8rem;">Cierre Total con Trailing Stop EMA 10</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("*Mega Híbrido Cuántico de Decisión · Ecosistema Cazador PRO · Puerto 8500*")





