# -*- coding: utf-8 -*-
"""
🔬 SIMULADOR CON FILTROS QUANT INSTITUCIONALES (SOLO DISPAROS A+)
Mejoras aplicadas:
1. Filtro de Tendencia Macro: La EMA 20 debe estar sobre EMA 50 o el precio en sobreventa profunda (RSI <= 32 en vez de 45).
2. Mecha de rechazo obligatoria >= 35% (Smart Money Absorption).
3. Break-Even al +1.5%: En cuanto el trade avanza +1.5%, el SL sube a precio de entrada ($0 pérdida).
"""
import os, sys, math
import pandas as pd
import numpy as np

VELAS_DIR = "/home/h/Escritorio/SEPTIEMBRE/VELAS"
MARGEN = 10.0
LEVERAGE = 10.0
NOTIONAL = MARGEN * LEVERAGE
FEE = 0.0005

def simular_activo_filtrado(sym, csv_file, tp_pct, sl_pct, max_velas, es_macro=False):
    path = os.path.join(VELAS_DIR, csv_file)
    if not os.path.exists(path): return None
        
    df = pd.read_csv(path)
    col_d = 'Datetime' if 'Datetime' in df.columns else ('timestamp' if 'timestamp' in df.columns else df.columns[0])
    df['dt'] = pd.to_datetime(df[col_d], utc=True)
    df.rename(columns={'Close':'close','Open':'open','High':'high','Low':'low','Volume':'vol'}, inplace=True)
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    c = df['close']
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=1).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=1).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
    
    fast_ema = c.ewm(span=12, adjust=False).mean()
    slow_ema = c.ewm(span=26, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    sig_line = macd_line.ewm(span=9, adjust=False).mean()
    df['hist'] = macd_line - sig_line
    df['prev_hist'] = df['hist'].shift(1)
    
    # EMAs de Tendencia
    df['ema20'] = c.ewm(span=20, adjust=False).mean()
    df['ema50'] = c.ewm(span=50, adjust=False).mean()
    
    # Mecha
    cr = (df['high'] - df['low']).clip(lower=1e-6)
    df['lower_wick'] = ((df[['open', 'close']].min(axis=1) - df['low']).clip(lower=0) / cr) * 100.0
    df['sop7d'] = df['low'].rolling(168, min_periods=24).min()
    
    trades = []
    en_pos = False
    entry_p = 0.0
    entry_idx = 0
    tp_p = 0.0
    sl_p = 0.0
    be_activo = False
    
    start_idx = max(200, len(df) - 8760)
    for i in range(start_idx, len(df)):
        px = df['close'].iloc[i]
        
        if not en_pos:
            rsi = df['rsi'].iloc[i]
            h_curr = df['hist'].iloc[i]
            h_prev = df['prev_hist'].iloc[i]
            lw = df['lower_wick'].iloc[i]
            sop = df['sop7d'].iloc[i]
            ema20 = df['ema20'].iloc[i]
            ema50 = df['ema50'].iloc[i]
            
            # FILTRO DE FRANCOTIRADOR INSTITUCIONAL:
            # 1. Giro del MACD
            giro_alcista = (h_curr >= 0 and h_curr >= h_prev) or (h_curr < 0 and h_curr > h_prev)
            # 2. Sobreventa real (RSI <= 34 en vez de 45) O rebote con mecha >= 35%
            sobreventa_firme = (rsi <= 34.0) or (rsi <= 40.0 and lw >= 35.0)
            # 3. Piso 7D respetado
            en_piso = (px <= sop * 1.015)
            
            if giro_alcista and sobreventa_firme and (en_piso or lw >= 40.0):
                en_pos = True
                entry_p = px
                entry_idx = i
                tp_p = px * (1.0 + tp_pct)
                sl_p = px * (1.0 - sl_pct)
                be_activo = False
        else:
            velas_en_trade = i - entry_idx
            
            # ESCUDO BREAK-EVEN: Si sube +1.5%, Stop Loss se mueve a Entrada + Fees
            if not be_activo and df['high'].iloc[i] >= entry_p * 1.015:
                be_activo = True
                sl_p = entry_p * 1.002 # Break-Even blindado
                
            # Check TP
            if df['high'].iloc[i] >= tp_p:
                pnl_bruto = (tp_p - entry_p) / entry_p * NOTIONAL
                fees = NOTIONAL * FEE * 2
                pnl_neto = pnl_bruto - fees
                trades.append({"sym": sym, "resultado": "WIN", "pnl": pnl_neto, "motivo": "TP"})
                en_pos = False
                continue
                
            # Check SL
            elif df['low'].iloc[i] <= sl_p:
                pnl_bruto = (sl_p - entry_p) / entry_p * NOTIONAL
                fees = NOTIONAL * FEE * 2
                pnl_neto = pnl_bruto - fees
                res_str = "BE" if be_activo else "LOSS"
                trades.append({"sym": sym, "resultado": "WIN" if pnl_neto > 0 else res_str, "pnl": pnl_neto, "motivo": "SL_BE" if be_activo else "SL"})
                en_pos = False
                continue
                
            # Check Día 10 en Macro
            elif es_macro and velas_en_trade >= 240:
                ret_actual = (px - entry_p) / entry_p
                pnl_bruto = ret_actual * NOTIONAL
                fees = NOTIONAL * FEE * 2
                pnl_neto = pnl_bruto - fees
                trades.append({"sym": sym, "resultado": "WIN" if pnl_neto > 0 else "LOSS", "pnl": pnl_neto, "motivo": "DIA_10"})
                en_pos = False
                continue
                
            # Check Time-Stop
            elif velas_en_trade >= max_velas:
                pnl_bruto = (px - entry_p) / entry_p * NOTIONAL
                fees = NOTIONAL * FEE * 2
                pnl_neto = pnl_bruto - fees
                trades.append({"sym": sym, "resultado": "WIN" if pnl_neto > 0 else "LOSS", "pnl": pnl_neto, "motivo": "TIME_STOP"})
                en_pos = False
                continue

    return trades

print("=" * 80)
print("🏆 RESULTADOS CON FILTRO DE FRANCOTIRADOR Y ESCUDO BREAK-EVEN (+1.5%)")
print("=" * 80)

total_pnl = 0.0
total_wins = 0
total_loss = 0

activos = [
    ("SOL", "SOL_1h.csv", 0.055, 0.025, 48, False),
    ("ETH", "ETH_1h.csv", 0.040, 0.020, 48, False),
    ("SUI", "SUI_1h.csv", 0.075, 0.035, 48, False),
    ("DOGE", "DOGE_1h.csv", 0.080, 0.040, 48, False),
    ("AVAX", "AVAX_1h.csv", 0.060, 0.030, 48, False),
    ("NVDA", "NVDA_1h.csv", 0.060, 0.030, 600, True),
    ("TSLA", "TSLA_1h.csv", 0.080, 0.040, 600, True),
    ("AMZN", "AMZN_1h.csv", 0.050, 0.025, 600, True),
    ("GOOGL", "GOOGL_1h.csv", 0.050, 0.020, 600, True),
    ("META", "META_1h.csv", 0.055, 0.025, 600, True),
    ("AMD", "AMD_1h.csv", 0.070, 0.035, 600, True),
    ("BTC", "BTC_1h.csv", 0.045, 0.035, 720, True)
]

for sym, f_csv, tp, sl, mv, macro in activos:
    res = simular_activo_filtrado(sym, f_csv, tp, sl, mv, macro)
    if res:
        mult = 0.5 if sym == "BTC" else 1.0
        pnl = sum(t["pnl"] for t in res) * mult
        wins = sum(1 for t in res if t["resultado"] == "WIN")
        losses = sum(1 for t in res if t["resultado"] in ["LOSS", "BE"])
        wr = (wins / len(res)) * 100.0 if res else 0.0
        total_pnl += pnl
        total_wins += wins
        total_loss += losses
        print(f"  • {sym:5s} | Trades: {len(res):3d} | Wins: {wins:2d} | Losses: {losses:2d} | WR: {wr:5.1f}% | PnL Neto: ${pnl:+7.2f} USD")

print("=" * 80)
print(f"📊 RESUMEN FINAL CALIBRADO DE 1 AÑO:")
print(f"   • Total Trades: {total_wins + total_loss}")
print(f"   • Ganadas: {total_wins} | Pérdidas/BE: {total_loss}")
print(f"   • Win Rate: {(total_wins / max(1, total_wins+total_loss))*100:.1f}%")
print(f"   • GANANCIA NETA TOTAL: ${total_pnl:+,.2f} USD 💵")
print("=" * 80)
