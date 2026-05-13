# WeFlow 本地微信智能回复系统（wxbot）

本项目在本地启动一个服务端，接收 WeFlow 转发的微信消息，做本地加密存储，并通过本地 LLM 生成候选回复与角色化风格。

## 前置依赖：WeFlow

**WeFlow** 是一个微信消息转发服务，负责接收微信消息并通过 SSE 实时推送给本项目的后端。**你需要先部署 WeFlow 才能接收微信消息。**

- WeFlow 仓库：[https://github.com/hicccc77/WeFlow](https://github.com/hicccc77/WeFlow)
- 请按照 WeFlow 仓库的说明完成安装和配置，确保 WeFlow 服务正常运行。
- WeFlow 默认监听 `http://127.0.0.1:5031`，本项目通过 `WEFLOW_*` 环境变量与其对接。

如果暂时没有 WeFlow，本项目仍可独立启动：后端和前端聊天工作台可以正常运行，只是不会收到新消息。

## 快速开始

### 1) 安装依赖

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2) 配置

复制环境变量示例：

```bash
copy .env.example .env
```

最小可用配置：

- `WXBOT_LLM_PROVIDER=ollama`
- `WXBOT_OLLAMA_BASE_URL=http://localhost:11434`
- `WXBOT_OLLAMA_MODEL=llama3`

使用第三方 / 自建 OpenAI 兼容接口：

- `WXBOT_LLM_PROVIDER=openai_compat`
- `WXBOT_LLM_BASE_URL=...`（例如 `https://api.openai.com/v1` 或你的网关地址）
- `WXBOT_LLM_API_KEY=...`
- `WXBOT_LLM_MODEL=...`

WeFlow 对接需要你填入实际的 API 地址与鉴权信息（不同部署可能不同）：

- `WEFLOW_BASE_URL=http://127.0.0.1:5031`
- `WEFLOW_TOKEN=...`
- `WEFLOW_SSE_PATH=/api/v1/push/messages`
- `WEFLOW_MESSAGES_PATH=/api/v1/messages`

### 3) 运行

```bash
uvicorn wxbot.main:app --host 0.0.0.0 --port 8000
```

一键启动（同时启动后端 + 前端）：

```bash
python dev_up.py --backend-reload
```

不打开命令行、直接双击启动（Windows）：

- 双击根目录的 `start_chat.cmd`
- 停止时双击 `stop_chat.cmd`（或在启动窗口按 Ctrl+C）

如果你正在接收 WeFlow 实时消息，建议不要开启后端热重载（写入 `data/` 会触发重载导致页面频繁离线）：

```bash
python dev_up.py
```

前端网址：

- `http://localhost:5173/`
- `http://127.0.0.1:5173/`

健康检查：`GET http://localhost:8000/health`

## 数据与安全

- 每个联系人独立文件：`data/contacts/<contact_id>/events.jsonl`（明文）或 `events.jsonl.enc`（加密）。
- 本地只缓存最近 `WXBOT_CACHE_MAX_MESSAGES` 条事件（写入后自动裁剪）。
- 去重/游标保存在 `data/contacts/<contact_id>/state.json`（或 `state.json.enc`）。
- 主密钥默认保存在 `secrets/master.key`；也可用环境变量 `WXBOT_MASTER_KEY` 注入。
- `WXBOT_STORAGE_ENCRYPTION=on/off` 控制是否加密（测试时可关闭）。
- 备份默认只打包加密后的 `data/`，不包含密钥。

## Docker

见 `docker-compose.yml` 与 `docs/deploy.md`。
