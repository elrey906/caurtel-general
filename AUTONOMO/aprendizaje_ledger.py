# -*- coding: utf-8 -*-
"""
LIBRO MAYOR CONTABLE Y AUTO-APRENDIZAJE
1. Registra cada trade en dólares netos ($), porcentaje y duración.
2. Calcula Win Rate, Profit Factor y balance acumulado.
3. Guarda lecciones aprendidas (ajuste de ponderación por activo).
"""
import os, sys, json, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORIAL_FILE = os.path.join(BASE_DIR, "libro_mayor_pnl.json")
MEMORIA_FILE = os.path.join(BASE_DIR, "memoria_aprendizaje.json")

def cargar_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return default

def guardar_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error guardando {path}: {e}")

def registrar_operacion_cerrada(fase, sym, exchange, side, entry_px, exit_px, margen_usd, pnl_usd, motivo, duracion_str):
    """
    Registra el trade completado en el Libro Mayor
    """
    ledger = cargar_json(HISTORIAL_FILE, {
        "balance_neto_total_usd": 0.0,
        "ganancia_bruta_usd": 0.0,
        "perdida_bruta_usd": 0.0,
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "historial": []
    })
    
    pnl_real = round(float(pnl_usd), 2)
    es_win = pnl_real > 0
    
    ledger["total_trades"] += 1
    ledger["balance_neto_total_usd"] = round(ledger["balance_neto_total_usd"] + pnl_real, 2)
    if es_win:
        ledger["wins"] += 1
        ledger["ganancia_bruta_usd"] = round(ledger["ganancia_bruta_usd"] + pnl_real, 2)
    else:
        ledger["losses"] += 1
        ledger["perdida_bruta_usd"] = round(ledger["perdida_bruta_usd"] + abs(pnl_real), 2)
        
    ticket = {
        "id_trade": f"TRD_{sym}_{int(datetime.datetime.now().timestamp())}",
        "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fase": fase, # FASE 1 o FASE 2 o BINANCE_BTC
        "sym": sym,
        "exchange": exchange,
        "side": side,
        "entry_px": entry_px,
        "exit_px": exit_px,
        "margen_usd": margen_usd,
        "pnl_usd": pnl_real,
        "pnl_pct": round((pnl_real / margen_usd) * 100.0, 1) if margen_usd > 0 else 0.0,
        "motivo": motivo,
        "duracion": duracion_str
    }
    ledger["historial"].insert(0, ticket)
    guardar_json(HISTORIAL_FILE, ledger)
    
    # Actualizar Memoria de Aprendizaje
    memoria = cargar_json(MEMORIA_FILE, {"estadisticas_por_activo": {}, "reglas_aprendidas": []})
    stats_act = memoria["estadisticas_por_activo"].setdefault(sym, {"trades": 0, "wins": 0, "pnl_acumulado": 0.0})
    stats_act["trades"] += 1
    if es_win: stats_act["wins"] += 1
    stats_act["pnl_acumulado"] = round(stats_act["pnl_acumulado"] + pnl_real, 2)
    
    if not es_win and "DIA_10" in motivo:
        memoria["reglas_aprendidas"].append(f"Regla Día 10 aplicada en {sym}: Se cortó posición estancada con pérdida limitada de ${pnl_real:.2f} USD")
        
    guardar_json(MEMORIA_FILE, memoria)
    return ticket

def obtener_resumen_contable():
    ledger = cargar_json(HISTORIAL_FILE, {
        "balance_neto_total_usd": 0.0,
        "ganancia_bruta_usd": 0.0,
        "perdida_bruta_usd": 0.0,
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "historial": []
    })
    tt = ledger["total_trades"]
    wr = (ledger["wins"] / max(1, tt)) * 100.0
    pf = (ledger["ganancia_bruta_usd"] / max(0.01, ledger["perdida_bruta_usd"])) if ledger["perdida_bruta_usd"] > 0 else ledger["ganancia_bruta_usd"]
    return {
        "balance_neto": ledger["balance_neto_total_usd"],
        "ganancia_bruta": ledger["ganancia_bruta_usd"],
        "perdida_bruta": ledger["perdida_bruta_usd"],
        "total_trades": tt,
        "win_rate": round(wr, 1),
        "profit_factor": round(pf, 2),
        "ultimos_tickets": ledger["historial"][:10]
    }
