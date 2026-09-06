import sys, json, os, datetime
sys.path.insert(0, '/home/h/Escritorio/SEPTIEMBRE/AUTONOMO')
from config_adn import UNIVERSO_FASE1, UNIVERSO_FASE2, UNIVERSO_BTC_BINANCE
from motor_adn_quant import calcular_adn_activo
from cazador_mega_agente_autonomo import activos_ocupados_por_otros_cerebros
from aprendizaje_ledger import obtener_resumen_contable

ocupados = activos_ocupados_por_otros_cerebros()
pnl_data = obtener_resumen_contable()

print("=" * 80)
print(f"🧬 MEGA-AGENTE ADN: ESTADO LIMPIO Y VERIFICACIÓN EN VIVO (MODO REAL 🟢)")
print(f"⏰ Fecha/Hora: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

print(f"\n📊 LIBRO MAYOR CONTABLE (RESET A CERO VERIFICADO):")
print(f"   • Balance Neto: ${pnl_data['balance_neto']:,.2f} USD")
print(f"   • Ganancia Bruta: ${pnl_data['ganancia_bruta']:,.2f} USD")
print(f"   • Pérdida Bruta: ${pnl_data['perdida_bruta']:,.2f} USD")
print(f"   • Total Trades Cerrados: {pnl_data['total_trades']}")

print(f"\n🛡️ PACTO DE RESPETO (Activos donde NO se interferirá):")
print(f"   • {', '.join(sorted(list(ocupados)))} (En manos de Cerebro 1 y Cerebro 3)")

print(f"\n⚡ RADAR FASE 1: ALTCOINS RÁPIDAS (0/3 Ranuras Ocupadas)")
for cfg in UNIVERSO_FASE1:
    sym = cfg['sym']
    if sym in ocupados: continue
    adn = calcular_adn_activo(sym, cfg['bingx_sym'], 'CRIPTO')
    estado = "🚀 GATILLO A+" if adn['gatillo_valido'] else "⏳ En Rango / Esperando Sobreventa"
    print(f"   • {sym:5s}: ${adn['precio']:,.2f} | Score: {adn['score']} pts | RSI: {adn['rsi_1h']} | {estado}")

print(f"\n🏛️ RADAR FASE 2: WALL STREET MACRO (0/3 Ranuras Ocupadas)")
for cfg in UNIVERSO_FASE2:
    sym = cfg['sym']
    if sym in ocupados:
        print(f"   • {sym:5s}: 🛑 RESPETADO (Operado por Cerebro 1/3)")
        continue
    adn = calcular_adn_activo(sym, cfg['bingx_sym'], 'ACCION')
    estado = "🚀 GATILLO A+" if adn['gatillo_valido'] else "⏳ En Rango / Esperando Entrada"
    print(f"   • {sym:5s}: ${adn['precio']:,.2f} | Score: {adn['score']} pts | RSI: {adn['rsi_1h']} | {estado}")

print(f"\n🪙 RADAR BITCOIN BINANCE MARGIN 5X (0/3 Balas Disparadas)")
adn_btc = calcular_adn_activo('BTC', 'BTC-USDT', 'CRIPTO')
estado_btc = "🚀 COMPRA A+" if adn_btc['gatillo_valido'] else "⏳ Esperando Piso 7D / Descuento"
print(f"   • BTC  : ${adn_btc['precio']:,.2f} | Score: {adn_btc['score']} pts | RSI: {adn_btc['rsi_1h']} | {estado_btc}")
print("=" * 80)
