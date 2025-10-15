# Voice Agent TTS 服务 - 快速参考

## 🚀 快速启动

### 1. 启动服务器

```bash
python start_server.py
```

服务器将运行在: http://127.0.0.1:8000

### 2. 访问 API 文档

```
http://127.0.0.1:8000/docs
```

---

## 🧪 测试

### 推荐测试脚本

```bash
python test_stream_simple.py
```

**功能**：
- ✅ 对比普通 TTS vs 流式 TTS
- ✅ 实时显示音频块接收过程
- ✅ 性能分析（首字节时间对比）
- ✅ 自动生成测试音频文件

---

## 📚 文档

### 核心文档（按推荐阅读顺序）

1. **TTS_FIXED_REPORT.md** - 问题诊断与解决报告
   - 发音人参数问题的完整解决过程
   - 可用发音人列表
   - 快速验证步骤

2. **TTS_STREAM_GUIDE.md** - 流式 TTS 完整指南
   - 什么是流式 TTS
   - 使用方法（Python, JavaScript, curl）
   - 性能对比
   - 最佳实践

3. **HOW_TO_VERIFY_STREAMING.md** - 如何验证流式效果
   - 为什么 Swagger UI 看不出流式
   - 多种验证方法
   - 实时效果展示

---

## 🎯 API 接口

### 普通 TTS（适合短文本）

```
POST /api/v1/voice/tts/synthesize
```

**测试 JSON**：
```json
{
  "text": "你好，世界！",
  "voice": "x5_lingxiaoxuan_flow",
  "speed": 50
}
```

### 流式 TTS（适合长文本）

```
POST /api/v1/voice/tts/synthesize-stream
```

**测试 JSON**：
```json
{
  "text": "这是一段较长的文本，流式模式会实时传输音频数据...",
  "voice": "x5_lingxiaoxuan_flow",
  "speed": 50
}
```

---

## 🎨 可用发音人

| 发音人代码 | 名称 | 性别 |
|-----------|------|------|
| `x5_lingxiaoxuan_flow` | 聆小璇 | 女声 ⭐ 默认 |
| `x5_lingfeiyi_flow` | 聆飞逸 | 男声 |
| `x5_lingxiaoyue_flow` | 聆小玥 | 女声 |
| `x5_lingyuzhao_flow` | 聆玉昭 | 女声 |
| `x5_lingyuyan_flow` | 聆玉言 | 女声 |

---

## 📊 性能对比

### 测试结果（200字文本）

| 指标 | 普通模式 | 流式模式 | 提升 |
|------|---------|---------|------|
| 首字节时间 | ~6秒 | ~3秒 | **50%** ⚡ |
| 用户体验 | 等待慢 | 响应快 | 显著提升 |

**关键理解**：
- 流式模式的优势在于**首字节响应时间**
- 用户感知：流式模式快 **45-55%**

---

## 🔧 常见问题

### Q: 如何更改默认发音人？

修改 `.env` 文件：
```bash
VOICE_AGENT_SPEECH__TTS__VOICE=x5_lingfeiyi_flow  # 改为男声
```

### Q: 如何在 API 请求中指定发音人？

```json
{
  "text": "测试",
  "voice": "x5_lingfeiyi_flow"  # 指定发音人
}
```

### Q: 流式模式支持的最大文本长度？

- 普通模式：5,000 字符
- 流式模式：10,000 字符

### Q: 如何验证流式效果？

运行测试脚本查看实时传输：
```bash
python test_stream_simple.py
```

---

## 📁 项目结构

```
Ivan_happyWoods/
├── src/                          # 源代码
│   ├── api/                      # API 路由
│   │   └── voice_routes.py       # TTS/STT 接口
│   ├── services/                 # 服务层
│   │   └── voice/
│   │       ├── tts_simple.py     # 普通 TTS
│   │       ├── tts_streaming.py  # 流式 TTS
│   │       └── stt_simple.py     # STT 服务
│   └── config/                   # 配置
├── start_server.py               # 服务器启动脚本
├── test_stream_simple.py         # 流式 TTS 测试脚本 ⭐
├── requirements.txt              # 依赖列表
├── .env                          # 环境变量配置
└── docs/                         # 文档目录
    ├── TTS_FIXED_REPORT.md       # 问题修复报告
    ├── TTS_STREAM_GUIDE.md       # 流式使用指南
    └── HOW_TO_VERIFY_STREAMING.md # 验证方法
```

---

## ⚙️ 环境变量配置

关键配置项（`.env` 文件）：

```bash
# iFlytek 凭证
IFLYTEK_APPID=c3f1e28b
IFLYTEK_APIKEY=your_api_key
IFLYTEK_APISECRET=your_api_secret

# TTS 配置
VOICE_AGENT_SPEECH__TTS__VOICE=x5_lingxiaoxuan_flow
VOICE_AGENT_SPEECH__TTS__SPEED=50
VOICE_AGENT_SPEECH__TTS__VOLUME=60

# API 配置
VOICE_AGENT_API__PORT=8000
API_KEYS=dev-test-key-123
```

---

## 🎯 下一步

1. ✅ 启动服务器：`python start_server.py`
2. ✅ 访问 API 文档：http://127.0.0.1:8000/docs
3. ✅ 运行测试：`python test_stream_simple.py`
4. ✅ 在 Swagger UI 中测试接口
5. ✅ 查看文档了解更多

---

**版本**: 1.0  
**更新时间**: 2025-10-15  
**状态**: ✅ 生产就绪
