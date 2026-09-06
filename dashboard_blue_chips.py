import os
import sys
import json
import time
import datetime
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(
    page_title="Cerebro 1: Wall Street & Blue Chips (Septiembre 2027)",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
ESTADO_FILE = os.path.join(BASE_DIR, "estado_blue_chips.json")
CONFIG_MODO_FILE = os.path.join(BASE_DIR, "config_blue_chips_modo.json")

def clean_num(val, fallback=0.0):
    try:
        if val is None or np.isnan(val) or np.isinf(val):
            return fallback
        return float(val)
    except:
        return fallback

import requests
import concurrent.futures

def cargar_modo():
    if os.path.exists(CONFIG_MODO_FILE):
        try:
            with open(CONFIG_MODO_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("modo", "FANTASMA").upper()
        except: pass
    return "FANTASMA"

def guardar_modo(nuevo_modo):
    try:
        with open(CONFIG_MODO_FILE, "w", encoding="utf-8") as f:
            json.dump({"modo": nuevo_modo.upper()}, f, indent=2)
    except Exception as e:
        st.error(f"Error guardando modo: {e}")

def cargar_estado():
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"posiciones": {}, "historial": [], "pnl_acumulado": 0.0, "total_trades": 0, "wins": 0, "losses": 0}

@st.cache_data(ttl=4)
def obtener_precios_en_vivo_bingx(activos_list):
    precios = {}
    def fetch_p(sym):
        try:
            url = f"https://open-api.bingx.com/openApi/swap/v2/quote/ticker?symbol={sym}-USDT"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            r = requests.get(url, headers=headers, timeout=3).json()
            if r.get("code") == 0 and "data" in r and "lastPrice" in r["data"]:
                return sym, float(r["data"]["lastPrice"])
        except: pass
        return sym, None

    if activos_list:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(activos_list), 15)) as executor:
            results = executor.map(fetch_p, activos_list)
            for sym, px in results:
                if px: precios[sym] = px
    return precios

