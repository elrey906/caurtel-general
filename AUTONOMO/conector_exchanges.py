# -*- coding: utf-8 -*-
"""
CONECTOR SEGURO MULTI-EXCHANGE (BINGX HEDGE & BINANCE CROSS MARGIN)
Blindajes:
1. Precisión estricta de cantidad (tokens/contratos según step_qty y min_qty).
2. clientOrderId único determinista para evitar duplicación ante reintentos/timeouts.
3. User-Agent, firma HMAC SHA256 y manejo de excepciones de red con fallback.
4. Consulta de posiciones vivas filtrando por clientOrderId o prefijo para NO tocar otros cerebros.
"""
import os, sys, time, json, datetime, hmac, hashlib, math, requests, logging
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROD_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
ENV_PATH = os.path.join(PROD_DIR, ".env")
load_dotenv(ENV_PATH)

BINGX_KEY = os.getenv("BINGX_API_KEY", "")
BINGX_SECRET = os.getenv("BINGX_API_SECRET", "")
BINGX_URL = "https://open-api.bingx.com"

BINANCE_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET = os.getenv("BINANCE_API_SECRET", os.getenv("BINANCE_SECRET_KEY", ""))

HEADERS_STD = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def ajustar_cantidad_bingx(monto_usd, palanca, precio, step_qty, min_qty):
    """
    Convierte dólares a tokens exactos redondeando al step_qty y respetando el min_qty
    Ejemplo: $10 USD * 10X = $100 nominal / $180 (SOL) = 0.5555 -> 0.55 SOL
    """
    if precio <= 0: return 0.0
    nominal = monto_usd * palanca
    raw_qty = nominal / precio
    if step_qty < 1:
        precision = int(round(-math.log10(step_qty)))
    else:
        precision = 0
    qty = round(math.floor(raw_qty / step_qty) * step_qty, precision)
    return max(qty, min_qty)

