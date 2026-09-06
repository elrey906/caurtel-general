# 🔒 GUÍA DE SUBIDA A GITHUB PRIVADO & STREAMLIT CLOUD (100% BLINDADO)

Este repositorio local ya fue inicializado y blindado con un `.gitignore` militar:
* 🛡️ Tu archivo `.env` con claves reales **ESTÁ BLOQUEADO Y NUNCA SE SUBIRÁ**.
* 🛡️ Los logs, saldos locales y bases de datos **ESTÁN PROTEGIDOS**.
* 🛡️ Ningún crawler, bot ni IA pública puede acceder a tus claves.

---

## 📌 PASO 1: Crear el Repositorio en GitHub (Modo Privado)

1. Ve a [https://github.com/new](https://github.com/new).
2. **Repository name:** `cazador-cuartel-general` (o el nombre que prefieras).
3. **Visibilidad:** Selecciona obligatorio **🔒 Private** (Privado).
4. **NO marques** "Add a README file", ni ".gitignore", ni "license" (el repositorio local ya los tiene listos).
5. Haz clic en **Create repository**.

---

## 📌 PASO 2: Vincular y Subir tu Código Local

Copia y corre estos comandos en una terminal dentro de `/home/h/Escritorio/SEPTIEMBRE`:

```bash
cd /home/h/Escritorio/SEPTIEMBRE

# Reemplaza TU_USUARIO_GITHUB con tu nombre de usuario real en GitHub:
git remote add origin https://github.com/TU_USUARIO_GITHUB/cazador-cuartel-general.git

# Empujar el código a la rama main:
git push -u origin main
```
*(GitHub te pedirá tu usuario y tu Personal Access Token como contraseña).*

---

## 📌 PASO 3: Desplegar en Streamlit Community Cloud (Gratis y Permanente)

1. Entra a [https://share.streamlit.io](https://share.streamlit.io) e inicia sesión con tu cuenta de GitHub.
2. Haz clic en **"New app"**.
3. Configura:
   * **Repository:** `TU_USUARIO_GITHUB/cazador-cuartel-general`
   * **Branch:** `main`
   * **Main file path:** `dashboard_maestro.py`
4. **IMPORTANTE (SECRETOS BLINDADOS):**
   * Despliega la opción **"Advanced settings..."** y ve a la sección **Secrets**.
   * Pega allí las variables de tu archivo `.env` con esta sintaxis:

```toml
BINANCE_API_KEY = "tu_binance_api_key"
BINANCE_API_SECRET = "tu_binance_api_secret"

BINGX_API_KEY = "tu_bingx_api_key"
BINGX_API_SECRET = "tu_bingx_api_secret"

TELEGRAM_BOT_TOKEN = "tu_telegram_bot_token"
TELEGRAM_CHAT_ID = "tu_telegram_chat_id"
```
5. Haz clic en **Deploy!**.

---

## 🎉 RESULTADO FINAL:
* Tendrás una **URL HTTPS fija e inviolable** (ej: `https://cazador-cuartel-general.streamlit.app`).
* Acceso instantáneo desde el móvil **sin necesidad de túneles Cloudflare ni terminales abiertas**.
* Tus claves estarán encriptadas y protegidas por la infraestructura de Streamlit y GitHub.
