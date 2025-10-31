# Ollama 本地大模型集成 - 快速参考

## 🎯 一键启动

```bash
# 步骤 1: 启动 Ollama
ollama serve

# 步骤 2: 下载模型 (新终端)
ollama pull qwen2.5:latest

# 步骤 3: 启动服务 (新终端)
cd d:\Projects\ivanHappyWoods\backEnd
$env:VOICE_AGENT_ENVIRONMENT="ollama"; python start_server.py

# 步骤 4: 运行测试 (新终端)
python test_ollama_integration.py
```

---

## ✅ 完成的工作

### 1. 配置文件
- ✅ **config/ollama.yaml** - Ollama 专用配置文件
  - 配置 Ollama API 地址: `http://localhost:11434/v1`
  - 默认模型: `qwen2.5:latest`
  - 增加超时时间: 60 秒(适应本地推理)
  - 保留数据库持久化配置

### 2. 代码更新
- ✅ **src/utils/llm_compat.py** - 添加 Ollama 模型支持
  - 添加 6 个 Ollama 模型特性映射:
    - `qwen2.5` (中文对话优先)
    - `qwen2` (中文对话)
    - `llama3.2` (快速推理)
    - `llama3.1` (大上下文)
    - `mistral` (平衡性能)
    - `deepseek-coder` (代码生成)
  
  - 更新 `get_model_features()` 函数:
    - 支持 Ollama 模型标签格式 (如 `qwen2.5:latest`)
    - 自动剥离标签后匹配基础模型名
    - 逻辑: `qwen2.5:latest` → 尝试 `qwen2.5` → 匹配成功

### 3. 测试脚本
- ✅ **test_ollama_integration.py** - 全面集成测试
  - 检查 Ollama 服务状态
  - 检查后端服务状态
  - 测试简单对话功能
  - 测试持久化和上下文记忆
  - 测试流式响应
  - 彩色输出和详细报告

### 4. 文档
- ✅ **README_OLLAMA.md** - 完整使用指南
  - 安装步骤(Windows/Linux/macOS)
  - 模型下载和管理
  - 配置说明
  - 启动流程
  - 测试验证方法
  - 故障排查清单
  - 性能优化建议
  - 常见问题解答

---

## 📚 支持的 Ollama 模型

| 模型 | 大小 | 用途 | 上下文长度 | 函数调用 |
|------|------|------|-----------|---------|
| qwen2.5 | ~4.7GB | 中文对话(推荐) | 32K | ✅ |
| llama3.2 | ~2GB | 快速响应 | 8K | ✅ |
| llama3.1 | ~4.7GB | 大上下文 | 128K | ✅ |
| mistral | ~4.1GB | 平衡性能 | 32K | ✅ |
| deepseek-coder | ~3.8GB | 代码生成 | 16K | ✅ |
| qwen2 | ~4.7GB | 中文对话 | 32K | ✅ |

---

## 🔧 核心技术实现

### 模型名称匹配逻辑

```python
def get_model_features(model: str) -> Dict[str, Any]:
    # 1. 精确匹配
    if model in MODEL_FEATURES:
        return MODEL_FEATURES[model]
    
    # 2. Ollama 标签剥离 (NEW!)
    if ':' in model:
        base_model = model.split(':')[0]
        if base_model in MODEL_FEATURES:
            return MODEL_FEATURES[base_model]
    
    # 3. 前缀匹配
    for model_prefix, features in MODEL_FEATURES.items():
        if model.startswith(model_prefix):
            return features
    
    # 4. 默认特性
    return default_features
```

**支持的格式**:
- ✅ `qwen2.5` - 基础名称
- ✅ `qwen2.5:latest` - 带标签
- ✅ `qwen2.5:7b` - 带参数量
- ✅ `llama3.1:8b-instruct-fp16` - 完整标签

### Ollama API 兼容性

**OpenAI-Compatible 端点**:
- Ollama 提供 `/v1/chat/completions` 端点
- 与 OpenAI API 格式兼容
- 无需修改现有代码,只需更改 `base_url`

