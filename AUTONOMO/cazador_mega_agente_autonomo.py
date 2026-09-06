# -*- coding: utf-8 -*-
"""
👑 CEREBRO SUPREMO: MEGA-AGENTE ADN AUTÓNOMO (PILOTO AUTOMÁTICO)
=============================================================================
Cuotas de Operación Estrictas & Blindajes:
  1. Modo Fantasma por Defecto:
     - Toda recomendación se genera en MODO FANTASMA (100% Simulado).
     - Alerta instantánea a Telegram con parámetros cuantitativos.
     - El usuario decide en el Dashboard si promover a REAL o dejar en FANTASMA.
  2. Blindaje Anti-Bucle Infinito:
     - Candado de Cooldown estricto (mínimo 6h por activo tras señal, 24h si toca SL).
     - Sincronización de API con Circuit Breaker: Caída de red NUNCA borra posiciones.
  3. Pacto de Respeto Absoluto:
     - No toca el SHORT sagrado de MSFT ni activos de Cerebros 1, 2 y 3.
  4. Libro Contable ($ USD PnL) y Auto-Aprendizaje.
=============================================================================
"""
import os, sys, time, json, datetime, math, logging
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROD_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, PROD_DIR)

from config_adn import (
    CONFIG_FILE, ESTADO_FILE, LOG_FILE,
    BINGX_F1_MAX_POS, BINGX_F2_MAX_POS, BINGX_MARGEN_USD, BINGX_LEVERAGE,
    COOLDOWN_HORAS_TRAS_SL,
    BINANCE_BTC_MAX_BALAS, BINANCE_MARGEN_USD, BINANCE_LEVERAGE,
    UNIVERSO_FASE1, UNIVERSO_FASE2, UNIVERSO_BTC_BINANCE
)
from conector_exchanges import (
    ajustar_cantidad_bingx,
    bingx_obtener_precio,
    bingx_establecer_apalancamiento,
    bingx_abrir_posicion_mercado,
    bingx_cerrar_posicion_mercado,
    bingx_obtener_posiciones_seguras,
    bingx_obtener_posiciones_activas,
    bingx_ejecutar_promocion_real,
    binance_margin_account_info,
    binance_margin_comprar_btc,
    binance_margin_vender_btc
)
from motor_adn_quant import calcular_adn_activo
from aprendizaje_ledger import registrar_operacion_cerrada, cargar_json, guardar_json
from notificador_telegram import (
    notificar_alerta_fantasma,
    notificar_promocion_real,
    notificar_cierre_trade,
    notificar_disparo_binance_btc
)

# Configurar Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("MEGA_AGENTE_ADN")

COOLDOWN_SENAL_HORAS = 6.0  # Candado mínimo de 6h para evitar repetir la misma señal

def obtener_modos_operativos():
    """
    Retorna la configuración granular de modos:
    - Fase 1 (Altcoins): FANTASMA por defecto
    - Fase 2 (Wall Street): FANTASMA por defecto
    - Binance Margin (BTC): REAL (operaciones vivas en Binance Cross Margin 5X)
    """
    cfg = cargar_json(CONFIG_FILE, {
        "modo_fase1_bingx": "FANTASMA",
        "modo_fase2_bingx": "FANTASMA",
        "modo_binance_btc": "REAL"
    })
    return {
        "fase1": cfg.get("modo_fase1_bingx", "FANTASMA").upper(),
        "fase2": cfg.get("modo_fase2_bingx", "FANTASMA").upper(),
        "binance_btc": cfg.get("modo_binance_btc", "REAL").upper()
    }

def obtener_modo_operativo():
    modos = obtener_modos_operativos()
    return modos.get("fase1", "FANTASMA")

def leer_estado_agente():
    st = cargar_json(ESTADO_FILE, {
        "fase1_rapidas_activas": {},  # max 3
        "fase2_macro_activas": {},    # max 3
        "recomendaciones_fantasma": {}, # Todas las recomendaciones activas con estado
        "binance_btc_balas": [],      # max 3
        "btc_acumulado_agente": 0.0,
        "btc_costo_promedio": 0.0,
        "radar_top3_fase1": [],
        "radar_top3_fase2": [],
        "candado_cooldown_senales": {}, # {sym: {"ts": now, "expira": now+6h, "motivo": "..."}}
        "enfriamiento_sl": {},        # {sym: ts_expira} -> Bloqueo anti-venganza si pierde
        "ultima_actualizacion": datetime.datetime.now().isoformat()
    })
    if "recomendaciones_fantasma" not in st:
        st["recomendaciones_fantasma"] = {}
    if "candado_cooldown_senales" not in st:
        st["candado_cooldown_senales"] = {}
    return st

