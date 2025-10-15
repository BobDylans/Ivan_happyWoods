# 智能对话 API 使用指南

## 📚 目录

- [概述](#概述)
- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [API 端点](#api-端点)
- [使用示例](#使用示例)
- [多轮对话](#多轮对话)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)

---

## 概述

智能对话 API 整合了语音识别（STT）、智能体（Agent）和语音合成（TTS）功能，提供完整的语音交互体验。

### 核心流程

```
用户输入（文本/语音）
        ↓
    [STT识别]（语音输入时）
        ↓
    [智能体处理]
        ↓
    [TTS合成]（语音输出时）
        ↓
返回结果（文本/语音）
```

### 技术栈

- **STT**: 科大讯飞语音识别
- **Agent**: LangGraph 智能体（支持工具调用和多轮对话）
- **TTS**: 科大讯飞流式语音合成
- **音频格式**: 自动转换（支持 MP3, WAV, M4A 等）

---

## 功能特性

### ✅ 灵活的输入输出

| 输入模式 | 输出模式 | 适用场景 |
|---------|---------|---------|
| 文本 | 文本 | 传统文本聊天 |
| 文本 | 语音 | 文本转语音播报 |
| 语音 | 文本 | 语音转文字记录 |
| 语音 | 语音 | 完整语音对话 |

### ✅ 多轮对话记忆

- 基于 `session_id` 维护对话历史
- 智能体可记住用户信息
- LangGraph 状态管理

### ✅ 流式语音输出

- 边合成边传输
- 降低首字节延迟
- 适合长文本回复

### ✅ 自动音频转换

- 支持多种音频格式（MP3, WAV, M4A, OGG, FLAC 等）
- 自动转换为 PCM
- 音频质量验证

---

## 快速开始

### 1. 启动服务

```bash
python start_server.py
```

服务地址: http://127.0.0.1:8000

### 2. 运行测试

```bash
# 安装依赖
pip install colorama requests

# 运行测试脚本
python test_conversation.py
```

### 3. 查看 API 文档

浏览器访问: http://127.0.0.1:8000/docs

---

## API 端点

### 1. 文本输入 → 文本输出

```http
POST /api/v1/conversation/message
```

**请求体**:
```json
{
  "text": "你好，请介绍一下你自己",
  "output_mode": "text",
  "session_id": "可选-用于多轮对话",
  "user_id": "可选-用户标识"
}
```

**响应**:
```json
{
  "success": true,
  "session_id": "conv_a1b2c3d4e5f6",
  "user_input": "你好，请介绍一下你自己",
  "agent_response": "你好！我是一个智能语音助手...",
  "output_mode": "text",
  "timestamp": "2025-10-15T10:30:00"
}
```

**curl 示例**:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/conversation/message" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: dev-test-key-123" \
     -d '{
       "text": "你好，请介绍一下你自己",
       "output_mode": "text"
     }'
```

---

### 2. 文本输入 → 语音输出（流式）

```http
POST /api/v1/conversation/message-stream
```

**请求体**:
```json
{
  "text": "给我讲个笑话",
  "output_mode": "audio",
  "voice": "x5_lingxiaoxuan_flow",
  "speed": 50,
  "volume": 50,
  "pitch": 50,
  "session_id": "可选"
}
```

**响应**: 流式音频数据（MP3 格式）

**curl 示例**:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/conversation/message-stream" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: dev-test-key-123" \
     -d '{
       "text": "给我讲个笑话",
       "output_mode": "audio",
       "voice": "x5_lingxiaoxuan_flow"
     }' \
     --output joke.mp3
```

---

### 3. 语音输入 → 文本输出

```http
POST /api/v1/conversation/message-audio
```

**请求参数** (multipart/form-data):
- `audio` (file): 音频文件
- `output_mode` (string): "text"
- `session_id` (string, 可选): 会话ID
- `user_id` (string, 可选): 用户ID

**响应**:
```json
{
  "success": true,
  "session_id": "conv_a1b2c3d4e5f6",
  "user_input": "今天天气怎么样",
  "agent_response": "今天天气晴朗，温度适宜...",
  "output_mode": "text",
  "input_metadata": {
    "input_mode": "audio",
    "audio_format": "mp3",
    "audio_converted": true,
    "audio_duration": 2.5,
    "stt_success": true
  }
}
```

**curl 示例**:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/conversation/message-audio" \
     -H "X-API-Key: dev-test-key-123" \
     -F "audio=@question.mp3" \
     -F "output_mode=text"
```

---

### 4. 语音输入 → 语音输出（完整语音对话）

```http
POST /api/v1/conversation/message-audio-stream
```

**请求参数** (multipart/form-data):
- `audio` (file): 音频文件
- `voice` (string, 可选): 发音人，默认 "x5_lingxiaoxuan_flow"
- `speed` (int, 可选): 语速 0-100，默认 50
- `volume` (int, 可选): 音量 0-100，默认 50
- `pitch` (int, 可选): 音调 0-100，默认 50
- `session_id` (string, 可选): 会话ID

**响应**: 流式音频数据（MP3 格式）

**curl 示例**:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/conversation/message-audio-stream" \
     -H "X-API-Key: dev-test-key-123" \
     -F "audio=@my_question.mp3" \
     -F "voice=x5_lingxiaoxuan_flow" \
     -F "speed=50" \
     --output agent_reply.mp3
```

---

### 5. 服务状态检查

```http
GET /api/v1/conversation/status
```

**响应**:
```json
{
  "service": "conversation",
  "available": true,
  "components": {
    "stt": true,
    "agent": true,
    "tts": true
  },
  "error": null
}
```

---

## 使用示例

### Python 示例

#### 1. 文本对话

```python
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"
API_KEY = "dev-test-key-123"

# 发送文本消息
response = requests.post(
    f"{BASE_URL}/conversation/message",
    json={
        "text": "你好，请介绍一下你自己",
        "output_mode": "text"
    },
    headers={"X-API-Key": API_KEY}
)

result = response.json()
print(f"用户: {result['user_input']}")
print(f"智能体: {result['agent_response']}")
print(f"会话ID: {result['session_id']}")
```

#### 2. 文本输入，流式语音输出

```python
import requests

response = requests.post(
    f"{BASE_URL}/conversation/message-stream",
    json={
        "text": "给我讲个故事",
        "output_mode": "audio",
        "voice": "x5_lingxiaoxuan_flow"
    },
    headers={"X-API-Key": API_KEY},
    stream=True
)

# 保存音频文件
with open("story.mp3", "wb") as f:
    for chunk in response.iter_content(chunk_size=4096):
        if chunk:
            f.write(chunk)
            print(f"接收 {len(chunk)} 字节")

print("音频保存成功！")
```

#### 3. 完整语音对话

```python
import requests

# 上传语音，获取语音回复
with open("my_question.mp3", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/conversation/message-audio-stream",
        files={"audio": f},
        data={
            "voice": "x5_lingxiaoxuan_flow",
            "speed": 50
        },
        headers={"X-API-Key": API_KEY},
        stream=True
    )

# 保存语音回复
with open("agent_reply.mp3", "wb") as f:
    for chunk in response.iter_content(chunk_size=4096):
        if chunk:
            f.write(chunk)

# 获取元数据
session_id = response.headers.get("X-Session-Id")
user_input = response.headers.get("X-User-Input")

print(f"会话ID: {session_id}")
print(f"识别文本: {user_input}")
print(f"回复已保存: agent_reply.mp3")
```

---

### JavaScript 示例

#### 1. 文本对话

```javascript
const response = await fetch('http://127.0.0.1:8000/api/v1/conversation/message', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'dev-test-key-123'
  },
  body: JSON.stringify({
    text: '你好，请介绍一下你自己',
    output_mode: 'text'
  })
});

const result = await response.json();
console.log('用户:', result.user_input);
console.log('智能体:', result.agent_response);
console.log('会话ID:', result.session_id);
```

#### 2. 语音输入

```javascript
// 从文件输入获取音频
const fileInput = document.getElementById('audioFile');
const audioFile = fileInput.files[0];

const formData = new FormData();
formData.append('audio', audioFile);
formData.append('output_mode', 'text');

const response = await fetch('http://127.0.0.1:8000/api/v1/conversation/message-audio', {
  method: 'POST',
  headers: {
    'X-API-Key': 'dev-test-key-123'
  },
  body: formData
});

const result = await response.json();
console.log('识别文本:', result.user_input);
console.log('智能体回复:', result.agent_response);
```

#### 3. 流式语音播放

```javascript
const response = await fetch('http://127.0.0.1:8000/api/v1/conversation/message-stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'dev-test-key-123'
  },
  body: JSON.stringify({
    text: '给我讲个笑话',
    output_mode: 'audio',
    voice: 'x5_lingxiaoxuan_flow'
  })
});

// 读取流式音频
const reader = response.body.getReader();
const chunks = [];

while (true) {
  const {done, value} = await reader.read();
  if (done) break;
  
  chunks.push(value);
  console.log(`接收 ${value.length} 字节`);
}

// 合并并播放
const blob = new Blob(chunks, {type: 'audio/mpeg'});
const audioUrl = URL.createObjectURL(blob);
const audio = new Audio(audioUrl);
audio.play();
```

---

## 多轮对话

### 使用 session_id 维护对话历史

```python
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"
API_KEY = "dev-test-key-123"

# 第一轮对话
response1 = requests.post(
    f"{BASE_URL}/conversation/message",
    json={"text": "我叫小明，今年18岁", "output_mode": "text"},
    headers={"X-API-Key": API_KEY}
)

data1 = response1.json()
session_id = data1['session_id']
print(f"智能体: {data1['agent_response']}")
print(f"会话ID: {session_id}\n")

# 第二轮对话（使用相同 session_id）
response2 = requests.post(
    f"{BASE_URL}/conversation/message",
    json={
        "text": "你还记得我叫什么名字吗？",
        "output_mode": "text",
        "session_id": session_id  # 关键：使用相同会话ID
    },
    headers={"X-API-Key": API_KEY}
)

data2 = response2.json()
print(f"智能体: {data2['agent_response']}")

# 智能体应该能记住用户叫"小明"
```

### 语音多轮对话

```python
session_id = None

def voice_chat(audio_file: str):
    global session_id
    
    with open(audio_file, "rb") as f:
        data = {"voice": "x5_lingxiaoxuan_flow"}
        
        # 如果有 session_id，继续使用
        if session_id:
            data["session_id"] = session_id
        
        response = requests.post(
            f"{BASE_URL}/conversation/message-audio-stream",
            files={"audio": f},
            data=data,
            headers={"X-API-Key": API_KEY},
            stream=True
        )
        
        # 获取会话ID
        session_id = response.headers.get("X-Session-Id")
        
        # 保存回复
        output = f"reply_{audio_file}"
        with open(output, "wb") as out:
            for chunk in response.iter_content(chunk_size=4096):
                out.write(chunk)
        
        print(f"回复保存: {output}")
        print(f"会话ID: {session_id}")

# 持续对话
voice_chat("question1.mp3")
voice_chat("question2.mp3")  # 使用相同 session_id
voice_chat("question3.mp3")  # 继续使用相同 session_id
```

---

## 错误处理

### 常见错误

#### 1. 服务未初始化

```json
{
  "detail": "对话服务未初始化，请检查服务器配置"
}
```

**解决**: 确保服务器正常启动，检查日志中是否有初始化错误

#### 2. 音频格式不支持

```json
{
  "detail": "不支持的音频格式: xyz。支持的格式: .mp3, .wav, .m4a, ..."
}
```

**解决**: 使用支持的音频格式（MP3, WAV, M4A, OGG, FLAC 等）

#### 3. 语音识别失败

```json
{
  "success": false,
  "error": "语音识别失败: WebSocket连接超时"
}
```

**解决**: 
- 检查音频质量（清晰度、噪音）
- 检查网络连接
- 确认音频时长 < 60秒

#### 4. 音频验证失败

```json
{
  "detail": "音频验证失败: 音频过长: 70.00秒 (最大 60秒)"
}
```

**解决**: 
- 限制音频时长 < 60秒
- 分段上传长音频

---

## 最佳实践

### 1. 性能优化

#### 使用流式端点处理长文本

```python
# ✅ 推荐：长文本使用流式
response = requests.post(
    "/conversation/message-stream",
    json={"text": long_text, "output_mode": "audio"},
    stream=True
)

# ❌ 不推荐：长文本使用非流式（等待时间长）
response = requests.post(
    "/conversation/message",
    json={"text": long_text, "output_mode": "both"}
)
```

#### 复用 session_id

```python
# ✅ 推荐：维护会话ID，减少上下文重建
session_id = "conv_12345"
for message in messages:
    response = chat(message, session_id=session_id)

# ❌ 不推荐：每次都创建新会话
for message in messages:
    response = chat(message)  # 每次都是新会话
```

### 2. 音频处理

#### 音频质量建议

- ✅ **采样率**: 16kHz 或更高
- ✅ **格式**: MP3, WAV（兼容性好）
- ✅ **时长**: 1-30秒（最佳）
- ✅ **清晰度**: 减少背景噪音
- ✅ **音量**: 适中，避免过大或过小

#### 音频预处理

```python
from pydub import AudioSegment

# 加载音频
audio = AudioSegment.from_file("input.mp3")

# 降噪、标准化音量
audio = audio.normalize()

# 转换为 16kHz
audio = audio.set_frame_rate(16000)

# 导出
audio.export("optimized.mp3", format="mp3")
```

### 3. 错误处理

```python
import requests
from requests.exceptions import Timeout, RequestException

def safe_conversation(text: str, session_id: str = None):
    """安全的对话请求"""
    try:
        response = requests.post(
            f"{BASE_URL}/conversation/message",
            json={"text": text, "session_id": session_id},
            headers={"X-API-Key": API_KEY},
            timeout=30  # 设置超时
        )
        
        response.raise_for_status()  # 检查 HTTP 错误
        return response.json()
    
    except Timeout:
        print("请求超时，请重试")
        return None
    
    except RequestException as e:
        print(f"请求失败: {e}")
        return None
    
    except Exception as e:
        print(f"未知错误: {e}")
        return None
```

### 4. 并发处理

```python
import asyncio
import aiohttp

async def async_conversation(session, text, session_id=None):
    """异步对话请求"""
    async with session.post(
        f"{BASE_URL}/conversation/message",
        json={"text": text, "session_id": session_id},
        headers={"X-API-Key": API_KEY}
    ) as response:
        return await response.json()

async def batch_conversations(messages):
    """批量处理对话"""
    async with aiohttp.ClientSession() as session:
        tasks = [
            async_conversation(session, msg)
            for msg in messages
        ]
        results = await asyncio.gather(*tasks)
        return results

# 使用
messages = ["你好", "今天天气怎么样", "讲个笑话"]
results = asyncio.run(batch_conversations(messages))
```

---

## 发音人选项

### 可用发音人（x5 系列）

| 发音人代码 | 名称 | 性别 | 特点 |
|-----------|------|------|------|
| `x5_lingxiaoxuan_flow` | 聆小璇 | 女声 | 温柔自然 ⭐ 推荐 |
| `x5_lingfeiyi_flow` | 聆飞逸 | 男声 | 沉稳大气 |
| `x5_lingxiaoyue_flow` | 聆小玥 | 女声 | 活泼可爱 |
| `x5_lingyuzhao_flow` | 聆玉昭 | 女声 | 典雅知性 |
| `x5_lingyuyan_flow` | 聆玉言 | 女声 | 专业播报 |

### 使用示例

```python
# 使用不同发音人
voices = [
    "x5_lingxiaoxuan_flow",  # 女声，默认
    "x5_lingfeiyi_flow",     # 男声
    "x5_lingxiaoyue_flow"    # 女声
]

for voice in voices:
    response = requests.post(
        f"{BASE_URL}/conversation/message-stream",
        json={
            "text": "你好，这是语音测试",
            "output_mode": "audio",
            "voice": voice
        },
        headers={"X-API-Key": API_KEY},
        stream=True
    )
    
    with open(f"test_{voice}.mp3", "wb") as f:
        for chunk in response.iter_content(chunk_size=4096):
            f.write(chunk)
```

---

## 参数说明

### TTS 参数

| 参数 | 类型 | 范围 | 默认值 | 说明 |
|------|------|------|--------|------|
| voice | string | - | x5_lingxiaoxuan_flow | 发音人 |
| speed | int | 0-100 | 50 | 语速（50=正常） |
| volume | int | 0-100 | 50 | 音量（50=正常） |
| pitch | int | 0-100 | 50 | 音调（50=正常） |

### 调整示例

```python
# 快速、高音量
{
  "voice": "x5_lingxiaoxuan_flow",
  "speed": 70,    # 加快语速
  "volume": 80,   # 提高音量
  "pitch": 50     # 正常音调
}

# 慢速、低音调（适合讲故事）
{
  "voice": "x5_lingfeiyi_flow",
  "speed": 30,    # 放慢语速
  "volume": 50,   # 正常音量
  "pitch": 40     # 降低音调
}
```

---

## 常见问题 (FAQ)

### Q1: 为什么语音识别失败？

**A**: 可能的原因：
- 音频质量差（噪音大、音量小）
- 音频格式不支持
- 网络连接问题
- 音频时长超过限制（60秒）

**解决方法**:
1. 使用高质量录音设备
2. 减少背景噪音
3. 使用支持的音频格式（MP3, WAV）
4. 分段处理长音频

### Q2: 多轮对话不记得之前的内容？

**A**: 确保使用相同的 `session_id`

```python
# ✅ 正确：保持 session_id
session_id = "conv_12345"
response1 = chat("我叫小明", session_id=session_id)
response2 = chat("我叫什么", session_id=session_id)  # 会记住

# ❌ 错误：每次都是新 session_id
response1 = chat("我叫小明")  # session_id: conv_aaa
response2 = chat("我叫什么")  # session_id: conv_bbb（不记得）
```

### Q3: 流式音频如何播放？

**A**: 前端示例：

```javascript
// 接收流式音频
const response = await fetch('/conversation/message-stream', {...});
const reader = response.body.getReader();
const chunks = [];

while (true) {
  const {done, value} = await reader.read();
  if (done) break;
  chunks.push(value);
}

// 合并并播放
const blob = new Blob(chunks, {type: 'audio/mpeg'});
const audioUrl = URL.createObjectURL(blob);
const audio = new Audio(audioUrl);
audio.play();
```

### Q4: 如何自定义智能体行为？

**A**: 修改智能体配置或 prompt

```python
# 在 src/agent/ 中修改
# 或通过 system message 配置
```

### Q5: 支持哪些音频格式？

**A**: 支持格式：
- ✅ MP3
- ✅ WAV  
- ✅ M4A (AAC)
- ✅ OGG
- ✅ FLAC
- ✅ WEBM
- ✅ AMR

所有格式会自动转换为 PCM。

---

## 性能指标

### 响应时间（参考）

| 场景 | 首字节时间 | 总时间 |
|------|-----------|--------|
| 文本对话 | ~1s | ~2s |
| 文本→语音（短） | ~2s | ~4s |
| 文本→语音（长，流式） | ~1s | ~10s |
| 语音→文本 | ~3s | ~5s |
| 语音→语音 | ~4s | ~8s |

*实际时间取决于网络、服务器性能和文本长度*

### 流式 vs 非流式

| 指标 | 非流式 | 流式 |
|------|-------|------|
| 首字节 | 等待完整合成 | 快速响应 |
| 用户体验 | 较差（需等待） | 优秀（实时） |
| 适用场景 | 短文本 | 长文本 |

---

## 相关文档

- **[TTS_QUICKSTART.md](./TTS_QUICKSTART.md)** - TTS 服务快速参考
- **[TTS_STREAM_GUIDE.md](./TTS_STREAM_GUIDE.md)** - 流式 TTS 完整指南
- **[API 文档](http://127.0.0.1:8000/docs)** - 完整 API 参考

---

## 技术支持

- **API 文档**: http://127.0.0.1:8000/docs
- **测试脚本**: `test_conversation.py`
- **服务状态**: http://127.0.0.1:8000/api/v1/conversation/status

---

**版本**: 1.0  
**更新时间**: 2025-10-15  
**状态**: ✅ 生产就绪
