# Ivan_happyWoods 项目文档

## 📚 文档索引

### 🚀 实现文档
- [Phase 2A Implementation](./phase2a-implementation.md) - Phase 2A 实现文档
- [Phase 2C Implementation](./phase2c-implementation.md) - Phase 2C 实现文档
- [Phase 2D Implementation](./phase2d-implementation.md) - Phase 2D 实现文档

### 📖 使用指南
- [测试文件使用说明](../TESTS_README.md) - 如何使用项目中的测试文件
- [测试清理报告](../TEST_CLEANUP_REPORT.md) - 测试文件清理过程记录

### 🎤 语音服务文档
语音识别（STT）和语音合成（TTS）服务的实现已经完成，相关技术细节可以查看：
- `src/services/voice/stt_simple.py` - STT服务实现
- `src/api/voice_routes.py` - 语音服务HTTP API
- `demo/stt/` - STT示例代码
- `demo/tts/` - TTS示例代码

#### STT服务要点
- **API版本**: iFlytek V1 (多语言端点)
- **URL**: wss://iat.cn-huabei-1.xf-yun.com/v1
- **配置**: domain="iat", language="mul_cn"
- **音频格式**: PCM 16kHz 16-bit mono
- **测试结果**: ✅ 成功识别真实语音

#### API端点
```
POST /api/v1/voice/stt/recognize
GET  /api/v1/voice/status
POST /api/v1/voice/tts/synthesize (待实现)
```

### 🗂️ 归档文档
历史开发过程中的配置和修复文档，供参考查阅：
- [归档文档说明](./archive/README.md)

---

## 🔧 快速开始

### 启动API服务器
```bash
python start_api.py
```

### 运行测试
```bash
# 测试STT服务（直接调用）
python test_stt_simple.py

# 测试STT HTTP API
python test_stt_api.py

# 测试API集成
python test_api_integration.py

# 通用API测试
python test_api.py
```

### 环境配置
确保 `.env` 文件中配置了以下变量：
```env
IFLYTEK_APPID=your_app_id
IFLYTEK_APIKEY=your_api_key
IFLYTEK_APISECRET=your_api_secret
OPENAI_API_KEY=your_openai_key
```

---

## 📝 项目结构

```
Ivan_happyWoods/
├── src/                          # 源代码
│   ├── api/                     # API路由
│   │   ├── main.py             # FastAPI主应用
│   │   ├── routes.py           # 通用路由
│   │   └── voice_routes.py     # 语音服务路由
│   ├── services/                # 服务层
│   │   └── voice/              # 语音服务
│   │       ├── stt_simple.py   # STT服务
│   │       ├── iflytek_auth.py # iFlytek认证
│   │       └── tts.py          # TTS服务(待实现)
│   ├── agent/                   # Agent逻辑
│   └── config/                  # 配置管理
│
├── tests/                       # 测试目录(待创建)
├── demo/                        # 示例代码
│   ├── stt/                    # STT示例
│   └── tts/                    # TTS示例
│
├── docs/                        # 文档
│   ├── README.md               # 本文件
│   ├── archive/                # 归档文档
│   └── phase*.md               # 阶段实现文档
│
├── specs/                       # 需求规格
│
├── start_api.py                # API启动脚本
├── test_*.py                   # 测试脚本
├── TESTS_README.md             # 测试说明
├── TEST_CLEANUP_REPORT.md      # 清理报告
└── README.md                   # 项目主README
```

---

## 🎯 当前状态

### ✅ 已完成
- [x] Phase 2A: 基础Agent实现
- [x] Phase 2B: 语音服务配置
- [x] STT服务实现与测试
- [x] HTTP API集成
- [x] 项目文件清理

### 🚧 进行中
- [ ] TTS服务实现
- [ ] WebSocket音频流支持
- [ ] Session上下文集成
- [ ] 单元测试（目标80%覆盖率）

### 📋 待办
- [ ] Phase 2D完整实现
- [ ] 性能优化
- [ ] 生产环境部署

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可

[添加许可信息]
