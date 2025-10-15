# 编码错误修复

## 📅 修复日期
2025-10-15

## 🐛 问题描述

运行测试时出现两个编码相关错误：

### 错误 1: HTTP 头部编码错误
```
UnicodeEncodeError: 'latin-1' codec can't encode characters in position 0-5: ordinal not in range(256)
```

**位置**: `src/api/conversation_routes.py` 行 403, 555  
**原因**: HTTP 响应头部 `X-User-Input` 包含中文字符，但 HTTP 头部默认使用 `latin-1` 编码，不支持中文。

### 错误 2: Datetime JSON 序列化错误
```
Object of type datetime is not JSON serializable
```

**位置**: API 响应序列化  
**原因**: agent 返回的 metadata 中包含 `datetime` 对象，无法直接序列化为 JSON。

## ✅ 修复方案

### 修复 1: HTTP 头部中文 URL 编码

**文件**: `src/api/conversation_routes.py`

在两处 `StreamingResponse` 调用前添加 URL 编码：

```python
# 对中文进行 URL 编码以避免 HTTP 头部编码错误
from urllib.parse import quote
user_input_encoded = quote(user_input[:100])

return StreamingResponse(
    audio_generator(),
    media_type="audio/mpeg",
    headers={
        "X-Session-Id": session_id,
        "X-User-Input": user_input_encoded,  # 使用编码后的文本
        "X-Voice": request.voice,
        "Content-Disposition": f"attachment; filename=response_{session_id}.mp3"
    }
)
```

**修改位置**:
- 第 403 行 (`/message-stream` 端点)
- 第 555 行 (`/message-audio-stream` 端点)

**解释**: 
- `quote()` 将中文转换为 URL 编码格式（如 `%E4%BD%A0%E5%A5%BD`）
- 客户端可以使用 `unquote()` 解码回中文
- HTTP 头部只支持 ASCII 字符，URL 编码是标准做法

### 修复 2: Datetime 对象序列化

**文件**: `src/services/conversation_service.py`

#### 2.1 添加序列化工具函数

在文件开头添加：

```python
def serialize_datetime(obj: Any) -> Any:
    """递归转换字典中的 datetime 对象为 ISO 字符串"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetime(item) for item in obj]
    return obj
```

#### 2.2 应用序列化

在 `get_agent_response()` 方法中（约第 203 行）：

```python
# 序列化所有 datetime 对象
metadata = serialize_datetime({
    "session_id": session_id,
    "agent_success": result.get("success", True),
    "response_length": len(agent_response),
    "timestamp": result.get("timestamp", datetime.now().isoformat()),
    "message_count": result.get("message_count", 0),
    "agent_metadata": result.get("metadata", {})
})
```

**解释**:
- 递归遍历所有嵌套字典和列表
- 将所有 `datetime` 对象转换为 ISO 格式字符串
- 保证整个响应可以安全地序列化为 JSON

#### 2.3 额外增强 (已添加但未使用)

在 `src/api/conversation_routes.py` 添加了自定义 JSON 编码器作为备用方案：

```python
class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
```

## 🧪 验证步骤

### 1. 重启服务器

```bash
# 停止当前服务 (Ctrl+C)

# 重新启动
python start_server.py
```

### 2. 运行测试

```bash
python test_conversation.py
```

### 3. 期待结果

✅ **测试 1**: 文本对话成功，返回真实 LLM 回复  
✅ **测试 2**: 流式语音输出成功，无编码错误  
✅ **测试 5**: 多轮对话成功，记住用户信息  

**不应该再出现**:
- ❌ `UnicodeEncodeError: 'latin-1' codec...`
- ❌ `Object of type datetime is not JSON serializable`

### 4. 检查 HTTP 头部

测试时可以检查响应头部：

```python
response = requests.post(...)
print(response.headers['X-User-Input'])  # 应该是 URL 编码格式
from urllib.parse import unquote
print(unquote(response.headers['X-User-Input']))  # 解码后是中文
```

## 📝 技术说明

### HTTP 头部编码规范

根据 RFC 7230，HTTP 头部字段值应该是：
- 可见的 ASCII 字符 (VCHAR)
- 可选的空白字符

中文字符不在这个范围内，因此需要编码。

**常见编码方案**:
1. **URL 编码** (我们使用的): `quote()`/`unquote()`
2. **Base64 编码**: 更冗长但更通用
3. **RFC 2047**: 专门用于邮件头部

我们选择 URL 编码因为：
- ✅ 简单易用
- ✅ 标准化
- ✅ 客户端库广泛支持
- ✅ 可读性相对较好（短文本）

### JSON 序列化

Python 的 `json` 模块默认支持的类型：
- `str`, `int`, `float`, `bool`, `None`
- `list`, `tuple`, `dict`

**不支持**:
- ❌ `datetime`, `date`, `time`
- ❌ `Decimal`, `UUID`
- ❌ 自定义对象

**解决方案**:
1. **预处理** (我们使用的): 在序列化前转换
2. **自定义编码器**: `json.dumps(obj, cls=CustomEncoder)`
3. **Pydantic**: 自动处理（但嵌套字典需要注意）

我们选择预处理因为：
- ✅ 最可靠（确保所有数据都被处理）
- ✅ 不依赖序列化库的具体实现
- ✅ 递归处理嵌套结构
- ✅ 性能开销小

## 🔍 相关问题排查

### 如果还出现编码错误

1. **检查其他响应头部**: 确保所有头部字段都是 ASCII
2. **检查文件名**: `Content-Disposition` 中的文件名也需要编码
3. **检查日志输出**: 有些日志库可能也有编码问题

### 如果还出现 JSON 错误

1. **检查其他数据类型**: UUID, Decimal 等
2. **增加调试日志**: 
   ```python
   logger.debug(f"Metadata types: {[(k, type(v)) for k, v in metadata.items()]}")
   ```
3. **使用类型检查**: `mypy` 可以帮助发现类型问题

## 📊 修复文件清单

| 文件 | 修改内容 | 行数 |
|------|---------|------|
| `src/api/conversation_routes.py` | 添加 URL 编码 | 403, 555 |
| `src/api/conversation_routes.py` | 添加 DateTimeEncoder 类 | 25-29 |
| `src/services/conversation_service.py` | 添加 serialize_datetime() | 23-31 |
| `src/services/conversation_service.py` | 应用序列化 | 203 |

## ✅ 验证清单

运行测试后检查：

- [ ] 服务器成功启动，无错误
- [ ] 测试 1 返回真实 LLM 回复（不是 Fallback）
- [ ] 测试 2 流式输出成功，无编码错误
- [ ] 测试 5 多轮对话记住信息
- [ ] 日志中没有 UnicodeEncodeError
- [ ] 日志中没有 JSON serialization 错误
- [ ] HTTP 响应头部 X-User-Input 正确编码

---

**修复人**: GitHub Copilot  
**修复时间**: 2025-10-15  
**影响范围**: HTTP 响应头部 + JSON 序列化  
**验证状态**: 🔄 等待测试验证
