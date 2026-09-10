# -*- coding: utf-8 -*-
"""
CONECTOR SEGURO MULTI-EXCHANGE (BINGX HEDGE & BINANCE CROSS MARGIN)
Blindajes de Nivel Bancario:
1. Circuit Breaker & Resiliencia: La caída de API nunca borra estados locales ni dispara bucles.
2. Precisión estricta de cantidad (tokens/contratos según step_qty y min_qty).
3. clientOrderId único determinista para evitar duplicación ante reintentos/timeouts.
4. Modo Fantasma por Defecto: Bloqueo de órdenes automáticas; solo se ejecutan órdenes reales por acción manual explícita.
5. Regla Sagrada MSFT: El SHORT de MSFT nunca se toca ni se cierra.
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

# Variables de Circuit Breaker para BingX
_CIRCUIT_FAILURES = 0
_CIRCUIT_PAUSED_UNTIL = 0.0

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
    global _CIRCUIT_FAILURES, _CIRCUIT_PAUSED_UNTIL
    now = time.time()

    if now < _CIRCUIT_PAUSED_UNTIL:
        logging.getLogger().warning(f"⚡ [CIRCUIT BREAKER BINGX ACTIVO] Pausado por fallos de API hasta {int(_CIRCUIT_PAUSED_UNTIL - now)}s.")
        return {"code": -995, "msg": "CIRCUIT_BREAKER_ACTIVE"}

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
            
        data = r.json()
        code = data.get("code")
        if code == 0:
            _CIRCUIT_FAILURES = 0 # Reset circuit breaker
            return data
        else:
            _CIRCUIT_FAILURES += 1
            if _CIRCUIT_FAILURES >= 5:
                _CIRCUIT_PAUSED_UNTIL = now + 120.0 # Pausar 2 min
                logging.getLogger().error("🚨 [CIRCUIT BREAKER DISPARADO] 5 fallos consecutivos de BingX API. Pausando 120s.")
            return data
    except Exception as e:
        _CIRCUIT_FAILURES += 1
        if _CIRCUIT_FAILURES >= 5:
            _CIRCUIT_PAUSED_UNTIL = now + 120.0
            logging.getLogger().error(f"🚨 [CIRCUIT BREAKER DISPARADO] Excepciones repetidas de BingX: {e}. Pausando 120s.")
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

def bingx_abrir_posicion_mercado(bingx_sym, side, qty, client_order_id, es_promocion_manual=False, tp_px=0, sl_px=0):
    """
    Abre posición a mercado en BingX en Modo Cobertura con clientOrderId determinista.
    es_promocion_manual: True si fue ordenada explícitamente por el usuario desde la UI.
    """
    pos_side = "LONG" if side.upper() in ["BUY", "LONG"] else "SHORT"
    order_side = "BUY" if pos_side == "LONG" else "SELL"
    
    # 🛡️ CANDADO DE ACERO: Bloqueo de órdenes automáticas si no es promoción manual
    if not es_promocion_manual:
        logging.getLogger().info(f"👻 [MODO FANTASMA ACTIVO] Orden en {bingx_sym} preservada en simulación (Sin envío real).")
        return {"code": 0, "msg": "EJECUTADO_EN_MODO_FANTASMA_SIMULADO", "clientOrderID": client_order_id}

    params = {
        "symbol": bingx_sym,
        "side": order_side,
        "positionSide": pos_side,
        "type": "MARKET",
        "quantity": float(qty),
        "clientOrderID": client_order_id
    }
    if tp_px > 0 or sl_px > 0:
        import json
        tpsl = {}
        if tp_px > 0:
            tpsl["takeProfit"] = {"type": "TAKE_PROFIT_MARKET", "stopPrice": float(tp_px), "workingType": "MARK_PRICE"}
        if sl_px > 0:
            tpsl["stopLoss"] = {"type": "STOP_MARKET", "stopPrice": float(sl_px), "workingType": "MARK_PRICE"}
        # BingX requires this as string depending on endpoint or just direct properties in v2.
        if tp_px > 0: params["takeProfit"] = json.dumps(tpsl["takeProfit"])
        if sl_px > 0: params["stopLoss"] = json.dumps(tpsl["stopLoss"])
        
    return bingx_request("POST", "/openApi/swap/v2/trade/order", params)

def bingx_cerrar_posicion_mercado(bingx_sym, pos_side, qty, client_order_id=None):
    """
    Cierra posición a mercado en BingX modo cobertura
    CANDADO DE ACERO: Si el símbolo es MSFT y pos_side es SHORT, ESTÁ ESTRICTAMENTE PROHIBIDO CERRARLA.
    """
    if "MSFT" in str(bingx_sym).upper() and str(pos_side).upper() == "SHORT":
        logging.getLogger().error("⛔ [INTENTO DE CIERRE BLOQUEADO] Regla sagrada: ¡EL SHORT DE MSFT NUNCA SE TOCA NI SE CIERRA!")
        return {"code": -998, "msg": "REGLA_SAGRADA: EL SHORT DE MSFT NO SE TOCA"}
        
    order_side = "SELL" if pos_side.upper() == "LONG" else "BUY"
    params = {
        "symbol": bingx_sym,
        "side": order_side,
        "positionSide": pos_side.upper(),
        "type": "MARKET",
        "quantity": float(qty)
    }
    if client_order_id:
        params["clientOrderID"] = client_order_id
    return bingx_request("POST", "/openApi/swap/v2/trade/order", params)

def bingx_obtener_posiciones_seguras():
    """
    Retorna una tupla (ok: bool, posiciones: list).
    ok es True ÚNICAMENTE si la API respondió exitosamente con code == 0.
    Si hay timeout, error de red o error de API, retorna (False, []).
    ¡ESTO PREVIENE BORRADOS ERRÓNEOS Y BUCLES INFINITOS!
    """
    r = bingx_request("GET", "/openApi/swap/v2/user/positions")
    if r.get("code") == 0 and "data" in r and isinstance(r["data"], list):
        return True, r["data"]
    return False, []

def bingx_obtener_posiciones_activas():
    """Retorna las posiciones vivas en BingX (wrapper compatible)"""
    ok, pos = bingx_obtener_posiciones_seguras()
    return pos if ok else []

def bingx_ejecutar_promocion_real(sym, bingx_sym, side, qty, tp_px, sl_px, leverage=10):
    """
    Ejecuta de forma segura la promoción manual de una recomendación Fantasma a REAL en BingX.
    Verifica que no exista posición duplicada previa, configura apalancamiento y envía orden a mercado.
    """
    try:
        from notificador_telegram import notificar_promocion_real
    except ImportError:
        def notificar_promocion_real(*args, **kwargs): pass

    # 1. Verificar si ya existe posición viva para evitar compras dobles
    ok, live_pos = bingx_obtener_posiciones_seguras()
    if ok:
        for p in live_pos:
            if p.get("symbol") == bingx_sym and float(p.get("positionAmt", 0)) != 0:
                p_side = p.get("positionSide", "").upper()
                if p_side == side.upper():
                    return {
                        "ok": False,
                        "msg": f"Ya existe una posición real abierta en BingX para {sym} en {side}. Promoción abortada para evitar duplicados."
                    }

    # 2. Configurar apalancamiento
    bingx_establecer_apalancamiento(bingx_sym, leverage=leverage, side=side)

    # 3. Disparar orden a mercado real
    cid = f"PROMO_REAL_{sym}_{int(time.time())}"
    r_ord = bingx_abrir_posicion_mercado(bingx_sym, side, qty, cid, es_promocion_manual=True, tp_px=tp_px, sl_px=sl_px)

    if r_ord.get("code") == 0:
        data_ord = r_ord.get("data", {}).get("order", {})
        order_id = str(data_ord.get("orderId", cid))
        px_exec = float(data_ord.get("avgPrice", 0.0))
        if px_exec <= 0:
            px_exec = bingx_obtener_precio(bingx_sym) or 0.0

        # Notificar a Telegram
        try:
            notificar_promocion_real(sym, side, px_exec, qty, tp_px, sl_px, order_id)
        except Exception as e:
            logging.getLogger().warning(f"Error notificando promoción a Telegram: {e}")

        return {
            "ok": True,
            "order_id": order_id,
            "client_order_id": cid,
            "precio_ejecucion": px_exec,
            "msg": f"Orden de {sym} ({side}) ejecutada exitosamente en BingX."
        }
    else:
        return {
            "ok": False,
            "msg": f"Error de BingX ({r_ord.get('code')}): {r_ord.get('msg')}",
            "code": r_ord.get("code")
        }

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
    headers = {"X-MBX-APIKEY": BINANCE_KEY}
    for base in ["https://api3.binance.com", "https://api1.binance.com", "https://api.binance.com"]:
        url = f"{base}/sapi/v1/margin/account?{qs}&signature={sig}"
        try:
            r = requests.get(url, headers=headers, timeout=12)
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
