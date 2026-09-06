# -*- coding: utf-8 -*-
"""
CONFIGURACIÓN Y UNIVERSO DE ACTIVOS DEL MEGA-AGENTE ADN
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROD_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

# Archivos de Estado y Configuración Independiente
CONFIG_FILE = os.path.join(BASE_DIR, "config_mega_agente.json")
ESTADO_FILE = os.path.join(BASE_DIR, "estado_mega_agente.json")
LEARNING_FILE = os.path.join(BASE_DIR, "aprendizaje_historico.json")
LOG_FILE = os.path.join(BASE_DIR, "mega_agente_adn.log")

# Cuotas Estrictas
BINGX_F1_MAX_POS = 3        # Máximo 3 posiciones rápidas
BINGX_F2_MAX_POS = 3        # Máximo 3 posiciones macro
BINGX_MARGEN_USD = 10.0     # $10 USD margen por trade
BINGX_LEVERAGE = 10         # 10X apalancamiento

BINANCE_BTC_MAX_BALAS = 3   # Máximo 3 compras de por vida hasta vender en TP
BINANCE_MARGEN_USD = 10.0   # $10 USD margen por bala
BINANCE_LEVERAGE = 5        # 5X Cross Margin

# Universo de Activos: FASE 1 (Rápidas - Altcoins de Alto Beta)
UNIVERSO_FASE1 = [
    {"sym": "SOL",  "bingx_sym": "SOL-USDT",  "tipo": "CRIPTO", "step_qty": 0.01,  "min_qty": 0.01,  "price_prec": 2, "tp_pct": 0.045, "sl_pct": 0.025, "max_horas": 48},
    {"sym": "ETH",  "bingx_sym": "ETH-USDT",  "tipo": "CRIPTO", "step_qty": 0.001, "min_qty": 0.001, "price_prec": 2, "tp_pct": 0.035, "sl_pct": 0.020, "max_horas": 48},
    {"sym": "NEAR", "bingx_sym": "NEAR-USDT", "tipo": "CRIPTO", "step_qty": 0.1,   "min_qty": 0.1,   "price_prec": 3, "tp_pct": 0.060, "sl_pct": 0.035, "max_horas": 48},
    {"sym": "SUI",  "bingx_sym": "SUI-USDT",  "tipo": "CRIPTO", "step_qty": 0.1,   "min_qty": 0.1,   "price_prec": 4, "tp_pct": 0.065, "sl_pct": 0.035, "max_horas": 48},
    {"sym": "AVAX", "bingx_sym": "AVAX-USDT", "tipo": "CRIPTO", "step_qty": 0.01,  "min_qty": 0.01,  "price_prec": 2, "tp_pct": 0.050, "sl_pct": 0.030, "max_horas": 48},
    {"sym": "DOGE", "bingx_sym": "DOGE-USDT", "tipo": "CRIPTO", "step_qty": 1.0,   "min_qty": 1.0,   "price_prec": 5, "tp_pct": 0.070, "sl_pct": 0.040, "max_horas": 48}
]

# Universo de Activos: FASE 2 (Macro - Wall Street & Blue Chips)
UNIVERSO_FASE2 = [
    {"sym": "NVDA",  "bingx_sym": "NCSKNVDA2USD-USDT",  "tipo": "ACCION", "step_qty": 0.01, "min_qty": 0.01, "price_prec": 2, "tp_pct": 0.060, "sl_pct": 0.035, "max_dias": 25},
    {"sym": "TSLA",  "bingx_sym": "NCSKTSLA2USD-USDT",  "tipo": "ACCION", "step_qty": 0.01, "min_qty": 0.01, "price_prec": 2, "tp_pct": 0.080, "sl_pct": 0.045, "max_dias": 25},
    {"sym": "AVGO",  "bingx_sym": "NCSKAVGO2USD-USDT",  "tipo": "ACCION", "step_qty": 0.01, "min_qty": 0.01, "price_prec": 2, "tp_pct": 0.060, "sl_pct": 0.035, "max_dias": 25},
    {"sym": "AAPL",  "bingx_sym": "NCSKAAPL2USD-USDT",  "tipo": "ACCION", "step_qty": 0.01, "min_qty": 0.01, "price_prec": 2, "tp_pct": 0.045, "sl_pct": 0.025, "max_dias": 25},
    {"sym": "AMZN",  "bingx_sym": "NCSKAMZN2USD-USDT",  "tipo": "ACCION", "step_qty": 0.01, "min_qty": 0.01, "price_prec": 2, "tp_pct": 0.050, "sl_pct": 0.030, "max_dias": 25},
    {"sym": "META",  "bingx_sym": "NCSKMETA2USD-USDT",  "tipo": "ACCION", "step_qty": 0.01, "min_qty": 0.01, "price_prec": 2, "tp_pct": 0.055, "sl_pct": 0.030, "max_dias": 25},
    {"sym": "GOOGL", "bingx_sym": "NCSKGOOGL2USD-USDT", "tipo": "ACCION", "step_qty": 0.01, "min_qty": 0.01, "price_prec": 2, "tp_pct": 0.050, "sl_pct": 0.025, "max_dias": 25},
    {"sym": "AMD",   "bingx_sym": "NCSKAMD2USD-USDT",   "tipo": "ACCION", "step_qty": 0.01, "min_qty": 0.01, "price_prec": 2, "tp_pct": 0.070, "sl_pct": 0.040, "max_dias": 25},
    {"sym": "MSFT",  "bingx_sym": "NCSKMSFT2USD-USDT",  "tipo": "ACCION", "step_qty": 0.01, "min_qty": 0.01, "price_prec": 2, "tp_pct": 0.045, "sl_pct": 0.025, "max_dias": 25}
]

# Universo Bitcoin (Binance Cross Margin 5X)
UNIVERSO_BTC_BINANCE = {
    "sym": "BTC",
    "symbol_binance": "BTCUSDT",
    "tipo": "CRIPTO_MARGIN",
    "step_qty": 0.00001,
    "min_qty": 0.00001,
    "tp_pct": 0.040,       # +4% TP para reciclar la bala
    "sl_pct": 0.060,       # -6% SL de protección de colateral
    "max_balas": 3
}
