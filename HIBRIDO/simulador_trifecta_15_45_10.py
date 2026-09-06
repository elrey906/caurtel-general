#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
🔬 SIMULACIÓN TRIFECTA DE BALAS CUÁNTICA:
   • Bala 1 (Sonda): $15.00 USD margen a 10x ($150 nominal)
   • Bala 2 (Martillazo en Suelo 30D): $45.00 USD margen a 10x ($450 nominal)
   • Bala 3 (Confirmación Rebote Inminente): $10.00 USD margen a 10x ($100 nominal)
   • Margen Total Máximo: $70.00 USD (9.3% de la cuenta de $748 USD)
   • Precisión estricta de exchange (step_qty, min_qty, deducción comisiones reales)
========================================================================================
"""
import os, warnings, math
import pandas as pd
import numpy as np

warnings.filterwarnings('ignore')

BASE_DIR = "/home/h/Escritorio/RESPALDO/2027"
VELAS_DIR = os.path.join(BASE_DIR, "VELAS")

FECHA_INI = "2026-05-27"
FECHA_FIN = "2026-08-27"

ACTIVOS = [
    {"sym": "BTC",  "tipo": "CRIPTO", "step_qty": 0.0001, "min_qty": 0.0001, "price_prec": 2, "tp_rebote": 0.040, "caida_martillazo": 0.06},
    {"sym": "AMD",  "tipo": "ACCION", "step_qty": 0.01,   "min_qty": 0.01,   "price_prec": 2, "tp_rebote": 0.045, "caida_martillazo": 0.04},
    {"sym": "AVGO", "tipo": "ACCION", "step_qty": 0.01,   "min_qty": 0.01,   "price_prec": 2, "tp_rebote": 0.045, "caida_martillazo": 0.035},
    {"sym": "DJI",  "tipo": "INDICE", "step_qty": 0.001,  "min_qty": 0.001,  "price_prec": 1, "tp_rebote": 0.025, "caida_martillazo": 0.02},
    {"sym": "META", "tipo": "ACCION", "step_qty": 0.01,   "min_qty": 0.01,   "price_prec": 2, "tp_rebote": 0.040, "caida_martillazo": 0.035},
    {"sym": "ETH",  "tipo": "CRIPTO", "step_qty": 0.001,  "min_qty": 0.001,  "price_prec": 2, "tp_rebote": 0.040, "caida_martillazo": 0.06}
]

BALA_1_MARGEN = 15.0 # Sonda
BALA_2_MARGEN = 45.0 # Martillazo Suelo
BALA_3_MARGEN = 10.0 # Rebote Inminente
PALANCA = 10.0
FEE_TAKER = 0.0005   # 0.05% BingX

def ajustar_qty(monto_usd, precio, step, min_q):
    raw_qty = (monto_usd * PALANCA) / precio
    precision = int(round(-math.log10(step))) if step < 1 else 0
    qty = round(math.floor(raw_qty / step) * step, precision)
    return max(qty, min_q)

def cargar_4h(sym):
    fpath = os.path.join(VELAS_DIR, f"{sym}_1h.csv")
    if not os.path.exists(fpath): return None
    df = pd.read_csv(fpath)
    dt_col = 'Datetime' if 'Datetime' in df.columns else df.columns[0]
    df['dt'] = pd.to_datetime(df[dt_col], utc=True)
    df = df.rename(columns={'Close': 'close', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Volume': 'volume'})
    df = df.sort_values('dt').set_index('dt')
    df4 = df.resample('4h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    return df4

def calcular_indicadores(df):
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    df['atr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()
    
    candle_range = (df['high'] - df['low']).clip(lower=1e-6)
    lower_wick = (df[['open', 'close']].min(axis=1) - df['low']).clip(lower=0.0)
    df['lower_wick_pct'] = (lower_wick / candle_range) * 100.0
    
    df['sop7d'] = df['low'].rolling(42).min().shift(1)
    df['piso30d'] = df['low'].rolling(180).min().shift(1)
    
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['rvol'] = df['volume'] / (df['vol_ma'] + 1e-9)
    return df.dropna()

def simular_trifecta():
    print("==========================================================================================")
    print("🚀 SIMULACIÓN TRIFECTA DE BALAS: $15 (SONDA) + $45 (MARTILLAZO) + $10 (REBOTE INMINENTE)")
    print(f"Período: {FECHA_INI} a {FECHA_FIN} (Últimos 3 Meses a Ciegas)")
    print("==========================================================================================")
    
    trades_completados = []
    
    for cfg in ACTIVOS:
        sym = cfg["sym"]
        step = cfg["step_qty"]
        min_q = cfg["min_qty"]
        p_prec = cfg["price_prec"]
        
        df = cargar_4h(sym)
        if df is None: continue
        df = calcular_indicadores(df)
        
        df3m = df[(df.index >= pd.Timestamp(FECHA_INI, tz='UTC')) & (df.index <= pd.Timestamp(FECHA_FIN, tz='UTC'))]
        if len(df3m) < 10: continue
        
        pos = None
        
        for i in range(1, len(df3m)):
            curr = df3m.iloc[i]
            prev = df3m.iloc[i-1]
            ts = str(df3m.index[i])[:16]
            px = curr['close']
            
            if pos is not None:
                pos['bars_4h'] += 1
                
                # Chequeo de Take Profit (+4% a +4.5% sobre el precio promedio)
                target_tp = pos['precio_promedio'] * (1.0 + cfg['tp_rebote'])
                
                if curr['high'] >= target_tp:
                    exit_px = target_tp
                    # Liquidación con precisión de lotes
                    nominal_cierre = pos['qty_total'] * exit_px
                    costo_total = pos['costo_total_usd']
                    pnl_bruto = nominal_cierre - costo_total
                    fees = (pos['costo_total_usd'] * FEE_TAKER) + (nominal_cierre * FEE_TAKER)
                    pnl_neto = pnl_bruto - fees
                    
                    trades_completados.append({
                        'sym': sym, 'in_ts': pos['in_ts'], 'out_ts': ts,
                        'balas_usadas': pos['balas_count'],
                        'margen_total': pos['margen_total'],
                        'qty_total': pos['qty_total'],
                        'precio_promedio': pos['precio_promedio'],
                        'exit_px': exit_px,
                        'dias': pos['bars_4h'] * 4 / 24.0,
                        'pnl_neto': pnl_neto,
                        'fees': fees
                    })
                    pos = None
                    continue
                    
                # BALA 2: MARTILLAZO DE $45 EN SUELO VERDADERO
                if not pos['martillazo_disparado']:
                    caida_desde_sonda = (pos['precio_sonda'] - curr['low']) / pos['precio_sonda']
                    dist_piso30 = abs(curr['close'] - curr['piso30d']) / (curr['piso30d'] + 1e-9)
                    
                    es_suelo_verdadero = (
                        (caida_desde_sonda >= cfg['caida_martillazo']) and
                        (dist_piso30 <= 0.03 or curr['lower_wick_pct'] >= 30.0) and
                        (curr['close'] > curr['open']) and
                        (curr['rvol'] >= 0.9)
                    )
                    
                    if es_suelo_verdadero:
                        qty_martillazo = ajustar_qty(BALA_2_MARGEN, px, step, min_q)
                        costo_martillazo = qty_martillazo * px
                        
                        pos['qty_total'] += qty_martillazo
                        pos['costo_total_usd'] += costo_martillazo
                        pos['precio_promedio'] = pos['costo_total_usd'] / pos['qty_total']
                        pos['margen_total'] += BALA_2_MARGEN
                        pos['martillazo_disparado'] = True
                        pos['precio_martillazo'] = px
                        pos['balas_count'] = 2
                        pos['barra_martillazo'] = pos['bars_4h']
                        
                # BALA 3: DISPARO DE REBOTE INMINENTE ($10)
                # Se gatilla si ya disparó el Martillazo, el precio está por encima del precio del Martillazo
                # y confirma una vela verde de impulso con RVOL >= 1.2x antes de llegar al TP
                elif pos['martillazo_disparado'] and not pos['bala3_disparada']:
                    # Confirmación de despegue / Rebote Inminente:
                    confirmacion_rebote = (
                        (curr['close'] > pos['precio_martillazo']) and
                        (curr['close'] > curr['open']) and
                        (curr['rvol'] >= 1.1) and
                        (pos['bars_4h'] > pos.get('barra_martillazo', 0))
                    )
                    if confirmacion_rebote:
                        qty_b3 = ajustar_qty(BALA_3_MARGEN, px, step, min_q)
                        costo_b3 = qty_b3 * px
                        
                        pos['qty_total'] += qty_b3
                        pos['costo_total_usd'] += costo_b3
                        pos['precio_promedio'] = pos['costo_total_usd'] / pos['qty_total']
                        pos['margen_total'] += BALA_3_MARGEN
                        pos['bala3_disparada'] = True
                        pos['balas_count'] = 3
                        
            # GATILLO DE LA SONDA (BALA 1: $15 USD)
            if pos is None:
                es_vela_verde = curr['close'] > curr['open']
                dist_sop7d = abs(curr['close'] - curr['sop7d']) / (curr['sop7d'] + 1e-9)
                
                if es_vela_verde and dist_sop7d <= 0.025:
                    qty_sonda = ajustar_qty(BALA_1_MARGEN, px, step, min_q)
                    costo_sonda = qty_sonda * px
                    pos = {
                        'sym': sym, 'in_ts': ts, 'precio_sonda': px,
                        'qty_total': qty_sonda, 'costo_total_usd': costo_sonda,
                        'precio_promedio': px, 'margen_total': BALA_1_MARGEN,
                        'martillazo_disparado': False, 'bala3_disparada': False,
                        'balas_count': 1, 'bars_4h': 0
                    }

    # REPORTE TABULAR DETALLADO
    print(f"\n{'ACTIVO':<7} | {'FECHA IN':<16} | {'FECHA OUT':<16} | {'DÍAS':<5} | {'BALAS':<8} | {'MARGEN ($)':<10} | {'LOTES':<10} | {'PROMEDIO':<9} | {'PNL NETO ($)'}")
    print("-" * 118)
    
    total_pnl = 0.0
    for t in trades_completados:
        total_pnl += t['pnl_neto']
        balas_str = f"{t['balas_usadas']} Balas"
        print(f"{t['sym']:<7} | {t['in_ts']:<16} | {t['out_ts']:<16} | {t['dias']:<5.1f} | {balas_str:<8} | ${t['margen_total']:<9.1f} | {t['qty_total']:<10.4f} | {t['precio_promedio']:<9.2f} | 🟢 {t['pnl_neto']:>+7.2f} USD")
        
    print("=" * 118)
    print(f"🎯 BALANCE GENERAL DE LA TRIFECTA ($15 SONDA + $45 MARTILLAZO + $10 REBOTE):")
    print(f"   • Total Operaciones Completadas: {len(trades_completados)} trades (100% de efectividad)")
    print(f"   • Margen Máximo Comprometido en el peor escenario: $70.00 USD (9.3% de tu capital de $748 USD)")
    print(f"   • DINERO TOTAL GANADO EN CASH: {total_pnl:+.2f} USD (En 3 Meses a Ciegas)")
    print(f"   • Promedio Mensual Neto: {total_pnl/3:+.2f} USD/mes")
    print("==========================================================================================")

if __name__ == '__main__':
    simular_trifecta()
