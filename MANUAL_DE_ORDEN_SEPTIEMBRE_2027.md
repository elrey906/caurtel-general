# 📜 MANUAL DE ORDEN OPERATIVO: SEPTIEMBRE 2027
**Proyecto:** Cazador PRO — Antigravity Orchestrator  
**Carpeta Directriz Oficial:** `/home/h/Escritorio/RESPALDO/2027/SEPTIEMBRE_2027/`  
**Fecha de Vigencia:** Septiembre 2027 en adelante  

---

## ⚠️ DIRECTIVA SUPREMA DE ARQUITECTURA (SÓLO 2 CEREBROS VIVOS)
Queda **ESTRICTAMENTE PROHIBIDO** invocar, proponer o modificar cerebros del pasado (antiguo Cerebro 3, Cerebro 4, 5, 6 o 7 fuera del alcance oficial).  
Toda la operación real y el desarrollo activo del proyecto se centra **ÚNICA Y EXCLUSIVAMENTE EN LOS 2 CEREBROS DE LA CARPETA `SEPTIEMBRE_2027`**:

---

## 🏛️ 1. CEREBRO 1: ALPHA WALL STREET & BLUE CHIPS (BINGX)
* **Función:** Capturar movimientos institucionales en acciones líderes y Blue Chips de Wall Street.
* **Exchange Operativo:** BingX Perpetuos.
* **Motor Autónomo:** [`cazador_blue_chips_wall_street.py`](file:///home/h/Escritorio/RESPALDO/2027/SEPTIEMBRE_2027/cazador_blue_chips_wall_street.py)
* **Dashboard de Monitoreo:** Puerto `8540` ([`dashboard_blue_chips.py`](file:///home/h/Escritorio/RESPALDO/2027/SEPTIEMBRE_2027/dashboard_blue_chips.py))
* **Archivo de Modo:** [`config_blue_chips_modo.json`](file:///home/h/Escritorio/RESPALDO/2027/SEPTIEMBRE_2027/config_blue_chips_modo.json)
* **Archivo de Estado:** [`estado_blue_chips.json`](file:///home/h/Escritorio/RESPALDO/2027/SEPTIEMBRE_2027/estado_blue_chips.json)
* **Universo de Activos (11):** `AVGO`, `GOOGL`, `QQQ`, `MSFT`, `META`, `SP500`, `NVDA`, `DJI`, `AAPL`, `AMD`, `AMZN`.
* **Reglas de Ejecución:**
  1. Compras Límite exclusivamente en Soporte Institucional 7D (`soporte_7d`).
  2. Gestión Táctica con TP1 al 50% de la posición + movimiento automático a Break-Even.
  3. TP2 Macro Swing en extremo opuesto del canal.

---

## ⚡ 2. CEREBRO 2: MEGA HÍBRIDO QUANTUM BTC DUAL (BINANCE CROSS MARGIN 5X)
* **Función:** Motor Supremo de acumulación y captura de liquidez en Bitcoin. Es el **reemplazo oficial definitivo** de la antigua estrategia Binance.
* **Exchange Operativo:** **Binance Cross Margin 5X** (Pares `BTCUSDT` y `BTCUSDC`).
* **Motor Autónomo:** [`cazador_mega_hibrido_btc_dual.py`](file:///home/h/Escritorio/RESPALDO/2027/SEPTIEMBRE_2027/cazador_mega_hibrido_btc_dual.py)
* **Dashboard de Monitoreo:** Puerto `8545` ([`dashboard_mega_hibrido_btc.py`](file:///home/h/Escritorio/RESPALDO/2027/SEPTIEMBRE_2027/dashboard_mega_hibrido_btc.py))
* **Archivo de Modo:** [`config_MEGA_HIBRIDO_BTC_modo.json`](file:///home/h/Escritorio/RESPALDO/2027/SEPTIEMBRE_2027/config_MEGA_HIBRIDO_BTC_modo.json)
* **Archivo de Estado:** [`estado_mega_hibrido_btc_dual.json`](file:///home/h/Escritorio/RESPALDO/2027/SEPTIEMBRE_2027/estado_mega_hibrido_btc_dual.json)
* **Capital & Apalancamiento:** $200 USD Base + $10 USD quincenales (10X apalancamiento efectivo).
* **Reglas de Oro Inviolables:**
  1. **BALA 1 (Entrada de Soporte 7D):** Se activa única y exclusivamente en el Piso de 7 Días (`soporte_7d`).
  2. **PISO / REBOTE INMINENTE (Gatillo Squeeze Momentum 1D & ATR):**
     - Gatilla **BALA DOBLE ($12.00 USD)** `SI Y SOLO SI` el `Margin Level` proyectado $\ge 1.50x$.
     - Si `Margin Level` $< 1.50x$, modula automáticamente a **BALA SIMPLE ($6.00 USD)**.
  3. **BLINDAJE DE TECHO ($85,000 USD):** Switch configurable en Dashboard para pausar compras si BTC $\ge \$85,000$ USD.
  4. **COMANDOS MANUALES DE EMERGENCIA:** Botones interactivos en la barra lateral del Dashboard 8545 para Cierre Total Inmediato (100%) o Venta Parcial (50%).
  5. **CONEXIÓN EN VIVO TIEMPO REAL:** Integración directa con Binance API3 usando sincronización `serverTime`.

---

## 🏛️ 3. SAKURA & MATRIX SUPREMA DUAL 2027 (PUERTO 8500)
* **Dashboard Consolidado:** Puerto `8500` ([`dashboard_maestro.py`](file:///home/h/Escritorio/RESPALDO/2027/dashboard_maestro.py))
* **Propósito:** Visualización unificada de saldos consolidados, control de cada peso en flotante, asistente táctico IA de entradas y métricas macro on-chain.

---

## 📌 MATRIZ RESUMEN DE PUERTOS Y COMANDOS

| Componente | Exchange | Puerto Dashboard | Script de Motor | Estado |
| :--- | :--- | :---: | :--- | :---: |
| **Cerebro 1: Blue Chips** | BingX | **8540** | [`cazador_blue_chips_wall_street.py`](file:///home/h/Escritorio/RESPALDO/2027/SEPTIEMBRE_2027/cazador_blue_chips_wall_street.py) | 🟢 EN VIVO |
| **Cerebro 2: Mega Híbrido BTC** | Binance 5X | **8545** | [`cazador_mega_hibrido_btc_dual.py`](file:///home/h/Escritorio/RESPALDO/2027/SEPTIEMBRE_2027/cazador_mega_hibrido_btc_dual.py) | 🟢 EN VIVO |
| **Matrix Suprema Dual 2027** | Consolidado | **8500** | [`dashboard_maestro.py`](file:///home/h/Escritorio/RESPALDO/2027/dashboard_maestro.py) | 🟢 EN VIVO |

---

## 🔒 COMPROMISO DE ENFOQUE DEL AGENTE AI
El asistente IA está programado para mantener su foco de trabajo **exclusivamente en estos 2 cerebros de la carpeta Septiembre 2027**. Cualquier solicitud o análisis se ajustará a este marco sin inventar ni desviar la atención a configuraciones anteriores.
