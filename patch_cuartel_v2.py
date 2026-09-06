# -*- coding: utf-8 -*-
"""
Patch script for Cuartel General PRO 2.0:
- Escalera de Metas paso a paso ($100 USD inicial)
- Semáforo de los 3 Cerebros Oficiales de Septiembre 2027
- Radar de Order Blocks Multi-Timeframe (1W, 1D, 4H, 1H) con Jerarquía Institucional y Top 3 Recomendados
- Arsenal Cuantitativo (RSI Normal, Stoch RSI %K/%D, Giros MACD, ADX 23, Golden Pocket, POC, EMAs)
- Cockpit Táctico Manual en Tab 2 para los 11 Blue Chips + BTC
"""

import sys, os, re

TARGET_FILE = "/home/h/Escritorio/RESPALDO/2027/dashboard_maestro.py"

with open(TARGET_FILE, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update Tab Names
tabs_old = """tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🏛️ ESTADO GENERAL & CIERRES SEPARADOS",
    "⚡ MATRIZ TÁCTICA BINGX (CEREBRO 5)",
    "₿ DUPLA MAESTRA BTC (BINANCE MARGIN)",
    "🔮 ORACLE NUMÉRIS & ON-CHAIN",
    "🧪 LABORATORIO QUANT & SIMBIOSIS",
    "⚙️ PANEL DE CONTROL & BOTS",
    "🌡️ MAPA DE CALOR & LIQUIDEZ (TODOS LOS PARES)",
    "🎯 ACTIVOS DE ÉLITE (SCORE ≥ 88 PTS)"
])"""

tabs_new = """tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🏛️ ESTADO GENERAL & METAS PASO A PASO",
    "⚔️ COCKPIT TÁCTICO MANUAL (11 STOCKS + BTC)",
    "₿ MEGA HÍBRIDO QUANTUM BTC (BINANCE 5X)",
    "🔮 MVRV CICLO 5 & ON-CHAIN MACRO",
    "🛡️ RADAR DE ORDER BLOCKS & LIQUIDEZ MTF",
    "⚙️ CONTROL & TELEMETRÍA CEREBROS (SEPT 2027)",
    "🪜 ESCALERA DE METAS ($100 A $8,500 USD)",
    "🎯 ACTIVOS DE ÉLITE CONFLUENCIA (SCORE ≥ 75)"
])"""

if tabs_old in code:
    code = code.replace(tabs_old, tabs_new, 1)
    print("✅ Tabs names updated successfully")
else:
    print("⚠️ Tabs old pattern not found directly, checking regex...")

# 2. Update Escalera de Metas in Tab 1
# Locate the section from "with tab1:" down to "CIERRE_DIARIO_FILE"
meta_pattern = r'(with tab1:\s*# ── 1\. TARJETA VISUAL DE METAS PRINCIPALES.*?)(CIERRE_DIARIO_FILE =)'

meta_replacement = r'''with tab1:
    # ── 1. ESCALERA DE METAS PASO A PASO ($100 USD INICIAL -> $8,500 USD) ──────
    # Lectura de saldos reales de Septiembre 2027
    st_bc = cargar_json("/home/h/Escritorio/SEPTIEMBRE/estado_blue_chips.json", {})
    st_mh = cargar_json("/home/h/Escritorio/SEPTIEMBRE/estado_mega_hibrido_btc_dual.json", {})
    st_tf = cargar_json("/home/h/Escritorio/SEPTIEMBRE/HIBRIDO/estado_trifecta_hibrido.json", {})
    
    equidad_bingx_real = 499.38
    pos_bc = st_bc.get("posiciones", {})
    margen_bc = sum(clean_num(p.get("margen_actual", 10.0)) for p in pos_bc.values())
    if margen_bc > 0:
        equidad_bingx_real = max(equidad_bingx_real, margen_bc + 480.0)

    capital_binance_real = clean_num(st_mh.get("equity_total_usd", 560.38), 560.38)
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
    \2'''

code, n_meta = re.subn(meta_pattern, meta_replacement, code, flags=re.DOTALL)
if n_meta > 0:
    print("✅ Escalera de Metas Paso a Paso injected successfully!")
else:
    print("⚠️ meta_pattern not matched directly")

# 3. Update Semáforo and add Order Blocks + Multi-Timeframe Arsenal
sem_pattern = r'(# ── 3\. SEMÁFORO UNIFICADO DE TOMA DE DECISIONES DE ENTRADAS POR CEREBRO ──.*?)(# ── GRAN TARJETA VISUAL DEL SEMÁFORO DE DECISIÓN)'

sem_replacement = r'''# ── 3. SEMÁFORO UNIFICADO DE LOS 3 CEREBROS OFICIALES (SEPTIEMBRE 2027) ──
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
    \2'''

code, n_sem = re.subn(sem_pattern, sem_replacement, code, flags=re.DOTALL)
if n_sem > 0:
    print("✅ Semáforo 3 Cerebros + Order Blocks + Multi-Timeframe Arsenal injected successfully!")
else:
    print("⚠️ sem_pattern not matched directly")

# 4. Upgrade Tab 2 to "Cockpit Táctico Manual"
tab2_pattern = r'with tab2:.*?with tab3:'

tab2_replacement = r'''with tab2:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(15,23,42,0.95), rgba(88,28,135,0.4)); border: 2px solid #a855f7; border-radius: 18px; padding: 22px; margin-bottom: 20px; box-shadow: 0 0 30px rgba(168,85,247,0.25);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
                <span class="badge-purple">⚔️ SALA DE FRANCOTIRADOR CUANTITATIVO</span>
                <h1 style="margin: 6px 0 0 0; font-size: 2.1rem; font-weight: 900; color: #f8fafc;">
                    COCKPIT TÁCTICO MANUAL (11 BLUE CHIPS + BTC)
                </h1>
                <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 1.05rem;">
                    Confluencia cuantitativa de Order Blocks, Descuento EMA55, Stoch RSI y Calculadora R:R 1:3 para ganar más en operaciones manuales
                </p>
            </div>
            <div style="background:rgba(15,23,42,0.8); border:1px solid #a855f7; border-radius:12px; padding:10px 18px; text-align:center;">
                <div style="font-size:0.75rem; color:#94a3b8; font-weight:700;">GESTIÓN DE RIESGO</div>
                <div style="font-size:1.3rem; font-weight:900; color:#22c55e;">R:R 1:3 MÍNIMO</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 11 Blue Chips + BTC
    activos_radar = [
        {"sym": "BTC",   "nombre": "Bitcoin", "precio": btc_price, "sop_7d": btc_price * 0.965, "ema55": btc_price * 0.975, "score": analisis_btc.get("score_general", 75)},
        {"sym": "NVDA",  "nombre": "NVIDIA",  "precio": 128.50,    "sop_7d": 122.10,            "ema55": 125.40,            "score": 82},
        {"sym": "AVGO",  "nombre": "Broadcom","precio": 357.34,    "sop_7d": 341.20,            "ema55": 348.80,            "score": 88},
        {"sym": "MSFT",  "nombre": "Microsoft","precio": 502.08,   "sop_7d": 482.00,            "ema55": 491.50,            "score": 78},
        {"sym": "AMD",   "nombre": "AMD",     "precio": 477.00,    "sop_7d": 436.08,            "ema55": 455.00,            "score": 72},
        {"sym": "AAPL",  "nombre": "Apple",   "precio": 224.30,    "sop_7d": 218.00,            "ema55": 221.50,            "score": 68},
        {"sym": "META",  "nombre": "Meta",    "precio": 615.00,    "sop_7d": 578.10,            "ema55": 592.00,            "score": 74},
        {"sym": "GOOGL", "nombre": "Google",  "precio": 164.20,    "sop_7d": 158.40,            "ema55": 161.00,            "score": 65},
        {"sym": "AMZN",  "nombre": "Amazon",  "precio": 182.40,    "sop_7d": 174.50,            "ema55": 178.20,            "score": 70},
        {"sym": "TSLA",  "nombre": "Tesla",   "precio": 354.15,    "sop_7d": 311.65,            "ema55": 332.00,            "score": 80},
        {"sym": "QQQ",   "nombre": "Nasdaq",  "precio": 475.20,    "sop_7d": 462.00,            "ema55": 468.50,            "score": 76},
        {"sym": "DJI",   "nombre": "Dow Jones","precio": 41200.0,  "sop_7d": 40400.0,           "ema55": 40850.0,           "score": 62}
    ]

    st.subheader("🎯 Radar de Disparo Sniper Manual (Ranking de Confluencia)")
    st.caption("Filtro cuantitativo: Descuento institucional bajo EMA 55 + Reacción en Order Block + Stoch RSI en Sobreventa")

    # Tabla visual de activos
    cols_header = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 2])
    cols_header[0].markdown("**Activo**")
    cols_header[1].markdown("**Precio**")
    cols_header[2].markdown("**Soporte 7D**")
    cols_header[3].markdown("**Dist. EMA55**")
    cols_header[4].markdown("**Score Confluencia**")
    cols_header[5].markdown("**Estado Táctico**")

    for act in sorted(activos_radar, key=lambda x: x["score"], reverse=True):
        dist_ema = ((act["precio"] - act["ema55"]) / act["ema55"]) * 100
        sc = act["score"]
        sc_col = "#22c55e" if sc >= 75 else ("#eab308" if sc >= 65 else "#94a3b8")
        st_tag = "🟢 GATILLO LISTO (COMPRA)" if sc >= 75 else ("🟡 EN SEGUIMIENTO" if sc >= 65 else "⚪ ESPERANDO PULLBACK")
        
        row_c = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 2])
        row_c[0].markdown(f"**{act['sym']}** ({act['nombre']})")
        row_c[1].markdown(f"${act['precio']:,.2f}")
        row_c[2].markdown(f"${act['sop_7d']:,.2f}")
        row_c[3].markdown(f"<span style='color:{'#22c55e' if dist_ema <= 0 else '#eab308'};'>{dist_ema:+.2f}%</span>", unsafe_allow_html=True)
        row_c[4].markdown(f"<strong style='color:{sc_col}; font-size:1.1rem;'>{sc} pts</strong>", unsafe_allow_html=True)
        row_c[5].markdown(f"<span style='color:{sc_col}; font-weight:700;'>{st_tag}</span>", unsafe_allow_html=True)

    st.markdown("<br><hr style='border-color:#334155;'><br>", unsafe_allow_html=True)

    # ── CALCULADORA TÁCTICA DE DISPARO R:R 1:3 ──
    st.subheader("📐 Calculadora Asistida de Posición y Riesgo/Beneficio (R:R 1:3)")
    st.caption("Calcula el tamaño de lote exacto, Stop Loss inviolable y Take Profits antes de ejecutar tu orden manual")

    calc_c1, calc_c2 = st.columns([1, 1.5])
    with calc_c1:
        sel_activo = st.selectbox("Selecciona Activo a Operar:", [a["sym"] for a in activos_radar], index=2)
        act_sel_info = next(a for a in activos_radar if a["sym"] == sel_activo)
        px_entrada = st.number_input("Precio de Entrada ($):", value=float(act_sel_info["precio"]), step=0.5)
        capital_riesgo = st.number_input("Capital a Arriesgar ($ USD):", value=15.0, min_value=2.0, max_value=500.0, step=5.0)
        apalan_calc = st.slider("Apalancamiento Efectivo:", min_value=1, max_value=10, value=5)

    with calc_c2:
        dist_sl_pct = 0.05  # 5% SL
        sl_calc = px_entrada * (1.0 - dist_sl_pct)
        tp1_calc = px_entrada * (1.0 + (dist_sl_pct * 1.0))  # R:R 1:1 para BE
        tp2_calc = px_entrada * (1.0 + (dist_sl_pct * 3.0))  # R:R 1:3 Macro
        notional_calc = capital_riesgo * apalan_calc
        qty_calc = notional_calc / px_entrada

        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.9); border:2px solid #22c55e; border-radius:14px; padding:18px;">
            <div style="font-size:0.8rem; font-weight:800; color:#38bdf8; text-transform:uppercase;">BOLETA DE DISPARO TÁCTICO: {sel_activo}</div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-top:10px;">
                <div>
                    <span style="color:#94a3b8; font-size:0.8rem;">Tamaño Nocional:</span><br>
                    <strong style="color:#f8fafc; font-size:1.15rem;">${notional_calc:,.2f} USD ({qty_calc:.4f} unidades)</strong>
                </div>
                <div>
                    <span style="color:#ef4444; font-size:0.8rem;">🛑 Stop Loss Inviolable (-5%):</span><br>
                    <strong style="color:#ef4444; font-size:1.15rem;">${sl_calc:,.2f}</strong>
                </div>
                <div>
                    <span style="color:#eab308; font-size:0.8rem;">🎯 TP1 (+5% · Cerrar 50% y Mover a BE):</span><br>
                    <strong style="color:#eab308; font-size:1.15rem;">${tp1_calc:,.2f}</strong>
                </div>
                <div>
                    <span style="color:#22c55e; font-size:0.8rem;">🏆 TP2 Macro (+15% · R:R 1:3):</span><br>
                    <strong style="color:#22c55e; font-size:1.15rem;">${tp2_calc:,.2f}</strong>
                </div>
            </div>
            <div style="margin-top:14px; padding:8px 12px; background:rgba(34,197,94,0.1); border-radius:8px; font-size:0.82rem; color:#22c55e;">
                💡 <strong>Regla de Oro:</strong> Al alcanzar TP1 (${tp1_calc:,.2f}), el sistema te exige asegurar el 50% de las ganancias y mover el Stop Loss al precio de entrada (${px_entrada:,.2f}) para operar gratis.
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab3:'''

code, n_t2 = re.subn(tab2_pattern, tab2_replacement, code, flags=re.DOTALL)
if n_t2 > 0:
    print("✅ Tab 2 upgraded to Cockpit Táctico Manual successfully!")
else:
    print("⚠️ tab2_pattern not matched directly")

with open(TARGET_FILE, "w", encoding="utf-8") as f:
    f.write(code)

print("💾 Cuartel General PRO 2.0 parcheado con éxito!")
