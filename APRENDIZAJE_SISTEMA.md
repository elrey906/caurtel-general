# 🧠 APRENDIZAJE PERMANENTE DEL SISTEMA & REGLAS DE ORO DE COTIZACIONES

## 📌 LECCIÓN APRENDIDA: CASO NVIDIA (NVDA) Y ACTIVOS TRADFI EN BINGX (07/SEP/2026)

### 1. Nomenclatura Estricta de Contratos BingX TradFi
* En BingX Futuros Perpetuos, los contratos de acciones de Wall Street **NO** utilizan el sufijo estándar de cripto (ej. `NVDA-USDT` no existe en el motor de precios).
* Deben consultarse y mapearse estrictamente bajo el formato TradFi oficial:
  - **NVIDIA:** `NCSKNVDA2USD-USDT`
  - **MICROSOFT:** `NCSKMSFT2USD-USDT`
  - **AMAZON:** `NCSKAMZN2USD-USDT`
  - **GOOGLE:** `NCSKGOOGL2USD-USDT`
  - **APPLE:** `NCSKAAPL2USD-USDT`
  - **BROADCOM:** `NCSKAVGO2USD-USDT`
  - **TESLA:** `NCSKTSLA2USD-USDT`
  - **AMD:** `NCSKAMD2USD-USDT`
  - **META:** `NCSKMETA2USD-USDT`
  - **PETRÓLEO WTI:** `NCCO1OILWTI-USDT`
  - **S&P 500:** `NCSISP500-USDT`

### 2. Prohibición Absoluta de Fallbacks Estáticos Desfasados
* Queda terminantemente prohibido dejar diccionarios con precios fijos desfasados en cualquier dashboard o script sin validación contra los feeds en tiempo real.
* Todo componente visual (Cockpit, Tarjetas Tácticas, Simuladores) debe pasar por el **Agente Centinela de Precios y APIs** (`auditar_salud_apis_y_precios()`).

### 3. Mecánica del Agente Centinela en Dashboard Maestro
* El Dashboard Maestro ejecuta una auditoría de latencia y rango de seguridad de 8 activos críticos en cada carga.
* Si una cotización se desvía más del 15% de su rango esperado o una API responde con error, el Centinela despliega una alerta visual en rojo/amarillo en el encabezado para proteger al operador antes de ejecutar cualquier orden manual o automática.
