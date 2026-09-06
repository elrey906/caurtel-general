# -*- coding: utf-8 -*-
"""
🎛️ SALA DE MANDO: MEGA-AGENTE ADN AUTÓNOMO (PUERTO 8560)
=============================================================================
Visualiza:
  1. Estado del Piloto Automático (Modo FANTASMA 👻 vs REAL 🟢).
  2. Cuotas BingX:
     - Fase 1 (Rápidas): [X/3] Ranuras ocupadas ($10 @ 10X).
     - Fase 2 (Macro):   [X/3] Ranuras ocupadas ($10 @ 10X) con Checkpoint Día 10.
  3. Cuota Binance:
     - [X/3] Balas disparadas ($10 @ 5X). Candado de acero hasta TP.
  4. Libro Mayor de Ganancias y Pérdidas Reales en $ USD.
  5. Radar ADN en Vivo (Top 3 Rápido y Top 3 Macro).
=============================================================================
"""
import streamlit as st
import os, sys, json, datetime, pandas as pd, numpy as np

st.set_page_config(page_title="Mega-Agente ADN Autónomo", page_icon="🧬", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config_adn import CONFIG_FILE, ESTADO_FILE
from aprendizaje_ledger import obtener_resumen_contable, cargar_json, guardar_json

st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 900; color: #38bdf8; margin-bottom: 5px; }
    .card-slot { background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 12px; }
    .slot-empty { border: 1px dashed #64748b; background: rgba(15, 23, 42, 0.4); }
    .badge-fase1 { background: #0284c7; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.8rem; }
    .badge-fase2 { background: #7c3aed; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.8rem; }
    .badge-binance { background: #eab308; color: black; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>🧬 MEGA-AGENTE ADN: PILOTO AUTOMÁTICO BIAXIAL</div>", unsafe_allow_html=True)
st.caption("Fase 1 (Altcoins Rápidas 48h) · Fase 2 (Wall Street Macro 25D) · Binance Margin (BTC 3 Balas) · Puerto 8560")

# SIDEBAR: MODO Y CONTROLES
st.sidebar.header("🕹️ Centro de Control de Mando")
cfg = cargar_json(CONFIG_FILE, {"modo": "FANTASMA"})
modo_actual = cfg.get("modo", "FANTASMA").upper()

nuevo_modo = st.sidebar.radio(
    "Estado del Piloto Automático:",
    ["FANTASMA 👻 (Simulación Segura)", "REAL 🟢 (Órdenes Vivas a Exchange)"],
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
st.sidebar.markdown("• **Binance BTC:** Máx 3 balas ($10 @ 5X)")
st.sidebar.markdown("• **Checkpoint:** Alarma en Día 10")
st.sidebar.markdown("• **Pacto de Respeto:** Cerebros 1, 2 y 3 Intocables")

# CARGAR ESTADOS Y LIBRO CONTABLE
st_agente = cargar_json(ESTADO_FILE, {
    "fase1_rapidas_activas": {}, "fase2_macro_activas": {}, "binance_btc_balas": [],
    "btc_acumulado_agente": 0.0, "btc_costo_promedio": 0.0,
    "radar_top3_fase1": [], "radar_top3_fase2": []
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

# SECCIÓN 2: LAS 3 FASES Y RANURAS ACTIVAS
col_f1, col_f2, col_bin = st.columns(3)

# ── FASE 1: BINGX RÁPIDAS (ALTCOINS) ──────────────────────────
with col_f1:
    pos_f1 = st_agente.get("fase1_rapidas_activas", {})
    st.markdown(f"### ⚡ FASE 1: RÁPIDAS ({len(pos_f1)}/3 Ranuras)")
    st.caption("Caza de mechas y rebotes elásticos (Máx 48 horas · $10 @ 10X)")
    
    for i in range(3):
        syms_f1 = list(pos_f1.keys())
        if i < len(syms_f1):
            sym = syms_f1[i]
            p = pos_f1[sym]
            horas = (time.time() - p["ts_entry"]) / 3600.0
            st.markdown(f"""
            <div class='card-slot'>
                <div style='display:flex; justify-content:space-between;'>
                    <strong style='color:#38bdf8; font-size:1.1rem;'>{sym} (LONG)</strong>
                    <span class='badge-fase1'>RANURA {i+1} ACTIVA</span>
                </div>
                <div style='margin-top:8px; font-size:0.85rem; color:#cbd5e1;'>
                    <b>Entrada:</b> ${p['entry_px']:,.2f} | <b>Lote:</b> {p['qty_tokens']} tokens<br>
                    <b>🎯 TP:</b> ${p['tp_px']:,.2f} | <b>🛑 SL:</b> ${p['sl_px']:,.2f}<br>
                    <b>Tiempo activo:</b> {horas:.1f}h / 48h
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='card-slot slot-empty'>
                <span style='color:#64748b;'>⚪ Ranura {i+1} Disponible (Pólvora lista para disparo)</span>
            </div>
            """, unsafe_allow_html=True)

# ── FASE 2: BINGX MACRO (WALL STREET) ─────────────────────────
with col_f2:
    pos_f2 = st_agente.get("fase2_macro_activas", {})
    st.markdown(f"### 🏛️ FASE 2: MACRO ({len(pos_f2)}/3 Ranuras)")
    st.caption("Acciones Wall Street (Máx 25 Días · Alarma Día 10 · $10 @ 10X)")
    
    for i in range(3):
        syms_f2 = list(pos_f2.keys())
        if i < len(syms_f2):
            sym = syms_f2[i]
            p = pos_f2[sym]
            dias = (time.time() - p["ts_entry"]) / 86400.0
            alerta_d10 = "⚠️ DÍA 10 SUPERADO" if dias >= 10.0 else f"Día {dias:.1f}/25"
            st.markdown(f"""
            <div class='card-slot'>
                <div style='display:flex; justify-content:space-between;'>
                    <strong style='color:#a855f7; font-size:1.1rem;'>{sym} (LONG)</strong>
                    <span class='badge-fase2'>RANURA {i+1} ACTIVA</span>
                </div>
                <div style='margin-top:8px; font-size:0.85rem; color:#cbd5e1;'>
                    <b>Entrada:</b> ${p['entry_px']:,.2f} | <b>Lote:</b> {p['qty_tokens']} tokens<br>
                    <b>🎯 TP:</b> ${p['tp_px']:,.2f} | <b>🛑 SL:</b> ${p['sl_px']:,.2f}<br>
                    <b>Control de Tiempo:</b> <span style='color:#f59e0b;'>{alerta_d10}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
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
            <b>Balas Disparadas:</b> {len(balas_bin)} de 3 ($10 c/u)<br>
            <b>BTC Acumulado:</b> {btc_acum:.5f} BTC<br>
            <b>Costo Promedio:</b> ${costo_prom:,.2f} USD<br>
            <b>🎯 TP Venta / Reciclaje:</b> ${costo_prom * 1.04:,.2f} (+4.0%)
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    for b in balas_bin:
        st.markdown(f"<div style='font-size:0.8rem; color:#94a3b8;'>• Bala #{b.get('bala_num')}: ${b.get('precio'):,.2f} ({b.get('fecha')})</div>", unsafe_allow_html=True)

st.divider()

# SECCIÓN 3: RADAR ADN EN VIVO (TOP 3 RÁPIDO & TOP 3 MACRO)
st.subheader("📡 Radar de Detección de ADN Cuántico (Top 3 en Espera)")
r_col1, r_col2 = st.columns(2)

with r_col1:
    st.markdown("#### ⚡ Top 3 Candidatos Fase 1 (Altcoins)")
    cand_f1 = st_agente.get("radar_top3_fase1", [])
    if cand_f1:
        df_f1 = pd.DataFrame([
            {"Activo": c["sym"], "Score ADN": f"{c['score']} pts", "Precio": f"${c['precio']:,.2f}", "RSI 1H": c["rsi_1h"], "Squeeze": c["macd_estado"], "Gatillo": "🚀 ACTIVO" if c["gatillo_valido"] else "⏳ ESPERA"}
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
            {"Empresa": c["sym"], "Score ADN": f"{c['score']} pts", "Precio": f"${c['precio']:,.2f}", "RSI 1H": c["rsi_1h"], "Squeeze": c["macd_estado"], "Gatillo": "🚀 ACTIVO" if c["gatillo_valido"] else "⏳ ESPERA"}
            for c in cand_f2
        ])
        st.dataframe(df_f2, use_container_width=True, hide_index=True)
    else:
        st.info("Escaneando acciones de Wall Street...")

st.divider()

# SECCIÓN 4: HISTORIAL DE TICKETS CONTABLES
st.subheader("📜 Libro Mayor de Tickets Cerrados ($ USD)")
hist_tickets = resumen_pnl.get("ultimos_tickets", [])
if hist_tickets:
    df_tickets = pd.DataFrame(hist_tickets)
    st.dataframe(df_tickets, use_container_width=True, hide_index=True)
else:
    st.info("El Libro Mayor se actualizará automáticamente con el PnL de cada trade cerrado.")