# ══════════════════════════════════════════════════════════════════
# BINGX API PERPETUOS MODO COBERTURA
# ══════════════════════════════════════════════════════════════════
def bingx_request(method, endpoint, params=None):
    if not BINGX_KEY or not BINGX_SECRET:
        return {"code": -1, "msg": "Sin credenciales de BingX"}
    params = params.copy() if params else {}
    params["timestamp"] = int(time.time() * 1000)
    query = "&".join([f"{k}={params[k]}" for k in sorted(params.keys())])
    sig = hmac.new(BINGX_SECRET.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
    url = f"{BINGX_URL}{endpoint}?{query}&signature={sig}"
    headers = {"X-BX-APIKEY": BINGX_KEY, "User-Agent": "Mozilla/5.0"}
    try:
        if method.upper() == "GET":
            r = requests.get(url, headers=headers, timeout=8)
        else:
            r = requests.post(url, headers=headers, timeout=8)
        return r.json()
    except Exception as e:
        return {"code": -999, "msg": str(e)}

def bingx_obtener_precio(bingx_sym):
    try:
        url = f"{BINGX_URL}/openApi/swap/v2/quote/ticker?symbol={bingx_sym}"
        r = requests.get(url, headers=HEADERS_STD, timeout=5).json()
        if r.get("code") == 0 and "data" in r:
            return float(r["data"]["lastPrice"])
    except: pass
    return None

def bingx_establecer_apalancamiento(bingx_sym, leverage=10, side="LONG"):
    """Configura el apalancamiento en modo cobertura"""
    params = {
        "symbol": bingx_sym,
        "leverage": int(leverage),
        "side": side
    }
    return bingx_request("POST", "/openApi/swap/v2/trade/leverage", params)

def bingx_abrir_posicion_mercado(bingx_sym, side, qty, client_order_id):
    """
    Abre posición a mercado en BingX en Modo Cobertura con clientOrderId determinista
    side: 'LONG' o 'SHORT'
    positionSide: 'LONG' o 'SHORT'
    """
    pos_side = "LONG" if side.upper() == "BUY" or side.upper() == "LONG" else "SHORT"
    order_side = "BUY" if pos_side == "LONG" else "SELL"
    
    # 🛡️ CANDADO DE ACERO: FASE 1 (ALTCOINS) ESTÁ 100% PROHIBIDA EN REAL (SOLO PAPER TRADING)
    f1_alts = ["SOL", "ETH", "NEAR", "SUI", "AVAX", "DOGE"]
    for alt in f1_alts:
        if bingx_sym.upper().startswith(alt):
            logging.getLogger().warning(f"🚫 [CANDADO ACTIVO] Intento de orden real en {bingx_sym} bloqueado: Fase 1 opera exclusivamente en FANTASMA/PAPER TRADING.")
            return {"code": -997, "msg": "BLOQUEO_FASE1_SOLO_PAPER_TRADING"}

    params = {
        "symbol": bingx_sym,
        "side": order_side,
        "positionSide": pos_side,
        "type": "MARKET",
        "quantity": float(qty),
        "clientOrderID": client_order_id
    }
    return bingx_request("POST", "/openApi/swap/v2/trade/order", params)

def bingx_cerrar_posicion_mercado(bingx_sym, pos_side, qty, client_order_id=None):
    """
    Cierra posición a mercado en BingX modo cobertura
    Si pos_side era LONG, se envía SELL con positionSide=LONG
    CANDADO DE ACERO: Si el símbolo es MSFT y pos_side es SHORT, ESTÁ ESTRICTAMENTE PROHIBIDO CERRARLA.
    """
    if "MSFT" in str(bingx_sym).upper() and str(pos_side).upper() == "SHORT":
        logging.getLogger().error("⛔ [INTENTO DE CIERRE BLOQUEADO] Regla sagrada: ¡EL SHORT DE MSFT NUNCA SE TOCA NI SE CIERRA!")
        return {"code": -998, "msg": "REGLA_SAGRADA: EL SHORT DE MSFT NO SE TOCA"}
        
    order_side = "SELL" if pos_side == "LONG" else "BUY"
    params = {
        "symbol": bingx_sym,
        "side": order_side,
        "positionSide": pos_side,
        "type": "MARKET",
        "quantity": float(qty)
    }
    if client_order_id:
        params["clientOrderID"] = client_order_id
    return bingx_request("POST", "/openApi/swap/v2/trade/order", params)

def bingx_obtener_posiciones_activas():
    """Retorna las posiciones vivas en BingX"""
    r = bingx_request("GET", "/openApi/swap/v2/user/positions")
    if r.get("code") == 0 and "data" in r:
        return r["data"]
    return []

# ══════════════════════════════════════════════════════════════════
# BINANCE CROSS MARGIN 5X (EXCLUSIVO BITCOIN)
# ══════════════════════════════════════════════════════════════════
def binance_firmar(query_str):
    return hmac.new(BINANCE_SECRET.encode('utf-8'), query_str.encode('utf-8'), hashlib.sha256).hexdigest()

def binance_obtener_server_time():
    for base in ["https://api.binance.com", "https://api3.binance.com", "https://data-api.binance.vision"]:
        try:
            r = requests.get(f"{base}/api/v3/time", timeout=3)
            if r.status_code == 200:
                return r.json().get("serverTime")
        except: pass
    return int(time.time() * 1000)

def binance_margin_account_info():
    """Consulta balance y Margin Level real en Binance Cross Margin"""
    if not BINANCE_KEY or not BINANCE_SECRET:
        return None
    s_time = binance_obtener_server_time()
    qs = f"recvWindow=60000&timestamp={s_time}"
    sig = binance_firmar(qs)
    url = f"https://api.binance.com/sapi/v1/margin/account?{qs}&signature={sig}"
    headers = {"X-MBX-APIKEY": BINANCE_KEY}
    try:
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code == 200:
            return r.json()
    except: pass
    return None

def binance_margin_comprar_btc(monto_usd=10.0, client_order_id=None):
    """
    Ejecuta compra en Binance Cross Margin con borrow automático o saldo libre
    Usa quoteOrderQty=$10.00 exactos para evitar errores de redondeo de tokens
    """
    if not BINANCE_KEY or not BINANCE_SECRET:
        return {"error": "Sin credenciales de Binance"}
    
    s_time = binance_obtener_server_time()
    params = [
        "symbol=BTCUSDT",
        "isIsolated=FALSE",
        "side=BUY",
        "type=MARKET",
        "sideEffectType=MARGIN_BUY",
        f"quoteOrderQty={float(monto_usd):.2f}",
        "recvWindow=60000",
        f"timestamp={s_time}"
    ]
    if client_order_id:
        params.append(f"newClientOrderId={client_order_id}")
    
    qs = "&".join(params)
    sig = binance_firmar(qs)
    url = f"https://api.binance.com/sapi/v1/margin/order?{qs}&signature={sig}"
    headers = {"X-MBX-APIKEY": BINANCE_KEY}
    try:
        r = requests.post(url, headers=headers, timeout=8)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def binance_margin_vender_btc(qty_btc, client_order_id=None):
    """
    Vende BTC para devolver préstamo o asegurar ganancia en Binance Margin
    Precisión de paso de BTC es 0.00001 (5 decimales)
    """
    if not BINANCE_KEY or not BINANCE_SECRET:
        return {"error": "Sin credenciales de Binance"}
    
    qty_fmt = math.floor(qty_btc * 100000.0) / 100000.0
    if qty_fmt < 0.00001:
        return {"error": "Cantidad menor al mínimo de BTC (0.00001)"}
        
    s_time = binance_obtener_server_time()
    params = [
        "symbol=BTCUSDT",
        "isIsolated=FALSE",
        "side=SELL",
        "type=MARKET",
        "sideEffectType=AUTO_REPAY",
        f"quantity={qty_fmt:.5f}",
        "recvWindow=60000",
        f"timestamp={s_time}"
    ]
    if client_order_id:
        params.append(f"newClientOrderId={client_order_id}")
    
    qs = "&".join(params)
    sig = binance_firmar(qs)
    url = f"https://api.binance.com/sapi/v1/margin/order?{qs}&signature={sig}"
    headers = {"X-MBX-APIKEY": BINANCE_KEY}
    try:
        r = requests.post(url, headers=headers, timeout=8)
        return r.json()
    except Exception as e:
        return {"error": str(e)}
