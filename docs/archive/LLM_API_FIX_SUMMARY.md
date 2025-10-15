# LLM API 兼容性修复总结

**日期**: 2025-10-14  
**问题**: GPT-5 系列模型不支持 `max_tokens` 参数

---

## 🐛 问题描述

测试 LLM 连接时遇到错误：
```
"Unsupported parameter: 'max_tokens' is not supported with this model. 
Use 'max_completion_tokens' instead."
```

**原因**: GPT-5 系列模型使用新的 API 参数：
- **旧参数**: `max_tokens` (GPT-4 及更早版本)
- **新参数**: `max_completion_tokens` (GPT-5 系列)

---

## ✅ 解决方案

### 1. 创建 LLM 兼容层

**文件**: `src/utils/llm_compat.py`

**核心功能**:
```python
def prepare_llm_params(model, messages, temperature, max_tokens, **kwargs):
    """自动适配不同模型的参数"""
    params = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    
    # GPT-5 系列使用 max_completion_tokens
    if model.startswith("gpt-5"):
        params["max_completion_tokens"] = max_tokens
    else:
        params["max_tokens"] = max_tokens
    
    return params
```

**其他工具函数**:
- `is_gpt5_model(model)` - 判断模型类型
- `get_max_tokens_param_name(model)` - 获取参数名
- `get_model_features(model)` - 获取模型特性
- `validate_model_params(model, **params)` - 验证参数

### 2. 更新 Agent 代码

**修改文件**:
1. `src/agent/nodes.py`
   - 导入兼容层
   - 更新 `call_llm()` 方法
   - 更新 `_make_llm_call()` 方法
   - 更新 `stream_llm_call()` 方法

2. `src/agent/graph.py`
   - 导入兼容层
   - 更新 `process_message_stream()` 方法

**修改示例**:
```python
# 旧代码
llm_config = {
    "model": model,
    "messages": messages,
    "temperature": temperature,
    "max_tokens": max_tokens
}

# 新代码（使用兼容层）
llm_config = prepare_llm_params(
    model=model,
    messages=messages,
    temperature=temperature,
    max_tokens=max_tokens
)
```

### 3. 更新测试代码

**文件**: `test_llm_connection.py`

**修改**:
```python
payload = {
    "model": config.llm.models.fast,
    "messages": [...],
    "max_completion_tokens": 100  # 使用新参数
}
```

---

## 📊 支持的模型映射

| 模型系列 | max_tokens 参数 | 上下文长度 | 功能支持 |
|---------|----------------|-----------|---------|
| **gpt-5-pro** | `max_completion_tokens` | 128K | Vision + Function Calling |
| **gpt-5-mini** | `max_completion_tokens` | 128K | Vision + Function Calling |
| **gpt-5-chat-latest** | `max_completion_tokens` | 128K | Vision + Function Calling |
| **gpt-5-nano** | `max_completion_tokens` | 32K | Function Calling |
| **gpt-4-turbo** | `max_tokens` | 128K | Vision + Function Calling |
| **gpt-4** | `max_tokens` | 8K | Function Calling |
| **gpt-3.5-turbo** | `max_tokens` | 16K | Function Calling |

---

## 🧪 测试验证

### 测试工具

1. **配置验证**: `python test_config.py`
   - ✅ 7/7 测试通过

2. **LLM 连接测试**: `python test_llm_connection.py`
   - 测试 `/models` 端点
   - 测试 `/chat/completions` 端点
   - 验证模型可用性

3. **快速测试**: `python test_quick_llm.py`
   - 简化版 API 测试
   - 直接测试 max_completion_tokens

### 预期结果

```bash
$ python test_quick_llm.py

🧪 快速 LLM API 测试
URL: https://api.openai-proxy.org/v1
Model: gpt-5-mini
API Key: sk-M9DIQm5fQ66GgUtC...

测试对话...
Status: 200
✅ 成功!
响应: 配置测试成功！

🎉 配置验证通过！LLM API 工作正常。
```

---

## 🔄 向后兼容性

兼容层**完全向后兼容**，支持：
- ✅ GPT-5 系列（自动使用 max_completion_tokens）
- ✅ GPT-4 系列（使用 max_tokens）
- ✅ GPT-3.5 系列（使用 max_tokens）
- ✅ 自定义模型（默认使用 max_tokens）

---

## 📝 代码变更清单

### 新增文件
- `src/utils/llm_compat.py` (200+ 行)
- `src/utils/__init__.py`
- `test_quick_llm.py`
- `LLM_API_FIX_SUMMARY.md` (本文档)

### 修改文件
- `src/agent/nodes.py`
  - 导入 `prepare_llm_params`
  - 3 处使用兼容层
- `src/agent/graph.py`
  - 导入 `prepare_llm_params`
  - 1 处使用兼容层
- `test_llm_connection.py`
  - 使用 `max_completion_tokens`

---

## 💡 使用指南

### 在代码中使用兼容层

```python
from utils.llm_compat import prepare_llm_params

# 自动适配参数
params = prepare_llm_params(
    model="gpt-5-mini",  # 或 "gpt-4", "gpt-3.5-turbo"
    messages=messages,
    temperature=0.7,
    max_tokens=2048
)

# params 将包含正确的参数名：
# GPT-5: {"model": "gpt-5-mini", "max_completion_tokens": 2048, ...}
# GPT-4: {"model": "gpt-4", "max_tokens": 2048, ...}
```

### 检查模型类型

```python
from utils.llm_compat import is_gpt5_model, get_model_features

# 判断模型类型
if is_gpt5_model("gpt-5-mini"):
    print("This is GPT-5")

# 获取模型特性
features = get_model_features("gpt-5-pro")
print(features["max_tokens_param"])  # "max_completion_tokens"
print(features["max_context"])       # 128000
```

---

## ✅ 验证清单

- [x] 创建 LLM 兼容层 (`utils/llm_compat.py`)
- [x] 更新 `nodes.py` 使用兼容层
- [x] 更新 `graph.py` 使用兼容层
- [x] 修复 `test_llm_connection.py`
- [x] 创建快速测试脚本
- [x] 文档化解决方案
- [ ] 运行完整测试套件
- [ ] 验证 API 服务器启动
- [ ] 测试端到端对话功能

---

## 🎯 下一步

1. **运行完整测试**:
   ```bash
   python test_llm_connection.py
   python test_quick_llm.py
   ```

2. **启动服务器**:
   ```bash
   python start_server.py
   ```

3. **测试 API**:
   ```bash
   python test_api.py
   ```

4. **继续 Phase 2B 开发**:
   - 实现 STT 服务
   - 实现 TTS 服务
   - 集成语音流程

---

**修复状态**: ✅ 已完成  
**测试状态**: ⏳ 待验证  
**影响范围**: Agent 核心代码，完全向后兼容
