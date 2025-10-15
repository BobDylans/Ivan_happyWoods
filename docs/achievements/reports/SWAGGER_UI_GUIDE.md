# Swagger UI 使用指南

## 🔐 如何在 Swagger UI 中添加 API Key

### 步骤 1: 打开 Swagger UI
访问: http://127.0.0.1:8000/docs

### 步骤 2: 点击右上角的 "Authorize" 按钮
在页面右上角，你会看到一个 **🔓 Authorize** 按钮。

### 步骤 3: 输入 API Key
1. 点击 **Authorize** 按钮
2. 在弹出的对话框中，找到 **ApiKeyAuth (apiKey)** 部分
3. 在 **Value** 输入框中输入: `dev-test-key-123`
4. 点击 **Authorize** 按钮
5. 点击 **Close** 关闭对话框

### 步骤 4: 测试 API
现在你可以测试任何 API 接口了，API Key 会自动添加到请求头中。

---

## 🧪 测试 TTS 接口

### 1. 展开 `/api/v1/voice/tts/synthesize` 接口

### 2. 点击 "Try it out" 按钮

### 3. 修改请求体
```json
{
  "text": "你好，世界！这是一段测试语音。",
  "voice": "x4_lingxiaoxuan_oral",
  "speed": 50,
  "volume": 60,
  "pitch": 50,
  "format": "mp3"
}
```

### 4. 点击 "Execute" 按钮

### 5. 查看响应
- **成功**: 会显示音频文件下载链接（MP3）
- **失败**: 会显示 JSON 错误信息

---

## 📝 可用的 API Keys

开发环境中配置的 API Keys（在 `.env` 文件中）:
- `dev-test-key-123`
- `prod-key-456`

---

## 🚀 快速测试（命令行方式）

如果不想使用 Swagger UI，可以直接用命令行测试：

### PowerShell:
```powershell
# 测试 TTS 合成
curl -X POST "http://127.0.0.1:8000/api/v1/voice/tts/synthesize" `
     -H "Content-Type: application/json" `
     -H "X-API-Key: dev-test-key-123" `
     -d '{\"text\": \"你好，世界！\"}' `
     --output test.mp3

# 检查服务状态
curl -X GET "http://127.0.0.1:8000/api/v1/voice/status" `
     -H "X-API-Key: dev-test-key-123"
```

### Python 测试脚本:
```powershell
# 简单测试
python test_tts_simple.py

# 完整测试套件
python test_tts_api.py
```

---

## ⚠️ 常见问题

### Q: 为什么显示 "401 Unauthorized"?
**A**: 没有添加 API Key。请按照上面的步骤在 Swagger UI 中点击 Authorize 按钮添加 API Key。

### Q: 为什么显示 "403 Forbidden"?
**A**: API Key 无效。请确保使用正确的 API Key（如 `dev-test-key-123`）。

### Q: 如何禁用 API Key 认证（仅开发环境）?
**A**: 在 `.env` 文件中设置:
```bash
API_KEY_ENABLED=false
```
然后重启服务。

---

## 📚 更多文档

- **TTS 实现报告**: `TTS_IMPLEMENTATION_REPORT.md`
- **快速开始**: `QUICKSTART.md`
- **API 文档**: http://127.0.0.1:8000/docs