def guardar_estado_agente(st):
    st["ultima_actualizacion"] = datetime.datetime.now().isoformat()
    guardar_json(ESTADO_FILE, st)

def activos_ocupados_por_otros_cerebros():
    """
    Lee los estados locales y las posiciones reales en BingX para:
    1. Proteger sagradamente el SHORT de MSFT.
    2. Evitar duplicar activos que ya tengan posiciones activas en la misma dirección.
    """
    ocupados = set()
    # 1. Cerebro 1 (Blue Chips)
    c1_path = os.path.join(PROD_DIR, "estado_blue_chips.json")
    if os.path.exists(c1_path):
        try:
            st1 = cargar_json(c1_path, {})
            for sym in st1.get("posiciones", {}).keys():
                if sym != "MSFT":
                    ocupados.add(sym)
        except: pass
        
    # 2. Cerebro 3 (Trifecta)
    c3_path = os.path.join(PROD_DIR, "HIBRIDO", "estado_trifecta_hibrido.json")
    if os.path.exists(c3_path):
        try:
            st3 = cargar_json(c3_path, {})
            for sym in st3.get("posiciones_activas", {}).keys():
                if sym != "MSFT":
                    ocupados.add(sym)
        except: pass
        
    # 3. Consulta segura a la API de BingX
    try:
        ok, live_positions = bingx_obtener_posiciones_seguras()
        if ok:
            for p in live_positions:
                amt = float(p.get("positionAmt", 0))
                if amt != 0:
                    bsym = p.get("symbol", "")
                    pside = p.get("positionSide", "").upper()
                    
                    if "MSFT" in bsym:
                        if pside == "SHORT":
                            continue
                        elif pside == "LONG":
                            ocupados.add("MSFT")
                    
                    if "ETH" in bsym and pside == "LONG":
                        ocupados.add("ETH")
                    elif "BNB" in bsym and pside == "LONG":
                        ocupados.add("BNB")
    except Exception as e:
        log.warning(f"Aviso consultando posiciones vivas en BingX para ocupados: {e}")
        
    return ocupados

def esta_en_cooldown(st, sym, now_ts):
    """Verifica si un activo está bloqueado por cooldown de señal o Stop Loss"""
    # 1. Enfriamiento por Stop Loss (24h)
    enfriamiento_sl = st.get("enfriamiento_sl", {})
    if sym in enfriamiento_sl and now_ts < enfriamiento_sl[sym]:
        return True, f"Enfriamiento SL ({int((enfriamiento_sl[sym] - now_ts)/3600)}h restantes)"
        
    # 2. Candado de Cooldown de Señal Reciente (6h)
    candados = st.get("candado_cooldown_senales", {})
    if sym in candados:
        expira = candados[sym].get("expira", 0.0)
        if now_ts < expira:
            return True, f"Cooldown Señal Reciente ({int((expira - now_ts)/60)}m restantes)"
            
    return False, ""

def registrar_cooldown_senal(st, sym, now_ts, horas=COOLDOWN_SENAL_HORAS):
    """Registra el candado anti-bucle por 6 horas para el símbolo"""
    if "candado_cooldown_senales" not in st:
        st["candado_cooldown_senales"] = {}
    st["candado_cooldown_senales"][sym] = {
        "ts": now_ts,
        "expira": now_ts + (horas * 3600.0),
        "motivo": "RECOMENDACION_EMITIDA"
    }

