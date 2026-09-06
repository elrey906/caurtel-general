#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
🎛️ DASHBOARD DE CONTROL: CEREBRO HÍBRIDO TRIFECTA CUÁNTICA ($15 + $45 + $10)
========================================================================================
Puerto Oficial: 8555
Controles:
  • Selector de Modo Independiente por Activo (REAL 🟢 vs FANTASMA 👻).
  • Semáforos ADN en tiempo real (Distancia al Martillazo 🔨 y Distancia al TP 🎯).
  • Botón manual de cierre inmediato a mercado en BingX por activo.
  • Historial y posiciones activas con trazabilidad del modo.
========================================================================================
"""
import streamlit as st
import os, sys, json, datetime, pandas as pd, numpy as np

st.set_page_config(page_title="Cerebro Híbrido Trifecta", page_icon="👑", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_MODO_FILE = os.path.join(BASE_DIR, "config_trifecta_modo.json")
ESTADO_FILE = os.path.join(BASE_DIR, "estado_trifecta_hibrido.json")
TELEMETRIA_FILE = os.path.join(BASE_DIR, "telemetria_adn_trifecta.json")
COMANDOS_FILE = os.path.join(BASE_DIR, "comandos_manuales.json")

def clean_num(val, fallback=0.0):
    try:
        v = float(val)
        return fallback if np.isnan(v) or np.isinf(v) else v
    except: return fallback

def cargar_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return default

st.markdown("""
<style>
    .main-header { font-size: 1.8rem; font-weight: 800; color: #00e5ff; margin-bottom: 5px; }
    .card { background: #0e1626; border: 1px solid #1e293b; border-radius: 10px; padding: 15px; margin-bottom: 15px; }
    .card-active { background: #0d233a; border: 1px solid #00e5ff; border-radius: 10px; padding: 15px; margin-bottom: 15px; }
    .badge-win { background: #059669; color: white; padding: 3px 8px; border-radius: 5px; font-weight: bold; }
    .badge-warn { background: #d97706; color: white; padding: 3px 8px; border-radius: 5px; font-weight: bold; }
    .badge-mode { background: #3b82f6; color: white; padding: 3px 8px; border-radius: 5px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-header'>👑 CEREBRO HÍBRIDO TRIFECTA CUÁNTICA ($15 + $45 + $10)</div>", unsafe_allow_html=True)
st.caption("Ecosistema de Élite: AMD, AVGO, META, DJI, BTC, ETH | Puerto 8555 | Ubicación: /home/h/Escritorio/SEPTIEMBRE/HIBRIDO/")

# SIDEBAR: GESTIÓN DE MODOS POR ACTIVO
st.sidebar.header("🎛️ Modos Independientes por Activo")
cfg_modos = cargar_json(CONFIG_MODO_FILE, {
    "AMD": "FANTASMA", "AVGO": "FANTASMA", "META": "FANTASMA", "DJI": "FANTASMA", "BTC": "FANTASMA", "ETH": "FANTASMA"
})

cambio_detectado = False
activos_lista = ["AMD", "AVGO", "META", "DJI", "BTC", "ETH"]

for sym in activos_lista:
    m_actual = cfg_modos.get(sym, "FANTASMA").upper()
    nuevo_m = st.sidebar.radio(
        f"{sym}:", ["FANTASMA 👻", "REAL 🟢"],
        index=0 if m_actual == "FANTASMA" else 1,
        key=f"sidebar_modo_{sym}"
    )
    val_m = "FANTASMA" if "FANTASMA" in nuevo_m else "REAL"
    if val_m != m_actual:
        cfg_modos[sym] = val_m
        cambio_detectado = True

if cambio_detectado:
    cfg_modos["actualizado"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CONFIG_MODO_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg_modos, f, indent=2)
    st.sidebar.success("Modos actualizados correctamente.")
    st.rerun()

st.sidebar.divider()
st.sidebar.markdown("**Estructura Trifecta:**")
st.sidebar.markdown("• **Bala 1:** $15 USD (Sonda 7D)")
st.sidebar.markdown("• **Bala 2:** $45 USD (Martillazo 30D)")
st.sidebar.markdown("• **Bala 3:** $10 USD (Rebote Inminente)")

estado = cargar_json(ESTADO_FILE, {"pnl_total": 0.0, "total_trades": 0, "wins": 0, "losses": 0, "posiciones_activas": {}, "historial": []})
telemetria = cargar_json(TELEMETRIA_FILE, {})

col1, col2, col3, col4 = st.columns(4)
col1.metric("PnL Realizado Total", f"${clean_num(estado.get('pnl_total', 0.0)):+.2f} USD")
col2.metric("Total Operaciones", f"{estado.get('total_trades', 0)}")
wr = (estado.get('wins', 0) / max(1, estado.get('total_trades', 0))) * 100.0
col3.metric("Win Rate", f"{wr:.1f}%")
col4.metric("Posiciones Abiertas", f"{len(estado.get('posiciones_activas', {}))}")

st.divider()

# TARJETAS CON SEMÁFORO ADN Y SELECTOR DE MODO
st.subheader("📊 Radar ADN & Control Independiente por Activo")

cols = st.columns(2)

for idx, sym in enumerate(activos_lista):
    col = cols[idx % 2]
    data = telemetria.get(sym, {})
    activo_pos = data.get("activo", False)
    modo_sym = cfg_modos.get(sym, "FANTASMA")
    
    with col:
        clase_card = "card-active" if activo_pos else "card"
        px = clean_num(data.get("precio_actual", 0.0))
        dist_mart = clean_num(data.get("dist_martillazo_pct", 0.0))
        dist_tp = clean_num(data.get("dist_tp_pct", 0.0))
        pnl_flot = clean_num(data.get("pnl_flotante", 0.0))
        balas_cnt = data.get("balas_count", 0)
        estado_adn = data.get("estado_adn", "⚪ ESPERANDO SEÑAL")
        
        badge_modo_color = "🟢 REAL" if modo_sym == "REAL" else "👻 FANTASMA"
        
        st.markdown(f"""
        <div class='{clase_card}'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <span style='font-size: 1.25rem; font-weight: bold; color: #00e5ff;'>{sym}</span>
                <div>
                    <span class='badge-mode'>{badge_modo_color}</span>
                    <span class='{"badge-win" if activo_pos else "badge-warn"}' style='margin-left: 5px;'>{"EN POSICIÓN" if activo_pos else "BUSCANDO ENTRADA"}</span>
                </div>
            </div>
            <div style='margin-top: 8px;'><b>Precio Actual:</b> ${px:,.2f} USD</div>
            <div><b>ADN:</b> {estado_adn}</div>
            <hr style='border: 0.5px solid #1e293b; margin: 8px 0;'>
            <div>🔨 <b>Distancia al Martillazo (30D):</b> {dist_mart:+.2f}%</div>
            <div>🎯 <b>Distancia al Take Profit:</b> {dist_tp:+.2f}%</div>
            <div>💼 <b>Margen Invertido:</b> ${clean_num(data.get('margen_total', 0.0)):.1f} USD ({balas_cnt} Balas)</div>
            <div>💵 <b>PnL Flotante:</b> <span style='color: {"#10b981" if pnl_flot >= 0 else "#ef4444"}; font-weight: bold;'>{pnl_flot:+.2f} USD</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Botón de Cierre Manual si está en posición
        if activo_pos:
            if st.button(f"🚨 CERRAR POSICIÓN {sym} A MERCADO", key=f"btn_close_{sym}"):
                with open(COMANDOS_FILE, "w", encoding="utf-8") as f:
                    json.dump({"cerrar_posicion": sym, "timestamp": datetime.datetime.now().isoformat()}, f, indent=2)
                st.warning(f"Orden de cierre enviada para {sym}. El bot la ejecutará de inmediato.")
                st.rerun()

st.divider()

# HISTORIAL DE OPERACIONES
st.subheader("📜 Historial de Operaciones Realizadas")
hist = estado.get("historial", [])
if len(hist) > 0:
    df_hist = pd.DataFrame(hist)
    st.dataframe(df_hist, use_container_width=True)
else:
    st.info("Aún no hay operaciones registradas en el historial.")
