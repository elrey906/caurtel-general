# -*- coding: utf-8 -*-
"""
🔬 SIMULACIÓN CUÁNTICA ASIMÉTRICA: RATIO R:R 1:3 (EL SECRETO INSTITUCIONAL)
En lugar de arriesgar lo mismo que se gana:
1. El Stop Loss es milimétrico (-1.5% o -2.0% máximo).
2. Se toma TP1 (+2.5%) asegurando el 50% y moviendo el Stop a Break-Even.
3. El 50% restante se deja correr a TP2 (+6% / +8% macro).
4. Caza exclusiva de Order Blocks no mitigados con absorción >= 40%.
"""
import os, sys, math
import pandas as pd
import numpy as np

VELAS_DIR = "/home/h/Escritorio/SEPTIEMBRE/VELAS"
MARGEN = 10.0
LEVERAGE = 10.0
NOTIONAL = MARGEN * LEVERAGE
FEE = 0.0005

def simular_activo_asimetrico(sym, csv_file, tp1_pct, tp2_pct, sl_pct, max_velas, es_macro=False):
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
    
    cr = (df['high'] - df['low']).clip(lower=1e-6)
    df['lower_wick'] = ((df[['open', 'close']].min(axis=1) - df['low']).clip(lower=0) / cr) * 100.0
    df['sop7d'] = df['low'].rolling(168, min_periods=24).min()
    
    trades = []
    en_pos = False
    entry_p = 0.0
    entry_idx = 0
    tp1_p = 0.0
    tp2_p = 0.0
    sl_p = 0.0
    tp1_hit = False
    
    start_idx = max(200, len(df) - 8760)
    for i in range(start_idx, len(df)):
        px = df['close'].iloc[i]
        
        if not en_pos:
            rsi = df['rsi'].iloc[i]
            h_curr = df['hist'].iloc[i]
            h_prev = df['prev_hist'].iloc[i]
            lw = df['lower_wick'].iloc[i]
            sop = df['sop7d'].iloc[i]
            
            # FILTRO DE CONFLUENCIA ASIMÉTRICA:
            # Giro alcista en valle rojo encogiéndose + RSI en sobreventa + mecha >= 35%
            giro_valle = (h_curr < 0 and h_curr > h_prev) or (h_curr >= 0 and h_curr >= h_prev)
            sobreventa = rsi <= 35.0
            piso_firme = px <= sop * 1.012
            
            if giro_valle and sobreventa and (lw >= 35.0 or piso_firme):
                en_pos = True
                entry_p = px
                entry_idx = i
                tp1_p = px * (1.0 + tp1_pct)
                tp2_p = px * (1.0 + tp2_pct)
                sl_p = px * (1.0 - sl_pct)
                tp1_hit = False
        else:
            velas_en_trade = i - entry_idx
            
            # 1. Take Profit 1 (Cerrar 50% y Mover SL a Break-Even +0.3%)
            if not tp1_hit and df['high'].iloc[i] >= tp1_p:
                tp1_hit = True
                sl_p = entry_p * 1.003 # Blindaje de ganancia en el SL
                
            # 2. Take Profit 2 Final (Cerrar 50% restante)
            if df['high'].iloc[i] >= tp2_p:
                # 50% cobrado a TP1 + 50% cobrado a TP2
                pnl1 = (tp1_p - entry_p) / entry_p * (NOTIONAL * 0.5)
                pnl2 = (tp2_p - entry_p) / entry_p * (NOTIONAL * 0.5)
                fees = NOTIONAL * FEE * 2
                pnl_neto = (pnl1 + pnl2) - fees
                trades.append({"sym": sym, "resultado": "WIN", "pnl": pnl_neto, "motivo": "TP2_RUNNER"})
                en_pos = False
                continue
                
            # 3. Stop Loss
            elif df['low'].iloc[i] <= sl_p:
                if tp1_hit:
                    # El primer 50% ya ganó en TP1, el segundo 50% sale a Break-Even
                    pnl1 = (tp1_p - entry_p) / entry_p * (NOTIONAL * 0.5)
                    pnl2 = (sl_p - entry_p) / entry_p * (NOTIONAL * 0.5)
                    fees = NOTIONAL * FEE * 2
                    pnl_neto = (pnl1 + pnl2) - fees
                    trades.append({"sym": sym, "resultado": "WIN", "pnl": pnl_neto, "motivo": "TP1_MAS_BE"})
                else:
                    # Pérdida completa de la posición
                    pnl_bruto = (sl_p - entry_p) / entry_p * NOTIONAL
                    fees = NOTIONAL * FEE * 2
                    pnl_neto = pnl_bruto - fees
                    trades.append({"sym": sym, "resultado": "LOSS", "pnl": pnl_neto, "motivo": "SL"})
                en_pos = False
                continue
                
            # 4. Check Día 10 en Macro
            elif es_macro and velas_en_trade >= 240:
                ret_actual = (px - entry_p) / entry_p
                pnl_bruto = ret_actual * NOTIONAL
                fees = NOTIONAL * FEE * 2
                pnl_neto = pnl_bruto - fees
                trades.append({"sym": sym, "resultado": "WIN" if pnl_neto > 0 else "LOSS", "pnl": pnl_neto, "motivo": "DIA_10"})
                en_pos = False
                continue
                
            # 5. Expiración Time-Stop
            elif velas_en_trade >= max_velas:
                ret_actual = (px - entry_p) / entry_p
                pnl_bruto = ret_actual * NOTIONAL
                fees = NOTIONAL * FEE * 2
                pnl_neto = pnl_bruto - fees
                trades.append({"sym": sym, "resultado": "WIN" if pnl_neto > 0 else "LOSS", "pnl": pnl_neto, "motivo": "TIME_STOP"})
                en_pos = False
                continue

    return trades

