#!/bin/bash
DIR_SEPTIEMBRE="/home/h/Escritorio/SEPTIEMBRE"
DIR_AUTONOMO="$DIR_SEPTIEMBRE/AUTONOMO"
VENV="$DIR_SEPTIEMBRE/venv_cazador/bin"
LOG_DIR="$DIR_SEPTIEMBRE/LOGS"

mkdir -p "$LOG_DIR"

echo "🧬 Iniciando Cerebro 4: Mega-Agente ADN Autónomo..."
pkill -f "cazador_mega_agente_autonomo.py"
pkill -f "dashboard_mega_agente.py"

nohup "$VENV/python3" "$DIR_AUTONOMO/cazador_mega_agente_autonomo.py" > "$DIR_AUTONOMO/mega_agente_adn.log" 2>&1 &
nohup "$VENV/streamlit" run "$DIR_AUTONOMO/dashboard_mega_agente.py" --server.port 8560 --server.headless true --server.enableCORS false --server.enableXsrfProtection false > "$LOG_DIR/dashboard_8560.log" 2>&1 &

echo "✅ Cerebro 4 Mega-Agente iniciado en Puerto 8560."
