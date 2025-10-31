# Ollama 本地大模型集成指南

## 📋 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [安装 Ollama](#安装-ollama)
- [下载模型](#下载模型)
- [配置系统](#配置系统)
- [启动服务](#启动服务)
- [测试验证](#测试验证)
- [支持的模型](#支持的模型)
- [常见问题](#常见问题)
- [性能优化](#性能优化)

---

## 概述

本系统现已支持使用 **Ollama** 在本地运行大语言模型,实现完全离线、隐私保护的 AI 对话功能。

### ✨ Ollama 集成优势

- 🔒 **完全离线**: 无需互联网连接,数据完全本地化
- 💰 **零成本**: 无 API 调用费用,无使用限制
- 🚀 **低延迟**: 本地推理,响应速度快
- 🔐 **隐私保护**: 敏感数据不离开本地服务器
- 🎯 **可定制**: 支持加载自定义微调模型

### 🎯 适用场景

- 企业内网部署(数据安全要求高)
- 开发测试环境(降低成本)
- 离线环境使用
- 私密对话场景
- 自定义模型训练与部署

---

## 快速开始

**5 分钟快速体验 Ollama 集成**:

```bash
# 1. 安装 Ollama (Windows)
# 访问 https://ollama.com/download/windows 下载安装包

# 2. 下载模型
ollama pull qwen2.5:latest

# 3. 启动 Ollama 服务
ollama serve

# 4. 启动语音代理系统 (新终端)
cd d:\Projects\ivanHappyWoods\backEnd
$env:VOICE_AGENT_ENVIRONMENT="ollama"; python start_server.py

# 5. 测试
python test_persistence_simple.py
```

---

## 安装 Ollama

### Windows 系统

1. **下载安装包**:
   - 访问 [Ollama 官网](https://ollama.com/download/windows)
   - 下载 Windows 安装程序
   - 双击运行安装

2. **验证安装**:
   ```powershell
   ollama --version
   # 输出示例: ollama version 0.1.25
   ```

3. **环境变量** (通常自动配置):
   - `OLLAMA_HOST=127.0.0.1:11434`
   - `PATH` 中包含 Ollama 可执行文件路径

### Linux / macOS

```bash
# 一键安装
curl -fsSL https://ollama.com/install.sh | sh

# 验证
ollama --version
```

### Docker 部署 (可选)

```bash
docker pull ollama/ollama
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

---

## 下载模型

### 推荐模型列表

| 模型名称 | 大小 | 用途 | 下载命令 |
|---------|------|------|----------|
| **qwen2.5:latest** | ~4.7GB | 中文对话(推荐) | `ollama pull qwen2.5:latest` |
| **llama3.2:latest** | ~2GB | 快速响应 | `ollama pull llama3.2:latest` |
| **llama3.1:8b** | ~4.7GB | 英文对话 | `ollama pull llama3.1:8b` |
| **mistral:latest** | ~4.1GB | 平衡性能 | `ollama pull mistral:latest` |
| **deepseek-coder:latest** | ~3.8GB | 代码生成 | `ollama pull deepseek-coder:latest` |

### 下载步骤

```bash
# 1. 查看可用模型
ollama list

# 2. 搜索模型 (浏览器访问)
# https://ollama.com/library

# 3. 下载模型
ollama pull qwen2.5:latest

# 4. 验证下载
ollama list
# 输出:
# NAME                 ID              SIZE      MODIFIED
# qwen2.5:latest       abc123def456    4.7 GB    2 minutes ago

# 5. 测试模型
ollama run qwen2.5:latest
# 输入: 你好
# 输出: 你好!我是 Qwen,很高兴为你服务...
# (输入 /bye 退出)
```

### 模型选择建议

- **中文对话优先**: qwen2.5 (阿里通义千问)
- **速度优先**: llama3.2 (较小模型)
- **英文对话**: llama3.1 (Meta 官方)
- **代码任务**: deepseek-coder (深度求索)
- **平衡选择**: mistral (Mistral AI)

---

## 配置系统

### 方式 1: 使用预配置文件 (推荐)

项目已包含 `config/ollama.yaml` 配置文件:

```yaml
llm:
  provider: "ollama"
  base_url: "http://localhost:11434/v1"  # Ollama API 地址
  api_key: ""  # Ollama 无需 API Key
  timeout: 60  # 本地推理可能较慢,增加超时
  
  models:
    default: "qwen2.5:latest"    # 默认模型
    fast: "llama3.2:latest"       # 快速模型
    creative: "qwen2.5:latest"    # 创意模型

  max_tokens: 4096
  temperature: 0.7
  stream: true
```

**使用方法**:
```bash
# 设置环境变量指向 Ollama 配置
$env:VOICE_AGENT_ENVIRONMENT="ollama"
python start_server.py
```

### 方式 2: 环境变量覆盖

```bash
# 设置 Ollama 相关环境变量
$env:VOICE_AGENT_LLM__PROVIDER="ollama"
$env:VOICE_AGENT_LLM__BASE_URL="http://localhost:11434/v1"
$env:VOICE_AGENT_LLM__API_KEY=""
$env:VOICE_AGENT_LLM__MODELS__DEFAULT="qwen2.5:latest"
$env:VOICE_AGENT_LLM__TIMEOUT="60"

# 启动服务
python start_server.py
```

### 配置项说明

| 配置项 | 说明 | Ollama 值 |
|-------|------|-----------|
| `provider` | 提供商名称 | `"ollama"` |
| `base_url` | API 基础地址 | `"http://localhost:11434/v1"` |
| `api_key` | API 密钥 | `""` (留空) |
| `timeout` | 超时时间(秒) | `60` (本地推理较慢) |
| `models.default` | 默认模型 | `"qwen2.5:latest"` |
| `max_tokens` | 最大生成长度 | `4096` |

---

## 启动服务

### 步骤 1: 启动 Ollama 服务

```bash
# 新终端 1: 启动 Ollama
ollama serve

# 输出:
# Ollama is running on http://localhost:11434
```

**验证 Ollama 运行**:
```bash
# 新终端测试
curl http://localhost:11434/api/tags

# 或访问浏览器
# http://localhost:11434
```

### 步骤 2: 启动语音代理系统

```bash
# 新终端 2: 启动后端服务
cd d:\Projects\ivanHappyWoods\backEnd

# 使用 Ollama 配置启动
$env:VOICE_AGENT_ENVIRONMENT="ollama"; python start_server.py

# 看到以下日志表示成功:
# ✅ 使用 PostgreSQL 数据库持久化
# ✅ LLM Provider: ollama
# ✅ LLM Base URL: http://localhost:11434/v1
# ✅ Default Model: qwen2.5:latest
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 步骤 3: 验证系统状态

```bash
# 新终端 3: 健康检查
curl http://localhost:8000/health

# 预期输出:
# {
#   "status": "healthy",
#   "database": "connected",
#   "llm_provider": "ollama"
# }
```

---

## 测试验证

### 测试脚本 1: 简单对话

创建 `test_ollama_basic.py`:

```python
import asyncio
import httpx

async def test_ollama_chat():
    """测试 Ollama 基础对话"""
    url = "http://localhost:8000/api/conversation/send"
    
    payload = {
        "session_id": "ollama_test_001",
        "message": "你好,请用一句话介绍你自己",
        "stream": False
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

asyncio.run(test_ollama_chat())
```

**运行测试**:
```bash
python test_ollama_basic.py

# 预期输出:
# Status: 200
# Response: {
#   "session_id": "ollama_test_001",
#   "message": "你好!我是 Qwen,一个由阿里云开发的大型语言模型...",
#   "model_used": "qwen2.5:latest"
# }
```

### 测试脚本 2: 持久化验证

使用现有的 `test_persistence_simple.py`,修改为 Ollama 配置:

```python
# 在脚本开头添加
import os
os.environ['VOICE_AGENT_ENVIRONMENT'] = 'ollama'

# 然后运行
python test_persistence_simple.py
```

**预期结果**:
- ✅ 发送初始消息成功
- ✅ 数据库保存 checkpoint
- ✅ 重启服务后能够恢复上下文

### 测试脚本 3: 流式响应

```python
import asyncio
import httpx

async def test_ollama_streaming():
    """测试 Ollama 流式响应"""
    url = "http://localhost:8000/api/conversation/stream"
    
    params = {
        "session_id": "ollama_stream_001",
        "message": "列举3个 Python 的特点,每个用一句话说明"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("GET", url, params=params) as response:
            print("Streaming response:")
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    print(line[6:])  # 去掉 "data: " 前缀

asyncio.run(test_ollama_streaming())
```

---

## 支持的模型

### 已配置模型特性

系统已在 `src/utils/llm_compat.py` 中配置以下 Ollama 模型:

| 模型 | 上下文长度 | 参数格式 | 温度支持 | 函数调用 |
|------|-----------|---------|---------|---------|
| **qwen2.5** | 32K | max_tokens | ✅ | ✅ |
| **qwen2** | 32K | max_tokens | ✅ | ✅ |
| **llama3.2** | 8K | max_tokens | ✅ | ✅ |
| **llama3.1** | 128K | max_tokens | ✅ | ✅ |
| **mistral** | 32K | max_tokens | ✅ | ✅ |
| **deepseek-coder** | 16K | max_tokens | ✅ | ✅ |

### 添加新模型

如需添加其他 Ollama 模型:

1. **在 `src/utils/llm_compat.py` 中添加模型特性**:
   ```python
   "your-model-name": {
       "max_tokens_param": "max_tokens",
       "supports_temperature": True,
       "supports_vision": False,
       "supports_function_calling": True,
       "max_context": 8192,
       "provider": "ollama",
   },
   ```

2. **下载模型**:
   ```bash
   ollama pull your-model-name:latest
   ```

3. **更新配置文件** `config/ollama.yaml`:
   ```yaml
   llm:
     models:
       default: "your-model-name:latest"
   ```

### 模型标签支持

系统支持 Ollama 的模型标签格式:

- ✅ `qwen2.5:latest` - 使用最新版本
- ✅ `qwen2.5:7b` - 指定参数量版本
- ✅ `llama3.1:8b-instruct-fp16` - 完整标签

**自动匹配逻辑**:
- 精确匹配: `qwen2.5:latest` → 查找 `qwen2.5:latest`
- 标签剥离: `qwen2.5:latest` → 查找 `qwen2.5` → 匹配成功
- 前缀匹配: `qwen2.5-custom` → 查找 `qwen2.5` → 匹配成功

---

## 常见问题

### Q1: Ollama 服务未启动

**症状**: 
```
httpx.ConnectError: [Errno 10061] No connection could be made
```

**解决方案**:
```bash
# 确认 Ollama 正在运行
curl http://localhost:11434/api/tags

# 如果失败,启动 Ollama
ollama serve
```

### Q2: 模型未下载

**症状**:
```
{"error": "model not found"}
```

**解决方案**:
```bash
# 检查已下载模型
ollama list

# 下载缺失模型
ollama pull qwen2.5:latest
```

### Q3: 推理速度慢

**症状**: 响应时间 > 30 秒

**解决方案**:

1. **使用更小的模型**:
   ```bash
   ollama pull llama3.2:latest  # 2GB,速度更快
   ```

2. **减少生成长度**:
   ```yaml
   llm:
     max_tokens: 1024  # 从 4096 减少到 1024
   ```

3. **GPU 加速**:
   - Ollama 自动检测并使用 GPU
   - 确认 NVIDIA 驱动已安装
   - 查看 GPU 使用: `nvidia-smi`

### Q4: 端口冲突

**症状**:
```
Error: listen tcp 127.0.0.1:11434: bind: address already in use
```

**解决方案**:
```bash
# 查找占用端口的进程
netstat -ano | findstr :11434

# 杀掉进程 (替换 PID)
taskkill /PID <pid> /F

# 或更改 Ollama 端口
$env:OLLAMA_HOST="127.0.0.1:11435"
ollama serve
```

### Q5: 数据库连接失败

**症状**: 
```
Database connection failed: could not connect to server
```

**解决方案**:
```bash
# 确认 PostgreSQL 容器运行
docker ps | findstr voice_agent_postgres

# 如果未运行,启动容器
docker start voice_agent_postgres

# 或启动整个环境
docker-compose up -d
```

### Q6: 中文乱码

**症状**: Ollama 返回乱码或方块字符

**解决方案**:

1. **使用中文优化模型**:
   ```bash
   ollama pull qwen2.5:latest  # 阿里通义千问,中文效果好
   ```

2. **检查编码**:
   ```python
   # 在代码中确保 UTF-8 编码
   response = await client.post(url, json=payload, headers={"Content-Type": "application/json; charset=utf-8"})
   ```

---

## 性能优化

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| **CPU** | 4 核 | 8 核以上 |
| **内存** | 8GB | 16GB 以上 |
| **显卡** | 无 (CPU 推理) | NVIDIA RTX 3060 (6GB VRAM) 或更高 |
| **硬盘** | 20GB 可用空间 | SSD, 50GB 以上 |

### GPU 加速

**检查 GPU 支持**:
```bash
# Ollama 会自动检测 GPU
ollama serve

# 查看日志
# 如果有 GPU: "CUDA available, using GPU"
# 如果无 GPU: "CUDA not available, using CPU"
```

**强制使用 CPU** (调试用):
```bash
$env:CUDA_VISIBLE_DEVICES=""
ollama serve
```

### 模型量化

Ollama 支持量化模型以减少内存占用:

```bash
# 原始模型 (约 15GB)
ollama pull llama3.1:70b

# 4-bit 量化 (约 4GB)
ollama pull llama3.1:70b-q4_0

# 8-bit 量化 (约 8GB)
ollama pull llama3.1:70b-q8_0
```

### 并发优化

修改 `config/ollama.yaml`:

```yaml
api:
  workers: 2  # 减少并发数,避免 OOM
  
llm:
  timeout: 120  # 增加超时时间
  max_tokens: 2048  # 减少生成长度
```

### 缓存策略

Ollama 自动缓存模型到内存:

```bash
# 查看 Ollama 内存占用
ollama ps

# 清理缓存
ollama stop <model_name>
```

---

## 混合部署

### 场景: Ollama 对话 + 云端 TTS

使用 Ollama 进行对话,使用科大讯飞进行语音合成:

```yaml
# config/hybrid.yaml
llm:
  provider: "ollama"
  base_url: "http://localhost:11434/v1"
  models:
    default: "qwen2.5:latest"

speech:
  tts:
    provider: "iflytek"  # 使用云端 TTS
    appid: "${IFLYTEK_APPID}"
    apikey: "${IFLYTEK_APIKEY}"
```

**启动**:
```bash
$env:VOICE_AGENT_ENVIRONMENT="hybrid"; python start_server.py
```

---

## 监控与调试

### 查看 Ollama 日志

```bash
# Windows
Get-Content "$env:USERPROFILE\.ollama\logs\server.log" -Tail 50 -Wait

# Linux / macOS
tail -f ~/.ollama/logs/server.log
```

### 查看系统日志

```bash
# 后端日志
Get-Content logs\voice_agent.log -Tail 50 -Wait

# 数据库日志
docker logs -f voice_agent_postgres
```

### 性能监控

```python
# 添加到代码中
import time

start = time.time()
response = await llm_call()
elapsed = time.time() - start

print(f"LLM 推理耗时: {elapsed:.2f}秒")
```

---

## 故障排查清单

**遇到问题时,按顺序检查**:

- [ ] Ollama 服务是否运行: `curl http://localhost:11434/api/tags`
- [ ] 模型是否已下载: `ollama list`
- [ ] PostgreSQL 是否运行: `docker ps | findstr postgres`
- [ ] 配置文件路径是否正确: `$env:VOICE_AGENT_ENVIRONMENT="ollama"`
- [ ] 环境变量是否生效: `echo $env:VOICE_AGENT_ENVIRONMENT`
- [ ] 端口是否被占用: `netstat -ano | findstr :8000`
- [ ] 日志中是否有错误: `Get-Content logs\voice_agent.log`
- [ ] API 健康检查: `curl http://localhost:8000/health`

---

## 下一步

✅ **Ollama 集成完成后,可以尝试**:

1. **训练自定义模型**: 使用 Ollama 加载微调后的模型
2. **多模型切换**: 在对话中动态切换不同模型
3. **RAG 集成**: 结合本地向量数据库(如 ChromaDB)
4. **离线部署**: 完全断网环境下的 AI 系统

---

## 参考链接

- [Ollama 官方网站](https://ollama.com/)
- [Ollama GitHub](https://github.com/ollama/ollama)
- [Ollama 模型库](https://ollama.com/library)
- [通义千问官网](https://tongyi.aliyun.com/)
- [项目文档](./PROJECT.md)

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2025-01-18 | 初始版本,支持 6 个 Ollama 模型 |

---

**贡献者**: Ivan_HappyWoods Team  
**最后更新**: 2025-01-18  
**许可证**: [项目许可证]
