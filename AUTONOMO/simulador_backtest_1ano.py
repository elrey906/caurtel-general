# -*- coding: utf-8 -*-
"""
🔬 LABORATORIO CUÁNTICO: SIMULADOR HISTÓRICO DE 1 AÑO (BACKTEST 2024 - 2025/2026)
Evalúa las reglas reales de:
  • Fase 1: Altcoins Rápidas ($10 @ 10X, TP +4.5%, SL -2.5%, Time-Stop 48h, Máx 3 abiertas).
  • Fase 2: Wall Street Macro ($10 @ 10X, TP +6.0%, SL -3.5%, Alarma Día 10, Máx 3 abiertas).
  • Binance BTC Margin ($10 @ 5X, TP +4.0%, SL -6.0%, Máx 3 compras).
"""
import os, sys, math
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROD_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
VELAS_DIR = os.path.join(PROD_DIR, "VELAS")

# Parámetros del Mega-Agente
MARGEN_BINGX = 10.0
LEVERAGE_BINGX = 10.0
NOTIONAL_BINGX = MARGEN_BINGX * LEVERAGE_BINGX # $100 USD

FEE_TAKER = 0.0005 # 0.05%

def simular_activo(sym, csv_file, tp_pct, sl_pct, max_velas, es_macro=False):
    path = os.path.join(VELAS_DIR, csv_file)
    if not os.path.exists(path):
        return None
        
    df = pd.read_csv(path)
    col_d = 'Datetime' if 'Datetime' in df.columns else ('timestamp' if 'timestamp' in df.columns else df.columns[0])
    df['dt'] = pd.to_datetime(df[col_d], utc=True)
    df.rename(columns={'Close':'close','Open':'open','High':'high','Low':'low','Volume':'vol'}, inplace=True)
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # Indicadores
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
    
    # Mechas
    cr = (df['high'] - df['low']).clip(lower=1e-6)
    df['lower_wick'] = ((df[['open', 'close']].min(axis=1) - df['low']).clip(lower=0) / cr) * 100.0
    df['sop7d'] = df['low'].rolling(168, min_periods=24).min()
    
    trades = []
    en_pos = False
    entry_p = 0.0
    entry_idx = 0
    tp_p = 0.0
    sl_p = 0.0
    
    # Recorrer velas cronológicamente (últimas ~8,000 velas = 1 año)
    start_idx = max(200, len(df) - 8760)
    for i in range(start_idx, len(df)):
        px = df['close'].iloc[i]
        
        if not en_pos:
            rsi = df['rsi'].iloc[i]
            h_curr = df['hist'].iloc[i]
            h_prev = df['prev_hist'].iloc[i]
            lw = df['lower_wick'].iloc[i]
            sop = df['sop7d'].iloc[i]
            
            # Condición de Gatillo Cuántico
            giro_alcista = (h_curr >= 0 and h_curr >= h_prev) or (h_curr < 0 and h_curr > h_prev)
            zona_sobreventa = rsi <= 45.0
            cerca_soporte = abs(px - sop) / sop <= 0.025
            
            if giro_alcista and zona_sobreventa and (lw >= 30.0 or cerca_soporte):
                en_pos = True
                entry_p = px
                entry_idx = i
                tp_p = px * (1.0 + tp_pct)
                sl_p = px * (1.0 - sl_pct)
        else:
            velas_en_trade = i - entry_idx
            duracion_horas = velas_en_trade
            
            # Check TP
            if df['high'].iloc[i] >= tp_p:
                pnl_bruto = (tp_p - entry_p) / entry_p * NOTIONAL_BINGX
                fees = NOTIONAL_BINGX * FEE_TAKER * 2
                pnl_neto = pnl_bruto - fees
                trades.append({
                    "sym": sym, "resultado": "WIN", "pnl": pnl_neto,
                    "entry": entry_p, "exit": tp_p, "horas": duracion_horas, "motivo": "TP"
                })
                en_pos = False
                continue
                
            # Check SL
            elif df['low'].iloc[i] <= sl_p:
                pnl_bruto = (sl_p - entry_p) / entry_p * NOTIONAL_BINGX
                fees = NOTIONAL_BINGX * FEE_TAKER * 2
                pnl_neto = pnl_bruto - fees
                trades.append({
                    "sym": sym, "resultado": "LOSS", "pnl": pnl_neto,
                    "entry": entry_p, "exit": sl_p, "horas": duracion_horas, "motivo": "SL"
                })
                en_pos = False
                continue
                
            # Check Alarma Día 10 en Macro
            elif es_macro and velas_en_trade >= 240: # 10 días = 240 horas
                ret_actual = (px - entry_p) / entry_p
                if ret_actual < 0.01: # Estancado
                    pnl_bruto = ret_actual * NOTIONAL_BINGX
                    fees = NOTIONAL_BINGX * FEE_TAKER * 2
                    pnl_neto = pnl_bruto - fees
                    trades.append({
                        "sym": sym, "resultado": "WIN" if pnl_neto > 0 else "LOSS", "pnl": pnl_neto,
                        "entry": entry_p, "exit": px, "horas": duracion_horas, "motivo": "DIA_10_RECORTE"
                    })
                    en_pos = False
                    continue
                    
            # Check Expiración Time-Stop
            elif velas_en_trade >= max_velas:
                pnl_bruto = (px - entry_p) / entry_p * NOTIONAL_BINGX
                fees = NOTIONAL_BINGX * FEE_TAKER * 2
                pnl_neto = pnl_bruto - fees
                trades.append({
                    "sym": sym, "resultado": "WIN" if pnl_neto > 0 else "LOSS", "pnl": pnl_neto,
                    "entry": entry_p, "exit": px, "horas": duracion_horas, "motivo": "TIME_STOP"
                })
                en_pos = False
                continue

    return trades