def sincronizar_posiciones_reales_bingx(st, modo):
    """
    Audita en BingX las posiciones vivas ÚNICAMENTE para trades promovidos a REAL.
    Si la API falla (ok=False), PRESERVA el estado local sin borrar nada (Circuit Breaker).
    """
    ok, live_positions = bingx_obtener_posiciones_seguras()
    if not ok:
        # Fallo de red o API: NUNCA borrar estados locales
        return

    syms_vivos = {p.get("symbol") for p in live_positions if float(p.get("positionAmt", 0)) != 0}

    # Verificar Fase 2 (Wall Street) promovidas a REAL
    for sym, data in list(st["fase2_macro_activas"].items()):
        if data.get("modo_ejecucion") == "REAL":
            bsym = data["bingx_sym"]
            if bsym not in syms_vivos:
                log.info(f"🔔 [CIERRE DETECTADO EN BINGX] {sym} de Fase 2 Real ya no está abierta en BingX.")
                registrar_operacion_cerrada(
                    "FASE2_MACRO", sym, "BINGX", "LONG",
                    data["entry_px"], data["tp_px"], BINGX_MARGEN_USD,
                    data["margen_usd"] * 0.60, "CIERRE_EXTERNO_O_TP_BINGX", "Verificado en API Real"
                )
                try:
                    notificar_cierre_trade("FASE 2 MACRO", sym, "LONG", data["entry_px"], data["tp_px"], data["margen_usd"] * 0.60, "TP / Cierre en BingX", "Verificado en API", es_real=True)
                except: pass
                del st["fase2_macro_activas"][sym]

    # Verificar Fase 1 (Altcoins) que hayan sido promovidas a REAL
    for sym, data in list(st["fase1_rapidas_activas"].items()):
        if data.get("modo_ejecucion") == "REAL":
            bsym = data["bingx_sym"]
            if bsym not in syms_vivos:
                log.info(f"🔔 [CIERRE DETECTADO EN BINGX] {sym} de Fase 1 Real ya no está abierta en BingX.")
                registrar_operacion_cerrada(
                    "FASE1_RAPIDA", sym, "BINGX", "LONG",
                    data["entry_px"], data["tp_px"], BINGX_MARGEN_USD,
                    data["margen_usd"] * 0.45, "CIERRE_EXTERNO_O_TP_BINGX", "Verificado en API Real"
                )
                try:
                    notificar_cierre_trade("FASE 1 RÁPIDA", sym, "LONG", data["entry_px"], data["tp_px"], data["margen_usd"] * 0.45, "TP / Cierre en BingX", "Verificado en API", es_real=True)
                except: pass
                del st["fase1_rapidas_activas"][sym]

