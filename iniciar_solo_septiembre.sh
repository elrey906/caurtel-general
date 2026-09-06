#!/bin/bash
# ==============================================================================
# SCRIPT MAESTRO DE INICIO EXCLUSIVO: SEPTIEMBRE 2027
# Solo levanta los cerebros autorizados en /home/h/Escritorio/SEPTIEMBRE
# ==============================================================================

DIR_SEPTIEMBRE="/home/h/Escritorio/SEPTIEMBRE"
VENV="$DIR_SEPTIEMBRE/venv_cazador/bin"
LOG_DIR="$DIR_SEPTIEMBRE/LOGS"

mkdir -p "$LOG_DIR"

echo "🚀 [SEPTIEMBRE] Iniciando Cerebros Oficiales..."

# 1. Cerebro 1: Blue Chips Wall Street (BingX)
pkill -f "cazador_blue_chips_wall_street.py"
pkill -f "dashboard_blue_chips.py"
nohup "$VENV/python3" "$DIR_SEPTIEMBRE/cazador_blue_chips_wall_street.py" > "$LOG_DIR/blue_chips_bot.log" 2>&1 &
nohup "$VENV/streamlit" run "$DIR_SEPTIEMBRE/dashboard_blue_chips.py" --server.port 8540 --server.headless true --server.enableCORS false --server.enableXsrfProtection false > "$LOG_DIR/dashboard_blue_chips.log" 2>&1 &

# 2. Cerebro 2: Mega Híbrido BTC Dual (Binance Cross Margin 5X)
pkill -f "cazador_mega_hibrido_btc_dual.py"
pkill -f "dashboard_mega_hibrido_btc.py"
nohup "$VENV/python3" "$DIR_SEPTIEMBRE/cazador_mega_hibrido_btc_dual.py" > "$LOG_DIR/mega_hibrido_bot.log" 2>&1 &
nohup "$VENV/streamlit" run "$DIR_SEPTIEMBRE/dashboard_mega_hibrido_btc.py" --server.port 8545 --server.headless true --server.enableCORS false --server.enableXsrfProtection false > "$LOG_DIR/dashboard_mega_hibrido.log" 2>&1 &

# 3. Cerebro 3: Trifecta Cuántica Híbrida (BingX USDC/USDT)
if [ -d "$DIR_SEPTIEMBRE/HIBRIDO" ]; then
    cd "$DIR_SEPTIEMBRE/HIBRIDO"
    pkill -f "cazador_trifecta_hibrido.py"
    pkill -f "dashboard_trifecta_hibrido.py"
    nohup "$VENV/python3" "$DIR_SEPTIEMBRE/HIBRIDO/cazador_trifecta_hibrido.py" > "$DIR_SEPTIEMBRE/HIBRIDO/cazador_trifecta.log" 2>&1 &
    nohup "$VENV/streamlit" run "$DIR_SEPTIEMBRE/HIBRIDO/dashboard_trifecta_hibrido.py" --server.port 8555 --server.headless true > "$DIR_SEPTIEMBRE/HIBRIDO/dashboard_8555.log" 2>&1 &
    cd "$DIR_SEPTIEMBRE"
fi

# 4. Dashboard Maestro Consolidado (8500)
pkill -f "dashboard_maestro.py"
nohup "$VENV/streamlit" run "$DIR_SEPTIEMBRE/dashboard_maestro.py" --server.port 8500 --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false > "$LOG_DIR/dashboard_maestro.log" 2>&1 &

# 5. Guardián de Túnel Cloudflare Remoto & Notificador Telegram
pkill -f "tunel_maestro_telegram.py"
nohup "$VENV/python3" "$DIR_SEPTIEMBRE/tunel_maestro_telegram.py" > "$LOG_DIR/tunel_maestro.log" 2>&1 &

echo "✅ Cerebros oficiales de SEPTIEMBRE y Túnel Remoto iniciados exitosamente."
