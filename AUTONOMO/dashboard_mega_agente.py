# -*- coding: utf-8 -*-
"""
🎛️ SALA DE MANDO: MEGA-AGENTE ADN AUTÓNOMO (PUERTO 8560)
=============================================================================
Visualiza:
  1. Fichas Interactivas de Recomendación Fantasma con botones:
     - 🟢 Pasar a REAL (Disparo directo a BingX + Alerta Telegram)
     - 👻 Dejar en FANTASMA (Seguimiento Simulado)
     - ❌ Descartar
  2. Cuotas BingX:
     - Fase 1 (Altcoins): [X/3] Ranuras ($10 @ 10X).
     - Fase 2 (Wall Street): [X/3] Ranuras ($10 @ 10X).
  3. Cuota Binance:
     - [X/3] Balas disparadas ($20 @ 5X BTC).
  4. Radar ADN Cuántico en Vivo & Candados Anti-Bucle (Cooldown 6h).
  5. Libro Mayor Contable en $ USD.
=============================================================================
"""
import streamlit as st
import os, sys, time, json, datetime, pandas as pd, numpy as np

st.set_page_config(page_title="Mega-Agente ADN Autónomo", page_icon="🧬", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROD_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, PROD_DIR)

from config_adn import CONFIG_FILE, ESTADO_FILE, BINGX_MARGEN_USD, BINGX_LEVERAGE
from conector_exchanges import bingx_obtener_precio, bingx_ejecutar_promocion_real
from aprendizaje_ledger import obtener_resumen_contable, cargar_json, guardar_json