def render_tarjeta_posicion_viva(symbol, pos, px_act):
    entry = clean_num(pos.get("entry_px", 0.0))
    sl = clean_num(pos.get("sl", 0.0))
    tp1 = clean_num(pos.get("tp1", 0.0))
    tp2 = clean_num(pos.get("tp2", 0.0))
    tp1_hit = pos.get("tp1_hit", False)
    margen = clean_num(pos.get("margen_actual", 10.0))
    leverage = 10.0
    notional = margen * leverage
    
    if entry <= 0:
        return
        
    px_act = px_act if px_act > 0 else entry
    
    pnl_pct = ((px_act - entry) / entry) * 100.0
    pnl_usd = notional * (pnl_pct / 100.0)
    
    dist_sl_usd = px_act - sl
    dist_sl_pct = ((px_act - sl) / px_act) * 100.0 if px_act > 0 else 0.0
    
    dist_tp1_usd = tp1 - px_act
    dist_tp1_pct = ((tp1 - px_act) / px_act) * 100.0 if px_act > 0 else 0.0
    dist_tp2_usd = tp2 - px_act
    dist_tp2_pct = ((tp2 - px_act) / px_act) * 100.0 if px_act > 0 else 0.0
    
    denom = max(1e-5, tp1 - sl)
    prog_pct = min(100.0, max(0.0, ((px_act - sl) / denom) * 100.0))
    
    color_pnl = "#00ff88" if pnl_usd >= 0 else "#ff3366"
    bg_pnl = "rgba(0, 255, 136, 0.15)" if pnl_usd >= 0 else "rgba(255, 51, 102, 0.15)"
    badge_icon = "🔥 GANANDO" if pnl_usd >= 0 else "❄️ PERDIENDO"
    
    import textwrap
    html_card = textwrap.dedent(f"""
    <div style="background: rgba(16, 23, 38, 0.9); border: 1px solid rgba(0, 229, 255, 0.3); border-radius: 14px; padding: 18px; margin-bottom: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.45);">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px; margin-bottom: 12px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size: 18px;">🟢</span>
                <strong style="font-size: 18px; color: #ffffff; letter-spacing: 0.5px;">LONG: {symbol}</strong>
            </div>
            <div style="background: {bg_pnl}; border: 1px solid {color_pnl}; color: {color_pnl}; padding: 6px 14px; border-radius: 20px; font-weight: 800; font-size: 15px; font-family: monospace; text-shadow: 0 0 10px {color_pnl};">
                {badge_icon}: ${pnl_usd:+,.2f} USD ({pnl_pct:+,.2f}%)
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 14px; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.05);">
            <div>
                <div style="font-size:11px; color:#94a3b8; font-weight:700;">PRECIO ENTRADA</div>
                <div style="font-size:16px; font-weight:800; color:#cbd5e1; font-family:monospace;">${entry:,.2f}</div>
            </div>
            <div>
                <div style="font-size:11px; color:#00e5ff; font-weight:700;">📡 PRECIO ACTUAL VIVO</div>
                <div style="font-size:16px; font-weight:800; color:#00e5ff; font-family:monospace;">${px_act:,.2f}</div>
            </div>
            <div>
                <div style="font-size:11px; color:#94a3b8; font-weight:700;">ESTADO TP1</div>
                <div style="font-size:14px; font-weight:700; color:{'#00ff88' if tp1_hit else '#ffaa00'};">{'✅ COBRADO' if tp1_hit else '⏳ PENDIENTE'}</div>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; font-size: 12px; margin-bottom: 14px;">
            <div style="background: rgba(255, 51, 102, 0.12); border-left: 4px solid #ff3366; padding: 9px; border-radius: 6px;">
                <div style="color: #ff3366; font-weight: 800;">🛑 STOP LOSS: ${sl:,.2f}</div>
                <div style="color: #f87171; margin-top:3px; font-weight:600;">Falta a SL: -${dist_sl_usd:,.2f} (-{dist_sl_pct:.2f}%)</div>
            </div>
            <div style="background: rgba(0, 255, 136, 0.12); border-left: 4px solid #00ff88; padding: 9px; border-radius: 6px;">
                <div style="color: #00ff88; font-weight: 800;">🟢 TP1: ${tp1:,.2f}</div>
                <div style="color: #4ade80; margin-top:3px; font-weight:600;">Falta a TP1: +${dist_tp1_usd:,.2f} (+{dist_tp1_pct:.2f}%)</div>
            </div>
            <div style="background: rgba(0, 229, 255, 0.12); border-left: 4px solid #00e5ff; padding: 9px; border-radius: 6px;">
                <div style="color: #00e5ff; font-weight: 800;">🎯 TP2 MACRO: ${tp2:,.2f}</div>
                <div style="color: #38bdf8; margin-top:3px; font-weight:600;">Falta a TP2: +${dist_tp2_usd:,.2f} (+{dist_tp2_pct:.2f}%)</div>
            </div>
        </div>
        <div style="margin-top: 10px;">
            <div style="display: flex; justify-content: space-between; font-size: 11px; color: #94a3b8; font-weight: 700; margin-bottom: 5px;">
                <span>🔴 SL (${sl:,.2f})</span>
                <span style="color: {color_pnl}; font-weight: 800;">📍 POSICIÓN EN VIVO: {prog_pct:.1f}% HACIA TP1</span>
                <span>🟢 TP1 (${tp1:,.2f})</span>
            </div>
            <div style="width: 100%; background: #0f172a; height: 12px; border-radius: 6px; overflow: hidden; position: relative; border: 1px solid rgba(255,255,255,0.12);">
                <div style="width: {prog_pct}%; background: linear-gradient(90deg, #ff3366 0%, #ffaa00 50%, #00ff88 100%); height: 100%; border-radius: 6px; box-shadow: 0 0 10px {color_pnl};"></div>
            </div>
        </div>
    </div>
    """)
    st.markdown(html_card, unsafe_allow_html=True)

