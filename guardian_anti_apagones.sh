#!/bin/bash
# ==============================================================================
# 🛡️ GUARDIÁN WATCHDOG RESILIENTE (ANTI-LUZ, ANTI-CAÍDAS, VIVE AUTOMÁTICO 24/7)
# ==============================================================================
DIR_SEPTIEMBRE="/home/h/Escritorio/SEPTIEMBRE"
VENV="$DIR_SEPTIEMBRE/venv_cazador/bin"
LOG_DIR="$DIR_SEPTIEMBRE/LOGS"
mkdir -p "$LOG_DIR"

echo "🦅 [GUARDIÁN 24/7] Iniciando Fábrica Cuántica de Septiembre 2027..."

while true; do
    # 1. Verificar si hay conexión básica antes de revivir procesos
    if ping -c 1 8.8.8.8 > /dev/null 2>&1 || ping -c 1 1.1.1.1 > /dev/null 2>&1; then
        
        # Cerebro 1: Blue Chips Wall Street (BingX)
        if ! pgrep -f "cazador_blue_chips_wall_street.py" > /dev/null; then
            echo "[$(date)] 🚀 Cerebro 1 (Blue Chips) iniciado/revivido." >> "$LOG_DIR/guardian.log"
            nohup "$VENV/python3" "$DIR_SEPTIEMBRE/cazador_blue_chips_wall_street.py" >> "$LOG_DIR/blue_chips_bot.log" 2>&1 &
        fi

        # Cerebro 2: Mega Híbrido BTC (Binance Margin 5X)
        if ! pgrep -f "cazador_mega_hibrido_btc_dual.py" > /dev/null; then
            echo "[$(date)] 🚀 Cerebro 2 (Mega Híbrido BTC) iniciado/revivido." >> "$LOG_DIR/guardian.log"
            nohup "$VENV/python3" "$DIR_SEPTIEMBRE/cazador_mega_hibrido_btc_dual.py" >> "$LOG_DIR/mega_hibrido_bot.log" 2>&1 &
        fi

        # Cerebro 3: Trifecta Cuántica Híbrida (BingX)
        if ! pgrep -f "cazador_trifecta_hibrido.py" > /dev/null; then
            echo "[$(date)] 🚀 Cerebro 3 (Trifecta Híbrido) iniciado/revivido." >> "$LOG_DIR/guardian.log"
            cd "$DIR_SEPTIEMBRE/HIBRIDO"
            nohup "$VENV/python3" "$DIR_SEPTIEMBRE/HIBRIDO/cazador_trifecta_hibrido.py" >> "$DIR_SEPTIEMBRE/HIBRIDO/cazador_trifecta.log" 2>&1 &
            cd "$DIR_SEPTIEMBRE"
        fi

        # Cerebro 4: Mega-Agente Autónomo (Modo Fantasma por Defecto + Alertas Telegram)
        if ! pgrep -f "cazador_mega_agente_autonomo.py" > /dev/null; then
            echo "[$(date)] 🚀 Cerebro 4 (Mega-Agente ADN) iniciado/revivido en Modo Fantasma." >> "$LOG_DIR/guardian.log"
            nohup "$VENV/python3" "$DIR_SEPTIEMBRE/AUTONOMO/cazador_mega_agente_autonomo.py" >> "$DIR_SEPTIEMBRE/AUTONOMO/mega_agente_adn.log" 2>&1 &
        fi

        # Dashboard Maestro (Puerto 8500)
        if ! pgrep -f "dashboard_maestro.py" > /dev/null; then
            echo "[$(date)] 🚀 Dashboard Maestro (8500) iniciado/revivido." >> "$LOG_DIR/guardian.log"
            nohup "$VENV/streamlit" run "$DIR_SEPTIEMBRE/dashboard_maestro.py" --server.port 8500 --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false >> "$LOG_DIR/dashboard_maestro.log" 2>&1 &
        fi

        # Dashboard Cerebro 4 (Puerto 8560)
        if ! pgrep -f "dashboard_mega_agente.py" > /dev/null; then
            echo "[$(date)] 🚀 Dashboard Cerebro 4 (8560) iniciado/revivido." >> "$LOG_DIR/guardian.log"
            nohup "$VENV/streamlit" run "$DIR_SEPTIEMBRE/AUTONOMO/dashboard_mega_agente.py" --server.port 8560 --server.headless true --server.enableCORS false --server.enableXsrfProtection false >> "$LOG_DIR/dashboard_8560.log" 2>&1 &
        fi

        # Dashboard Cerebro 3 (Puerto 8555)
        if ! pgrep -f "dashboard_trifecta_hibrido.py" > /dev/null; then
            echo "[$(date)] 🚀 Dashboard Trifecta (8555) iniciado/revivido." >> "$LOG_DIR/guardian.log"
            nohup "$VENV/streamlit" run "$DIR_SEPTIEMBRE/HIBRIDO/dashboard_trifecta_hibrido.py" --server.port 8555 --server.headless true --server.enableCORS false --server.enableXsrfProtection false >> "$LOG_DIR/dashboard_8555.log" 2>&1 &
        fi

    else
        echo "[$(date)] 🌐 Sin internet. Esperando reconexión..." >> "$LOG_DIR/guardian.log"
    fi

    sleep 20
done