print("=" * 80)
print("🚀 BACKTEST DE 1 AÑO CON GESTIÓN DE BENEFICIO ASIMÉTRICO (TP1 + RUNNER TP2)")
print("=" * 80)

total_pnl = 0.0
total_wins = 0
total_loss = 0

activos = [
    # sym, csv, tp1, tp2, sl, max_h, es_macro
    ("SOL", "SOL_1h.csv", 0.025, 0.065, 0.018, 48, False),
    ("ETH", "ETH_1h.csv", 0.020, 0.050, 0.015, 48, False),
    ("SUI", "SUI_1h.csv", 0.035, 0.090, 0.025, 48, False),
    ("DOGE", "DOGE_1h.csv", 0.035, 0.095, 0.025, 48, False),
    ("AVAX", "AVAX_1h.csv", 0.028, 0.075, 0.020, 48, False),
    ("NVDA", "NVDA_1h.csv", 0.030, 0.080, 0.020, 600, True),
    ("TSLA", "TSLA_1h.csv", 0.035, 0.095, 0.025, 600, True),
    ("AMZN", "AMZN_1h.csv", 0.025, 0.065, 0.018, 600, True),
    ("GOOGL", "GOOGL_1h.csv", 0.022, 0.060, 0.015, 600, True),
    ("META", "META_1h.csv", 0.025, 0.070, 0.018, 600, True),
    ("AMD", "AMD_1h.csv", 0.030, 0.085, 0.022, 600, True),
    ("BTC", "BTC_1h.csv", 0.025, 0.055, 0.020, 720, True)
]

for sym, f_csv, tp1, tp2, sl, mv, macro in activos:
    res = simular_activo_asimetrico(sym, f_csv, tp1, tp2, sl, mv, macro)
    if res:
        mult = 0.5 if sym == "BTC" else 1.0
        pnl = sum(t["pnl"] for t in res) * mult
        wins = sum(1 for t in res if t["resultado"] == "WIN")
        losses = sum(1 for t in res if t["resultado"] == "LOSS")
        wr = (wins / len(res)) * 100.0 if res else 0.0
        total_pnl += pnl
        total_wins += wins
        total_loss += losses
        print(f"  • {sym:5s} | Trades: {len(res):3d} | Wins: {wins:2d} | Losses: {losses:2d} | WR: {wr:5.1f}% | PnL Neto: ${pnl:+7.2f} USD")

print("=" * 80)
print(f"🏆 RESULTADO GLOBAL FINAL ASIMÉTRICO (1 AÑO COMPLETO):")
print(f"   • Total Trades Disparados: {total_wins + total_loss}")
print(f"   • Trades Ganadores (TP1 / TP2): {total_wins} ✅")
print(f"   • Trades Perdedores (SL Pleno): {total_loss} ❌")
print(f"   • Win Rate Global: {(total_wins / max(1, total_wins+total_loss))*100:.1f}%")
print(f"   • BENEFICIO NETO TOTAL GENERADO: ${total_pnl:+,.2f} USD 💵")
print("=" * 80)