# ══════════════════════════════════════════════════════════════════
# GESTIÓN DE FASE 1: OPERACIONES RÁPIDAS (ALTCOINS)
# ══════════════════════════════════════════════════════════════════
def evaluar_y_ejecutar_fase1(st, modo, ocupados):
    pos_f1 = st["fase1_rapidas_activas"]
    recoms = st.setdefault("recomendaciones_fantasma", {})
    now_ts = time.time()
    
    # 1. Monitoreo de Salidas y Time-Stop (48h)
    for sym, pos in list(pos_f1.items()):
        px = bingx_obtener_precio(pos["bingx_sym"]) or pos["entry_px"]
        horas_vida = (now_ts - pos["ts_entry"]) / 3600.0
        es_real = pos.get("modo_ejecucion") == "REAL"
        
        # Take Profit
        if px >= pos["tp_px"]:
            log.info(f"🎯 [TAKE PROFIT F1 ALCANZADO] {sym} @ ${px:,.2f} >= TP ${pos['tp_px']:,.2f} ({'REAL' if es_real else 'FANTASMA'})")
            pnl_usd = (px - pos["entry_px"]) * pos["qty_tokens"]
            if es_real:
                bingx_cerrar_posicion_mercado(pos["bingx_sym"], "LONG", pos["qty_tokens"])
                
            registrar_operacion_cerrada(
                "FASE1_RAPIDA", sym, "BINGX" if es_real else "PAPER_BINGX", "LONG",
                pos["entry_px"], px, pos["margen_usd"], pnl_usd, "TAKE_PROFIT_F1", f"{horas_vida:.1f}h"
            )
            try:
                notificar_cierre_trade("FASE 1 RÁPIDA", sym, "LONG", pos["entry_px"], px, pnl_usd, "🎯 TAKE PROFIT ALCANZADO", f"{horas_vida:.1f}h", es_real=es_real)
            except: pass
            
            # Actualizar recomendación en historial
            cid = pos.get("client_order_id")
            if cid in recoms:
                recoms[cid]["estado"] = "CERRADO_TP"
                recoms[cid]["pnl_usd"] = round(pnl_usd, 2)
            del pos_f1[sym]
            continue
            
        # Stop Loss
        elif px <= pos["sl_px"]:
            log.info(f"🛑 [STOP LOSS F1 EJECUTADO] {sym} @ ${px:,.2f} <= SL ${pos['sl_px']:,.2f} ({'REAL' if es_real else 'FANTASMA'})")
            pnl_usd = (px - pos["entry_px"]) * pos["qty_tokens"]
            if es_real:
                bingx_cerrar_posicion_mercado(pos["bingx_sym"], "LONG", pos["qty_tokens"])
                
            registrar_operacion_cerrada(
                "FASE1_RAPIDA", sym, "BINGX" if es_real else "PAPER_BINGX", "LONG",
                pos["entry_px"], px, pos["margen_usd"], pnl_usd, "STOP_LOSS_F1", f"{horas_vida:.1f}h"
            )
            try:
                notificar_cierre_trade("FASE 1 RÁPIDA", sym, "LONG", pos["entry_px"], px, pnl_usd, "🛑 STOP LOSS EJECUTADO", f"{horas_vida:.1f}h", es_real=es_real)
            except: pass
            
            # 🧊 ENFRIAMIENTO ACTIVADO (24h tras Stop Loss)
            if "enfriamiento_sl" not in st: st["enfriamiento_sl"] = {}
            st["enfriamiento_sl"][sym] = now_ts + (COOLDOWN_HORAS_TRAS_SL * 3600.0)
            registrar_cooldown_senal(st, sym, now_ts, horas=COOLDOWN_HORAS_TRAS_SL)
            log.warning(f"🧊 [ENFRIAMIENTO ACTIVO] {sym} congelado por {COOLDOWN_HORAS_TRAS_SL}h tras Stop Loss.")
            
            cid = pos.get("client_order_id")
            if cid in recoms:
                recoms[cid]["estado"] = "CERRADO_SL"
                recoms[cid]["pnl_usd"] = round(pnl_usd, 2)
            del pos_f1[sym]
            continue

        # Time-Stop 48h
        elif horas_vida >= pos.get("max_horas", 48):
            log.info(f"⏰ [TIME STOP 48H F1] {sym} cumplió {horas_vida:.1f}h. Cerrando.")
            pnl_usd = (px - pos["entry_px"]) * pos["qty_tokens"]
            if es_real:
                bingx_cerrar_posicion_mercado(pos["bingx_sym"], "LONG", pos["qty_tokens"])
            registrar_operacion_cerrada(
                "FASE1_RAPIDA", sym, "BINGX" if es_real else "PAPER_BINGX", "LONG",
                pos["entry_px"], px, pos["margen_usd"], pnl_usd, "TIME_STOP_48H", f"{horas_vida:.1f}h"
            )
            del pos_f1[sym]
            continue

    # 2. Evaluación de Nuevas Entradas (Si ranuras libres < 3)
    candidatos_f1 = []
    for cfg in UNIVERSO_FASE1:
        sym = cfg["sym"]
        bloqueado, motivo = esta_en_cooldown(st, sym, now_ts)
        if sym in pos_f1 or sym in ocupados or bloqueado:
            continue
        adn = calcular_adn_activo(sym, cfg["bingx_sym"], "CRIPTO")
        adn["cfg"] = cfg
        candidatos_f1.append(adn)
        
    candidatos_f1.sort(key=lambda x: x["score"], reverse=True)
    st["radar_top3_fase1"] = candidatos_f1[:3]
    
    # Abrir recomendación en Modo Fantasma por defecto si hay cupo disponible
    cupo_disponible = BINGX_F1_MAX_POS - len(pos_f1)
    if cupo_disponible > 0:
        for cand in candidatos_f1:
            if cupo_disponible <= 0: break
            if cand["gatillo_valido"]:
                sym = cand["sym"]
                cfg = cand["cfg"]
                px = cand["precio"]
                if px <= 0: continue
                
                bloqueado, _ = esta_en_cooldown(st, sym, now_ts)
                if bloqueado: continue

                qty = ajustar_cantidad_bingx(BINGX_MARGEN_USD, BINGX_LEVERAGE, px, cfg["step_qty"], cfg["min_qty"])
                tp = round(px * (1.0 + cfg["tp_pct"]), cfg["price_prec"])
                sl = round(px * (1.0 - cfg["sl_pct"]), cfg["price_prec"])
                cid = f"FANTASMA_F1_{sym}_{int(now_ts)}"
                
                # Candado de Cooldown inmediato
                registrar_cooldown_senal(st, sym, now_ts, horas=COOLDOWN_SENAL_HORAS)
                
                log.info(f"👻 [RECOMENDACIÓN FANTASMA FASE 1] {sym} @ ${px} | Qty: {qty} | TP: ${tp} | SL: ${sl} | Score: {cand['score']}")
                
                # Despachar Alerta a Telegram
                try:
                    notificar_alerta_fantasma(
                        sym=sym, fase="1", tipo="CRIPTO", side="LONG",
                        entry_px=px, tp_px=tp, sl_px=sl,
                        tp_pct=cfg["tp_pct"], sl_pct=cfg["sl_pct"],
                        score=cand["score"], qty=qty,
                        rsi=cand.get("rsi_1h", 0.0), squeeze=cand.get("macd_estado", "")
                    )
                except Exception as e:
                    log.warning(f"Aviso enviando alerta telegram F1: {e}")

                pos_f1[sym] = {
                    "sym": sym, "bingx_sym": cfg["bingx_sym"], "side": "LONG",
                    "entry_px": px, "tp_px": tp, "sl_px": sl, "qty_tokens": qty,
                    "margen_usd": BINGX_MARGEN_USD, "leverage": BINGX_LEVERAGE,
                    "ts_entry": now_ts, "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "max_horas": cfg.get("max_horas", 48), "client_order_id": cid,
                    "modo_ejecucion": "FANTASMA",
                    "fase": "FASE1_ALTCOINS",
                    "score_adn": cand["score"]
                }
                
                recoms[cid] = {
                    "sym": sym, "bingx_sym": cfg["bingx_sym"], "fase": "FASE1_ALTCOINS",
                    "side": "LONG", "entry_px": px, "tp_px": tp, "sl_px": sl,
                    "qty_tokens": qty, "margen_usd": BINGX_MARGEN_USD, "leverage": BINGX_LEVERAGE,
                    "score": cand["score"], "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "estado": "FANTASMA", "ts": now_ts, "client_order_id": cid
                }
                cupo_disponible -= 1

