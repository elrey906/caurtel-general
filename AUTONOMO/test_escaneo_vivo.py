import sys
sys.path.insert(0, '/home/h/Escritorio/SEPTIEMBRE/AUTONOMO')
from config_adn import UNIVERSO_FASE1, UNIVERSO_FASE2, UNIVERSO_BTC_BINANCE
from motor_adn_quant import calcular_adn_activo
from cazador_mega_agente_autonomo import activos_ocupados_por_otros_cerebros

ocupados = activos_ocupados_por_otros_cerebros()
print("🛡️ ACTIVOS INTOCABLES (Ya operados por Cerebro 1 o Cerebro 3):", ocupados)

print("\n⚡ --- RADAR EN VIVO: FASE 1 (ALTCOINS RÁPIDAS) ---")
for cfg in UNIVERSO_FASE1:
    sym = cfg['sym']
    if sym in ocupados:
        print(f"  • {sym:5s}: 🛑 BLOQUEADO POR RESPETO (Ya en Cerebro 1 o 3)")
        continue
    adn = calcular_adn_activo(sym, cfg['bingx_sym'], 'CRIPTO')
    px = adn.get('precio', 0.0)
    score = adn.get('score', 0)
    rsi = adn.get('rsi_1h', 0)
    macd = adn.get('macd_estado', '')
    gat = adn.get('gatillo_valido', False)
    estado = "🚀 ¡DISPARO DISPONIBLE!" if gat else "⏳ EN ESPERA DE OPORTUNIDAD"
    print(f"  • {sym:5s}: ${px:,.2f} | Score: {score} pts | RSI 1H: {rsi} | MACD: {macd} -> {estado}")

print("\n🏛️ --- RADAR EN VIVO: FASE 2 (WALL STREET MACRO) ---")
for cfg in UNIVERSO_FASE2:
    sym = cfg['sym']
    if sym in ocupados:
        print(f"  • {sym:5s}: 🛑 BLOQUEADO POR RESPETO (Ya en Cerebro 1 o 3)")
        continue
    adn = calcular_adn_activo(sym, cfg['bingx_sym'], 'ACCION')
    px = adn.get('precio', 0.0)
    score = adn.get('score', 0)
    rsi = adn.get('rsi_1h', 0)
    macd = adn.get('macd_estado', '')
    gat = adn.get('gatillo_valido', False)
    estado = "🚀 ¡DISPARO DISPONIBLE!" if gat else "⏳ EN ESPERA DE OPORTUNIDAD"
    print(f"  • {sym:5s}: ${px:,.2f} | Score: {score} pts | RSI 1H: {rsi} | MACD: {macd} -> {estado}")

print("\n🪙 --- RADAR EN VIVO: BITCOIN (BINANCE MARGIN 5X) ---")
adn_btc = calcular_adn_activo('BTC', 'BTC-USDT', 'CRIPTO')
px = adn_btc.get('precio', 0.0)
score = adn_btc.get('score', 0)
rsi = adn_btc.get('rsi_1h', 0)
macd = adn_btc.get('macd_estado', '')
gat = adn_btc.get('gatillo_valido', False)
estado = "🚀 ¡DISPARO DISPONIBLE!" if gat else "⏳ EN ESPERA DE OPORTUNIDAD"
print(f"  • BTC  : ${px:,.2f} | Score: {score} pts | RSI 1H: {rsi} | MACD: {macd} -> {estado}")
