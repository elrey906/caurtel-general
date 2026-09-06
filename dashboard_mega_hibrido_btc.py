import os
import sys
import json
import time
import hmac
import hashlib
import requests
import datetime
import pandas as pd
import numpy as np
import streamlit as st
from dotenv import load_dotenv

st.set_page_config(
    page_title="Cerebro Supremo: Mega Híbrido Quantum BTC Dual (Binance 5X)",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
ENV_PATH = os.path.join(BASE_DIR, ".env") if os.path.exists(os.path.join(BASE_DIR, ".env")) else os.path.join(ROOT_DIR, ".env")
load_dotenv(ENV_PATH)

ESTADO_FILE = os.path.join(BASE_DIR, "estado_mega_hibrido_btc_dual.json")
CONFIG_MODO_FILE = os.path.join(BASE_DIR, "config_MEGA_HIBRIDO_BTC_modo.json")

BINANCE_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET = os.getenv("BINANCE_API_SECRET", os.getenv("BINANCE_SECRET_KEY", ""))

def clean_num(val, fallback=0.0):
    try:
        if val is None or np.isnan(val) or np.isinf(val):
            return fallback
        return float(val)
    except:
        return fallback

@st.cache_data(ttl=4)
def obtener_precios_en_vivo_binance():
    precios = {}
    for sym in ["BTCUSDT", "BTCUSDC"]:
        try:
            r = requests.get(f"https://api3.binance.com/api/v3/ticker/price?symbol={sym}", timeout=3).json()
            if "price" in r:
                key = "BTC-USDT" if sym == "BTCUSDT" else "BTC-USDC"
                precios[key] = float(r["price"])
        except: pass
    return precios

def render_tarjeta_posicion_viva_btc(symbol, pos, px_act):
    btc_pos = clean_num(pos.get("btc_pos", 0.0))
    costo_prom = clean_num(pos.get("costo_prom", 0.0))
    compras = pos.get("compras_realizadas", [])
    ventas = pos.get("ventas_realizadas", [])
    be_activo = pos.get("stop_breakeven_activo", False)
    be_px = clean_num(pos.get("stop_be_px", costo_prom * 1.005))
    
    if btc_pos <= 0 or costo_prom <= 0:
        return
        
    px_act = px_act if px_act > 0 else costo_prom
    
    pnl_pct = ((px_act - costo_prom) / costo_prom) * 100.0
    pnl_usd = btc_pos * (px_act - costo_prom)
    
    tp1_px = costo_prom * 1.08
    dist_tp1_usd = tp1_px - px_act
    dist_tp1_pct = ((tp1_px - px_act) / px_act) * 100.0 if px_act > 0 else 0.0
    
    sl_px = be_px if be_activo else (costo_prom * 0.95)
    dist_sl_usd = px_act - sl_px
    dist_sl_pct = ((px_act - sl_px) / px_act) * 100.0 if px_act > 0 else 0.0
    
    denom = max(1e-5, tp1_px - sl_px)
    prog_pct = min(100.0, max(0.0, ((px_act - sl_px) / denom) * 100.0))
    
    color_pnl = "#00ff88" if pnl_usd >= 0 else "#ff3366"
    bg_pnl = "rgba(0, 255, 136, 0.15)" if pnl_usd >= 0 else "rgba(255, 51, 102, 0.15)"
    badge_icon = "🔥 GANANDO" if pnl_usd >= 0 else "❄️ PERDIENDO"
    
    import textwrap
    html_card = textwrap.dedent(f"""
    <div style="background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(247, 147, 26, 0.35); border-radius: 14px; padding: 18px; margin-bottom: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.45);">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px; margin-bottom: 12px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size: 18px;">🪙</span>
                <strong style="font-size: 18px; color: #ffffff; letter-spacing: 0.5px;">CARGADOR MARGIN: {symbol}</strong>
            </div>
            <div style="background: {bg_pnl}; border: 1px solid {color_pnl}; color: {color_pnl}; padding: 6px 14px; border-radius: 20px; font-weight: 800; font-size: 15px; font-family: monospace; text-shadow: 0 0 10px {color_pnl};">
                {badge_icon}: ${pnl_usd:+,.2f} USD ({pnl_pct:+,.2f}%)
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 10px; margin-bottom: 14px; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.05);">
            <div>
                <div style="font-size:11px; color:#94a3b8; font-weight:700;">INVENTARIO BTC</div>
                <div style="font-size:15px; font-weight:800; color:#f7931a; font-family:monospace;">{btc_pos:.5f} BTC</div>
            </div>
            <div>
                <div style="font-size:11px; color:#94a3b8; font-weight:700;">COSTO PROM. ENTRADA</div>
                <div style="font-size:15px; font-weight:800; color:#cbd5e1; font-family:monospace;">${costo_prom:,.2f}</div>
            </div>
            <div>
                <div style="font-size:11px; color:#00e5ff; font-weight:700;">📡 PRECIO BTC VIVO</div>
                <div style="font-size:15px; font-weight:800; color:#00e5ff; font-family:monospace;">${px_act:,.2f}</div>
            </div>
            <div>
                <div style="font-size:11px; color:#94a3b8; font-weight:700;">ESTADO BREAK-EVEN</div>
                <div style="font-size:14px; font-weight:700; color:{'#00ff88' if be_activo else '#ffaa00'};">{'🛡️ ACTIVO' if be_activo else '⏳ PENDIENTE (POST V1)'}</div>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12px; margin-bottom: 14px;">
            <div style="background: rgba(255, 51, 102, 0.12); border-left: 4px solid #ff3366; padding: 9px; border-radius: 6px;">
                <div style="color: #ff3366; font-weight: 800;">🛑 STOP / BE ({'BE' if be_activo else 'SL PISO'}): ${sl_px:,.2f}</div>
                <div style="color: #f87171; margin-top:3px; font-weight:600;">Falta a Piso/BE: -${dist_sl_usd:,.2f} (-{dist_sl_pct:.2f}%)</div>
            </div>
            <div style="background: rgba(0, 255, 136, 0.12); border-left: 4px solid #00ff88; padding: 9px; border-radius: 6px;">
                <div style="color: #00ff88; font-weight: 800;">🟢 TARGET FASE 1 (30% Profit): ${tp1_px:,.2f}</div>
                <div style="color: #4ade80; margin-top:3px; font-weight:600;">Falta a Target 1: +${dist_tp1_usd:,.2f} (+{dist_tp1_pct:.2f}%)</div>
            </div>
        </div>
        <div style="margin-top: 10px;">
            <div style="display: flex; justify-content: space-between; font-size: 11px; color: #94a3b8; font-weight: 700; margin-bottom: 5px;">
                <span>🔴 PISO/BE (${sl_px:,.2f})</span>
                <span style="color: {color_pnl}; font-weight: 800;">📍 POSICIÓN EN VIVO: {prog_pct:.1f}% HACIA TARGET FASE 1</span>
                <span>🟢 TARGET 1 (${tp1_px:,.2f})</span>
            </div>
            <div style="width: 100%; background: #0f172a; height: 12px; border-radius: 6px; overflow: hidden; position: relative; border: 1px solid rgba(255,255,255,0.12);">
                <div style="width: {prog_pct}%; background: linear-gradient(90deg, #ff3366 0%, #ffaa00 50%, #00ff88 100%); height: 100%; border-radius: 6px; box-shadow: 0 0 10px {color_pnl};"></div>
            </div>
        </div>
    </div>
    """)
    st.markdown(html_card, unsafe_allow_html=True)

def cargar_config():
    if os.path.exists(CONFIG_MODO_FILE):
        try:
            with open(CONFIG_MODO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {
        "modo_general": "REAL",
        "modo_btc_usdt": "REAL",
        "modo_btc_usdc": "REAL",
        "bloqueo_precio_max": True,
        "precio_max_compras": 85000.0,
        "orden_manual_pendiente": None
    }

def guardar_config(cfg):
    try:
        with open(CONFIG_MODO_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        st.error(f"Error guardando config: {e}")

def cargar_estado():
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {
        "capital_depositado_usd": 200.0,
        "cash_balance_usd": 200.0,
        "equity_total_usd": 200.0,
        "deuda_total_usd": 0.0,
        "margin_level_actual": 999.0,
        "posiciones": {
            "BTC-USDT": {"btc_pos": 0.0, "costo_prom": 0.0, "compras_realizadas": [], "ventas_realizadas": []},
            "BTC-USDC": {"btc_pos": 0.0, "costo_prom": 0.0, "compras_realizadas": [], "ventas_realizadas": []}
        },
        "pnl_acumulado_usd": 0.0,
        "total_fees_usd": 0.0,
        "total_trades": 0,
        "victorias": 0
    }

def obtener_saldo_real_binance_margin():
    if not BINANCE_KEY or not BINANCE_SECRET:
        return None
    for base_url in ["https://api3.binance.com", "https://api.binance.com", "https://api1.binance.com"]:
        try:
            s_time = requests.get(f"{base_url}/api/v3/time", timeout=5).json().get("serverTime", int(time.time()*1000))
            qs = f"recvWindow=60000&timestamp={s_time}"
            sig = hmac.new(BINANCE_SECRET.encode('utf-8'), qs.encode('utf-8'), hashlib.sha256).hexdigest()
            url = f"{base_url}/sapi/v1/margin/account?{qs}&signature={sig}"
            headers = {"X-MBX-APIKEY": BINANCE_KEY}
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200:
                res = r.json()
                if "marginLevel" in res:
                    ml = float(res.get("marginLevel", 999.0))
                    tot_asset_btc = float(res.get("totalAssetOfBtc", 0.0))
                    tot_net_btc = float(res.get("totalNetAssetOfBtc", 0.0))
                    tot_liab_btc = float(res.get("totalLiabilityOfBtc", 0.0))
                    
                    usdt_free = 0.0
                    for a in res.get("userAssets", []):
                        if a.get("asset") == "USDT":
                            usdt_free = clean_num(a.get("free", 0.0))
                            break
                            
                    return {
                        "margin_level": ml,
                        "total_asset_btc": tot_asset_btc,
                        "total_net_btc": tot_net_btc,
                        "total_liab_btc": tot_liab_btc,
                        "usdt_free": usdt_free
                    }
        except Exception:
            pass
    return None

# Estilos Visuales Neón Dark Glassmorphism
st.markdown("""
<style>
    .stApp { background-color: #080c14; color: #f1f5f9; }
    .header-box {
        background: radial-gradient(circle at center, rgba(247,147,26,0.12) 0%, transparent 75%);
        border: 1px solid rgba(247, 147, 26, 0.3); border-radius: 16px; padding: 22px;
        text-align: center; margin-bottom: 25px;
    }
    .header-box h1 { font-size: 30px; font-weight: 900; color: #fff; margin-bottom: 5px; }
    .header-box h1 span { color: #f7931a; text-shadow: 0 0 14px rgba(247,147,26,0.7); }
    .header-box p { color: #94a3b8; font-size: 14px; }
    
    .card-neon {
        background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(12px);
        border: 1px solid rgba(247, 147, 26, 0.25); border-radius: 14px; padding: 18px;
        margin-bottom: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }
    .kpi-val { font-family: monospace; font-size: 26px; font-weight: 800; }
    .neon-orange { color: #f7931a; text-shadow: 0 0 10px rgba(247,147,26,0.5); }
    .neon-green { color: #00ff88; text-shadow: 0 0 10px rgba(0,255,136,0.5); }
    .neon-cyan { color: #00e5ff; text-shadow: 0 0 10px rgba(0,229,255,0.5); }
    .neon-red { color: #ff3366; text-shadow: 0 0 10px rgba(255,51,102,0.5); }
</style>
""", unsafe_allow_html=True)

# Encabezado
st.markdown("""
<div class="header-box">
    <h1>⚡ CAZADOR PRO: <span>MEGA HÍBRIDO QUANTUM BTC DUAL</span></h1>
    <p>BINANCE CROSS MARGIN 5X | Pares BTCUSDT & BTCUSDC | $200 Base + $10 Quincenal | Cero Sentimientos</p>
</div>
""", unsafe_allow_html=True)

cfg = cargar_config()
st_data = cargar_estado()

# Sidebar de Configuración y Control
st.sidebar.markdown("### ⚙️ Control de Modos Operativos")
modo_gen = cfg.get("modo_general", "REAL")
st.sidebar.markdown(f"**Modo Global:** `{'🟢 REAL' if modo_gen == 'REAL' else '👻 FANTASMA (Paper Trading)'}`")

col_m1, col_m2 = st.sidebar.columns(2)
if col_m1.button("🟢 REAL", use_container_width=True):
    cfg["modo_general"] = "REAL"
    cfg["modo_btc_usdt"] = "REAL"
    cfg["modo_btc_usdc"] = "REAL"
    guardar_config(cfg)
    st.rerun()

if col_m2.button("👻 FANTASMA", use_container_width=True):
    cfg["modo_general"] = "FANTASMA"
    cfg["modo_btc_usdt"] = "FANTASMA"
    cfg["modo_btc_usdc"] = "FANTASMA"
    guardar_config(cfg)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛡️ Blindaje de Seguridad")

# 1. Checkbox Bloqueo de Compras si BTC > $85,000 USD
bloqueo_actual = cfg.get("bloqueo_precio_max", True)
chk_bloqueo = st.sidebar.checkbox(
    "🚫 Bloquear compras si BTC >= $85,000 USD",
    value=bloqueo_actual,
    help="Si está activado, la bot no comprará más si el precio de BTC supera los $85,000 USD."
)
if chk_bloqueo != bloqueo_actual:
    cfg["bloqueo_precio_max"] = chk_bloqueo
    guardar_config(cfg)
    st.toast(f"Filtro $85,000 {'ACTIVADO' if chk_bloqueo else 'DESACTIVADO'}")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🚨 Salida Manual de Emergencia")
st.sidebar.caption("Cierra posiciones inmediatamente antes de salir o dormir.")

col_c1, col_c2 = st.sidebar.columns(2)
if col_c1.button("🔴 CERRAR 100%", use_container_width=True, help="Cierra el 100% de las posiciones abiertas"):
    cfg["orden_manual_pendiente"] = {"symbol": "TODOS", "accion": "CERRAR_100", "pct": 1.0}
    guardar_config(cfg)
    st.success("✅ Orden de cierre 100% registrada. Se ejecutará en el siguiente ciclo (15s).")

if col_c2.button("🟠 VENDER 50%", use_container_width=True, help="Vende el 50% parcial de las posiciones abiertas"):
    cfg["orden_manual_pendiente"] = {"symbol": "TODOS", "accion": "VENDER_50", "pct": 0.5}
    guardar_config(cfg)
    st.warning("✅ Orden de venta 50% registrada. Se ejecutará en el siguiente ciclo (15s).")

# Cálculos KPIs Principales
cap_dep = clean_num(st_data.get("capital_depositado_usd", 200.0))
cash_bal = clean_num(st_data.get("cash_balance_usd", 200.0))
deuda_tot = clean_num(st_data.get("deuda_total_usd", 0.0))
ml_act = clean_num(st_data.get("margin_level_actual", 999.0))
pnl_acum = clean_num(st_data.get("pnl_acumulado_usd", 0.0))
total_fees = clean_num(st_data.get("total_fees_usd", 0.0))
total_trades = int(st_data.get("total_trades", 0))
wins = int(st_data.get("victorias", 0))
win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0

pos_usdt = st_data.get("posiciones", {}).get("BTC-USDT", {})
pos_usdc = st_data.get("posiciones", {}).get("BTC-USDC", {})
btc_tot = clean_num(pos_usdt.get("btc_pos", 0.0)) + clean_num(pos_usdc.get("btc_pos", 0.0))

px_ref_approx = 64000.0
equity_calc = cash_bal + (btc_tot * px_ref_approx) - deuda_tot
equity_tot = clean_num(st_data.get("equity_total_usd", equity_calc))

# SI ESTÁ EN MODO REAL, LEER SALDO BINANCE CROSS MARGIN 5X EN VIVO
if modo_gen == "REAL":
    saldo_bin = obtener_saldo_real_binance_margin()
    if saldo_bin:
        cash_bal = saldo_bin["usdt_free"]
        ml_act = saldo_bin["margin_level"]
        equity_tot = saldo_bin["total_net_btc"] * px_ref_approx
        deuda_tot = saldo_bin["total_liab_btc"] * px_ref_approx

# Sección Tarjetas Neón KPI (Fila 1: Saldo & Equity)
col_a1, col_a2, col_a3 = st.columns(3)

with col_a1:
    st.markdown(f"""
    <div class="card-neon">
        <div style="font-size:12px; color:#94a3b8; font-weight:700;">💵 USDT LIBRE EN BINANCE MARGIN</div>
        <div class="kpi-val neon-green">${cash_bal:,.2f} USDT</div>
        <div style="font-size:11px; color:#64748b; margin-top:4px;">{'🟡 Binance Margin 5X en Vivo' if modo_gen == 'REAL' else 'Margen Disponible Líquido'}</div>
    </div>
    """, unsafe_allow_html=True)

with col_a2:
    st.markdown(f"""
    <div class="card-neon">
        <div style="font-size:12px; color:#94a3b8; font-weight:700;">🏦 COLATERAL NETO REAL (NET ASSET)</div>
        <div class="kpi-val neon-cyan">${equity_tot:,.2f} USD</div>
        <div style="font-size:11px; color:#64748b; margin-top:4px;">{'🟡 Binance Margin 5X en Vivo' if modo_gen == 'REAL' else 'Cash + Colateral BTC - Deuda'}</div>
    </div>
    """, unsafe_allow_html=True)

with col_a3:
    st.markdown(f"""
    <div class="card-neon">
        <div style="font-size:12px; color:#94a3b8; font-weight:700;">💳 CAPITAL TOTAL DEPOSITADO</div>
        <div class="kpi-val neon-orange">${cap_dep:,.2f} USD</div>
        <div style="font-size:11px; color:#64748b; margin-top:4px;">$200 Base + Inyecciones Quincenales</div>
    </div>
    """, unsafe_allow_html=True)

# Fila 2: PnL, Margin Level, Win Rate
col_b1, col_b2, col_b3 = st.columns(3)

with col_b1:
    pnl_class = "neon-green" if pnl_acum >= 0 else "neon-red"
    st.markdown(f"""
    <div class="card-neon">
        <div style="font-size:12px; color:#94a3b8; font-weight:700;">💰 PNL REALIZADO NETO</div>
        <div class="kpi-val {pnl_class}">${pnl_acum:+,.2f} USD</div>
        <div style="font-size:11px; color:#64748b; margin-top:4px;">Deuda Borrow: ${deuda_tot:,.2f} USD</div>
    </div>
    """, unsafe_allow_html=True)

with col_b2:
    ml_color = "neon-green" if ml_act >= 2.0 else ("neon-orange" if ml_act >= 1.5 else "neon-red")
    st.markdown(f"""
    <div class="card-neon">
        <div style="font-size:12px; color:#94a3b8; font-weight:700;">⚡ SALUD MARGIN LEVEL BINANCE</div>
        <div class="kpi-val {ml_color}">{ml_act:.2f}x</div>
        <div style="font-size:11px; color:#64748b; margin-top:4px;">Límite Mínimo Permitido: 1.50x</div>
    </div>
    """, unsafe_allow_html=True)

with col_b3:
    st.markdown(f"""
    <div class="card-neon">
        <div style="font-size:12px; color:#94a3b8; font-weight:700;">🎯 WIN RATE & INVENTARIO BTC</div>
        <div class="kpi-val neon-green">{win_rate:.1f}%</div>
        <div style="font-size:11px; color:#64748b; margin-top:4px;">{btc_tot:.5f} BTC en Cartera ({wins}/{total_trades} Wins)</div>
    </div>
    """, unsafe_allow_html=True)

tab_pos, tab_hist, tab_cfg = st.tabs([
    "📈 POSICIONES ACTIVAS DUAL (BTCUSDT / BTCUSDC)",
    "📜 HISTORIAL DE OPERACIONES BINANCE 5X",
    "⚙️ CONFIGURACIÓN & REGLAS DE ORO (SEPTIEMBRE 2027)"
])

with tab_pos:
    precios_bin_vivos = obtener_precios_en_vivo_binance()
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        st.markdown("#### 🪙 Cargador 1: BTCUSDT (Binance Margin)")
        b_usdt = clean_num(pos_usdt.get("btc_pos", 0.0))
        c_usdt = clean_num(pos_usdt.get("costo_prom", 0.0))
        compras_usdt = pos_usdt.get("compras_realizadas", [])
        
        if b_usdt > 0:
            px_v_usdt = precios_bin_vivos.get("BTC-USDT", c_usdt)
            render_tarjeta_posicion_viva_btc("BTC-USDT", pos_usdt, px_v_usdt)
        else:
            st.info("Sin compras activas en BTCUSDT. Esperando Piso de 7 Días.")
            
        if compras_usdt:
            st.markdown("**📜 Historial de Balas Inyectadas en BTCUSDT:**")
            df_c1 = pd.DataFrame(compras_usdt)
            st.dataframe(df_c1, use_container_width=True)
            
    with col_p2:
        st.markdown("#### 🪙 Cargador 2: BTCUSDC (Binance Margin)")
        b_usdc = clean_num(pos_usdc.get("btc_pos", 0.0))
        c_usdc = clean_num(pos_usdc.get("costo_prom", 0.0))
        compras_usdc = pos_usdc.get("compras_realizadas", [])
        
        if b_usdc > 0:
            px_v_usdc = precios_bin_vivos.get("BTC-USDC", c_usdc)
            render_tarjeta_posicion_viva_btc("BTC-USDC", pos_usdc, px_v_usdc)
        else:
            st.info("Sin compras activas en BTCUSDC. Esperando Piso de 7 Días.")
            
        if compras_usdc:
            st.markdown("**📜 Historial de Balas Inyectadas en BTCUSDC:**")
            df_c2 = pd.DataFrame(compras_usdc)
            st.dataframe(df_c2, use_container_width=True)

with tab_hist:
    st.markdown("#### 📜 Registro de Ventas y Cierres Semáforo (30/30/40)")
    hist_ventas = []
    for s in ["BTC-USDT", "BTC-USDC"]:
        for v in st_data.get("posiciones", {}).get(s, {}).get("ventas_realizadas", []):
            v_copy = v.copy()
            v_copy["par"] = s
            hist_ventas.append(v_copy)
            
    if hist_ventas:
        df_h = pd.DataFrame(hist_ventas)
        st.dataframe(df_h, use_container_width=True)
    else:
        st.caption("Aún no se han ejecutado cierres parciales de ganancia.")

with tab_cfg:
    st.markdown("#### ⚙️ Parámetros de Blindaje Cuántico (Binance Cross Margin 5X)")
    st.json(cfg)
    st.caption("Última actualización de estado: " + str(st_data.get("ultima_actualizacion", "N/A")))

time.sleep(5)
st.rerun()