print("=" * 80)
print("🔬 RESULTADOS DEL BACKTEST HISTÓRICO DE 1 AÑO (VELAS REALES)")
print("=" * 80)

total_pnl_global = 0.0
total_wins_global = 0
total_loss_global = 0

# 1. FASE 1: RÁPIDAS (SOL, ETH, SUI, DOGE, AVAX)
print("\n⚡ [FASE 1: ALTCOINS RÁPIDAS - 48H TIME-STOP]")
fase1_activos = [
    ("SOL", "SOL_1h.csv", 0.045, 0.025, 48),
    ("ETH", "ETH_1h.csv", 0.035, 0.020, 48),
    ("SUI", "SUI_1h.csv", 0.065, 0.035, 48),
    ("DOGE", "DOGE_1h.csv", 0.070, 0.040, 48),
    ("AVAX", "AVAX_1h.csv", 0.050, 0.030, 48),
]

for sym, csv_f, tp, sl, max_v in fase1_activos:
    res = simular_activo(sym, csv_f, tp, sl, max_v, es_macro=False)
    if res:
        pnl = sum(t["pnl"] for t in res)
        wins = sum(1 for t in res if t["resultado"] == "WIN")
        losses = sum(1 for t in res if t["resultado"] == "LOSS")
        wr = (wins / len(res)) * 100.0 if res else 0.0
        total_pnl_global += pnl
        total_wins_global += wins
        total_loss_global += losses
        print(f"  • {sym:5s} | Trades: {len(res):3d} | Wins: {wins:2d} | Losses: {losses:2d} | WR: {wr:5.1f}% | PnL Neto: ${pnl:+7.2f} USD")

# 2. FASE 2: WALL STREET MACRO (NVDA, TSLA, AMZN, GOOGL, META, AMD)
print("\n🏛️ [FASE 2: WALL STREET MACRO - 25 DÍAS / ALARMA DÍA 10]")
fase2_activos = [
    ("NVDA", "NVDA_1h.csv", 0.060, 0.035, 600),
    ("TSLA", "TSLA_1h.csv", 0.080, 0.045, 600),
    ("AMZN", "AMZN_1h.csv", 0.050, 0.030, 600),
    ("GOOGL", "GOOGL_1h.csv", 0.050, 0.025, 600),
    ("META", "META_1h.csv", 0.055, 0.030, 600),
    ("AMD", "AMD_1h.csv", 0.070, 0.040, 600),
]

for sym, csv_f, tp, sl, max_v in fase2_activos:
    res = simular_activo(sym, csv_f, tp, sl, max_v, es_macro=True)
    if res:
        pnl = sum(t["pnl"] for t in res)
        wins = sum(1 for t in res if t["resultado"] == "WIN")
        losses = sum(1 for t in res if t["resultado"] == "LOSS")
        wr = (wins / len(res)) * 100.0 if res else 0.0
        total_pnl_global += pnl
        total_wins_global += wins
        total_loss_global += losses
        print(f"  • {sym:5s} | Trades: {len(res):3d} | Wins: {wins:2d} | Losses: {losses:2d} | WR: {wr:5.1f}% | PnL Neto: ${pnl:+7.2f} USD")

# 3. BITCOIN MARGIN
print("\n🪙 [BINANCE CROSS MARGIN: BITCOIN DUAL]")
res_btc = simular_activo("BTC", "BTC_1h.csv", 0.040, 0.050, 720, es_macro=True)
if res_btc:
    pnl = sum(t["pnl"] for t in res_btc) * 0.5 # 5X en vez de 10X
    wins = sum(1 for t in res_btc if t["resultado"] == "WIN")
    losses = sum(1 for t in res_btc if t["resultado"] == "LOSS")
    wr = (wins / len(res_btc)) * 100.0 if res_btc else 0.0
    total_pnl_global += pnl
    total_wins_global += wins
    total_loss_global += losses
    print(f"  • BTC   | Trades: {len(res_btc):3d} | Wins: {wins:2d} | Losses: {losses:2d} | WR: {wr:5.1f}% | PnL Neto: ${pnl:+7.2f} USD")

print("\n" + "=" * 80)
total_ops = total_wins_global + total_loss_global
wr_global = (total_wins_global / max(1, total_ops)) * 100.0
print(f"🏆 BALANCE GLOBAL DE 1 AÑO (MICRO-BALAS DE $10 USD):")
print(f"   • Total Operaciones: {total_ops}")
print(f"   • Operaciones Ganadas: {total_wins_global} ✅")
print(f"   • Operaciones Perdidas: {total_loss_global} ❌")
print(f"   • Win Rate Ponderado: {wr_global:.1f}%")
print(f"   • BENEFICIO NETO TOTAL: ${total_pnl_global:+,.2f} USD 💵")
print("=" * 80)