# Estilos Neón Dark Glassmorphism
st.markdown("""
<style>
    .stApp { background-color: #060911; color: #f1f5f9; }
    .header-box {
        background: radial-gradient(circle at center, rgba(0,229,255,0.08) 0%, transparent 70%);
        border: 1px solid rgba(0, 229, 255, 0.2); border-radius: 16px; padding: 20px;
        text-align: center; margin-bottom: 25px;
    }
    .header-box h1 { font-size: 28px; font-weight: 900; color: #fff; margin-bottom: 5px; }
    .header-box h1 span { color: #00e5ff; text-shadow: 0 0 12px rgba(0,229,255,0.6); }
    .header-box p { color: #94a3b8; font-size: 14px; }
    
    .card-neon {
        background: rgba(16, 23, 38, 0.75); backdrop-filter: blur(12px);
        border: 1px solid rgba(0, 229, 255, 0.18); border-radius: 14px; padding: 18px;
        margin-bottom: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.37);
    }
    .kpi-val { font-family: monospace; font-size: 26px; font-weight: 800; }
    .neon-green { color: #00ff88; text-shadow: 0 0 10px rgba(0,255,136,0.5); }
    .neon-cyan { color: #00e5ff; text-shadow: 0 0 10px rgba(0,229,255,0.5); }
    .neon-gold { color: #ffd700; text-shadow: 0 0 10px rgba(255,215,0,0.5); }
</style>
""", unsafe_allow_html=True)

