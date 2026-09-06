# -*- coding: utf-8 -*-
"""
👑 CEREBRO SUPREMO: MEGA-AGENTE ADN AUTÓNOMO (PILOTO AUTOMÁTICO)
=============================================================================
Cuotas de Operación Estrictas:
  1. BingX Futuros (Modo Cobertura):
     - Fase 1 (Rápidas / Altcoins): Máximo 3 posiciones ($10 USD @ 10X c/u).
     - Fase 2 (Macro / Wall Street): Máximo 3 posiciones ($10 USD @ 10X c/u).
  2. Binance Cross Margin 5X (Exclusivo BTC):
     - Máximo 3 compras ($10 USD @ 5X). Candado de acero: No compra más hasta vender en TP.
  3. Pacto de Respeto Absoluto:
     - No duplica activos de Cerebro 1 (Blue Chips) ni Cerebro 3 (Trifecta).
     - Solo adopta y gestiona sus propias posiciones (prefijo AUTO_).
  4. Auto-Aprendizaje y Libro Contable ($ USD PnL).
=============================================================================
"""
import os, sys, time, json, datetime, math, logging

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
    bingx_obtener_posiciones_activas,
    binance_margin_account_info,
    binance_margin_comprar_btc,
    binance_margin_vender_btc
)
from motor_adn_quant import calcular_adn_activo
from aprendizaje_ledger import registrar_operacion_cerrada, cargar_json, guardar_json

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

def obtener_modo_operativo():
    cfg = cargar_json(CONFIG_FILE, {"modo": "FANTASMA"}) # Inicia en modo seguro
    return cfg.get("modo", "FANTASMA").upper()

def leer_estado_agente():
    return cargar_json(ESTADO_FILE, {
        "fase1_rapidas_activas": {},  # max 3
        "fase2_macro_activas": {},    # max 3
        "binance_btc_balas": [],      # max 3
        "btc_acumulado_agente": 0.0,
        "btc_costo_promedio": 0.0,
        "radar_top3_fase1": [],
        "radar_top3_fase2": [],
        "enfriamiento_sl": {},        # {sym: ts_expira} -> Bloqueo anti-venganza si pierde
        "ultima_actualizacion": datetime.datetime.now().isoformat()
    })

def guardar_estado_agente(st):
    st["ultima_actualizacion"] = datetime.datetime.now().isoformat()
    guardar_json(ESTADO_FILE, st)

