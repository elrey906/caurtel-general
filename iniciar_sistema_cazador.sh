#!/bin/bash
# Script de inicio autónomo para Cazador PRO 2027 (Ejecución desde /home/h/Escritorio/SEPTIEMBRE)

VENV="/home/h/Escritorio/SEPTIEMBRE/venv_cazador/bin"
BASE_DIR="/home/h/Escritorio/SEPTIEMBRE"
DIR_SEPTIEMBRE="/home/h/Escritorio/SEPTIEMBRE"
LOG_DIR="$DIR_SEPTIEMBRE/LOGS"

mkdir -p "$LOG_DIR"

echo "🚀 Iniciando demonios y dashboards de Cazador PRO desde la nueva ubicación..."

# 1. Bot Cerebro 1 Blue Chips
nohup $VENV/python3 $DIR_SEPTIEMBRE/cazador_blue_chips_wall_street.py > $LOG_DIR/blue_chips_bot.log 2>&1 &

# 2. Dashboard Cerebro 1 (8540)
nohup $VENV/streamlit run $DIR_SEPTIEMBRE/dashboard_blue_chips.py --server.port 8540 --server.headless true --server.enableCORS false --server.enableXsrfProtection false > $LOG_DIR/dashboard_blue_chips.log 2>&1 &

# 3. Dashboard Cerebro 2 (8545)
nohup $VENV/streamlit run $DIR_SEPTIEMBRE/dashboard_mega_hibrido_btc.py --server.port 8545 --server.headless true --server.enableCORS false --server.enableXsrfProtection false > $LOG_DIR/dashboard_mega_hibrido.log 2>&1 &

# 4. Dashboard Maestro Unificado (8500)
nohup $VENV/streamlit run $BASE_DIR/dashboard_maestro.py --server.port 8500 --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false > $LOG_DIR/dashboard_maestro.log 2>&1 &

# 5. Bot Cerebro 2 Mega Hibrido BTC
nohup $VENV/python3 $DIR_SEPTIEMBRE/cazador_mega_hibrido_btc_dual.py > $LOG_DIR/mega_hibrido_bot.log 2>&1 &

# 6. Notificador Telegram 6H & 23:59 VET
nohup $VENV/python3 $BASE_DIR/HERRAMIENTAS/notificador_telegram_6h_2359.py > $LOG_DIR/notificador_telegram.log 2>&1 &

echo "✅ Los 6 procesos de Cazador PRO están corriendo en segundo plano desde /home/h/Escritorio/SEPTIEMBRE."
