# 部署说明

## 本地运行

- 安装 Python 3.8+，按 README 安装依赖
- 配置 `.env`
- 启动：`uvicorn wxbot.main:app --host 0.0.0.0 --port 8000`

## Docker 一键启动

```bash
docker compose up --build
```

数据目录以 volume 方式挂载：`./data`、`./secrets`、`./backups`。

## WeFlow 对接

本项目支持两种接入方式：

1) **推荐：直接订阅 WeFlow SSE 推送**（延迟低、无需额外转发）

- 在 WeFlow 设置页开启 `HTTP API 服务` 与 `主动推送`
- 在本项目 `.env` 配置：
  - `WEFLOW_BASE_URL=http://127.0.0.1:5031`
  - `WEFLOW_TOKEN=...`
  - `WEFLOW_SSE_PATH=/api/v1/push/messages`

启动本项目后会自动连接 `GET /api/v1/push/messages?access_token=...` 并消费 `message.new` 事件。

本地只缓存最近 `WXBOT_CACHE_MAX_MESSAGES` 条事件；SSE 去重/游标会写入联系人目录下的 `state.json(.enc)`。

2) **可选：Webhook 转发到本服务**

本项目提供接收入口：`POST /weflow/webhook`。你需要在中转层把新消息转发到该地址，并保证请求体至少包含：

```json
{
  "contact_id": "wxid_xxx",
  "content": "你好",
  "timestamp": 1715773894,
  "platform_message_id": "7291245..."
}
```

备注：WeFlow 当前公开的 HTTP API 文档主要覆盖“读取聊天记录/会话/联系人/媒体”和 SSE 推送，新消息“发送到微信”的接口不在该文档范围内，因此 `WEFLOW_SEND_PATH` 需要你根据实际可用能力另行配置。
