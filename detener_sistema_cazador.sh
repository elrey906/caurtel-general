#!/bin/bash
# Script para detener los procesos de Cazador PRO

echo "🛑 Deteniendo procesos de Cazador PRO..."
pkill -f "cazador_blue_chips_wall_street.py"
pkill -f "dashboard_blue_chips.py"
pkill -f "dashboard_mega_hibrido_btc.py"
pkill -f "dashboard_maestro.py"
pkill -f "cazador_mega_hibrido_btc_dual.py"
pkill -f "tunel_maestro_telegram.py"
pkill -f "notificador_telegram_6h_2359.py"

echo "✅ Todos los procesos han sido detenidos."
