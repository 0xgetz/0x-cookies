<div align="center">

<img src="../assets/banner.png" alt="0x Cookies" width="100%"/>

# 0x Cookies

**OpenBullet 风格的批量 Cookie 与会话检测器 —— 由真实 Chromium 驱动。**

批量检测你保存的 Cookie / 登录状态在 **139 个平台** 上是否仍然有效。
与普通的 HTTP 检测器不同，它运行 **真实的 headless Chromium**（Playwright），
因此在那些始终返回 `HTTP 200` 的网站（微软、社交、SaaS 等）上依然准确。

[![Python](https://img.shields.io/badge/python-3.9%2B-34e5b0?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/playwright-Chromium-8b7cf6?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev/)
[![Platforms](https://img.shields.io/badge/platforms-139-f5b642?style=flat-square)](#-内置平台)
[![License](https://img.shields.io/badge/license-MIT-34e5b0?style=flat-square)](../LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-8b7cf6?style=flat-square)](../CONTRIBUTING.md)
[![Made by 0xgetz](https://img.shields.io/badge/by-0xgetz-9aa4b2?style=flat-square&logo=github)](https://github.com/0xgetz)

[English](../README.md) · [Indonesia](README.id.md) · [Español](README.es.md) · [**中文**](README.zh.md) · [العربية](README.ar.md)

</div>

---

## 为什么需要它

大多数 Cookie 检测器发送一个 HTTP 请求然后看状态码。一旦某个网站对 **有效** 和
**失效** 的会话都返回 `200 OK`，这种方法就失效了 —— 你会在垃圾数据上得到 100% 的
“有效”。**0x Cookies** 在真实浏览器中加载页面，跟随跳转，并依据 **最终 URL + DOM**
判断你是否真的已登录。

- **真实浏览器裁决** —— 通过 Playwright 运行 headless Chromium。
- **隔离上下文** —— 每个输入都在独立的浏览器上下文中运行，Cookie 不会在账号间泄漏，
  失效的文件永远不会显示为有效。
- **失败优先于成功** —— 只要落在登录/错误页面，结果一定为 `invalid`。
- **139 个现成平台** —— 外加通用的 HTTP + 浏览器配置引擎。
- **Web 控制面板** —— 上传输入/配置/代理，启动/暂停/停止，实时统计。
- **CLI 运行器** —— 同一引擎，非常适合 VPS 或定时任务。
- **代理池** —— 失败时自动轮换与封禁（`http/https/socks4/socks5`）。

> **仅限授权使用。** 请只测试你自己拥有的、或已获得明确许可的账号。
> 参见 [免责声明](#️-disclaimer)。

---

## 快速开始

```bash
git clone https://github.com/0xgetz/0x-cookies.git
cd 0x-cookies
./start.sh                 # 打开 http://localhost:8080
```

`start.sh` 会安装 Playwright、下载 Chromium，并拉取所需的系统库（apt / dnf / apk）。
想手动操作？

```bash
pip install playwright
python -m playwright install chromium
python -m playwright install-deps chromium     # Debian/Ubuntu
python server.py --host 0.0.0.0 --port 8080
```

> 如果从其他机器访问面板，请开放 **8080**（面板）**和 8081**（实时统计 WebSocket）端口。
> 若 8081 被阻塞，面板会自动改用轮询。

---

## 使用控制面板

1. **Inputs** —— 每行一条粘贴，或上传 `.txt`。
   `userpass` 模式 → `user:pass`；`cookie` 模式 → Cookie 内容（或 Cookie 文件路径）。
2. **Config** —— 粘贴 JSON、选择预设，或从 `configs/platforms/<名称>.json` 加载
   139 个配置之一。
3. **Proxies** *（可选）* —— 每行一条：
   `host:port`、`user:pass@host:port`、`scheme://host:port`
   （`http` `https` `socks4` `socks5` `socks5h`）。自动轮换 + 自动封禁。
4. **Options** —— 并发数、超时、重试、代理封禁时长、headless 开关。
5. **Start** —— 实时查看 tested / hits / invalid / errors / CPM / progress。
6. 下载 **hits**（`data/hits.txt`）与 **全部结果**（`data/all.txt`）。

---

## 内置平台

[`configs/platforms/`](../configs/platforms) 中内置 **139 个配置**，覆盖社交、邮箱、
云服务、开发者、金融、流媒体、购物等 —— 例如
`google` `microsoft` `github` `discord` `instagram` `tiktok` `netflix` `spotify`
`openai` `claude` `notion` `aws` `binance` `paypal` `steam` 等。

每个配置要么是 `redirect` 检测（网站会弹开匿名用户），要么是 `marker` 检测
（SPA：通过有效/无效的 DOM 选择器和页面标记来匹配）。重新生成整套配置：

```bash
python gen_configs.py
```

---

## 配置格式（OpenBullet 风格）

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

| 字段 | 含义 |
|-------|------|
| `type` | `http` = 直接请求 · `browser` = 在 Chromium 中加载页面 |
| `input_format` | `line` · `userpass` · `cookie` |
| `request` | url / method / headers / body（仅 HTTP） |
| `captures` | 写入 **hits** 文件的正则捕获 |
| `success` / `fail` | `status` · `body_regex` · `url_regex` |
| 模板变量 | `<USER>` `<PASS>` `<LINE>` `<COOKIE>` 可用于 url、headers、body **和** 正则 |

**`fail` 始终优先于 `success`** —— 若最终 URL 匹配登录/错误页面，结果为 `invalid`，
无论其他条件是否匹配。

---

## CLI

```bash
# HTTP 配置
python cli.py --config configs/example_http.json --inputs users.txt \
  --proxies proxies.txt --workers 8 --timeout 30 \
  --hits hits.txt --all all.txt

# 使用内置平台做浏览器 Cookie 检测
python cli.py --config configs/platforms/github.json --inputs cookies/ \
  --workers 4 --headful
```

---

## REST API

| 方法 | 路径 | Body |
|--------|------|------|
| `POST` | `/api/inputs` | `{"text":"a\nb"}` 或 `{"lines":[...]}` |
| `POST` | `/api/config` | `{"raw":"<json>"}` 或配置对象 |
| `POST` | `/api/proxies` | `{"text":"host:port\n..."}` |
| `POST` | `/api/start` | `{"workers":4,"timeout":30,"retry":1,"headless":true}` |
| `POST` | `/api/stop` · `/api/pause` · `/api/resume` | — |
| `GET` | `/api/stats` | 统计 + 日志 |
| `GET` | `/api/hits` · `/api/all` | 结果（文本） |
| `WS` | `ws://host:8081/` | 每 0.5 秒推送统计 + 日志 |

设置 `OXC_TOKEN` 可要求每个 `POST` 都带 `X-Auth-Token` 头。

---

## 项目结构

完整带注释的图见 **[STRUCTURE.md](../STRUCTURE.md)**。

```
0x-cookies/
├── server.py          控制面板（HTTP + 实时统计 WebSocket）
├── cli.py             headless 运行器
├── start.sh           一键启动（安装浏览器 + 系统库）
├── gen_configs.py     生成 139 个平台配置
├── core/              config · engine · proxies
├── web/               仪表盘 UI
├── configs/           示例 + 各平台配置
├── docs/              5 种语言的 README
└── assets/            标志 + 横幅
```

---

## 无 root 的 VPS（手动安装 Chromium 库）

如果 `apt` 不可用，且 Chromium 报错
`error while loading shared libraries: libglib-2.0.so.0`：

```bash
mkdir -p third_party/lib
cp /path/to/*.so* third_party/lib/   # 收集缺失的 .so 文件
./start.sh                            # start.sh 会把 third_party/lib 加入 LD_LIBRARY_PATH
```

---

## 贡献

欢迎提交 Issue 和 PR —— 尤其是新的平台配置。参见
[CONTRIBUTING.md](../CONTRIBUTING.md)。

## 许可证

[MIT](../LICENSE) © 0x Cookies

## ⚠️ 免责声明

本工具仅供 **合法的安全研究，以及测试你自己拥有或已获明确授权的账号**。
你需对自己的使用方式负全部责任。切勿在未经许可的情况下用于任何系统或账号。

---

<div align="center">

由 **0x Cookies** 制作 · [GitHub @0xgetz](https://github.com/0xgetz) · [Telegram @xiyyyyz](https://t.me/xiyyyyz)

</div>
