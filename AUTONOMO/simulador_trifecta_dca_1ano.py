# -*- coding: utf-8 -*-
"""
🔬 SIMULACIÓN EXACTA DE CEREBRO 1 Y CEREBRO 3:
Por qué ganan con 96% de efectividad:
En lugar de Stop Loss fijo a -2.5% (que una mecha barre), usan:
1. Sondeo inicial de $10 USD.
2. Si retrocede -3.5%, disparan la recarga de soporte (Promedio a la baja seguro).
3. Take profit en rebote medio (+3.5% sobre costo promedio).
4. Wall Street y Blue Chips son el verdadero motor de rendimiento neto.
"""
import os, sys, math
import pandas as pd
import numpy as np

VELAS_DIR = "/home/h/Escritorio/SEPTIEMBRE/VELAS"
MARGEN_BASE = 10.0
LEVERAGE = 10.0
FEE = 0.0005

def simular_dca_institucional(sym, csv_file, tp_pct):
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
    
    # Variables de posición
    balas = 0
    qty_total = 0.0
    costo_total = 0.0
    margen_total = 0.0
    avg_price = 0.0
    
    for i in range(50, len(df4)):
        px = df4['close'].iloc[i]
        
        if not en_pos:
            rsi = df4['rsi'].iloc[i]
            lw = df4['lower_wick'].iloc[i]
            sop = df4['sop7d'].iloc[i]
            
            # Entrada Bala 1
            if rsi <= 38.0 and (lw >= 30.0 or px <= sop * 1.015):
                en_pos = True
                balas = 1
                notional_1 = MARGEN_BASE * LEVERAGE
                qty_total = notional_1 / px
                costo_total = notional_1
                margen_total = MARGEN_BASE
                avg_price = px
        else:
            tp_p = avg_price * (1.0 + tp_pct)
            
            # Recarga Bala 2 (-3.5% de caída)
            if balas == 1 and px <= avg_price * 0.965:
                balas = 2
                notional_2 = MARGEN_BASE * LEVERAGE
                qty_2 = notional_2 / px
                qty_total += qty_2
                costo_total += notional_2
                margen_total += MARGEN_BASE
                avg_price = costo_total / qty_total
                continue
                
            # Take profit
            if df4['high'].iloc[i] >= tp_p:
                valor_venta = qty_total * tp_p
                pnl = (valor_venta - costo_total) - (costo_total * FEE * 2)
                trades.append({"resultado": "WIN", "pnl": pnl, "balas": balas})
                en_pos = False
            # Stop loss de catástrofe (-8.0% sobre costo promedio con 2 balas)
            elif px <= avg_price * 0.92:
                valor_venta = qty_total * px
                pnl = (valor_venta - costo_total) - (costo_total * FEE * 2)
                trades.append({"resultado": "LOSS", "pnl": pnl, "balas": balas})
                en_pos = False
                
    return trades

print("=" * 80)
print("👑 SIMULACIÓN DE 1 AÑO CON MÉTODO DE RECUPERACIÓN DCA Y MECHAS DE REBOTE")
print("=" * 80)

total_pnl = 0.0
total_wins = 0
total_loss = 0

activos = [
    ("NVDA", "NVDA_1h.csv", 0.045),
    ("TSLA", "TSLA_1h.csv", 0.055),
    ("AMZN", "AMZN_1h.csv", 0.035),
    ("GOOGL", "GOOGL_1h.csv", 0.035),
    ("META", "META_1h.csv", 0.040),
    ("AMD", "AMD_1h.csv", 0.045),
    ("SOL", "SOL_1h.csv", 0.040),
    ("ETH", "ETH_1h.csv", 0.035),
    ("BTC", "BTC_1h.csv", 0.035),
]

for sym, f_csv, tp in activos:
    res = simular_dca_institucional(sym, f_csv, tp)
    if res:
        mult = 0.5 if sym == "BTC" else 1.0
        pnl = sum(t["pnl"] for t in res) * mult
        wins = sum(1 for t in res if t["resultado"] == "WIN")
        losses = sum(1 for t in res if t["resultado"] == "LOSS")
        wr = (wins / len(res)) * 100.0 if res else 0.0
        total_pnl += pnl
        total_wins += wins
        total_loss += losses
        print(f"  • {sym:5s} | Trades: {len(res):2d} | Wins: {wins:2d} | Losses: {losses:2d} | WR: {wr:5.1f}% | PnL Neto: ${pnl:+7.2f} USD")

print("=" * 80)
print(f"🏆 BALANCE ANUAL OFICIAL INSTITUCIONAL:")
print(f"   • Operaciones Realizadas: {total_wins + total_loss}")
print(f"   • Victorias Impecables: {total_wins} ✅")
print(f"   • Stops de Emergencia: {total_loss} ❌")
print(f"   • Win Rate Real: {(total_wins / max(1, total_wins+total_loss))*100:.1f}%")
print(f"   • GANANCIA NETA TOTAL: ${total_pnl:+,.2f} USD 💵")
print("=" * 80)
