<div align="center">

<img src="../assets/banner.png" alt="0x Cookies" width="100%"/>

# 0x Cookies

**Comprobador masivo de cookies y sesiones estilo OpenBullet — con Chromium real.**

Comprueba en masa si tus cookies / inicios de sesión guardados siguen vivos en
**139 plataformas**. A diferencia de los comprobadores HTTP simples, ejecuta un
**Chromium headless real** (Playwright), así que sigue siendo preciso en sitios que
siempre responden `HTTP 200` (Microsoft, redes sociales, SaaS, …).

[![Python](https://img.shields.io/badge/python-3.9%2B-34e5b0?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/playwright-Chromium-8b7cf6?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev/)
[![Platforms](https://img.shields.io/badge/platforms-139-f5b642?style=flat-square)](#-plataformas-integradas)
[![License](https://img.shields.io/badge/license-MIT-34e5b0?style=flat-square)](../LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-8b7cf6?style=flat-square)](../CONTRIBUTING.md)
[![Made by 0xgetz](https://img.shields.io/badge/by-0xgetz-9aa4b2?style=flat-square&logo=github)](https://github.com/0xgetz)

[English](../README.md) · [Indonesia](README.id.md) · [**Español**](README.es.md) · [中文](README.zh.md) · [العربية](README.ar.md)

</div>

---

## Por qué existe

La mayoría de los comprobadores de cookies envían una petición HTTP y miran el código de
estado. Eso falla en cuanto un sitio responde `200 OK` tanto para una sesión viva **como**
para una muerta — obtienes 100% "válido" con basura. **0x Cookies** carga la página en un
navegador real, sigue la redirección y decide por la **URL final + el DOM** si realmente
has iniciado sesión.

- **Veredictos de navegador real** — Chromium headless vía Playwright.
- **Contextos aislados** — cada entrada corre en su propio contexto, las cookies nunca se
  filtran entre cuentas y un archivo muerto jamás parece válido.
- **El fallo gana al éxito** — aterrizar en una página de login/error siempre es `invalid`.
- **139 plataformas listas** — más un motor de configuración HTTP + navegador genérico.
- **Panel de control web** — sube entradas/configs/proxies, start/pause/stop, estadísticas en vivo.
- **Runner CLI** — el mismo motor, ideal para un VPS o cron.
- **Pool de proxies** — rota y auto-bloquea al fallar (`http/https/socks4/socks5`).

> **Solo para uso autorizado.** Prueba cuentas propias o que tengas permiso explícito de
> probar. Ver [Disclaimer](#️-disclaimer).

---

## Inicio rápido

```bash
git clone https://github.com/0xgetz/0x-cookies.git
cd 0x-cookies
./start.sh                 # abre http://localhost:8080
```

`start.sh` instala Playwright, descarga Chromium y trae las librerías del sistema
necesarias (apt / dnf / apk). ¿Prefieres hacerlo a mano?

```bash
pip install playwright
python -m playwright install chromium
python -m playwright install-deps chromium     # Debian/Ubuntu
python server.py --host 0.0.0.0 --port 8080
```

> Abre los puertos **8080** (panel) **y 8081** (WebSocket de estadísticas en vivo) si
> accedes al panel desde otra máquina. Si 8081 está bloqueado, el panel recurre a polling.

---

## Usar el panel de control

1. **Inputs** — pega uno por línea, o sube un `.txt`.
   modo `userpass` → `user:pass`; modo `cookie` → el blob de cookie (o la ruta de un archivo).
2. **Config** — pega JSON, elige un preset, o carga uno de las 139 configs de
   `configs/platforms/<nombre>.json`.
3. **Proxies** *(opcional)* — uno por línea:
   `host:port`, `user:pass@host:port`, `scheme://host:port`
   (`http` `https` `socks4` `socks5` `socks5h`). Auto-rotación + auto-bloqueo.
4. **Options** — workers, timeout, reintentos, duración del bloqueo de proxy, headless on/off.
5. **Start** — observa tested / hits / invalid / errors / CPM / progress en vivo.
6. Descarga **hits** (`data/hits.txt`) y **todos los resultados** (`data/all.txt`).

---

## Plataformas integradas

**139 configuraciones** se incluyen en [`configs/platforms/`](../configs/platforms),
cubriendo social, email, nube, desarrollo, finanzas, streaming, compras y más — p. ej.
`google` `microsoft` `github` `discord` `instagram` `tiktok` `netflix` `spotify`
`openai` `claude` `notion` `aws` `binance` `paypal` `steam` …

Cada una es una comprobación `redirect` (el sitio rebota a usuarios anónimos) o `marker`
(SPA: cotejada por selectores DOM válidos/ inválidos y marcadores del body). Regenera
todo el conjunto con:

```bash
python gen_configs.py
```

---

## Formato de config (estilo OpenBullet)

```json
{
  "name": "Site login check",
  "author": "0x Cookies",
  "type": "http",
  "input_format": "userpass",
  "request": {
    "url": "https://site.com/api/login",
    "method": "POST",
    "headers": { "Cookie": "<COOKIE>", "User-Agent": "Mozilla/5.0" },
    "body": "user=<USER>&pass=<PASS>"
  },
  "captures": [ { "name": "token", "regex": "\"token\"\\s*:\\s*\"([^\"]+)\"" } ],
  "success": { "status": [200], "body_regex": "\"ok\":true", "url_regex": "/dashboard" },
  "fail":    { "body_regex": "invalid|incorrect", "url_regex": "(login|signin)" },
  "retry": 1
}
```

| Campo | Significado |
|-------|-------------|
| `type` | `http` = petición directa · `browser` = carga la página en Chromium |
| `input_format` | `line` · `userpass` · `cookie` |
| `request` | url / method / headers / body (solo HTTP) |
| `captures` | capturas regex escritas al archivo de **hits** |
| `success` / `fail` | `status` · `body_regex` · `url_regex` |
| vars de plantilla | `<USER>` `<PASS>` `<LINE>` `<COOKIE>` usables en url, headers, body **y** regex |

**`fail` siempre gana a `success`** — si la URL final coincide con una página de
login/error el resultado es `invalid`, sin importar qué más coincidió.

---

## CLI

```bash
# config HTTP
python cli.py --config configs/example_http.json --inputs users.txt \
  --proxies proxies.txt --workers 8 --timeout 30 \
  --hits hits.txt --all all.txt

# comprobación de cookies en navegador usando una plataforma integrada
python cli.py --config configs/platforms/github.json --inputs cookies/ \
  --workers 4 --headful
```

---

## REST API

| Método | Ruta | Body |
|--------|------|------|
| `POST` | `/api/inputs` | `{"text":"a\nb"}` o `{"lines":[...]}` |
| `POST` | `/api/config` | `{"raw":"<json>"}` o un objeto config |
| `POST` | `/api/proxies` | `{"text":"host:port\n..."}` |
| `POST` | `/api/start` | `{"workers":4,"timeout":30,"retry":1,"headless":true}` |
| `POST` | `/api/stop` · `/api/pause` · `/api/resume` | — |
| `GET` | `/api/stats` | stats + log |
| `GET` | `/api/hits` · `/api/all` | resultados (texto) |
| `WS` | `ws://host:8081/` | envía stats + log cada 0.5s |

Define `OXC_TOKEN` para exigir la cabecera `X-Auth-Token` en cada `POST`.

---

## Estructura del proyecto

Ver **[STRUCTURE.md](../STRUCTURE.md)** para el diagrama anotado completo.

```
0x-cookies/
├── server.py          panel de control (HTTP + WebSocket stats en vivo)
├── cli.py             runner headless
├── start.sh           lanzador de un paso (instala navegador + libs)
├── gen_configs.py     genera las 139 configs de plataformas
├── core/              config · engine · proxies
├── web/               UI del dashboard
├── configs/           ejemplo + configs por plataforma
├── docs/              5 READMEs traducidos
└── assets/            logo + banner
```

---

## VPS sin root (librerías Chromium manuales)

Si `apt` no está disponible y Chromium falla con
`error while loading shared libraries: libglib-2.0.so.0`:

```bash
mkdir -p third_party/lib
cp /path/to/*.so* third_party/lib/   # reúne los .so que falten
./start.sh                            # start.sh añade third_party/lib a LD_LIBRARY_PATH
```

---

## Contribuir

Issues y PRs son bienvenidos — sobre todo nuevas configs de plataformas. Ver
[CONTRIBUTING.md](../CONTRIBUTING.md).

## Licencia

[MIT](../LICENSE) © 0x Cookies

## ⚠️ Disclaimer

Esta herramienta se ofrece para **investigación de seguridad legítima y pruebas sobre
cuentas propias o para las que tengas autorización explícita**. Eres el único
responsable de cómo la uses. Nunca la uses contra sistemas o cuentas sin permiso.

---

<div align="center">

Hecho por **0x Cookies** · [GitHub @0xgetz](https://github.com/0xgetz) · [Telegram @xiyyyyz](https://t.me/xiyyyyz)

</div>