def activos_ocupados_por_otros_cerebros():
    """
    Lee los estados locales y las posiciones reales en BingX para:
    1. Proteger sagradamente el SHORT de MSFT (NUNCA se toca, pero si da LONG SI se puede operar).
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
        
    # 3. Consulta en vivo a la API de BingX
    try:
        live_positions = bingx_obtener_posiciones_activas()
        for p in live_positions:
            amt = float(p.get("positionAmt", 0))
            if amt != 0:
                bsym = p.get("symbol", "")
                pside = p.get("positionSide", "").upper()
                
                # REGLA SAGRADA MSFT:
                # Si es MSFT SHORT, es intocable y sagrado.
                # Pero NO bloquea operar MSFT en LONG si el sistema detecta señal de compra.
                if "MSFT" in bsym:
                    if pside == "SHORT":
                        # El SHORT de MSFT existe pero NO agregamos MSFT a ocupados para LONG
                        continue
                    elif pside == "LONG":
                        # Si ya tiene un LONG abierto de MSFT, entonces sí está ocupado el cupo LONG
                        ocupados.add("MSFT")
                
                # Mapear símbolos comunes
                if "ETH" in bsym and pside == "LONG":
                    ocupados.add("ETH")
                elif "BNB" in bsym and pside == "LONG":
                    ocupados.add("BNB")
    except Exception as e:
        log.warning(f"Aviso consultando posiciones vivas en BingX para ocupados: {e}")
        
    return ocupados

def sincronizar_posiciones_reales_bingx(st, modo):
    """
    Audita en BingX las posiciones vivas. Si alguna cerró por TP/SL externo, la liquida en el estado.
    """
    if modo != "REAL": return
    try:
        live = bingx_obtener_posiciones_activas()
        syms_vivos = {p.get("symbol") for p in live if float(p.get("positionAmt", 0)) != 0}
        
        # Nota: Fase 1 (Altcoins) se gestiona 100% en Paper Trading virtual por lo que no depende de posiciones de BingX.


        # Verificar Fase 2
        for sym, data in list(st["fase2_macro_activas"].items()):
            bsym = data["bingx_sym"]
            if bsym not in syms_vivos:
                log.info(f"🔔 [CIERRE DETECTADO EN BINGX] {sym} de Fase 2 ya no está abierta en BingX.")
                registrar_operacion_cerrada(
                    "FASE2_MACRO", sym, "BINGX", "LONG",
                    data["entry_px"], data["tp_px"], BINGX_MARGEN_USD,
                    data["margen_usd"] * 0.60, "CIERRE_EXTERNO_O_TP_BINGX", "Verificado en API"
                )
                del st["fase2_macro_activas"][sym]
    except Exception as e:
        log.warning(f"Error sincronizando posiciones de BingX: {e}")

# ══════════════════════════════════════════════════════════════════
# GESTIÓN DE FASE 1: OPERACIONES RÁPIDAS (ALTCOINS)
# ══════════════════════════════════════════════════════════════════
def evaluar_y_ejecutar_fase1(st, modo, ocupados):
    pos_f1 = st["fase1_rapidas_activas"]
    now_ts = time.time()
    
    # 1. Monitoreo de Salidas y Time-Stop (48h)
    for sym, pos in list(pos_f1.items()):
        px = bingx_obtener_precio(pos["bingx_sym"]) or pos["entry_px"]
        horas_vida = (now_ts - pos["ts_entry"]) / 3600.0
        
        # Take Profit
        if px >= pos["tp_px"]:
            log.info(f"🎯 [TAKE PROFIT F1 ALCANZADO (PAPER)] {sym} @ ${px:,.2f} >= TP ${pos['tp_px']:,.2f}")
            pnl_usd = (px - pos["entry_px"]) * pos["qty_tokens"]
            registrar_operacion_cerrada(
                "FASE1_RAPIDA", sym, "PAPER_BINGX", "LONG", pos["entry_px"], px,
                pos["margen_usd"], pnl_usd, "TAKE_PROFIT_F1_PAPER", f"{horas_vida:.1f}h"
            )
            del pos_f1[sym]
            continue
            
        # Stop Loss
        elif px <= pos["sl_px"]:
            log.info(f"🛑 [STOP LOSS F1 EJECUTADO (PAPER)] {sym} @ ${px:,.2f} <= SL ${pos['sl_px']:,.2f}")
            pnl_usd = (px - pos["entry_px"]) * pos["qty_tokens"]
            registrar_operacion_cerrada(
                "FASE1_RAPIDA", sym, "PAPER_BINGX", "LONG", pos["entry_px"], px,
                pos["margen_usd"], pnl_usd, "STOP_LOSS_F1_PAPER", f"{horas_vida:.1f}h"
            )
            
            # 🧊 ENFRIAMIENTO ACTIVADO (Anti-Revenge Trading)
            if "enfriamiento_sl" not in st: st["enfriamiento_sl"] = {}
            st["enfriamiento_sl"][sym] = now_ts + (COOLDOWN_HORAS_TRAS_SL * 3600.0)
            log.warning(f"🧊 [ENFRIAMIENTO ACTIVO] {sym} congelado por {COOLDOWN_HORAS_TRAS_SL}h tras Stop Loss.")
            
            del pos_f1[sym]
            continue

    # Limpiar enfriamientos expirados
    enfriamiento = st.get("enfriamiento_sl", {})
    activos_congelados = {s for s, exp in list(enfriamiento.items()) if now_ts < exp}

    # 2. Evaluación de Nuevas Entradas (Si hay ranura libre < 3)
    candidatos_f1 = []
    for cfg in UNIVERSO_FASE1:
        sym = cfg["sym"]
        if sym in pos_f1 or sym in ocupados or sym in activos_congelados:
            continue
        adn = calcular_adn_activo(sym, cfg["bingx_sym"], "CRIPTO")
        adn["cfg"] = cfg
        candidatos_f1.append(adn)
        
    candidatos_f1.sort(key=lambda x: x["score"], reverse=True)
    st["radar_top3_fase1"] = candidatos_f1[:3]
    
    # Abrir solo si hay cupo disponible
    cupo_disponible = BINGX_F1_MAX_POS - len(pos_f1)
    if cupo_disponible > 0:
        for cand in candidatos_f1:
            if cupo_disponible <= 0: break
            if cand["gatillo_valido"]:
                sym = cand["sym"]
                cfg = cand["cfg"]
                px = cand["precio"]
                if px <= 0: continue
                
                qty = ajustar_cantidad_bingx(BINGX_MARGEN_USD, BINGX_LEVERAGE, px, cfg["step_qty"], cfg["min_qty"])
                tp = round(px * (1.0 + cfg["tp_pct"]), cfg["price_prec"])
                sl = round(px * (1.0 - cfg["sl_pct"]), cfg["price_prec"])
                cid = f"SIM_F1_{sym}_{int(now_ts)}"
                
                # FASE 1: 100% PAPER TRADING / FANTASMA (Laboratorio sin riesgo real de capital)
                log.info(f"👻 [SIMULACIÓN FASE 1 FANTASMA] {sym} @ ${px} | Qty: {qty} tokens | TP: ${tp} | SL: ${sl} (Sin orden real en BingX)")
                # Nunca envía orden a BingX para Fase 1: se ejecuta puramente simulada para comparar rendimientos
                        
                pos_f1[sym] = {
                    "sym": sym, "bingx_sym": cfg["bingx_sym"], "side": "LONG",
                    "entry_px": px, "tp_px": tp, "sl_px": sl, "qty_tokens": qty,
                    "margen_usd": BINGX_MARGEN_USD, "leverage": BINGX_LEVERAGE,
                    "ts_entry": now_ts, "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "max_horas": cfg.get("max_horas", 48), "client_order_id": cid
                }
                cupo_disponible -= 1

# ══════════════════════════════════════════════════════════════════
# GESTIÓN DE FASE 2: OPERACIONES MACRO (WALL STREET)
# ══════════════════════════════════════════════════════════════════
def evaluar_y_ejecutar_fase2(st, modo, ocupados):
    pos_f2 = st["fase2_macro_activas"]
    now_ts = time.time()
    
    # 1. Monitoreo de Salidas y Chequeo de DÍA 10 y DÍA 25
    for sym, pos in list(pos_f2.items()):
        px = bingx_obtener_precio(pos["bingx_sym"]) or pos["entry_px"]
        dias_vida = (now_ts - pos["ts_entry"]) / 86400.0
        
        # Take Profit
        if px >= pos["tp_px"]:
            log.info(f"🏆 [TAKE PROFIT MACRO F2 ALCANZADO] {sym} @ ${px:,.2f} >= TP ${pos['tp_px']:,.2f}")
            if modo == "REAL":
                bingx_cerrar_posicion_mercado(pos["bingx_sym"], "LONG", pos["qty_tokens"])
                
            pnl_usd = (px - pos["entry_px"]) * pos["qty_tokens"]
            registrar_operacion_cerrada(
                "FASE2_MACRO", sym, "BINGX", "LONG", pos["entry_px"], px,
                pos["margen_usd"], pnl_usd, "TAKE_PROFIT_F2_MACRO", f"{dias_vida:.1f} días"
            )
            del pos_f2[sym]
            continue
            
        # Stop Loss
        elif px <= pos["sl_px"]:
            log.info(f"🛑 [STOP LOSS MACRO F2] {sym} @ ${px:,.2f} <= SL ${pos['sl_px']:,.2f}")
            if modo == "REAL":
                bingx_cerrar_posicion_mercado(pos["bingx_sym"], "LONG", pos["qty_tokens"])
                
            pnl_usd = (px - pos["entry_px"]) * pos["qty_tokens"]
            registrar_operacion_cerrada(
                "FASE2_MACRO", sym, "BINGX", "LONG", pos["entry_px"], px,
                pos["margen_usd"], pnl_usd, "STOP_LOSS_F2", f"{dias_vida:.1f} días"
            )
            
            # 🧊 ENFRIAMIENTO ACTIVADO (Anti-Revenge Trading en Wall Street)
            if "enfriamiento_sl" not in st: st["enfriamiento_sl"] = {}
            st["enfriamiento_sl"][sym] = now_ts + (COOLDOWN_HORAS_TRAS_SL * 3600.0)
            log.warning(f"🧊 [ENFRIAMIENTO ACTIVO] {sym} congelado por {COOLDOWN_HORAS_TRAS_SL}h tras Stop Loss.")
            
            del pos_f2[sym]
            continue
            
        # Checkpoint DÍA 10 (El seguro táctico contra estancamiento)
        elif dias_vida >= 10.0 and not pos.get("alerta_dia_10_revisada", False):
            pos["alerta_dia_10_revisada"] = True
            ganancia_actual_pct = ((px - pos["entry_px"]) / pos["entry_px"]) * 100.0
            log.warning(f"⚠️ [CHECKPOINT DÍA 10 EN {sym}] Días: {dias_vida:.1f} | Rendimiento: {ganancia_actual_pct:+.2f}%")
            
            # Si a los 10 días está en negativo o plano (< +1.0%), se activa recorte de riesgo
            if ganancia_actual_pct < 1.0:
                log.info(f"🔒 [DÍA 10 SIN FUERZA EN {sym}] Abortando posición para liberar ranura.")
                if modo == "REAL":
                    bingx_cerrar_posicion_mercado(pos["bingx_sym"], "LONG", pos["qty_tokens"])
                pnl_usd = (px - pos["entry_px"]) * pos["qty_tokens"]
                registrar_operacion_cerrada(
                    "FASE2_MACRO", sym, "BINGX", "LONG", pos["entry_px"], px,
                    pos["margen_usd"], pnl_usd, "RECORTE_ESTANCAMIENTO_DIA_10", f"{dias_vida:.1f} días"
                )
                del pos_f2[sym]
                continue
                
        # Time-Stop DÍA 25 Final
        elif dias_vida >= pos.get("max_dias", 25):
            log.info(f"🏁 [VENCIMIENTO 25 DÍAS F2] {sym} alcanzó límite de 25 días. Cerrando.")
            if modo == "REAL":
                bingx_cerrar_posicion_mercado(pos["bingx_sym"], "LONG", pos["qty_tokens"])
            pnl_usd = (px - pos["entry_px"]) * pos["qty_tokens"]
            registrar_operacion_cerrada(
                "FASE2_MACRO", sym, "BINGX", "LONG", pos["entry_px"], px,
                pos["margen_usd"], pnl_usd, "EXPIRACION_25_DIAS", f"{dias_vida:.1f} días"
            )
            del pos_f2[sym]
            continue

    # Limpiar enfriamientos expirados para Fase 2
    enfriamiento_f2 = st.get("enfriamiento_sl", {})
    activos_congelados_f2 = {s for s, exp in list(enfriamiento_f2.items()) if now_ts < exp}

    # 2. Evaluación de Nuevas Entradas Macro (Si cupo < 3)
    candidatos_f2 = []
    for cfg in UNIVERSO_FASE2:
        sym = cfg["sym"]
        if sym in pos_f2 or sym in ocupados or sym in activos_congelados_f2:
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
                
                qty = ajustar_cantidad_bingx(BINGX_MARGEN_USD, BINGX_LEVERAGE, px, cfg["step_qty"], cfg["min_qty"])
                tp = round(px * (1.0 + cfg["tp_pct"]), cfg["price_prec"])
                sl = round(px * (1.0 - cfg["sl_pct"]), cfg["price_prec"])
                cid = f"AUTO_F2_{sym}_{int(now_ts)}"
                
                log.info(f"🏛️ [DISPARO FASE 2 MACRO] {sym} @ ${px} | Qty: {qty} tokens | TP: ${tp} | SL: ${sl} | Modo: {modo}")
                if modo == "REAL":
                    bingx_establecer_apalancamiento(cfg["bingx_sym"], BINGX_LEVERAGE, "LONG")
                    r_ord = bingx_abrir_posicion_mercado(cfg["bingx_sym"], "LONG", qty, cid)
                    if r_ord.get("code") != 0:
                        log.error(f"Error abriendo {sym} en BingX: {r_ord.get('msg')}")
                        continue
                        
                pos_f2[sym] = {
                    "sym": sym, "bingx_sym": cfg["bingx_sym"], "side": "LONG",
                    "entry_px": px, "tp_px": tp, "sl_px": sl, "qty_tokens": qty,
                    "margen_usd": BINGX_MARGEN_USD, "leverage": BINGX_LEVERAGE,
                    "ts_entry": now_ts, "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "max_dias": cfg.get("max_dias", 25), "client_order_id": cid,
                    "alerta_dia_10_revisada": False
                }
                cupo_disponible -= 1

# ══════════════════════════════════════════════════════════════════
# GESTIÓN BINANCE CROSS MARGIN 5X (EXCLUSIVO BITCOIN)
# ══════════════════════════════════════════════════════════════════
def evaluar_y_ejecutar_binance_btc(st, modo):
    balas = st["binance_btc_balas"]
    now_ts = time.time()
    
    # 1. Obtener precio actual de BTC
    adn_btc = calcular_adn_activo("BTC", "BTC-USDT", "CRIPTO")
    px_btc = adn_btc["precio"]
    if px_btc <= 0: return

    # 2. Monitoreo de Venta en TP para reciclar balas (Filosofía Acumulador Ganar-Ganar)
    if len(balas) > 0 and st["btc_costo_promedio"] > 0:
        costo_prom = st["btc_costo_promedio"]
        tp_target = costo_prom * (1.0 + UNIVERSO_BTC_BINANCE["tp_pct"])
        
        # Take Profit Alcanzado en Binance (Venta exclusiva en beneficio)
        if px_btc >= tp_target:
            log.info(f"🏆 [BINANCE BTC TAKE PROFIT] BTC @ ${px_btc:,.2f} >= TP ${tp_target:,.2f}. VENDIENDO PARA RECICLAR BALAS.")
            if modo == "REAL":
                binance_margin_vender_btc(st["btc_acumulado_agente"], f"AUTO_BIN_TP_{int(now_ts)}")
                
            pnl_usd = (px_btc - costo_prom) * st["btc_acumulado_agente"]
            margen_total = len(balas) * BINANCE_MARGEN_USD
            registrar_operacion_cerrada(
                "BINANCE_BTC_MARGIN", "BTC", "BINANCE", "BUY_MARGIN",
                costo_prom, px_btc, margen_total, pnl_usd, "TAKE_PROFIT_RECICLADO_BALAS", "Ciclo Binance"
            )
            # Candado liberado: Se reinician las 3 balas tras cobrar
            st["binance_btc_balas"] = []
            st["btc_acumulado_agente"] = 0.0
            st["btc_costo_promedio"] = 0.0
            return

    # 3. Compra de Balas (Máximo 3 Balas de por vida hasta que venda en TP)
    if len(balas) < BINANCE_BTC_MAX_BALAS:
        # Solo dispara si el ADN de BTC está en zona verde/compresión
        if adn_btc["gatillo_valido"]:
            # Verificar si no está demasiado cerca de la bala anterior (mínimo 1.5% de caída)
            permitido = True
            if len(balas) > 0:
                ultima_px = balas[-1]["precio"]
                if px_btc > ultima_px * 0.985: # Debe haber caído al menos 1.5% para recargar
                    permitido = False
                    
            if permitido:
                num_bala = len(balas) + 1
                log.info(f"💎 [DISPARO BALA {num_bala}/3 EN BINANCE BTC] Precio: ${px_btc:,.2f} | Monto: ${BINANCE_MARGEN_USD} USD @ 5X")
                
                qty_btc_bala = (BINANCE_MARGEN_USD * BINANCE_LEVERAGE) / px_btc
                if modo == "REAL":
                    binance_margin_comprar_btc(BINANCE_MARGEN_USD, f"AUTO_BIN_B{num_bala}_{int(now_ts)}")
                    
                balas.append({
                    "bala_num": num_bala,
                    "precio": px_btc,
                    "monto_usd": BINANCE_MARGEN_USD,
                    "qty_btc": qty_btc_bala,
                    "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                
                # Recalcular Costo Promedio y BTC total del agente
                total_btc = sum(b["qty_btc"] for b in balas)
                costo_total = sum(b["qty_btc"] * b["precio"] for b in balas)
                st["btc_acumulado_agente"] = total_btc
                st["btc_costo_promedio"] = round(costo_total / total_btc, 2)
                log.info(f"✅ Nuevo Costo Promedio Agente BTC: ${st['btc_costo_promedio']:,.2f} (Total Balas: {len(balas)}/3)")
    else:
        # Candado de Acero Activo
        pass

# ══════════════════════════════════════════════════════════════════
# BUCLE PRINCIPAL DEL MEGA-AGENTE
# ══════════════════════════════════════════════════════════════════
def ciclo_operativo_autonomo():
    log.info("=" * 75)
    log.info("👑 INICIANDO MOTOR AUTÓNOMO: MEGA-AGENTE ADN CUÁNTICO (PILOTO AUTOMÁTICO)")
    log.info(f"⏰ Hora de Inicio: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"🛡️ Blindaje de Respeto Activado (MSFT, Cerebro 1 Blue Chips y Cerebro 3 Trifecta Intocables)")
    log.info("=" * 75)
    
    while True:
        try:
            modo = obtener_modo_operativo()
            st = leer_estado_agente()
            ocupados = activos_ocupados_por_otros_cerebros()
            
            # Sincronización viva
            sincronizar_posiciones_reales_bingx(st, modo)
            
            # 1. Ejecutar Fase 1 (Altcoins Rápidas)
            evaluar_y_ejecutar_fase1(st, modo, ocupados)
            
            # 2. Ejecutar Fase 2 (Wall Street Macro)
            evaluar_y_ejecutar_fase2(st, modo, ocupados)
            
            # 3. Ejecutar Binance Margin (BTC Exclusivo)
            evaluar_y_ejecutar_binance_btc(st, modo)
            
            guardar_estado_agente(st)
            
        except Exception as e:
            log.error(f"Error en bucle operativo: {e}")
            
        time.sleep(20)

if __name__ == "__main__":
    ciclo_operativo_autonomo()
