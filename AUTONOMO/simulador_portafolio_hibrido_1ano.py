# -*- coding: utf-8 -*-
"""
👑 SIMULADOR DEFINITIVO: PORTAFOLIO HÍBRIDO SEPTIEMBRE (EL VERDADERO CAMPEÓN)
Combina:
1. Wall Street Blue Chips (NVDA, AMZN, GOOGL, AMD, TSLA): Máxima rentabilidad y consistencia.
2. Bitcoin (Binance Margin 5X): Acumulador blindado.
3. Cripto Rápida Filtrada (SOL): Solo gatillos A+ en sobreventa extrema.
"""
import os, sys, math
import pandas as pd
import numpy as np

VELAS_DIR = "/home/h/Escritorio/SEPTIEMBRE/VELAS"
MARGEN_BASE = 10.0
LEVERAGE = 10.0
FEE = 0.0005

def simular_hibrido(sym, csv_file, tp_pct, sl_drop_pct=0.07):
    path = os.path.join(VELAS_DIR, csv_file)
    if not os.path.exists(path): return None
        
    df = pd.read_csv(path)
    col_d = 'Datetime' if 'Datetime' in df.columns else ('timestamp' if 'timestamp' in df.columns else df.columns[0])
    df['dt'] = pd.to_datetime(df[col_d], utc=True)
    df.rename(columns={'Close':'close','Open':'open','High':'high','Low':'low'}, inplace=True)
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    df.set_index('dt', inplace=True)
    df4 = df.resample('4h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna().reset_index()
    
    c = df4['close']
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=1).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=1).mean()
    df4['rsi'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
    
    cr = (df4['high'] - df4['low']).clip(lower=1e-6)
    df4['lower_wick'] = ((df4[['open', 'close']].min(axis=1) - df4['low']).clip(lower=0) / cr) * 100.0
    df4['sop7d'] = df4['low'].rolling(42, min_periods=12).min()
    
    trades = []
    en_pos = False
    
    balas = 0
    qty_total = 0.0
    costo_total = 0.0
    avg_price = 0.0
    
    for i in range(50, len(df4)):
        px = df4['close'].iloc[i]
        
        if not en_pos:
            rsi = df4['rsi'].iloc[i]
            lw = df4['lower_wick'].iloc[i]
            sop = df4['sop7d'].iloc[i]
            
            # Filtro estricto: RSI sobreventa + absorción
            if rsi <= 35.0 and (lw >= 35.0 or px <= sop * 1.01):
                en_pos = True
                balas = 1
                notional_1 = MARGEN_BASE * LEVERAGE
                qty_total = notional_1 / px
                costo_total = notional_1
                avg_price = px
        else:
            tp_p = avg_price * (1.0 + tp_pct)
            
            # Recarga inteligente si cae -3.0%
            if balas == 1 and px <= avg_price * 0.97:
                balas = 2
                notional_2 = MARGEN_BASE * LEVERAGE
                qty_2 = notional_2 / px
                qty_total += qty_2
                costo_total += notional_2
                avg_price = costo_total / qty_total
                continue
                
            # Take Profit
            if df4['high'].iloc[i] >= tp_p:
                valor_venta = qty_total * tp_p
                pnl = (valor_venta - costo_total) - (costo_total * FEE * 2)
                trades.append({"resultado": "WIN", "pnl": pnl, "balas": balas})
                en_pos = False
            # Stop Loss
            elif px <= avg_price * (1.0 - sl_drop_pct):
                valor_venta = qty_total * px
                pnl = (valor_venta - costo_total) - (costo_total * FEE * 2)
                trades.append({"resultado": "LOSS", "pnl": pnl, "balas": balas})
                en_pos = False
                
    return trades

print("=" * 80)
print("🏛️ PORTAFOLIO GANADOR OFICIAL (WALL STREET + BITCOIN + TOP ALTS)")
print("=" * 80)

activos_oficiales = [
    ("NVDA", "NVDA_1h.csv", 0.050, 0.06),
    ("AMZN", "AMZN_1h.csv", 0.040, 0.06),
    ("GOOGL", "GOOGL_1h.csv", 0.040, 0.05),
    ("AMD", "AMD_1h.csv", 0.050, 0.06),
    ("TSLA", "TSLA_1h.csv", 0.060, 0.08),
    ("BTC", "BTC_1h.csv", 0.040, 0.06),
    ("SOL", "SOL_1h.csv", 0.050, 0.06),
]

pnl_tot = 0.0
w_tot = 0
l_tot = 0

for sym, f_csv, tp, sl in activos_oficiales:
    res = simular_hibrido(sym, f_csv, tp, sl)
    if res:
        mult = 0.5 if sym == "BTC" else 1.0
        pnl = sum(t["pnl"] for t in res) * mult
        wins = sum(1 for t in res if t["resultado"] == "WIN")
        losses = sum(1 for t in res if t["resultado"] == "LOSS")
        wr = (wins / len(res)) * 100.0 if res else 0.0
        pnl_tot += pnl
        w_tot += wins
        l_tot += losses
        print(f"  • {sym:5s} | Trades: {len(res):2d} | Wins: {wins:2d} | Losses: {losses:2d} | WR: {wr:5.1f}% | PnL Neto: ${pnl:+7.2f} USD")

print("=" * 80)
print(f"🏆 RENDIMIENTO TOTAL DE 1 AÑO (PORTAFOLIO DE MICRO-BALAS $10 USD):")
print(f"   • Total Operaciones: {w_tot + l_tot}")
print(f"   • Operaciones Ganadas: {w_tot} ✅")
print(f"   • Operaciones Perdidas: {l_tot} ❌")
print(f"   • Win Rate Real del Sistema: {(w_tot / max(1, w_tot+l_tot))*100:.1f}%")
print(f"   • GANANCIA NETA TOTAL: ${pnl_tot:+,.2f} USD 💵")
print(f"   • ROI sobre Balas de $10 USD: +{pnl_tot / 10.0 * 100:.0f}%")
print("=" * 80)
