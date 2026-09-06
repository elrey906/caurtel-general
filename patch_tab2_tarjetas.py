# -*- coding: utf-8 -*-
"""
Patch script to upgrade Tab 2 of dashboard_maestro.py:
Transforms Cockpit Táctico into dedicated asset cards with exact LONG and SHORT plans,
ADN of Stop Loss, TP1 (BE), TP2 (R:R 1:3), Order Blocks, and Confluence Scores.
"""

import sys, os, re

TARGET_FILE = "/home/h/Escritorio/RESPALDO/2027/dashboard_maestro.py"

with open(TARGET_FILE, "r", encoding="utf-8") as f:
    code = f.read()

tab2_target_pattern = r'with tab2:.*?with tab3:'

tab2_new_code = r'''with tab2:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(15,23,42,0.95), rgba(88,28,135,0.4)); border: 2px solid #a855f7; border-radius: 18px; padding: 22px; margin-bottom: 20px; box-shadow: 0 0 30px rgba(168,85,247,0.25);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
                <span class="badge-purple">⚔️ SALA DE FRANCOTIRADOR CUANTITATIVO</span>
                <h1 style="margin: 6px 0 0 0; font-size: 2.1rem; font-weight: 900; color: #f8fafc;">
                    TARJETAS TÁCTICAS: PLANES LONG & SHORT CON ADN COMPLETO
                </h1>
                <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 1.05rem;">
                    Niveles exactos en dólares ($) para entradas manuales, Stop Loss inviolable, TP1 (Break-Even) y TP2 (R:R 1:3) por activo
                </p>
            </div>
            <div style="background:rgba(15,23,42,0.8); border:1px solid #a855f7; border-radius:12px; padding:10px 18px; text-align:center;">
                <div style="font-size:0.75rem; color:#94a3b8; font-weight:700;">GESTIÓN INSTITUCIONAL</div>
                <div style="font-size:1.3rem; font-weight:900; color:#22c55e;">ADN DE RIESGO 1:3</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 12 Activos Oficiales con su ADN Cuantitativo completo
    activos_detalle = [
        {
            "sym": "BTC",
            "nombre": "Bitcoin",
            "tipo": "CRIPTO",
            "exchange": "Binance Cross Margin 5X",
            "precio": btc_price,
            "sop_7d": btc_price * 0.965,
            "res_7d": btc_price * 1.045,
            "ema55": btc_price * 0.978,
            "ema200": btc_price * 0.940,
            "ob_dom": f"1W OB ${btc_price*0.96:,.0f} – ${btc_price*0.975:,.0f}",
            "rsi": 54.2,
            "stoch_k": 28.4,
            "adx": 34.5,
            "score": analisis_btc.get("score_general", 78),
            "recom": "LONG (Acumulación en Soportes)",
            "long_trigger": btc_price * 0.972,
            "long_sl": btc_price * 0.935,
            "long_tp1": btc_price * 1.035,
            "long_tp2": btc_price * 1.110,
            "short_trigger": btc_price * 1.040,
            "short_sl": btc_price * 1.075,
            "short_tp1": btc_price * 0.985,
            "short_tp2": btc_price * 0.915,
            "nota": "Priorizar compras límite en Soporte 7D y retrocesos a EMA 55."
        },
        {
            "sym": "AVGO",
            "nombre": "Broadcom",
            "tipo": "ACCION",
            "exchange": "BingX Perpetuos",
            "precio": 357.34,
            "sop_7d": 341.20,
            "res_7d": 378.50,
            "ema55": 348.80,
            "ema200": 332.00,
            "ob_dom": "1D Bullish OB $342.00 – $346.50",
            "rsi": 46.8,
            "stoch_k": 18.2,
            "adx": 29.4,
            "score": 88,
            "recom": "LONG (Rebote en Descuento)",
            "long_trigger": 348.50,
            "long_sl": 328.00,
            "long_tp1": 368.50,
            "long_tp2": 408.00,
            "short_trigger": 376.00,
            "short_sl": 394.00,
            "short_tp1": 358.00,
            "short_tp2": 322.00,
            "nota": "Stoch RSI en sobreventa extrema (%K < 20). Operación institucional de alta confluencia."
        },
        {
            "sym": "NVDA",
            "nombre": "NVIDIA",
            "tipo": "ACCION",
            "exchange": "BingX Perpetuos",
            "precio": 128.50,
            "sop_7d": 122.10,
            "res_7d": 136.80,
            "ema55": 125.40,
            "ema200": 118.00,
            "ob_dom": "4H Bullish OB $123.00 – $124.50",
            "rsi": 49.5,
            "stoch_k": 22.1,
            "adx": 31.0,
            "score": 82,
            "recom": "LONG (Continuación Alcista)",
            "long_trigger": 125.20,
            "long_sl": 118.50,
            "long_tp1": 132.80,
            "long_tp2": 146.50,
            "short_trigger": 136.00,
            "short_sl": 142.50,
            "short_tp1": 129.50,
            "short_tp2": 116.50,
            "nota": "EMA 55 testeada con mecha inferior de absorción. Entrada óptima con SL ajustado."
        },
        {
            "sym": "TSLA",
            "nombre": "Tesla",
            "tipo": "ACCION",
            "exchange": "BingX Perpetuos",
            "precio": 354.15,
            "sop_7d": 311.65,
            "res_7d": 372.00,
            "ema55": 332.00,
            "ema200": 298.00,
            "ob_dom": "1D Bullish OB $320.00 – $328.00",
            "rsi": 53.0,
            "stoch_k": 32.5,
            "adx": 38.2,
            "score": 80,
            "recom": "LONG (Momentum Fuerte)",
            "long_trigger": 338.00,
            "long_sl": 311.65,
            "long_tp1": 368.00,
            "long_tp2": 418.00,
            "short_trigger": 371.00,
            "short_sl": 395.00,
            "short_tp1": 348.00,
            "short_tp2": 302.00,
            "nota": "Posición activa en BingX. Proteger ganancias en TP1 y mover SL a Break-Even."
        },
        {
            "sym": "MSFT",
            "nombre": "Microsoft",
            "tipo": "ACCION",
            "exchange": "BingX Perpetuos",
            "precio": 502.08,
            "sop_7d": 482.00,
            "res_7d": 525.00,
            "ema55": 491.50,
            "ema200": 465.00,
            "ob_dom": "1W Bullish OB $485.00 – $492.00",
            "rsi": 51.2,
            "stoch_k": 34.0,
            "adx": 26.8,
            "score": 78,
            "recom": "LONG (Short Manual Protegido)",
            "long_trigger": 494.00,
            "long_sl": 482.00,
            "long_tp1": 512.00,
            "long_tp2": 548.00,
            "short_trigger": 524.00,
            "short_sl": 542.00,
            "short_tp1": 506.00,
            "short_tp2": 470.00,
            "nota": "🔒 BLINDAJE: El SHORT manual de MSFT es intocable para los bots. Compras permitidas en soporte."
        },
        {
            "sym": "QQQ",
            "nombre": "Nasdaq 100 ETF",
            "tipo": "ETF",
            "exchange": "BingX Perpetuos",
            "precio": 475.20,
            "sop_7d": 462.00,
            "res_7d": 492.00,
            "ema55": 468.50,
            "ema200": 448.00,
            "ob_dom": "1D Bullish OB $464.00 – $467.50",
            "rsi": 52.4,
            "stoch_k": 36.0,
            "adx": 25.4,
            "score": 76,
            "recom": "LONG (Soporte Índice)",
            "long_trigger": 469.00,
            "long_sl": 458.00,
            "long_tp1": 482.00,
            "long_tp2": 508.00,
            "short_trigger": 491.00,
            "short_sl": 504.00,
            "short_tp1": 478.00,
            "short_tp2": 452.00,
            "nota": "Excelente para cobertura macro con bajo deslizamiento."
        },
        {
            "sym": "META",
            "nombre": "Meta Platforms",
            "tipo": "ACCION",
            "exchange": "BingX Perpetuos",
            "precio": 615.00,
            "sop_7d": 578.10,
            "res_7d": 642.00,
            "ema55": 592.00,
            "ema200": 550.00,
            "ob_dom": "1D Bullish OB $582.00 – $590.00",
            "rsi": 55.0,
            "stoch_k": 42.0,
            "adx": 30.5,
            "score": 74,
            "recom": "ESPERA (Cerca de Resistencia)",
            "long_trigger": 592.00,
            "long_sl": 572.00,
            "long_tp1": 622.00,
            "long_tp2": 672.00,
            "short_trigger": 640.00,
            "short_sl": 662.00,
            "short_tp1": 618.00,
            "short_tp2": 574.00,
            "nota": "Esperar pullback hacia EMA 55 antes de gatillar nuevo Long."
        },
        {
            "sym": "AMD",
            "nombre": "AMD",
            "tipo": "ACCION",
            "exchange": "BingX Perpetuos",
            "precio": 477.00,
            "sop_7d": 436.08,
            "res_7d": 508.00,
            "ema55": 455.00,
            "ema200": 420.00,
            "ob_dom": "4H Bullish OB $448.00 – $454.00",
            "rsi": 48.0,
            "stoch_k": 25.5,
            "adx": 28.0,
            "score": 72,
            "recom": "LONG (Descuento Táctico)",
            "long_trigger": 458.00,
            "long_sl": 436.00,
            "long_tp1": 485.00,
            "long_tp2": 535.00,
            "short_trigger": 506.00,
            "short_sl": 528.00,
            "short_tp1": 484.00,
            "short_tp2": 440.00,
            "nota": "Posición activa con SL protegido en $436.08. Buscar TP1 en $483.48."
        },
        {
            "sym": "AMZN",
            "nombre": "Amazon",
            "tipo": "ACCION",
            "exchange": "BingX Perpetuos",
            "precio": 182.40,
            "sop_7d": 174.50,
            "res_7d": 194.00,
            "ema55": 178.20,
            "ema200": 170.00,
            "ob_dom": "1D Bullish OB $176.00 – $178.00",
            "rsi": 50.5,
            "stoch_k": 38.0,
            "adx": 22.0,
            "score": 70,
            "recom": "ESPERA (ADX < 23 Lateral)",
            "long_trigger": 178.00,
            "long_sl": 171.00,
            "long_tp1": 187.00,
            "long_tp2": 204.00,
            "short_trigger": 193.50,
            "short_sl": 201.00,
            "short_tp1": 186.00,
            "short_tp2": 172.00,
            "nota": "Mercado lateral; esperar ruptura con volumen institucional o retroceso a soporte."
        },
        {
            "sym": "AAPL",
            "nombre": "Apple",
            "tipo": "ACCION",
            "exchange": "BingX Perpetuos",
            "precio": 224.30,
            "sop_7d": 218.00,
            "res_7d": 236.00,
            "ema55": 221.50,
            "ema200": 210.00,
            "ob_dom": "1W Bullish OB $216.00 – $219.50",
            "rsi": 47.0,
            "stoch_k": 26.0,
            "adx": 24.5,
            "score": 68,
            "recom": "LONG (Consolidación Favorable)",
            "long_trigger": 221.00,
            "long_sl": 214.00,
            "long_tp1": 229.00,
            "long_tp2": 245.00,
            "short_trigger": 235.00,
            "short_sl": 243.00,
            "short_tp1": 227.00,
            "short_tp2": 211.00,
            "nota": "Soporte institucional sólido en $218.00. R:R favorable para swing trading."
        },
        {
            "sym": "GOOGL",
            "nombre": "Alphabet",
            "tipo": "ACCION",
            "exchange": "BingX Perpetuos",
            "precio": 164.20,
            "sop_7d": 158.40,
            "res_7d": 174.00,
            "ema55": 161.00,
            "ema200": 152.00,
            "ob_dom": "1D Bullish OB $159.00 – $161.00",
            "rsi": 48.5,
            "stoch_k": 30.0,
            "adx": 21.5,
            "score": 65,
            "recom": "ESPERA (Baja Volatilidad)",
            "long_trigger": 160.80,
            "long_sl": 154.50,
            "long_tp1": 168.00,
            "long_tp2": 182.00,
            "short_trigger": 173.50,
            "short_sl": 180.50,
            "short_tp1": 166.50,
            "short_tp2": 153.00,
            "nota": "Esperar confluencia de giro en Stoch RSI y volumen expansivo."
        },
        {
            "sym": "DJI",
            "nombre": "Dow Jones Ind.",
            "tipo": "INDICE",
            "exchange": "BingX Perpetuos",
            "precio": 41200.0,
            "sop_7d": 40400.0,
            "res_7d": 42100.0,
            "ema55": 40850.0,
            "ema200": 39500.0,
            "ob_dom": "1W Bullish OB $40200 – $40600",
            "rsi": 56.0,
            "stoch_k": 48.0,
            "adx": 27.0,
            "score": 62,
            "recom": "ESPERA (Cerca de Máximos)",
            "long_trigger": 40750.0,
            "long_sl": 39950.0,
            "long_tp1": 41650.0,
            "long_tp2": 43150.0,
            "short_trigger": 42050.0,
            "short_sl": 42850.0,
            "short_tp1": 41250.0,
            "short_tp2": 39750.0,
            "nota": "Índice cerca de zona alta; riesgo de falso rompimiento. Priorizar shorts tácticos o esperar soporte."
        }
    ]

    # Filtros y controles
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        st.subheader("📋 Tarjetas Tácticas Individuales por Activo")
        st.caption("Cada tarjeta incluye ADN de riesgo, precios de gatillo para LONG y SHORT, Stop Loss inviolable y Take Profits")
    with col_f2:
        filtro_tipo = st.multiselect("Filtrar por Mercado:", ["CRIPTO", "ACCION", "ETF", "INDICE"], default=["CRIPTO", "ACCION", "ETF", "INDICE"])

    activos_filtrados = [a for a in activos_detalle if a["tipo"] in filtro_tipo]

    # Renderizado en Grid de 2 Columnas para máxima legibilidad
    for i in range(0, len(activos_filtrados), 2):
        row_c1, row_c2 = st.columns(2)
        cols_tarjetas = [row_c1, row_c2]
        
        for j in range(2):
            if i + j < len(activos_filtrados):
                act = activos_filtrados[i + j]
                with cols_tarjetas[j]:
                    sc = act["score"]
                    card_border = "#22c55e" if sc >= 75 else ("#eab308" if sc >= 65 else "#64748b")
                    recom_color = "#22c55e" if "LONG" in act["recom"] else ("#ef4444" if "SHORT" in act["recom"] else "#eab308")
                    
                    st.markdown(f"""
                    <div style="background: rgba(15,23,42,0.92); border: 2px solid {card_border}; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 0 25px rgba(0,0,0,0.4);">
                        <!-- Cabecera de la Tarjeta -->
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid #334155; padding-bottom:12px; margin-bottom:14px;">
                            <div>
                                <span style="font-size:0.75rem; font-weight:800; background:{card_border}22; color:{card_border}; padding:3px 8px; border-radius:6px; text-transform:uppercase;">
                                    {act['tipo']} · {act['exchange']}
                                </span>
                                <h2 style="margin:6px 0 0 0; font-size:1.6rem; font-weight:900; color:#f8fafc;">
                                    {act['sym']} <span style="font-size:1rem; font-weight:600; color:#94a3b8;">({act['nombre']})</span>
                                </h2>
                                <div style="font-size:1.8rem; font-weight:900; color:#38bdf8; margin-top:2px;">
                                    ${act['precio']:,.2f} <span style="font-size:0.85rem; color:#94a3b8;">USD</span>
                                </div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-size:0.75rem; color:#94a3b8; font-weight:700;">CONFLUENCIA</div>
                                <div style="font-size:2.2rem; font-weight:900; color:{card_border}; line-height:1;">
                                    {sc}<span style="font-size:1rem; color:#64748b;">/100</span>
                                </div>
                                <div style="font-size:0.8rem; font-weight:800; color:{recom_color}; margin-top:4px;">
                                    {act['recom']}
                                </div>
                            </div>
                        </div>

                        <!-- 🧬 ADN Cuantitativo del Activo -->
                        <div style="background:rgba(30,41,59,0.5); border-radius:10px; padding:10px 14px; margin-bottom:14px; font-size:0.82rem; color:#cbd5e1;">
                            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                <span>🛡️ <strong>Soporte 7D:</strong> ${act['sop_7d']:,.2f}</span>
                                <span>🏰 <strong>Techo 7D:</strong> ${act['res_7d']:,.2f}</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                <span>📦 <strong>Order Block:</strong> {act['ob_dom']}</span>
                                <span>📈 <strong>EMA 55:</strong> ${act['ema55']:,.2f}</span>
                            </div>
                            <div style="display:flex; justify-content:space-between;">
                                <span>⚡ <strong>Stoch %K:</strong> {act['stoch_k']:.1f} (RSI {act['rsi']:.1f})</span>
                                <span>🌪️ <strong>ADX:</strong> {act['adx']:.1f} {'🟢 Fuerza' if act['adx']>=23 else '🔴 Lateral'}</span>
                            </div>
                        </div>

                        <!-- 🎯 Planes Operativos LONG vs SHORT -->
                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:14px;">
                            <!-- PLAN LONG -->
                            <div style="background:rgba(34,197,94,0.08); border:1px solid rgba(34,197,94,0.3); border-radius:10px; padding:12px;">
                                <div style="font-size:0.85rem; font-weight:800; color:#22c55e; border-bottom:1px solid rgba(34,197,94,0.2); padding-bottom:4px; margin-bottom:8px;">
                                    🟢 PLAN COMPRA (LONG)
                                </div>
                                <div style="font-size:0.8rem; color:#cbd5e1; line-height:1.6;">
                                    🎯 <strong>Gatillo Entrada:</strong> <strong style="color:#f8fafc;">${act['long_trigger']:,.2f}</strong><br>
                                    🛑 <strong>Stop Loss:</strong> <strong style="color:#ef4444;">${act['long_sl']:,.2f}</strong><br>
                                    🎯 <strong>TP1 (50% + BE):</strong> <strong style="color:#eab308;">${act['long_tp1']:,.2f}</strong><br>
                                    🏆 <strong>TP2 (R:R 1:3):</strong> <strong style="color:#22c55e;">${act['long_tp2']:,.2f}</strong>
                                </div>
                            </div>

                            <!-- PLAN SHORT -->
                            <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); border-radius:10px; padding:12px;">
                                <div style="font-size:0.85rem; font-weight:800; color:#ef4444; border-bottom:1px solid rgba(239,68,68,0.2); padding-bottom:4px; margin-bottom:8px;">
                                    🔴 PLAN VENTA (SHORT)
                                </div>
                                <div style="font-size:0.8rem; color:#cbd5e1; line-height:1.6;">
                                    🎯 <strong>Gatillo Entrada:</strong> <strong style="color:#f8fafc;">${act['short_trigger']:,.2f}</strong><br>
                                    🛑 <strong>Stop Loss:</strong> <strong style="color:#ef4444;">${act['short_sl']:,.2f}</strong><br>
                                    🎯 <strong>TP1 (50% + BE):</strong> <strong style="color:#eab308;">${act['short_tp1']:,.2f}</strong><br>
                                    🏆 <strong>TP2 (R:R 1:3):</strong> <strong style="color:#22c55e;">${act['short_tp2']:,.2f}</strong>
                                </div>
                            </div>
                        </div>

                        <!-- Nota Táctica -->
                        <div style="font-size:0.78rem; color:#94a3b8; border-left:3px solid {card_border}; padding-left:8px; line-height:1.4;">
                            💡 <strong>Táctica:</strong> {act['nota']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown("<br><hr style='border-color:#334155;'><br>", unsafe_allow_html=True)

    # ── CALCULADORA TÁCTICA DE DISPARO R:R 1:3 ──
    st.subheader("📐 Calculadora Asistida de Boleta y Tamaño de Lote (R:R 1:3)")
    st.caption("Introduce tu capital a arriesgar y obtendrás el número de contratos exacto, Stop Loss inviolable y Take Profits listos para ejecutar")

    calc_c1, calc_c2 = st.columns([1, 1.5])
    with calc_c1:
        sel_activo = st.selectbox("Selecciona Activo a Operar:", [a["sym"] for a in activos_detalle], index=1)
        act_sel_info = next(a for a in activos_detalle if a["sym"] == sel_activo)
        tipo_op = st.radio("Dirección de la Operación:", ["🟢 LONG (COMPRA)", "🔴 SHORT (VENTA)"], horizontal=True)
        px_entrada = st.number_input("Precio de Entrada ($):", value=float(act_sel_info["long_trigger"] if "LONG" in tipo_op else act_sel_info["short_trigger"]), step=0.5)
        capital_riesgo = st.number_input("Capital a Arriesgar ($ USD):", value=15.0, min_value=2.0, max_value=500.0, step=5.0)
        apalan_calc = st.slider("Apalancamiento Efectivo:", min_value=1, max_value=10, value=5)

    with calc_c2:
        es_long = "LONG" in tipo_op
        dist_sl_pct = 0.05
        if es_long:
            sl_calc = px_entrada * (1.0 - dist_sl_pct)
            tp1_calc = px_entrada * (1.0 + dist_sl_pct)
            tp2_calc = px_entrada * (1.0 + (dist_sl_pct * 3.0))
        else:
            sl_calc = px_entrada * (1.0 + dist_sl_pct)
            tp1_calc = px_entrada * (1.0 - dist_sl_pct)
            tp2_calc = px_entrada * (1.0 - (dist_sl_pct * 3.0))

        notional_calc = capital_riesgo * apalan_calc
        qty_calc = notional_calc / px_entrada

        badge_dir_col = "#22c55e" if es_long else "#ef4444"
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.9); border:2px solid {badge_dir_col}; border-radius:14px; padding:18px;">
            <div style="font-size:0.8rem; font-weight:800; color:{badge_dir_col}; text-transform:uppercase;">
                BOLETA DE DISPARO TÁCTICO: {sel_activo} ({tipo_op})
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-top:10px;">
                <div>
                    <span style="color:#94a3b8; font-size:0.8rem;">Tamaño Nocional:</span><br>
                    <strong style="color:#f8fafc; font-size:1.15rem;">${notional_calc:,.2f} USD ({qty_calc:.4f} unidades)</strong>
                </div>
                <div>
                    <span style="color:#ef4444; font-size:0.8rem;">🛑 Stop Loss Inviolable ({'-5%' if es_long else '+5%'}):</span><br>
                    <strong style="color:#ef4444; font-size:1.15rem;">${sl_calc:,.2f}</strong>
                </div>
                <div>
                    <span style="color:#eab308; font-size:0.8rem;">🎯 TP1 (Cerrar 50% y Mover a BE):</span><br>
                    <strong style="color:#eab308; font-size:1.15rem;">${tp1_calc:,.2f}</strong>
                </div>
                <div>
                    <span style="color:#22c55e; font-size:0.8rem;">🏆 TP2 Macro (R:R 1:3):</span><br>
                    <strong style="color:#22c55e; font-size:1.15rem;">${tp2_calc:,.2f}</strong>
                </div>
            </div>
            <div style="margin-top:14px; padding:8px 12px; background:{badge_dir_col}15; border-radius:8px; font-size:0.82rem; color:{badge_dir_col};">
                💡 <strong>Regla de Oro:</strong> Al alcanzar TP1 (${tp1_calc:,.2f}), asegurar el 50% del profit y mover el Stop Loss a ${px_entrada:,.2f} (Break-Even).
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab3:'''

code, n_t2 = re.subn(tab2_target_pattern, tab2_new_code, code, flags=re.DOTALL)
if n_t2 > 0:
    print("✅ Tab 2 upgraded to Rich Tactical Cards successfully!")
else:
    print("⚠️ tab2_target_pattern not matched")

with open(TARGET_FILE, "w", encoding="utf-8") as f:
    f.write(code)

with open("/home/h/Escritorio/SEPTIEMBRE/dashboard_maestro.py", "w", encoding="utf-8") as f:
    f.write(code)

print("💾 Archivos guardados y sincronizados!")
