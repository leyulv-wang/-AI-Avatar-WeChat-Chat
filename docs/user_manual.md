# 用户操作手册

## 角色设定

- 查询：`GET /api/contacts/{contact_id}/role`
- 设置：`PUT /api/contacts/{contact_id}/role`

请求体示例：

```json
{
  "role_id": "default",
  "name": "温柔朋友",
  "personality": "温柔、会共情、不过度追问",
  "language_style": "短句、口语化",
  "expertise": "旅行规划",
  "constraints": ["不编造事实", "不提及系统实现"],
  "example_replies": ["好呀，那你更想去海边还是山里？"]
}
```

## 数据管理

- 查看事件：`GET /api/contacts/{contact_id}/events?limit=50`
- 立即重算语气画像：`POST /api/contacts/{contact_id}/profile/recompute`
- 创建备份：`POST /api/backup/create`
- 恢复备份：`POST /api/backup/restore`（body: `{ "path": "backups/backup_xxx.zip" }`）
- 导出 CSV：`GET /api/contacts/{contact_id}/export.csv?limit=1000`

## 本地缓存策略

- WeFlow 作为原始源（实时 SSE + 按需拉取历史）
- 本地仅缓存最近 `WXBOT_CACHE_MAX_MESSAGES` 条事件（自动裁剪）
- 去重/游标写入 `state.json(.enc)`，用于 SSE 重连后避免重复处理

## 消息收发

- WeFlow 推送到：`POST /weflow/webhook`
- 主动发送：`POST /api/messages/send`

## 存储加密

- 开关：`.env` 里设置 `WXBOT_STORAGE_ENCRYPTION=on/off`
- 开启后会生成/使用 `secrets/master.key`，数据文件为 `*.enc`