# ══════════════════════════════════════════════════════════════════
# GESTIÓN DE FASE 2: OPERACIONES MACRO (WALL STREET)
# ══════════════════════════════════════════════════════════════════
def evaluar_y_ejecutar_fase2(st, modo, ocupados):
    pos_f2 = st["fase2_macro_activas"]
    recoms = st.setdefault("recomendaciones_fantasma", {})
    now_ts = time.time()
    
    # 1. Monitoreo de Salidas y Checkpoint DÍA 10 y DÍA 25
    for sym, pos in list(pos_f2.items()):
        px = bingx_obtener_precio(pos["bingx_sym"]) or pos["entry_px"]
        dias_vida = (now_ts - pos["ts_entry"]) / 86400.0
        es_real = pos.get("modo_ejecucion") == "REAL"
        
        # Take Profit
        if px >= pos["tp_px"]:
            log.info(f"🏆 [TAKE PROFIT MACRO F2] {sym} @ ${px:,.2f} >= TP ${pos['tp_px']:,.2f} ({'REAL' if es_real else 'FANTASMA'})")
            if es_real:
                bingx_cerrar_posicion_mercado(pos["bingx_sym"], "LONG", pos["qty_tokens"])
                
            pnl_usd = (px - pos["entry_px"]) * pos["qty_tokens"]
            registrar_operacion_cerrada(
                "FASE2_MACRO", sym, "BINGX" if es_real else "PAPER_BINGX", "LONG",
                pos["entry_px"], px, pos["margen_usd"], pnl_usd, "TAKE_PROFIT_F2_MACRO", f"{dias_vida:.1f} días"
            )
            try:
                notificar_cierre_trade("FASE 2 WALL STREET", sym, "LONG", pos["entry_px"], px, pnl_usd, "🏆 TAKE PROFIT MACRO", f"{dias_vida:.1f} días", es_real=es_real)
            except: pass
            
            cid = pos.get("client_order_id")
            if cid in recoms:
                recoms[cid]["estado"] = "CERRADO_TP"
                recoms[cid]["pnl_usd"] = round(pnl_usd, 2)
            del pos_f2[sym]
            continue
            
        # Stop Loss
        elif px <= pos["sl_px"]:
            log.info(f"🛑 [STOP LOSS MACRO F2] {sym} @ ${px:,.2f} <= SL ${pos['sl_px']:,.2f} ({'REAL' if es_real else 'FANTASMA'})")
            if es_real:
                bingx_cerrar_posicion_mercado(pos["bingx_sym"], "LONG", pos["qty_tokens"])
                
            pnl_usd = (px - pos["entry_px"]) * pos["qty_tokens"]
            registrar_operacion_cerrada(
                "FASE2_MACRO", sym, "BINGX" if es_real else "PAPER_BINGX", "LONG",
                pos["entry_px"], px, pos["margen_usd"], pnl_usd, "STOP_LOSS_F2", f"{dias_vida:.1f} días"
            )
            try:
                notificar_cierre_trade("FASE 2 WALL STREET", sym, "LONG", pos["entry_px"], px, pnl_usd, "🛑 STOP LOSS MACRO", f"{dias_vida:.1f} días", es_real=es_real)
            except: pass
            
            if "enfriamiento_sl" not in st: st["enfriamiento_sl"] = {}
            st["enfriamiento_sl"][sym] = now_ts + (COOLDOWN_HORAS_TRAS_SL * 3600.0)
            registrar_cooldown_senal(st, sym, now_ts, horas=COOLDOWN_HORAS_TRAS_SL)
            log.warning(f"🧊 [ENFRIAMIENTO ACTIVO] {sym} congelado por {COOLDOWN_HORAS_TRAS_SL}h tras Stop Loss.")
            
            cid = pos.get("client_order_id")
            if cid in recoms:
                recoms[cid]["estado"] = "CERRADO_SL"
                recoms[cid]["pnl_usd"] = round(pnl_usd, 2)
            del pos_f2[sym]
            continue
            
        # Checkpoint DÍA 10
        elif dias_vida >= 10.0 and not pos.get("alerta_dia_10_revisada", False):
            pos["alerta_dia_10_revisada"] = True
            ganancia_actual_pct = ((px - pos["entry_px"]) / pos["entry_px"]) * 100.0
            log.warning(f"⚠️ [CHECKPOINT DÍA 10 EN {sym}] Días: {dias_vida:.1f} | Rendimiento: {ganancia_actual_pct:+.2f}%")
            
            if ganancia_actual_pct < 1.0:
                log.info(f"🔒 [DÍA 10 SIN FUERZA EN {sym}] Abortando posición para liberar ranura.")
                if es_real:
                    bingx_cerrar_posicion_mercado(pos["bingx_sym"], "LONG", pos["qty_tokens"])
                pnl_usd = (px - pos["entry_px"]) * pos["qty_tokens"]
                registrar_operacion_cerrada(
                    "FASE2_MACRO", sym, "BINGX" if es_real else "PAPER_BINGX", "LONG",
                    pos["entry_px"], px, pos["margen_usd"], pnl_usd, "RECORTE_ESTANCAMIENTO_DIA_10", f"{dias_vida:.1f} días"
                )
                del pos_f2[sym]
                continue
                
        # Time-Stop DÍA 25 Final
        elif dias_vida >= pos.get("max_dias", 25):
            log.info(f"🏁 [VENCIMIENTO 25 DÍAS F2] {sym} alcanzó límite de 25 días. Cerrando.")
            if es_real:
                bingx_cerrar_posicion_mercado(pos["bingx_sym"], "LONG", pos["qty_tokens"])
            pnl_usd = (px - pos["entry_px"]) * pos["qty_tokens"]
            registrar_operacion_cerrada(
                "FASE2_MACRO", sym, "BINGX" if es_real else "PAPER_BINGX", "LONG",
                pos["entry_px"], px, pos["margen_usd"], pnl_usd, "EXPIRACION_25_DIAS", f"{dias_vida:.1f} días"
            )
            del pos_f2[sym]
            continue

    # 2. Evaluación de Nuevas Entradas Macro
    candidatos_f2 = []
    for cfg in UNIVERSO_FASE2:
        sym = cfg["sym"]
        bloqueado, motivo = esta_en_cooldown(st, sym, now_ts)
        if sym in pos_f2 or sym in ocupados or bloqueado:
            continue
        adn = calcular_adn_activo(sym, cfg["bingx_sym"], "ACCION")
        adn["cfg"] = cfg
        candidatos_f2.append(adn)
        
    candidatos_f2.sort(key=lambda x: x["score"], reverse=True)
    st["radar_top3_fase2"] = candidatos_f2[:3]
    
    cupo_disponible = BINGX_F2_MAX_POS - len(pos_f2)
    if cupo_disponible > 0:
        for cand in candidatos_f2:
            if cupo_disponible <= 0: break
            if cand["gatillo_valido"]:
                sym = cand["sym"]
                cfg = cand["cfg"]
                px = cand["precio"]
                if px <= 0: continue
                
                bloqueado, _ = esta_en_cooldown(st, sym, now_ts)
                if bloqueado: continue

                qty = ajustar_cantidad_bingx(BINGX_MARGEN_USD, BINGX_LEVERAGE, px, cfg["step_qty"], cfg["min_qty"])
                tp = round(px * (1.0 + cfg["tp_pct"]), cfg["price_prec"])
                sl = round(px * (1.0 - cfg["sl_pct"]), cfg["price_prec"])
                cid = f"FANTASMA_F2_{sym}_{int(now_ts)}"
                
                registrar_cooldown_senal(st, sym, now_ts, horas=COOLDOWN_SENAL_HORAS)
                
                log.info(f"👻 [RECOMENDACIÓN FANTASMA FASE 2] {sym} @ ${px} | Qty: {qty} | TP: ${tp} | SL: ${sl} | Score: {cand['score']}")
                
                try:
                    notificar_alerta_fantasma(
                        sym=sym, fase="2", tipo="ACCION", side="LONG",
                        entry_px=px, tp_px=tp, sl_px=sl,
                        tp_pct=cfg["tp_pct"], sl_pct=cfg["sl_pct"],
                        score=cand["score"], qty=qty,
                        rsi=cand.get("rsi_1h", 0.0), squeeze=cand.get("macd_estado", "")
                    )
                except Exception as e:
                    log.warning(f"Aviso enviando alerta telegram F2: {e}")

                pos_f2[sym] = {
                    "sym": sym, "bingx_sym": cfg["bingx_sym"], "side": "LONG",
                    "entry_px": px, "tp_px": tp, "sl_px": sl, "qty_tokens": qty,
                    "margen_usd": BINGX_MARGEN_USD, "leverage": BINGX_LEVERAGE,
                    "ts_entry": now_ts, "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "max_dias": cfg.get("max_dias", 25), "client_order_id": cid,
                    "alerta_dia_10_revisada": False,
                    "modo_ejecucion": "FANTASMA",
                    "fase": "FASE2_WALLSTREET",
                    "score_adn": cand["score"]
                }
                
                recoms[cid] = {
                    "sym": sym, "bingx_sym": cfg["bingx_sym"], "fase": "FASE2_WALLSTREET",
                    "side": "LONG", "entry_px": px, "tp_px": tp, "sl_px": sl,
                    "qty_tokens": qty, "margen_usd": BINGX_MARGEN_USD, "leverage": BINGX_LEVERAGE,
                    "score": cand["score"], "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "estado": "FANTASMA", "ts": now_ts, "client_order_id": cid
                }
                cupo_disponible -= 1