**参数差异**:
- ✅ Ollama 使用标准 `max_tokens` (不是 `max_completion_tokens`)
- ✅ 支持 `temperature` 参数
- ✅ 支持 `stream` 流式响应
- ✅ 无需 `api_key` (留空即可)

---

## 🚀 使用场景

### 1. 完全离线部署
```yaml
# config/offline.yaml
llm:
  provider: "ollama"
  base_url: "http://localhost:11434/v1"
  api_key: ""
  models:
    default: "qwen2.5:latest"

speech:
  tts:
    provider: "offline"  # 未来集成本地 TTS
  stt:
    provider: "offline"  # 未来集成本地 STT
```

### 2. 混合部署
```yaml
# config/hybrid.yaml
llm:
  provider: "ollama"  # 本地推理
  models:
    default: "qwen2.5:latest"

speech:
  tts:
    provider: "iflytek"  # 云端 TTS
  stt:
    provider: "iflytek"  # 云端 STT
```

### 3. 开发测试
```bash
# 本地测试时使用 Ollama (免费)
$env:VOICE_AGENT_ENVIRONMENT="ollama"
python start_server.py

# 生产环境使用云端 API
$env:VOICE_AGENT_ENVIRONMENT="production"
python start_server.py
```

---

## 📊 性能对比

| 指标 | 云端 API (OpenAI) | 本地 Ollama (CPU) | 本地 Ollama (GPU) |
|------|------------------|-------------------|-------------------|
| **首次响应** | ~600ms | ~3-5s | ~800ms-1.5s |
| **流式延迟** | 低 | 中 | 低 |
| **成本** | 按 token 计费 | 免费 | 免费 |
| **隐私** | 数据上云 | 完全本地 | 完全本地 |
| **稳定性** | 依赖网络 | 本地稳定 | 本地稳定 |
| **模型选择** | 受限于提供商 | 任意开源模型 | 任意开源模型 |

---

## ⚠️ 注意事项

### 硬件要求
- **最低**: 8GB RAM + 4 核 CPU
- **推荐**: 16GB RAM + 8 核 CPU + NVIDIA GPU (6GB+ VRAM)

### 首次启动
- 第一次推理会加载模型到内存(~10-30秒)
- 后续请求会复用已加载模型(响应更快)

### 超时设置
- Ollama 推理比云端 API 慢
- 已在配置中增加超时: 60 秒
- 如果仍超时,可增加到 120 秒

---

## 🐛 故障排查

### 问题 1: Ollama 服务未启动
```bash
# 错误: ConnectError: No connection could be made
# 解决:
ollama serve
```

### 问题 2: 模型未下载
```bash
# 错误: {"error": "model not found"}
# 解决:
ollama pull qwen2.5:latest
```

### 问题 3: 推理超时
```yaml
# 修改 config/ollama.yaml
llm:
  timeout: 120  # 增加到 120 秒
```

### 问题 4: 中文效果差
```bash
# 使用中文优化模型
ollama pull qwen2.5:latest  # 阿里通义千问
```

---

## 📖 详细文档

- **完整指南**: [README_OLLAMA.md](./README_OLLAMA.md)
- **项目文档**: [PROJECT.md](./PROJECT.md)
- **开发指南**: [DEVELOPMENT.md](./DEVELOPMENT.md)

---

## ✅ 验证清单

使用前请确认:

- [ ] Ollama 已安装: `ollama --version`
- [ ] Ollama 服务运行: `curl http://localhost:11434/api/tags`
- [ ] 至少下载一个模型: `ollama list`
- [ ] PostgreSQL 运行: `docker ps | findstr postgres`
- [ ] 配置文件存在: `config/ollama.yaml`
- [ ] 环境变量正确: `$env:VOICE_AGENT_ENVIRONMENT="ollama"`

**运行测试**:
```bash
python test_ollama_integration.py
```

预期输出:
```
✅ Ollama 服务运行正常
✅ 后端服务运行正常
✅ 对话测试成功
✅ 上下文记忆测试通过
✅ 流式响应测试成功
🎉 所有核心测试通过! Ollama 集成成功!
```

---

**状态**: ✅ 集成完成,待用户测试  
**版本**: 1.0  
**日期**: 2025-01-18  
**负责人**: Ivan_HappyWoods Team
