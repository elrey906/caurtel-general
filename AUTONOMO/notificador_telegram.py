# -*- coding: utf-8 -*-
"""
🛰️ MÓDULO NOTIFICADOR TELEGRAM: CEREBRO 4 & CUARTEL GENERAL PRO
Despacha alertas enriquecidas con emojis, formato HTML/Markdown y control de fallos silenciosos.
"""
import os
import sys
import time
import requests
import logging
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROD_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
ENV_PATH = os.path.join(PROD_DIR, ".env")
load_dotenv(ENV_PATH)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

log = logging.getLogger("TELEGRAM_NOTIFIER")

def fmt_px(val: float) -> str:
    if val <= 0: return "$0.00"
    if val < 0.001: return f"${val:,.6f}"
    if val < 1.0: return f"${val:,.4f}"
    return f"${val:,.2f}"

def enviar_mensaje_telegram(mensaje: str, parse_mode: str = "HTML") -> bool:
    """
    Envía un mensaje formateado a Telegram con manejo seguro de excepciones y timeout.
    """
    if not BOT_TOKEN or not CHAT_ID:
        log.warning("Credenciales de Telegram no configuradas en .env.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }

    try:
        r = requests.post(url, json=payload, timeout=8)
        if r.status_code == 200:
            return True
        else:
            log.warning(f"Error enviando mensaje a Telegram: {r.status_code} - {r.text}")
            return False
    except Exception as e:
        log.warning(f"Excepción de conexión a Telegram: {e}")
        return False

def notificar_alerta_fantasma(sym: str, fase: str, tipo: str, side: str, entry_px: float, tp_px: float, sl_px: float, tp_pct: float, sl_pct: float, score: float, qty: float, rsi: float = 0.0, squeeze: str = "") -> bool:
    """
    Envía alerta instantánea de recomendación en MODO FANTASMA para Cerebro 4.
    """
    hora_str = time.strftime("%Y-%m-%d %H:%M:%S")
    fase_label = "⚡ FASE 1: ALTCOINS (48h)" if "1" in str(fase) else ("🏛️ FASE 2: WALL STREET (25D)" if "2" in str(fase) else "🪙 BINANCE MARGIN (BTC)")
    
    px_e = fmt_px(entry_px)
    px_tp = fmt_px(tp_px)
    px_sl = fmt_px(sl_px)

    mensaje = f"""👻 <b>[CEREBRO 4 - RECOMENDACIÓN FANTASMA]</b>
━━━━━━━━━━━━━━━━━━━━━━━━
💎 <b>Activo:</b> #{sym} ({tipo})
📂 <b>Módulo:</b> {fase_label}
📈 <b>Dirección:</b> <b>{side.upper()}</b>
🧠 <b>Score Cuántico ADN:</b> <b>{score:.1f} / 100 pts</b>
━━━━━━━━━━━━━━━━━━━━━━━━
💵 <b>Precio Entrada:</b> {px_e}
🎯 <b>Take Profit:</b> {px_tp} (+{tp_pct*100:.1f}%)
🛑 <b>Stop Loss:</b> {px_sl} (-{sl_pct*100:.1f}%)
📊 <b>Lote Calculado:</b> {qty} contratos ($10 USD @ 10X)
📊 <b>RSI 1H:</b> {rsi:.1f} pts | <b>Squeeze:</b> {squeeze}
━━━━━━━━━━━━━━━━━━━━━━━━
🛡️ <b>ESTADO ACTUAL:</b> 👻 <b>MODO FANTASMA (100% Simulado)</b>
<i>El autómata NO ha abierto orden real. Para operarlo con capital real, ingresa al Dashboard y presiona 'Pasar a REAL'.</i>
🕒 <i>{hora_str}</i>"""

    return enviar_mensaje_telegram(mensaje)

def notificar_promocion_real(sym: str, side: str, px: float, qty: float, tp_px: float, sl_px: float, order_id: str) -> bool:
    """
    Notifica cuando el usuario promueve manualmente una recomendación a REAL desde el Dashboard.
    """
    hora_str = time.strftime("%Y-%m-%d %H:%M:%S")
    px_str = fmt_px(px)
    tp_str = fmt_px(tp_px)
    sl_str = fmt_px(sl_px)

    mensaje = f"""🚀 <b>[ORDEN PROMOVIDA A REAL EN BINGX]</b>
━━━━━━━━━━━━━━━━━━━━━━━━
💎 <b>Activo:</b> #{sym}
📈 <b>Dirección:</b> <b>{side.upper()}</b>
💵 <b>Precio de Ejecución:</b> {px_str}
🎯 <b>Take Profit Configurado:</b> {tp_str}
🛑 <b>Stop Loss Configurado:</b> {sl_str}
📦 <b>Lote Nominal:</b> {qty} contratos ($10 USD @ 10X)
🆔 <b>ID de Orden:</b> <code>{order_id}</code>
━━━━━━━━━━━━━━━━━━━━━━━━
🟢 <b>Estado:</b> Posición Viva y Auditada en BingX Futures
🕒 <i>{hora_str}</i>"""

    return enviar_mensaje_telegram(mensaje)

def notificar_cierre_trade(modulo: str, sym: str, side: str, entry_px: float, exit_px: float, pnl_usd: float, motivo: str, duracion: str, es_real: bool = False) -> bool:
    """
    Notifica el cierre de un trade (TP, SL o Time-Stop) tanto en Modo Fantasma como Real.
    """
    hora_str = time.strftime("%Y-%m-%d %H:%M:%S")
    emoji_resultado = "🏆" if pnl_usd >= 0 else "🛑"
    tipo_envio = "🟢 REAL BINGX" if es_real else "👻 FANTASMA / PAPER"
    signo = "+" if pnl_usd >= 0 else ""
    e_str = fmt_px(entry_px)
    s_str = fmt_px(exit_px)
    
    mensaje = f"""{emoji_resultado} <b>[CIERRE DE OPERACIÓN - {tipo_envio}]</b>
━━━━━━━━━━━━━━━━━━━━━━━━
💎 <b>Activo:</b> #{sym} ({modulo})
📈 <b>Dirección:</b> {side.upper()}
💵 <b>Entrada:</b> {e_str} ➔ <b>Salida:</b> {s_str}
💰 <b>PnL Neto:</b> <b>{signo}${pnl_usd:,.2f} USD</b>
⏱️ <b>Duración:</b> {duracion}
📌 <b>Motivo:</b> {motivo}
━━━━━━━━━━━━━━━━━━━━━━━━
🕒 <i>{hora_str}</i>"""

    return enviar_mensaje_telegram(mensaje)

def notificar_disparo_binance_btc(num_bala: int, px: float, monto_usd: float, qty_btc: float, es_real: bool = True) -> bool:
    """
    Notifica la ejecución o simulación de una bala en Binance Cross Margin 5X para Cerebro 4.
    """
    hora_str = time.strftime("%Y-%m-%d %H:%M:%S")
    tipo_txt = "🟢 REAL BINANCE CROSS MARGIN 5X" if es_real else "👻 FANTASMA (Simulado)"
    px_str = fmt_px(px)
    
    mensaje = f"""🪙 <b>[DISPARO BALA BTC #{num_bala}/3 EN BINANCE]</b>
━━━━━━━━━━━━━━━━━━━━━━━━
💎 <b>Activo:</b> #BTC (Bitcoin)
📂 <b>Módulo:</b> Cerebro 4 · Binance Cross Margin 5X
💵 <b>Precio de Entrada:</b> {px_str}
💰 <b>Monto Margen:</b> ${monto_usd:.2f} USD (Nominal: ${monto_usd * 5:.2f} USD @ 5X)
📦 <b>Lote Acumulado:</b> {qty_btc:.5f} BTC
🎯 <b>Take Profit Objetivo:</b> +4.0% sobre Costo Promedio (Reciclaje)
━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ <b>Modo de Ejecución:</b> {tipo_txt}
🕒 <i>{hora_str}</i>"""

    return enviar_mensaje_telegram(mensaje)
