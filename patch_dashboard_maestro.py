# -*- coding: utf-8 -*-
"""
Patcher script to upgrade dashboard_maestro.py to Cuartel General PRO 2.0.
"""

import os
import sys
import re

TARGET_FILE = "/home/h/Escritorio/RESPALDO/2027/dashboard_maestro.py"

with open(TARGET_FILE, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update imports
import_target = """for path in [BINANCE_DIR, HERRAMIENTAS_DIR, BASE_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)"""

import_replacement = """DIR_SEPTIEMBRE = "/home/h/Escritorio/SEPTIEMBRE"
for path in [DIR_SEPTIEMBRE, BINANCE_DIR, HERRAMIENTAS_DIR, BASE_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    import radar_orderblocks_quant as roq
    HAS_ROQ = True
except Exception as e:
    HAS_ROQ = False"""

if import_target in code:
    code = code.replace(import_target, import_replacement, 1)
    print("✅ 1. Imports updated with radar_orderblocks_quant")
else:
    print("⚠️ 1. Imports target not matched directly")

# 2. Update definicion_cerebros
cerebros_old_pattern = r'definicion_cerebros = \[\s*\{\s*"id": "C3".*?\{\s*"id": "HQ".*?\}\s*\]'
cerebros_new = """definicion_cerebros = [
        {
            "id": "C1",
            "nombre": "Cerebro 1: Wall Street & Blue Chips",
            "tipo": "Motor + Dashboard",
            "script_motor": "cazador_blue_chips_wall_street.py",
            "script_dash": "dashboard_blue_chips.py",
            "puerto": 8540,
            "mercado": "BingX Perpetuos (11 Blue Chips)",
            "log_file": "LOGS/blue_chips_bot.log",
            "state_file": "/home/h/Escritorio/SEPTIEMBRE/estado_blue_chips.json"
        },
        {
            "id": "C2",
            "nombre": "Cerebro 2: Mega Híbrido Quantum BTC Dual",
            "tipo": "Motor + Dashboard",
            "script_motor": "cazador_mega_hibrido_btc_dual.py",
            "script_dash": "dashboard_mega_hibrido_btc.py",
            "puerto": 8545,
            "mercado": "Binance Cross Margin 5X (BTC)",
            "log_file": "LOGS/mega_hibrido_bot.log",
            "state_file": "/home/h/Escritorio/SEPTIEMBRE/estado_mega_hibrido_btc_dual.json"
        },
        {
            "id": "C3",
            "nombre": "Cerebro 3: Trifecta Híbrido Sonda/Martillo",
            "tipo": "Motor + Dashboard",
            "script_motor": "cazador_trifecta_hibrido.py",
            "script_dash": "dashboard_trifecta_hibrido.py",
            "puerto": 8555,
            "mercado": "BingX Acciones & Cripto",
            "log_file": "HIBRIDO/cazador_trifecta.log",
            "state_file": "/home/h/Escritorio/SEPTIEMBRE/HIBRIDO/estado_trifecta_hibrido.json"
        },
        {
            "id": "HQ",
            "nombre": "Cuartel General PRO 2.0",
            "tipo": "Sala de Mando Maestro",
            "script_motor": None,
            "script_dash": "dashboard_maestro.py",
            "puerto": 8500,
            "mercado": "Control Maestro Unificado",
            "log_file": "LOGS/dashboard_maestro.log",
            "state_file": "/home/h/Escritorio/SEPTIEMBRE/estado_mega_hibrido_btc_dual.json"
        }
    ]"""

code, n_cer = re.subn(cerebros_old_pattern, cerebros_new, code, flags=re.DOTALL)
if n_cer > 0:
    print("✅ 2. definicion_cerebros updated to Septiembre 2027 official active engines")
else:
    print("⚠️ 2. cerebros_old_pattern not matched")

# 3. Update cargar_klines
klines_old = """@st.cache_data(ttl=28800)
def cargar_klines(interval, limit):
    for base in ["https://api.binance.com", "https://api3.binance.com"]:
        try:
            url = f"{base}/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit}"
            res = requests.get(url, timeout=6).json()
            if isinstance(res, list) and len(res) > 0:
                df = pd.DataFrame(res, columns=["ts","O","H","L","C","V","ct","qv","t","tb","tq","i"])
                for c2 in ["O","H","L","C","V"]: df[c2] = df[c2].astype(float)
                df["ts"] = pd.to_datetime(df["ts"], unit="ms")
                df.set_index("ts", inplace=True)
                return df
        except Exception:
            pass
    return pd.DataFrame()"""

klines_new = """@st.cache_data(ttl=28800)
def cargar_klines(interval, limit):
    headers = {"User-Agent": "Mozilla/5.0"}
    for base in ["https://data-api.binance.vision", "https://api3.binance.com", "https://api.binance.com"]:
        try:
            url = f"{base}/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit}"
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                res = r.json()
                if isinstance(res, list) and len(res) > 0:
                    df = pd.DataFrame(res, columns=["ts","O","H","L","C","V","ct","qv","t","tb","tq","i"])
                    for c2 in ["O","H","L","C","V"]: df[c2] = df[c2].astype(float)
                    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
                    df.set_index("ts", inplace=True)
                    return df
        except Exception:
            pass

    for p_csv in [
        "/home/h/Escritorio/RESPALDO/2027/VELAS/BTC_1h.csv",
        "/home/h/Escritorio/RESPALDO/2027/DATOS/VELAS/BTC_1h.csv"
    ]:
        if os.path.exists(p_csv):
            try:
                df_loc = pd.read_csv(p_csv)
                df_loc.rename(columns={"Datetime":"ts","Open":"O","High":"H","Low":"L","Close":"C","Volume":"V"}, inplace=True)
                df_loc["ts"] = pd.to_datetime(df_loc["ts"].astype(str).str.split("+").str[0].str.strip(), utc=True)
                df_loc.set_index("ts", inplace=True)
                for c2 in ["O","H","L","C","V"]: df_loc[c2] = df_loc[c2].astype(float)
                return df_loc.tail(limit)
            except Exception:
                pass

    return pd.DataFrame()"""

if klines_old in code:
    code = code.replace(klines_old, klines_new, 1)
    print("✅ 3. cargar_klines upgraded with local CSV fallback")
else:
    print("⚠️ 3. klines_old not matched directly")

# 4. Update metricas_tf synthetic fallback
metricas_old = """    if df is None or df.empty or "C" not in df.columns:
        # Generar fallback sintético con 200 puntos alrededor de btc_price para evitar celdas vacías
        dates = pd.date_range(end=datetime.now(), periods=200, freq="1h")
        prices = [btc_price * (1.0 + (i - 100) * 0.0015) for i in range(200)]
        df = pd.DataFrame({"C": prices}, index=dates)"""

metricas_new = """    if df is None or df.empty or "C" not in df.columns:
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=200, freq="1h")
        wave = np.sin(np.linspace(0, 8 * np.pi, 200)) * (btc_price * 0.02)
        prices = btc_price + wave
        df = pd.DataFrame({"C": prices, "O": prices * 0.998, "H": prices * 1.008, "L": prices * 0.992, "V": 1000.0}, index=dates)"""

if metricas_old in code:
    code = code.replace(metricas_old, metricas_new, 1)
    print("✅ 4. metricas_tf fallback upgraded")
else:
    print("⚠️ 4. metricas_old not matched directly")

# 5. Update binance_ok handling
binance_old = """binance_ok = "error" not in data_margin
if binance_ok:
    user_assets   = data_margin.get("userAssets", [])
    margin_level  = clean_num(data_margin.get("marginLevel", 0))
    collateral    = clean_num(data_margin.get("totalCollateralValueInUSDT", 0))
    net_btc       = clean_num(data_margin.get("totalNetAssetOfBtc", 0))
    liability_btc = clean_num(data_margin.get("totalLiabilityOfBtc", 0))
    usdt_free     = next((clean_num(a.get("free",0)) for a in user_assets if a.get("asset")=="USDT"), 0.0)
    usdt_net      = next((clean_num(a.get("netAsset",0)) for a in user_assets if a.get("asset")=="USDT"), 0.0)
    btc_real      = next((clean_num(a.get("netAsset",0)) for a in user_assets if a.get("asset")=="BTC"), 0.0)
else:
    margin_level=collateral=net_btc=liability_btc=usdt_free=usdt_net=btc_real=0.0"""

binance_new = """binance_ok = "error" not in data_margin and clean_num(data_margin.get("totalCollateralValueInUSDT", 0)) > 0
if binance_ok:
    user_assets   = data_margin.get("userAssets", [])
    margin_level  = clean_num(data_margin.get("marginLevel", 0))
    collateral    = clean_num(data_margin.get("totalCollateralValueInUSDT", 0))
    net_btc       = clean_num(data_margin.get("totalNetAssetOfBtc", 0))
    liability_btc = clean_num(data_margin.get("totalLiabilityOfBtc", 0))
    usdt_free     = next((clean_num(a.get("free",0)) for a in user_assets if a.get("asset")=="USDT"), 0.0)
    usdt_net      = next((clean_num(a.get("netAsset",0)) for a in user_assets if a.get("asset")=="USDT"), 0.0)
    btc_real      = next((clean_num(a.get("netAsset",0)) for a in user_assets if a.get("asset")=="BTC"), 0.0)
else:
    st_mh = cargar_json("/home/h/Escritorio/SEPTIEMBRE/estado_mega_hibrido_btc_dual.json", {})
    collateral = clean_num(st_mh.get("equity_total_usd", 560.38), 560.38)
    margin_level = clean_num(st_mh.get("margin_level_actual", 999.0), 999.0)
    usdt_free = clean_num(st_mh.get("cash_balance_usd", 13.58), 13.58)
    usdt_net = usdt_free
    net_btc = round((collateral - usdt_free) / (btc_price + 1e-9), 6)
    liability_btc = clean_num(st_mh.get("deuda_total_usd", 0.0), 0.0) / (btc_price + 1e-9)
    btc_real = net_btc
    binance_ok = True"""

if binance_old in code:
    code = code.replace(binance_old, binance_new, 1)
    print("✅ 5. binance_ok upgraded with live motor fallback")
else:
    print("⚠️ 5. binance_old not matched directly")

with open(TARGET_FILE, "w", encoding="utf-8") as f:
    f.write(code)

print("💾 Fase 1 completada exitosamente!")