st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 900; color: #38bdf8; margin-bottom: 5px; }
    .card-slot { background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 12px; }
    .card-ghost { background: linear-gradient(135deg, rgba(15,23,42,0.95), rgba(30,41,59,0.92)); border: 2px solid #38bdf8; border-radius: 14px; padding: 16px; margin-bottom: 14px; }
    .card-real { background: linear-gradient(135deg, rgba(6,78,59,0.3), rgba(15,23,42,0.95)); border: 2px solid #22c55e; border-radius: 14px; padding: 16px; margin-bottom: 14px; }
    .slot-empty { border: 1px dashed #64748b; background: rgba(15, 23, 42, 0.4); }
    .badge-fase1 { background: #0284c7; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.8rem; }
    .badge-fase2 { background: #7c3aed; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.8rem; }
    .badge-binance { background: #eab308; color: black; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.8rem; }
    .badge-ghost { background: rgba(56,189,248,0.2); color: #38bdf8; border: 1px solid #38bdf8; padding: 3px 8px; border-radius: 6px; font-weight: 800; font-size: 0.75rem; }
    .badge-real { background: rgba(34,197,94,0.2); color: #22c55e; border: 1px solid #22c55e; padding: 3px 8px; border-radius: 6px; font-weight: 800; font-size: 0.75rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>🧬 MEGA-AGENTE ADN: PILOTO AUTOMÁTICO BIAXIAL</div>", unsafe_allow_html=True)
st.caption("Modo Fantasma por Defecto · Alertas Telegram · Promoción Manual a Real · Puerto 8560")

# SIDEBAR: MODO Y CONTROLES
st.sidebar.header("🕹️ Centro de Control de Mando")
cfg = cargar_json(CONFIG_FILE, {"modo": "FANTASMA"})
modo_actual = cfg.get("modo", "FANTASMA").upper()

nuevo_modo = st.sidebar.radio(
    "Modo Operativo General:",
    ["FANTASMA 👻 (Laboratorio Simulado)", "REAL 🟢 (Confirmación Activa)"],
    index=0 if modo_actual == "FANTASMA" else 1
)
val_modo = "FANTASMA" if "FANTASMA" in nuevo_modo else "REAL"
if val_modo != modo_actual:
    cfg["modo"] = val_modo
    cfg["actualizado"] = datetime.datetime.now().isoformat()
    guardar_json(CONFIG_FILE, cfg)
    st.sidebar.success(f"Modo cambiado a: {val_modo}")
    st.rerun()

st.sidebar.divider()
st.sidebar.markdown("### 🛡️ Reglas de Blindaje")
st.sidebar.markdown("• **Fase 1:** Máx 3 posiciones ($10 @ 10X)")
st.sidebar.markdown("• **Fase 2:** Máx 3 posiciones ($10 @ 10X)")
st.sidebar.markdown("• **Binance BTC:** Máx 3 balas ($20 @ 5X)")
st.sidebar.markdown("• **Candado Cooldown:** 6h por señal emitida")
st.sidebar.markdown("• **Pacto de Respeto:** Cerebros 1, 2 y 3 Intocables")

if st.sidebar.button("🔄 Refrescar Telemetría", use_container_width=True, type="primary"):
    st.rerun()

# CARGAR ESTADOS Y LIBRO CONTABLE
st_agente = cargar_json(ESTADO_FILE, {
    "fase1_rapidas_activas": {}, "fase2_macro_activas": {}, "binance_btc_balas": [],
    "btc_acumulado_agente": 0.0, "btc_costo_promedio": 0.0,
    "radar_top3_fase1": [], "radar_top3_fase2": [],
    "candado_cooldown_senales": {}, "enfriamiento_sl": {}
})
resumen_pnl = obtener_resumen_contable()

# SECCIÓN 1: LIBRO MAYOR CONTABLE ($ USD EN VIVO)
col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
color_pnl = "normal" if resumen_pnl["balance_neto"] >= 0 else "inverse"
col_m1.metric("Balance Neto Histórico", f"${resumen_pnl['balance_neto']:+,.2f} USD", delta=f"{resumen_pnl['balance_neto']:+,.2f} USD", delta_color=color_pnl)
col_m2.metric("Ganancia Bruta", f"${resumen_pnl['ganancia_bruta']:,.2f} USD")
col_m3.metric("Pérdida Controlada", f"-${resumen_pnl['perdida_bruta']:,.2f} USD")
col_m4.metric("Win Rate Real", f"{resumen_pnl['win_rate']:.1f}%")
col_m5.metric("Profit Factor", f"{resumen_pnl['profit_factor']:.2f}x")

st.divider()

# SECCIÓN 2: LAS 3 FASES Y TARJETAS INTERACTIVAS DE RECOMENDACIÓN
col_f1, col_f2, col_bin = st.columns(3)

def render_tarjeta_posicion(pos, sym, fase_key, idx):
    es_real = pos.get("modo_ejecucion") == "REAL"
    px_live = bingx_obtener_precio(pos["bingx_sym"]) or pos["entry_px"]
    pnl_usd = (px_live - pos["entry_px"]) * pos["qty_tokens"]
    pnl_pct = ((px_live - pos["entry_px"]) / pos["entry_px"]) * 100.0 if pos["entry_px"] > 0 else 0.0
    color_pnl = "#22c55e" if pnl_usd >= 0 else "#ef4444"
    signo = "+" if pnl_usd >= 0 else ""
    horas = (time.time() - pos["ts_entry"]) / 3600.0

    card_class = "card-real" if es_real else "card-ghost"
    badge_estado = "<span class='badge-real'>🟢 REAL BINGX</span>" if es_real else "<span class='badge-ghost'>👻 MODO FANTASMA</span>"
    
    st.markdown(f"""
    <div class='{card_class}'>
        <div style='display:flex; justify-content:space-between; align-items:center;'>
            <div>
                <strong style='color:#38bdf8; font-size:1.15rem;'>{sym} (LONG)</strong>
                <span style='margin-left:6px;'>{badge_estado}</span>
            </div>
            <span style='font-size:0.8rem; color:#94a3b8;'>Ranura {idx+1}/3</span>
        </div>
        <div style='margin-top:8px; font-size:0.85rem; color:#cbd5e1; line-height:1.5;'>
            <b>Entrada:</b> ${pos['entry_px']:,.4f if pos['entry_px']<1 else f"{pos['entry_px']:,.2f}"} | <b>Actual:</b> ${px_live:,.4f if px_live<1 else f"{px_live:,.2f}"}<br>
            <b>🎯 TP:</b> ${pos['tp_px']:,.4f if pos['tp_px']<1 else f"{pos['tp_px']:,.2f}"} | <b>🛑 SL:</b> ${pos['sl_px']:,.4f if pos['sl_px']<1 else f"{pos['sl_px']:,.2f}"}<br>
            <b>Lote:</b> {pos['qty_tokens']} tokens ($10 @ 10X)<br>
            <b>PnL en Vivo:</b> <strong style='color:{color_pnl}; font-size:0.95rem;'>{signo}${pnl_usd:,.2f} USD ({signo}{pnl_pct:.2f}%)</strong><br>
            <b>Tiempo Activo:</b> {horas:.1f} horas
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Botones de Acción Interactiva
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if not es_real:
            if st.button(f"🟢 Pasar a REAL", key=f"btn_real_{fase_key}_{sym}", use_container_width=True, type="primary"):
                with st.spinner(f"Ejecutando {sym} en BingX..."):
                    res = bingx_ejecutar_promocion_real(
                        sym=sym, bingx_sym=pos["bingx_sym"], side=pos["side"],
                        qty=pos["qty_tokens"], tp_px=pos["tp_px"], sl_px=pos["sl_px"],
                        leverage=pos.get("leverage", BINGX_LEVERAGE)
                    )
                    if res.get("ok"):
                        st_agente[fase_key][sym]["modo_ejecucion"] = "REAL"
                        st_agente[fase_key][sym]["order_id_real"] = res.get("order_id")
                        guardar_json(ESTADO_FILE, st_agente)
                        st.toast(f"✅ {sym} promovido a REAL en BingX!", icon="🚀")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {res.get('msg')}")
        else:
            st.success("🟢 Posición Real Activa en BingX")
            
    with c_btn2:
        if st.button(f"❌ Descartar", key=f"btn_disc_{fase_key}_{sym}", use_container_width=True):
            del st_agente[fase_key][sym]
            guardar_json(ESTADO_FILE, st_agente)
            st.toast(f"🗑️ Recomendación {sym} archivada", icon="🗑️")
            time.sleep(0.5)
            st.rerun()

# ── FASE 1: BINGX RÁPIDAS (ALTCOINS) ──────────────────────────
with col_f1:
    pos_f1 = st_agente.get("fase1_rapidas_activas", {})
    st.markdown(f"### ⚡ FASE 1: ALTCOINS ({len(pos_f1)}/3 Ranuras)")
    st.caption("👻 MODO FANTASMA POR DEFECTO · Validación Cuántica 48h")
    
    syms_f1 = list(pos_f1.keys())
    for i in range(3):
        if i < len(syms_f1):
            sym = syms_f1[i]
            render_tarjeta_posicion(pos_f1[sym], sym, "fase1_rapidas_activas", i)
        else:
            st.markdown(f"""
            <div class='card-slot slot-empty'>
                <span style='color:#64748b;'>⚪ Ranura {i+1} Disponible (Buscando Squeeze + Absorción)</span>
            </div>
            """, unsafe_allow_html=True)

# ── FASE 2: BINGX MACRO (WALL STREET) ─────────────────────────
with col_f2:
    pos_f2 = st_agente.get("fase2_macro_activas", {})
    st.markdown(f"### 🏛️ FASE 2: MACRO ({len(pos_f2)}/3 Ranuras)")
    st.caption("Acciones Wall Street (Máx 25 Días · Checkpoint Día 10)")
    
    syms_f2 = list(pos_f2.keys())
    for i in range(3):
        if i < len(syms_f2):
            sym = syms_f2[i]
            render_tarjeta_posicion(pos_f2[sym], sym, "fase2_macro_activas", i)
        else:
            st.markdown(f"""
            <div class='card-slot slot-empty'>
                <span style='color:#64748b;'>⚪ Ranura {i+1} Disponible (Acción lista para entrada)</span>
            </div>
            """, unsafe_allow_html=True)

# ── BINANCE CROSS MARGIN: BITCOIN DUAL ────────────────────────
with col_bin:
    balas_bin = st_agente.get("binance_btc_balas", [])
    st.markdown(f"### 🪙 BINANCE MARGIN ({len(balas_bin)}/3 Balas)")
    st.caption("Acumulación Exclusiva BTC 5X (Candado: No compra más hasta vender en TP)")
    
    costo_prom = st_agente.get("btc_costo_promedio", 0.0)
    btc_acum = st_agente.get("btc_acumulado_agente", 0.0)
    
    st.markdown(f"""
    <div class='card-slot'>
        <div style='display:flex; justify-content:space-between;'>
            <strong style='color:#eab308; font-size:1.1rem;'>BITCOIN (5X MARGIN)</strong>
            <span class='badge-binance'>{'🔒 CANDADO ACTIVO' if len(balas_bin)>=3 else '🟢 BALAS DISPONIBLES'}</span>
        </div>
        <div style='margin-top:8px; font-size:0.85rem; color:#cbd5e1;'>
            <b>Balas Disparadas:</b> {len(balas_bin)} de 3 ($20 USD c/u @ 5X)<br>
            <b>Estrategia:</b> Acumulador Institucional (1D + 4H + 1H)<br>
            <b>BTC Acumulado:</b> {btc_acum:.5f} BTC<br>
            <b>Costo Promedio:</b> ${costo_prom:,.2f} USD<br>
            <b>🎯 TP Venta / Reciclaje:</b> ${costo_prom * 1.04:,.2f} (+4.0%)
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    for b in balas_bin:
        st.markdown(f"<div style='font-size:0.8rem; color:#94a3b8;'>• Bala #{b.get('bala_num')}: ${b.get('precio'):,.2f} ({b.get('fecha')})</div>", unsafe_allow_html=True)

st.divider()

# SECCIÓN 3: RADAR ADN EN VIVO Y CANDADOS DE COOLDOWN
st.subheader("📡 Radar de Detección de ADN Cuántico (Top 3 Candidatos)")
r_col1, r_col2 = st.columns(2)

with r_col1:
    st.markdown("#### ⚡ Top 3 Candidatos Fase 1 (Altcoins)")
    cand_f1 = st_agente.get("radar_top3_fase1", [])
    if cand_f1:
        df_f1 = pd.DataFrame([
            {"Activo": c["sym"], "Score ADN": f"{c['score']} pts", "Precio": f"${c['precio']:,.4f}" if c['precio']<1 else f"${c['precio']:,.2f}", "RSI 1H": c.get("rsi_1h", 0), "Squeeze": c.get("macd_estado", ""), "Gatillo": "🚀 ACTIVO" if c.get("gatillo_valido") else "⏳ ESPERA"}
            for c in cand_f1
        ])
        st.dataframe(df_f1, use_container_width=True, hide_index=True)
    else:
        st.info("Escaneando mercado de Altcoins...")

with r_col2:
    st.markdown("#### 🏛️ Top 3 Candidatos Fase 2 (Wall Street)")
    cand_f2 = st_agente.get("radar_top3_fase2", [])
    if cand_f2:
        df_f2 = pd.DataFrame([
            {"Empresa": c["sym"], "Score ADN": f"{c['score']} pts", "Precio": f"${c['precio']:,.2f}", "RSI 1H": c.get("rsi_1h", 0), "Squeeze": c.get("macd_estado", ""), "Gatillo": "🚀 ACTIVO" if c.get("gatillo_valido") else "⏳ ESPERA"}
            for c in cand_f2
        ])
        st.dataframe(df_f2, use_container_width=True, hide_index=True)
    else:
        st.info("Escaneando acciones de Wall Street...")

# SECCIÓN 4: CANDADOS ACTIVOS ANTI-BUCLE (COOLDOWN SHIELD)
st.markdown("---")
st.subheader("🛡️ Candados Activos de Cooldown Anti-Bucle (Mínimo 6 Horas)")
now_ts = time.time()
candados = st_agente.get("candado_cooldown_senales", {})
activos_bloqueados = []
for sym, info in candados.items():
    expira = info.get("expira", 0.0)
    if now_ts < expira:
        minutos_restantes = int((expira - now_ts) / 60)
        activos_bloqueados.append({
            "Activo": sym,
            "Motivo": info.get("motivo", "Cooldown"),
            "Tiempo Restante": f"{minutos_restantes} min ({minutos_restantes/60:.1f}h)",
            "Estado Protección": "🔒 Bloqueo Anti-Duplicado Activo"
        })

if activos_bloqueados:
    st.dataframe(pd.DataFrame(activos_bloqueados), use_container_width=True, hide_index=True)
else:
    st.caption("🟢 No hay activos en cooldown restrictivo. El escáner opera con todos los activos disponibles.")

st.divider()

# SECCIÓN 5: HISTORIAL DE TICKETS CONTABLES
st.subheader("📜 Libro Mayor de Operaciones Cerradas ($ USD)")
hist_tickets = resumen_pnl.get("ultimos_tickets", [])
if hist_tickets:
    df_tickets = pd.DataFrame(hist_tickets)
    st.dataframe(df_tickets, use_container_width=True, hide_index=True)
else:
    st.info("El Libro Mayor se actualizará automáticamente con el PnL de cada trade cerrado.")