# ══════════════════════════════════════════════════════════════════
# GESTIÓN BINANCE CROSS MARGIN 5X (EXCLUSIVO BITCOIN)
# ══════════════════════════════════════════════════════════════════
def evaluar_y_ejecutar_binance_btc(st, modo_btc="REAL"):
    balas = st["binance_btc_balas"]
    now_ts = time.time()
    
    adn_btc = calcular_adn_activo("BTC", "BTC-USDT", "CRIPTO")
    px_btc = adn_btc["precio"]
    if px_btc <= 0: return

    # Monitoreo de Venta en TP (+4.0%)
    if len(balas) > 0 and st["btc_costo_promedio"] > 0:
        costo_prom = st["btc_costo_promedio"]
        tp_target = costo_prom * (1.0 + UNIVERSO_BTC_BINANCE["tp_pct"])
        
        if px_btc >= tp_target:
            log.info(f"🏆 [BINANCE BTC TAKE PROFIT] BTC @ ${px_btc:,.2f} >= TP ${tp_target:,.2f} ({'REAL' if modo_btc == 'REAL' else 'FANTASMA'}).")
            if modo_btc == "REAL":
                r_ven = binance_margin_vender_btc(st["btc_acumulado_agente"], f"AUTO_BIN_TP_{int(now_ts)}")
                log.info(f"✅ Venta ejecutada en Binance Margin: {r_ven}")
                
            pnl_usd = (px_btc - costo_prom) * st["btc_acumulado_agente"]
            margen_total = len(balas) * BINANCE_MARGEN_USD
            registrar_operacion_cerrada(
                "BINANCE_BTC_MARGIN", "BTC", "BINANCE" if modo_btc == "REAL" else "PAPER_BINANCE", "BUY_MARGIN",
                costo_prom, px_btc, margen_total, pnl_usd, "TAKE_PROFIT_RECICLADO_BALAS", "Ciclo Binance 5X"
            )
            try:
                notificar_cierre_trade("BINANCE BTC 5X", "BTC", "BUY_MARGIN", costo_prom, px_btc, pnl_usd, "🎯 TAKE PROFIT +4% (Reciclaje de Balas)", "Ciclo Binance 5X", es_real=(modo_btc == "REAL"))
            except: pass
            
            st["binance_btc_balas"] = []
            st["btc_acumulado_agente"] = 0.0
            st["btc_costo_promedio"] = 0.0
            return

    # Compra de Balas (Máximo 3 Balas)
    if len(balas) < BINANCE_BTC_MAX_BALAS:
        if adn_btc["gatillo_valido"]:
            permitido = True
            if len(balas) > 0:
                ultima_px = balas[-1]["precio"]
                if px_btc > ultima_px * 0.985:
                    permitido = False
                    
            if permitido:
                num_bala = len(balas) + 1
                qty_btc_bala = (BINANCE_MARGEN_USD * BINANCE_LEVERAGE) / px_btc
                
                if modo_btc == "REAL":
                    log.info(f"💎 [DISPARO BALA REAL {num_bala}/3 EN BINANCE BTC] Precio: ${px_btc:,.2f} | Monto: ${BINANCE_MARGEN_USD} USD @ 5X")
                    r_ord = binance_margin_comprar_btc(BINANCE_MARGEN_USD, f"AUTO_BIN_B{num_bala}_{int(now_ts)}")
                    log.info(f"✅ Respuesta compra Binance Margin: {r_ord}")
                    try:
                        notificar_disparo_binance_btc(num_bala, px_btc, BINANCE_MARGEN_USD, qty_btc_bala, es_real=True)
                    except: pass
                else:
                    log.info(f"👻 [DISPARO BALA FANTASMA {num_bala}/3 EN BINANCE BTC] Precio: ${px_btc:,.2f} | Monto: ${BINANCE_MARGEN_USD} USD @ 5X")
                    try:
                        notificar_disparo_binance_btc(num_bala, px_btc, BINANCE_MARGEN_USD, qty_btc_bala, es_real=False)
                    except: pass
                    
                balas.append({
                    "bala_num": num_bala,
                    "precio": px_btc,
                    "monto_usd": BINANCE_MARGEN_USD,
                    "qty_btc": qty_btc_bala,
                    "modo": modo_btc,
                    "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                
                total_btc = sum(b["qty_btc"] for b in balas)
                costo_total = sum(b["qty_btc"] * b["precio"] for b in balas)
                st["btc_acumulado_agente"] = total_btc
                st["btc_costo_promedio"] = round(costo_total / total_btc, 2)
                log.info(f"✅ Nuevo Costo Promedio Agente BTC: ${st['btc_costo_promedio']:,.2f} (Total Balas: {len(balas)}/3 | Modo: {modo_btc})")

# ══════════════════════════════════════════════════════════════════
# BUCLE PRINCIPAL DEL MEGA-AGENTE
# ══════════════════════════════════════════════════════════════════
def ciclo_operativo_autonomo():
    log.info("=" * 75)
    log.info("👑 INICIANDO MOTOR AUTÓNOMO: MEGA-AGENTE ADN CUÁNTICO (PILOTO AUTOMÁTICO)")
    log.info(f"⏰ Hora de Inicio: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("👻 FASE 1 & 2 EN MODO FANTASMA (BINGX) | 🟢 BINANCE MARGIN BTC EN MODO REAL")
    log.info(f"🛡️ Blindaje de Respeto Activado (MSFT, Cerebro 1 Blue Chips y Cerebro 3 Trifecta Intocables)")
    log.info("=" * 75)
    
    while True:
        try:
            modos = obtener_modos_operativos()
            st = leer_estado_agente()
            ocupados = activos_ocupados_por_otros_cerebros()
            
            # Sincronización viva segura
            sincronizar_posiciones_reales_bingx(st, modos["fase2"])
            
            # 1. Ejecutar Fase 1 (Altcoins Rápidas) en su modo (FANTASMA)
            evaluar_y_ejecutar_fase1(st, modos["fase1"], ocupados)
            
            # 2. Ejecutar Fase 2 (Wall Street Macro) en su modo (FANTASMA)
            evaluar_y_ejecutar_fase2(st, modos["fase2"], ocupados)
            
            # 3. Ejecutar Binance Margin (BTC Exclusivo) en su modo (REAL)
            evaluar_y_ejecutar_binance_btc(st, modos["binance_btc"])
            
            guardar_estado_agente(st)
            
        except Exception as e:
            log.error(f"Error en bucle operativo: {e}", exc_info=True)
            
        time.sleep(35)

if __name__ == "__main__":
    ciclo_operativo_autonomo()