# Cabecera
st.markdown("""
<div class="header-box">
    <h1>🏛️ SEPTIEMBRE 2027: <span>CEREBRO 1 (ALPHA WALL STREET)</span></h1>
    <p>Flota Ganadora de Acciones e Índices Institucionales | 96.3% Win Rate Validado | 0% Cripto Tóxico</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
modo_actual = cargar_modo()
st.sidebar.markdown("### ⚙️ Control Operativo")
st.sidebar.markdown(f"**Modo Actual:** `{'🟢 REAL' if modo_actual == 'REAL' else '👻 FANTASMA'}`")

col_btn1, col_btn2 = st.sidebar.columns(2)
if col_btn1.button("🟢 REAL", use_container_width=True):
    guardar_modo("REAL")
    st.rerun()
if col_btn2.button("👻 FANTASMA", use_container_width=True):
    guardar_modo("FANTASMA")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Activos Oficiales (11)")
st.sidebar.caption("• Broadcom (AVGO) - 100% WR\n• AMD - 100% WR\n• Google (GOOGL) - 100% WR\n• Meta (META) - 100% WR\n• Nvidia (NVDA) - 100% WR\n• Apple (AAPL) - 100% WR\n• Microsoft (MSFT) - 100% WR\n• Amazon (AMZN) - 80% WR\n• Tesla (TSLA)\n• Nasdaq 100 (QQQ) - 100% WR\n• S&P 500 (SP500) - 100% WR\n• Dow Jones (DJI) - 100% WR")

# PESTAÑAS (UNICIDAD ESTRICTA)
tab1, tab2, tab3, tab4 = st.tabs([
    "🏛️ SALA DE MANDO CEREBRO 1 (SEPTIEMBRE 2027)",
    "⚡ SEMÁFORO TÁCTICO BLUE CHIPS (WALL STREET)",
    "📦 POSICIONES ABIERTAS & HISTORIAL VIVO",
    "📜 MANUAL OPERATIVO CEREBRO 1"
])

estado = cargar_estado()
posiciones = estado.get("posiciones", {})
historial = estado.get("historial", [])
pnl_tot = clean_num(estado.get("pnl_acumulado", 0.0))
trades_cnt = int(estado.get("total_trades", 0))
wins_cnt = int(estado.get("wins", 0))
wr_calc = (wins_cnt / trades_cnt * 100.0) if trades_cnt > 0 else 0.0

margen_usado = sum(clean_num(p.get("margen_actual", 10.0)) for p in posiciones.values())
cap_base = 200.0
cash_bal = cap_base - margen_usado + pnl_tot
equity_tot = cash_bal + margen_usado

with tab1:
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f"""
        <div class="card-neon">
            <div style="color:#94a3b8; font-size:12px; font-weight:700;">💵 SALDO DISPONIBLE (CASH)</div>
            <div class="kpi-val neon-green">${cash_bal:,.2f} USD</div>
            <div style="color:#64748b; font-size:11px;">Margen Disponible Líquido</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="card-neon">
            <div style="color:#94a3b8; font-size:12px; font-weight:700;">🏦 EQUITY TOTAL CUENTA</div>
            <div class="kpi-val neon-cyan">${equity_tot:,.2f} USD</div>
            <div style="color:#64748b; font-size:11px;">Cash + Colateral Operativo</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="card-neon">
            <div style="color:#94a3b8; font-size:12px; font-weight:700;">PNL HOY (PRODUCCIÓN)</div>
            <div class="kpi-val neon-green">${pnl_tot:+,.2f} USD</div>
            <div style="color:#64748b; font-size:11px;">PnL Realizado Neto</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="card-neon">
            <div style="color:#94a3b8; font-size:12px; font-weight:700;">WIN RATE HOY</div>
            <div class="kpi-val neon-cyan">{wr_calc:.1f}%</div>
            <div style="color:#64748b; font-size:11px;">{wins_cnt} Ganadas de {trades_cnt} Trades</div>
        </div>
        """, unsafe_allow_html=True)
    with k5:
        st.markdown(f"""
        <div class="card-neon">
            <div style="color:#94a3b8; font-size:12px; font-weight:700;">POSICIONES ABIERTAS</div>
            <div class="kpi-val neon-gold">{len(posiciones)} / 5 MÁX</div>
            <div style="color:#64748b; font-size:11px;">$10 USD Margen / 10x</div>
        </div>
        """, unsafe_allow_html=True)

    st.success("🏁 **Sesión Iniciada Hoy:** Todas las métricas, ganancias y operaciones arrancan estrictamente en **$0.00 USD / 0 trades**.")

    with st.expander("📚 Ver Auditoría Histórica de Validación (3 Meses a Ciegas)"):
        st.write("En la prueba previa fuera de muestra (Junio - Septiembre), este motor arrojó **+$61.36 USD** (96.3% Win Rate) en 27 operaciones con $10 de margen.")

    st.markdown("""
    <div style="background: rgba(255, 170, 0, 0.12); border: 1px solid #ffa500; border-radius: 12px; padding: 14px; margin-top: 15px;">
        <span style="font-size: 18px;">🛡️</span> <strong style="color: #ffaa00; font-size: 15px;">ESCUDO DE HIERRO INTOCABLE: SHORT MANUAL MSFT</strong>
        <p style="color: #cbd5e1; font-size: 13px; margin-top: 5px; margin-bottom: 0;">
            El SHORT manual en Microsoft (MSFT) está <strong>100% BLINDADO E INTOCABLE</strong>. El bot tiene prohibido tocarlo, modificarlo o cerrarlo. La posición LONG en MSFT y los demás activos sí pueden operar y ser adoptados normalmente.
        </p>
    </div>
    """, unsafe_allow_html=True)

with tab2:
    st.markdown("### ⚡ Semáforo Cuántico de los 11 Activos (Sesión Viva)")
    grid_cols = st.columns(3)
    
    activos_display = [
        {"name": "Broadcom", "ticker": "AVGO", "rend_bench": "+$12.55", "wr_bench": "100%"},
        {"name": "Google", "ticker": "GOOGL", "rend_bench": "+$16.87", "wr_bench": "100%"},
        {"name": "Nasdaq 100", "ticker": "QQQ", "rend_bench": "+$13.41", "wr_bench": "100%"},
        {"name": "Microsoft", "ticker": "MSFT", "rend_bench": "+$8.05", "wr_bench": "100%"},
        {"name": "Meta", "ticker": "META", "rend_bench": "+$6.90", "wr_bench": "100%"},
        {"name": "S&P 500", "ticker": "SP500", "rend_bench": "+$4.55", "wr_bench": "100%"},
        {"name": "Nvidia", "ticker": "NVDA", "rend_bench": "+$3.45", "wr_bench": "100%"},
        {"name": "Dow Jones", "ticker": "DJI", "rend_bench": "+$3.43", "wr_bench": "100%"},
        {"name": "Apple", "ticker": "AAPL", "rend_bench": "+$3.40", "wr_bench": "100%"},
        {"name": "AMD", "ticker": "AMD", "rend_bench": "+$1.15", "wr_bench": "100%"},
        {"name": "Amazon", "ticker": "AMZN", "rend_bench": "-$12.40", "wr_bench": "80%"}
    ]
    
    for idx, act in enumerate(activos_display):
        t_sym = act['ticker']
        pnl_act = sum(clean_num(t.get('pnl', 0.0)) for t in historial if t.get('activo') == t_sym)
        trades_act = sum(1 for t in historial if t.get('activo') == t_sym)
        wins_act = sum(1 for t in historial if t.get('activo') == t_sym and clean_num(t.get('pnl', 0.0)) > 0)
        wr_act = (wins_act / trades_act * 100.0) if trades_act > 0 else 0.0
        
        en_pos = t_sym in posiciones
        badge_status = "🔵 EN POSICIÓN LONG" if en_pos else "🟢 VIGILANCIA COMPRA"
        color_status = "#00e5ff" if en_pos else "#00ff88"
        
        with grid_cols[idx % 3]:
            st.markdown(f"""
            <div class="card-neon">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong style="font-size:16px; color:#fff;">{act['name']}</strong>
                    <span style="background:rgba(0,229,255,0.2); color:#00e5ff; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:700;">{t_sym}</span>
                </div>
                <div style="margin-top:10px; font-size:13px; color:#94a3b8;">
                    PnL Sesión: <strong style="color:#00ff88;">${pnl_act:+,.2f} USD</strong><br>
                    Trades Hoy: <strong>{trades_act}</strong> | Win Rate: <strong style="color:#00e5ff;">{wr_act:.1f}%</strong><br>
                    Estado: <span style="color:{color_status}; font-weight:700;">{badge_status}</span>
                </div>
                <div style="margin-top:6px; font-size:11px; color:#64748b; border-top:1px dashed rgba(255,255,255,0.1); padding-top:4px;">
                    Benchmark 3M: {act['rend_bench']} ({act['wr_bench']} WR)
                </div>
            </div>
            """, unsafe_allow_html=True)

with tab3:
    c_p1, c_p2 = st.columns([1.1, 0.9])
    with c_p1:
        st.markdown("### 💼 Posiciones Abiertas en Vivo (Semáforo Táctico)")
        if posiciones:
            activos_open = list(posiciones.keys())
            precios_vivos = obtener_precios_en_vivo_bingx(activos_open)
            for s, pos in posiciones.items():
                px_act = precios_vivos.get(s, clean_num(pos.get("entry_px", 0.0)))
                render_tarjeta_posicion_viva(s, pos, px_act)
        else:
            st.info("Sin posiciones abiertas actualmente. Escaneando niveles institucionales...")
            
    with c_p2:
        st.markdown("### 📜 Historial Reciente de Operaciones")
        if historial:
            df_hist = pd.DataFrame(historial)
            st.dataframe(df_hist, use_container_width=True)
        else:
            st.caption("No se han registrado cierres en esta sesión.")

with tab4:
    st.markdown("### 📖 Reglas Oficiales de Septiembre 2027")
    st.markdown("""
    1. **Aislamiento Total de Cripto Tóxico:** Cero exposición a altcoins volátiles que rompan a la baja.
    2. **Disparo Francotirador:** $10 USD de margen base a 10x apalancamiento ($100 USD nominal).
    3. **Salida Asimétrica:**
       - **TP1 al 50%:** Mitigación al POC 90D o ganancia de +1.5% a +2.0%. Realiza dinero en efectivo y sube el Stop Loss a Break-Even asegurado (+0.5%).
       - **TP2:** Trailing Stop a 1.5x ATR sobre el 50% restante hacia techos semanales.
    4. **Comisiones Deducidas:** Modelo estricto de fees taker reales (0.05%) de BingX Perpetuos.
    5. **Blindaje Absoluto del SHORT de MSFT:** El SHORT manual en Microsoft jamás será cerrado, adoptado ni alterado por ningún algoritmo. Es 100% intocable. El bot opera en compras (LONG) institucionales y adopta posiciones LONG de los demás activos.
    """)
