# -*- coding: utf-8 -*-
"""
🔬 SIMULADOR SWING INSTITUCIONAL 4H (FILTRO EXACTO DE CEREBRO 1 & 3)
"""
import os, sys, math
import pandas as pd
import numpy as np

VELAS_DIR = "/home/h/Escritorio/SEPTIEMBRE/VELAS"
MARGEN = 10.0
LEVERAGE = 10.0
NOTIONAL = MARGEN * LEVERAGE
FEE = 0.0005

def simular_swing(sym, csv_file, tp_pct, sl_pct):
    path = os.path.join(VELAS_DIR, csv_file)
    if not os.path.exists(path): return None
        
    df = pd.read_csv(path)
    col_d = 'Datetime' if 'Datetime' in df.columns else ('timestamp' if 'timestamp' in df.columns else df.columns[0])
    df['dt'] = pd.to_datetime(df[col_d], utc=True)
    df.rename(columns={'Close':'close','Open':'open','High':'high','Low':'low','Volume':'vol','volume':'vol'}, inplace=True)
    if 'vol' not in df.columns:
        df['vol'] = 1000.0
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
    entry_p = 0.0
    tp_p = 0.0
    sl_p = 0.0
    be_activo = False
    
    for i in range(50, len(df4)):
        px = df4['close'].iloc[i]
        
        if not en_pos:
            rsi = df4['rsi'].iloc[i]
            lw = df4['lower_wick'].iloc[i]
            sop = df4['sop7d'].iloc[i]
            es_verde = df4['close'].iloc[i] > df4['open'].iloc[i]
            
            # FILTRO INSTITUCIONAL CEREBRO 1 / CEREBRO 3
            if rsi <= 42.0 and lw >= 30.0 and es_verde and (px <= sop * 1.025):
                en_pos = True
                entry_p = px
                tp_p = px * (1.0 + tp_pct)
                sl_p = px * (1.0 - sl_pct)
                be_activo = False
        else:
            # Escudo Break-Even al +1.5%
            if not be_activo and df4['high'].iloc[i] >= entry_p * 1.015:
                be_activo = True
                sl_p = entry_p * 1.002
                
            if df4['high'].iloc[i] >= tp_p:
                pnl = ((tp_p - entry_p) / entry_p * NOTIONAL) - (NOTIONAL * FEE * 2)
                trades.append({"resultado": "WIN", "pnl": pnl})
                en_pos = False
            elif df4['low'].iloc[i] <= sl_p:
                pnl = ((sl_p - entry_p) / entry_p * NOTIONAL) - (NOTIONAL * FEE * 2)
                trades.append({"resultado": "WIN" if pnl > 0 else "LOSS", "pnl": pnl})
                en_pos = False
                
    return trades

print("=" * 80)
print("💎 SIMULACIÓN SWING INSTITUCIONAL 4H (FILTRO ANTIRRUIDO CEREBRO 1 & 3)")
print("=" * 80)

total_pnl = 0.0
total_wins = 0
total_loss = 0

activos = [
    ("SOL", "SOL_1h.csv", 0.045, 0.025),
    ("ETH", "ETH_1h.csv", 0.035, 0.020),
    ("SUI", "SUI_1h.csv", 0.060, 0.035),
    ("DOGE", "DOGE_1h.csv", 0.065, 0.035),
    ("AVAX", "AVAX_1h.csv", 0.050, 0.028),
    ("NVDA", "NVDA_1h.csv", 0.050, 0.025),
    ("TSLA", "TSLA_1h.csv", 0.060, 0.030),
    ("AMZN", "AMZN_1h.csv", 0.045, 0.020),
    ("GOOGL", "GOOGL_1h.csv", 0.045, 0.020),
    ("META", "META_1h.csv", 0.050, 0.025),
    ("AMD", "AMD_1h.csv", 0.055, 0.025),
    ("BTC", "BTC_1h.csv", 0.035, 0.025)
]

for sym, f_csv, tp, sl in activos:
    res = simular_swing(sym, f_csv, tp, sl)
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
print(f"🏆 BALANCE ANUAL SWING DE ÉLITE:")
print(f"   • Total Operaciones de Alta Calidad: {total_wins + total_loss}")
print(f"   • Ganadas: {total_wins} ✅ | Pérdidas: {total_loss} ❌")
print(f"   • Win Rate Ponderado: {(total_wins / max(1, total_wins+total_loss))*100:.1f}%")
print(f"   • BENEFICIO NETO TOTAL: ${total_pnl:+,.2f} USD 💵")
print("=" * 80)
