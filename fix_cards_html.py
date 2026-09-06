# -*- coding: utf-8 -*-
import re

TARGET = '/home/h/Escritorio/RESPALDO/2027/dashboard_maestro.py'
with open(TARGET, 'r', encoding='utf-8') as f:
    code = f.read()

card_pattern = r'st\.markdown\(f"""\s*<div style="background:\s*rgba\(15,23,42,0\.92\);.*?</div>\s*""",\s*unsafe_allow_html=True\)'

card_replacement = '''card_html = f"""<div style="background: rgba(15,23,42,0.92); border: 2px solid {card_border}; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 0 25px rgba(0,0,0,0.4);">
<div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid #334155; padding-bottom:12px; margin-bottom:14px;">
<div>
<span style="font-size:0.75rem; font-weight:800; background:{card_border}22; color:{card_border}; padding:3px 8px; border-radius:6px; text-transform:uppercase;">{act['tipo']} · {act['exchange']}</span>
<h2 style="margin:6px 0 0 0; font-size:1.6rem; font-weight:900; color:#f8fafc;">{act['sym']} <span style="font-size:1rem; font-weight:600; color:#94a3b8;">({act['nombre']})</span></h2>
<div style="font-size:1.8rem; font-weight:900; color:#38bdf8; margin-top:2px;">${act['precio']:,.2f} <span style="font-size:0.85rem; color:#94a3b8;">USD</span></div>
</div>
<div style="text-align:right;">
<div style="font-size:0.75rem; color:#94a3b8; font-weight:700;">CONFLUENCIA</div>
<div style="font-size:2.2rem; font-weight:900; color:{card_border}; line-height:1;">{sc}<span style="font-size:1rem; color:#64748b;">/100</span></div>
<div style="font-size:0.8rem; font-weight:800; color:{recom_color}; margin-top:4px;">{act['recom']}</div>
</div>
</div>
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
<div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:14px;">
<div style="background:rgba(34,197,94,0.08); border:1px solid rgba(34,197,94,0.3); border-radius:10px; padding:12px;">
<div style="font-size:0.85rem; font-weight:800; color:#22c55e; border-bottom:1px solid rgba(34,197,94,0.2); padding-bottom:4px; margin-bottom:8px;">🟢 PLAN COMPRA (LONG)</div>
<div style="font-size:0.8rem; color:#cbd5e1; line-height:1.6;">
🎯 <strong>Gatillo Entrada:</strong> <strong style="color:#f8fafc;">${act['long_trigger']:,.2f}</strong><br>
🛑 <strong>Stop Loss:</strong> <strong style="color:#ef4444;">${act['long_sl']:,.2f}</strong><br>
🎯 <strong>TP1 (50% + BE):</strong> <strong style="color:#eab308;">${act['long_tp1']:,.2f}</strong><br>
🏆 <strong>TP2 (R:R 1:3):</strong> <strong style="color:#22c55e;">${act['long_tp2']:,.2f}</strong>
</div>
</div>
<div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); border-radius:10px; padding:12px;">
<div style="font-size:0.85rem; font-weight:800; color:#ef4444; border-bottom:1px solid rgba(239,68,68,0.2); padding-bottom:4px; margin-bottom:8px;">🔴 PLAN VENTA (SHORT)</div>
<div style="font-size:0.8rem; color:#cbd5e1; line-height:1.6;">
🎯 <strong>Gatillo Entrada:</strong> <strong style="color:#f8fafc;">${act['short_trigger']:,.2f}</strong><br>
🛑 <strong>Stop Loss:</strong> <strong style="color:#ef4444;">${act['short_sl']:,.2f}</strong><br>
🎯 <strong>TP1 (50% + BE):</strong> <strong style="color:#eab308;">${act['short_tp1']:,.2f}</strong><br>
🏆 <strong>TP2 (R:R 1:3):</strong> <strong style="color:#22c55e;">${act['short_tp2']:,.2f}</strong>
</div>
</div>
</div>
<div style="font-size:0.78rem; color:#94a3b8; border-left:3px solid {card_border}; padding-left:8px; line-height:1.4;">
💡 <strong>Táctica:</strong> {act['nota']}
</div>
</div>"""
                    st.markdown(card_html, unsafe_allow_html=True)'''

code, n_subs = re.subn(card_pattern, card_replacement, code, flags=re.DOTALL)
print('Substitutions made:', n_subs)

with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(code)

with open('/home/h/Escritorio/SEPTIEMBRE/dashboard_maestro.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('✅ Flush-left HTML applied cleanly!')
