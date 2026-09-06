#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ROOT_DIR="$(dirname "$DIR")"
PYTHON_BIN="$ROOT_DIR/venv_cazador/bin/python3"
STREAMLIT_BIN="$ROOT_DIR/venv_cazador/bin/streamlit"

echo "🚀 Arrancando Cerebro 1 (Alpha Blue Chips) en Septiembre 2027..."
nohup "$PYTHON_BIN" "$DIR/cazador_blue_chips_wall_street.py" > "$DIR/motor_blue_chips.log" 2>&1 &
echo "  [1/2] 🤖 Motor Autónomo: PID $!"

nohup "$STREAMLIT_BIN" run "$DIR/dashboard_blue_chips.py" --server.port 8540 --server.headless true --server.enableCORS false --server.enableXsrfProtection false > "$DIR/dashboard_8540.log" 2>&1 &
echo "  [2/2] 📊 Dashboard Streamlit (Puerto 8540): PID $!"
echo "✅ Cerebro 1 desplegado en: http://localhost:8540"
