#!/bin/bash
cd /home/h/Escritorio/SEPTIEMBRE/HIBRIDO
pkill -f "cazador_trifecta_hibrido.py"
pkill -f "dashboard_trifecta_hibrido.py"

nohup /home/h/Escritorio/SEPTIEMBRE/venv_cazador/bin/python3 cazador_trifecta_hibrido.py > cazador_trifecta.log 2>&1 &
nohup /home/h/Escritorio/SEPTIEMBRE/venv_cazador/bin/streamlit run dashboard_trifecta_hibrido.py --server.port 8555 --server.headless true > dashboard_8555.log 2>&1 &

echo "👑 CEREBRO TRIFECTA CUÁNTICA INICIADO:"
echo "   • Motor Bot: PID $!"
echo "   • Dashboard: http://localhost:8555"
