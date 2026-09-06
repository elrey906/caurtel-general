# 📖 MANUAL OPERATIVO: CEREBRO HÍBRIDO TRIPLE TIRO (TRIFECTA CUÁNTICA)
**Ubicación Oficial:** `/home/h/Escritorio/SEPTIEMBRE/HIBRIDO/`
**Exchange:** BingX Futuros Perpetuos (Pares Cripto en USDC / Acciones en USDT)
**Dashboard Dedicado:** Puerto `8555` (`dashboard_trifecta_hibrido.py`)

---

## 🏛️ 1. FILOSOFÍA Y ARQUITECTURA DE LAS 3 BALAS
Este cerebro elimina el Stop Loss tradicional que provocaba pérdidas por mechazos institucionales, aprovechando el colchón de capital de la cuenta (~$748 USD) para absorber correcciones temporales y promediar con peso masivo en el fondo exacto.

### 🔫 Las 3 Balas Operativas (Apalancamiento 10x):
1. **Bala 1 (Sonda de Exploración):**
   - **Margen:** `$15.00 USD` (Posición nominal de `$150.00 USD`).
   - **Gatillo:** Visita al Soporte de 7 Días (`distancia <= 2.5%`) con vela verde de confirmación en 4H.
   - **Propósito:** Si el mercado rebota de inmediato, asegura ganancia rápida en cash sin dejar pasar la oportunidad. Si el mercado cae, NO IMPORTA; la sonda sirve como ancla para rastrear el suelo verdadero.
2. **Bala 2 (El Martillazo en Suelo 30D):**
   - **Margen:** `$45.00 USD` (Posición nominal de `$450.00 USD`).
   - **Gatillo:** Caída mínima requerida desde la sonda (ej. >= 4% en acciones, >= 6% en criptos) + llegada al Piso de 30 Días (Piscina SSL) con Mecha de Absorción >= 30% y vela verde de giro con $RVOL \ge 0.9x$.
   - **Efecto Matemático:** Al tener el triple de capital que la sonda (75% del peso en el fondo), el precio promedio ponderado colapsa directamente hacia el suelo real.
3. **Bala 3 (Rebote Inminente / Aceleración):**
   - **Margen:** `$10.00 USD` (Posición nominal de `$100.00 USD`).
   - **Gatillo:** Se dispara cuando el precio supera el nivel del Martillazo en +1.0% con volumen institucional ($RVOL \ge 1.1x$), montándose en la ola de despegue.
   - **Margen Total Comprometido (Peor Escenario):** `$70.00 USD` (Apenas el 9.3% de una cuenta de $748 USD, con 0% riesgo de liquidación).

---

## 🎯 2. TOMA DE GANANCIAS Y SALIDAS
* **Take Profit:** Entre `+4.0% y +4.5%` calculado sobre el **Precio Promedio Ponderado** de la posición completa.
* Al menor rebote desde el suelo verdadero, toda la posición ($700 USD nominales) se liquida íntegramente a mercado en BingX embolsando dólares limpios en la mano.

---

## 🛡️ 3. PROTOCOLO DE PRECISIÓN Y NO-COLISIÓN
1. **Precisión Matemática Estricta:**
   - Cada orden se formatea estrictamente con el paso de lote (`step_qty`), cantidad mínima (`min_qty`) y decimales de precio (`price_prec`) del exchange BingX, garantizando cero errores de orden rechazada.
2. **Blindaje Anti-Colisión:**
   - **Binance:** Aislamiento 100% físico (Cerebro 3 opera en Binance Margin 5x).
   - **Cerebro 6:** Aislamiento 100% por colateral (Cerebro 6 opera en pares USDC).
   - **Cerebro 1, Cerebro 5 y Entradas Manuales:** Todas las órdenes llevan el identificador único `clientOrderId = TRI_{sym}_{timestamp}`. El bot detecta si ya existe una posición manual o externa en ese activo y se abstiene de intervenir.
   - **Lista de Exclusión:** `NCSKMSFT2USD-USDT` permanece intocable e inviolable.

---

## 🎛️ 4. PANEL DE CONTROL (DASHBOARD PUERTO 8555)
* **Semáforos ADN en Vivo:**
  - 🔨 **Distancia al Martillazo (%):** Proximidad al piso de 30 días para anticipar la entrada de $45 USD.
  - 🎯 **Distancia al Take Profit (%):** Avance porcentual hacia el cobro de la ganancia.
* **Botón de Cierre Manual:** `🚨 CERRAR POSICIÓN A MERCADO EN BINGX` para cerrar cualquier trade de inmediato desde el navegador con un solo clic.
* **Selector Dinámico:** Alternar entre `FANTASMA 👻` y `REAL 🟢`.

---

## 🚀 5. COMANDOS DE EJECUCIÓN
* **Iniciar Cerebro y Dashboard:**
  ```bash
  bash /home/h/Escritorio/SEPTIEMBRE/HIBRIDO/iniciar_trifecta.sh
  ```
* **Detener:**
  ```bash
  bash /home/h/Escritorio/SEPTIEMBRE/HIBRIDO/detener_trifecta.sh
  ```
* **Acceso Web:** `http://localhost:8555`
