#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛰️ GUARDIÁN DE TÚNEL CLOUDFLARE 24/7 & NOTIFICADOR TELEGRAM
Mantiene un túnel público seguro apuntando a los Dashboards de Septiembre 2027 (Puerto 8500 por defecto),
detecta la URL generada por Cloudflare y la envía directamente a Telegram.
Si el túnel cae, se reinicia automáticamente y reenvía el nuevo enlace.
"""

import os
import sys
import time
import subprocess
import re
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

CLOUDFLARED_BIN = "/home/h/Escritorio/RESPALDO/parley-stats/bin/cloudflared"
PORT = 8500  # Dashboard Maestro Consolidado
URL_FILE_DESKTOP = "/home/h/Escritorio/ENLACE_CAZADOR_MOVIL.txt"
URL_FILE_LOCAL = os.path.join(BASE_DIR, "ENLACE_MOVIL.txt")
LOG_FILE = os.path.join(BASE_DIR, "LOGS", "tunel_maestro.log")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {msg}"
    print(entry, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass

def enviar_telegram(url):
    if not BOT_TOKEN or not CHAT_ID:
        log("❌ No se encontraron credenciales de Telegram.")
        return
        
    mensaje = (
        "🦅 *CAZADOR PRO 2027 — ENLACE REMOTO MÓVIL*\n\n"
        "📱 *Dashboard Maestro Consolidado (8500):*\n"
        f"🔗 `{url}`\n\n"
        "🟢 *Estado:* Cerebros y Dashboards 100% Vivos\n"
        "⚡ *Acceso:* Toca el enlace para ver posiciones, saldos y métricas en vivo desde la calle.\n"
        f"🕒 _Generado: {time.strftime('%Y-%m-%d %H:%M:%S')}_"
    )
    
    endpoint = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    try:
        r = requests.post(endpoint, json=payload, timeout=10)
        if r.status_code == 200:
            log("✅ Enlace enviado a Telegram con éxito.")
        else:
            log(f"⚠️ Error enviando a Telegram: {r.status_code} - {r.text}")
    except Exception as e:
        log(f"❌ Excepción enviando a Telegram: {e}")

def guardar_enlace_local(url):
    contenido = (
        "====================================================\n"
        "🦅 ENLACE REMOTO MÓVIL - CAZADOR PRO 2027\n"
        "====================================================\n"
        "📱 Abre este enlace en tu teléfono desde la calle:\n\n"
        f"   {url}\n\n"
        "====================================================\n"
        f"🕒 Actualizado: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        "====================================================\n"
    )
    for p in [URL_FILE_DESKTOP, URL_FILE_LOCAL]:
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(contenido)
            log(f"Enlace guardado en: {p}")
        except Exception as e:
            log(f"Error guardando {p}: {e}")

def main():
    log("🚀 Iniciando servicio de Túnel Remoto Cloudflare para Dashboard Maestro (8500)...")
    if not os.path.exists(CLOUDFLARED_BIN):
        log(f"❌ Binario cloudflared no encontrado en {CLOUDFLARED_BIN}")
        sys.exit(1)

    while True:
        try:
            cmd = [CLOUDFLARED_BIN, "tunnel", "--url", f"http://localhost:{PORT}"]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            url_notificada = None
            log("Túnel lanzado, capturando URL de Cloudflare...")
            
            for line in iter(proc.stdout.readline, ''):
                if not line:
                    break
                m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                if m:
                    url = m.group(0)
                    if url != url_notificada and "api.trycloudflare.com" not in url:
                        url_notificada = url
                        log(f"🎉 ¡TÚNEL ACTIVO! URL Remota: {url_notificada}")
                        guardar_enlace_local(url_notificada)
                        enviar_telegram(url_notificada)
                        
            proc.wait()
            log("⚠️ El proceso de cloudflared terminó. Reiniciando en 5 segundos...")
            time.sleep(5)
            
        except Exception as e:
            log(f"❌ Error en bucle principal del túnel: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
