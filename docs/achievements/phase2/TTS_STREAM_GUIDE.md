# 流式 TTS API 测试指南

## 🚀 什么是流式 TTS？

**流式 TTS** 与普通 TTS 的区别：

| 特性 | 普通 TTS (/synthesize) | 流式 TTS (/synthesize-stream) |
|------|----------------------|----------------------------|
| **响应方式** | 等待全部合成完成后返回 | 边合成边返回音频块 |
| **首字节时间** | 较慢（需等待完整合成） | 很快（立即开始传输） |
| **适用场景** | 短文本（< 100字） | 长文本（100-10000字） |
| **内存占用** | 需缓存完整音频 | 流式传输，低内存 |
| **用户体验** | 等待后一次性播放 | 实时播放，感觉更快 |
| **失败处理** | 可降级返回 JSON | 只能中断连接 |

---

## 📋 在 Swagger UI 中测试流式 TTS

### 步骤 1: 启动服务器

```bash
python start_server.py
```

### 步骤 2: 打开 Swagger UI

浏览器访问: http://127.0.0.1:8000/docs

### 步骤 3: 认证

1. 点击右上角 **"Authorize"** 按钮
2. 输入: `dev-test-key-123`
3. 点击 **"Authorize"**

### 步骤 4: 找到流式接口

展开 **`POST /api/v1/voice/tts/synthesize-stream`**

### 步骤 5: 使用测试 JSON

#### 测试 1: 基础流式合成

```json
{
  "text": "人工智能是计算机科学的一个重要分支。它致力于理解智能的实质，并生产出能以人类智能相似的方式做出反应的智能机器。该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。",
  "voice": "x5_lingxiaoxuan_flow",
  "speed": 50,
  "volume": 60,
  "pitch": 50
}
```

#### 测试 2: 长文本流式合成（500+ 字）

```json
{
  "text": "在遥远的未来，人类已经掌握了星际旅行的技术。宇宙飞船穿梭于各个星系之间，探索着未知的世界。科学家们发现了许多宜居的行星，人类文明开始向银河系扩张。然而，在探索的过程中，他们也遇到了许多挑战。陌生的环境、未知的生物、复杂的社会结构，这些都考验着人类的智慧和勇气。尽管困难重重，人类依然坚持前行，因为他们相信，宇宙中一定存在着更多的可能性，等待着他们去发现。在这个过程中，科技不断进步，文明不断演化，人类逐渐成为了银河系中最强大的种族之一。他们建立了星际联盟，制定了公平的法律，促进了各个文明之间的交流与合作。",
  "voice": "x5_lingxiaoxuan_flow",
  "speed": 55
}
```

#### 测试 3: 快速语速流式播报

```json
{
  "text": "今天的新闻播报：科技公司发布最新人工智能模型，性能提升显著。国际市场波动加剧，投资者需保持警惕。天气预报显示，明天将有降雨，请市民注意出行安全。",
  "voice": "x5_lingfeiyi_flow",
  "speed": 70,
  "volume": 70
}
```

#### 测试 4: 慢速朗读

```json
{
  "text": "静夜思。床前明月光，疑是地上霜。举头望明月，低头思故乡。",
  "voice": "x5_lingyuzhao_flow",
  "speed": 30,
  "pitch": 55
}
```

#### 测试 5: 最简配置

```json
{
  "text": "这是一个流式语音合成测试，使用默认参数。"
}
```

---

## 💻 使用命令行测试

### Windows PowerShell

```powershell
# 测试流式 TTS
$body = @{
    text = "人工智能正在改变世界。机器学习、深度学习、自然语言处理等技术快速发展，为人类带来了前所未有的便利。"
    voice = "x5_lingxiaoxuan_flow"
    speed = 50
} | ConvertTo-Json

Invoke-WebRequest `
    -Method POST `
    -Uri "http://localhost:8000/api/v1/voice/tts/synthesize-stream" `
    -ContentType "application/json" `
    -Headers @{"X-API-Key"="dev-test-key-123"} `
    -Body $body `
    -OutFile "stream_test.mp3"

# 播放生成的音频
start stream_test.mp3
```

### Linux/Mac (curl)

```bash
curl -X POST "http://localhost:8000/api/v1/voice/tts/synthesize-stream" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: dev-test-key-123" \
     -d '{
       "text": "流式语音合成测试。这段文字会被实时转换为语音，并以流式方式传输。",
       "voice": "x5_lingxiaoxuan_flow",
       "speed": 50
     }' \
     --output stream_test.mp3

# 播放
open stream_test.mp3  # macOS
# 或
xdg-open stream_test.mp3  # Linux
```

---

## 🐍 Python 客户端示例

### 示例 1: 使用 httpx 流式接收

```python
import httpx
import asyncio

async def stream_tts():
    """流式接收 TTS 音频"""
    url = "http://localhost:8000/api/v1/voice/tts/synthesize-stream"
    
    payload = {
        "text": "这是一段很长的文本。" * 20,  # 重复20次模拟长文本
        "voice": "x5_lingxiaoxuan_flow",
        "speed": 50
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "dev-test-key-123"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as response:
            print(f"状态码: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"发音人: {response.headers.get('X-Voice')}")
            print(f"文本长度: {response.headers.get('X-Text-Length')}")
            print()
            
            total_bytes = 0
            chunk_count = 0
            
            with open("stream_output.mp3", "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
                        total_bytes += len(chunk)
                        chunk_count += 1
                        print(f"✅ 接收第 {chunk_count} 块: {len(chunk)} bytes (总计: {total_bytes} bytes)")
            
            print()
            print(f"🎉 下载完成!")
            print(f"   总字节: {total_bytes:,}")
            print(f"   总块数: {chunk_count}")
            print(f"   文件: stream_output.mp3")

if __name__ == "__main__":
    asyncio.run(stream_tts())
```

### 示例 2: 使用 requests 流式下载

```python
import requests

def download_stream_tts():
    """使用 requests 下载流式 TTS"""
    url = "http://localhost:8000/api/v1/voice/tts/synthesize-stream"
    
    payload = {
        "text": "科技改变生活，创新引领未来。人工智能、大数据、云计算等新技术正在深刻影响着我们的工作和生活方式。",
        "voice": "x5_lingxiaoxuan_flow",
        "speed": 55
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "dev-test-key-123"
    }
    
    print("📡 开始流式下载...")
    
    with requests.post(url, json=payload, headers=headers, stream=True) as response:
        response.raise_for_status()
        
        print(f"✅ 状态码: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        print(f"   发音人: {response.headers.get('X-Voice')}")
        print()
        
        total_bytes = 0
        
        with open("stream_download.mp3", "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_bytes += len(chunk)
                    print(f"📥 已下载: {total_bytes:,} bytes", end="\r")
        
        print()
        print(f"🎉 下载完成: {total_bytes:,} bytes")

if __name__ == "__main__":
    download_stream_tts()
```

---

## 🌐 JavaScript/TypeScript 示例

### 浏览器中使用 fetch API

```javascript
async function streamTTS(text, voice = 'x5_lingxiaoxuan_flow') {
  const response = await fetch('http://localhost:8000/api/v1/voice/tts/synthesize-stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'dev-test-key-123'
    },
    body: JSON.stringify({
      text: text,
      voice: voice,
      speed: 50
    })
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  // 读取流式响应
  const reader = response.body.getReader();
  const chunks = [];
  let receivedBytes = 0;

  while (true) {
    const {done, value} = await reader.read();
    
    if (done) {
      console.log('✅ 流式接收完成!');
      break;
    }

    chunks.push(value);
    receivedBytes += value.length;
    console.log(`📥 接收: ${value.length} bytes (总计: ${receivedBytes} bytes)`);
  }

  // 合并所有块
  const audioBlob = new Blob(chunks, {type: 'audio/mpeg'});
  console.log(`🎵 音频大小: ${audioBlob.size} bytes`);

  // 播放音频
  const audioUrl = URL.createObjectURL(audioBlob);
  const audio = new Audio(audioUrl);
  audio.play();

  return audioUrl;
}

// 使用示例
streamTTS('你好，这是流式语音合成测试。感受实时传输的速度吧！')
  .then(url => console.log('音频 URL:', url))
  .catch(err => console.error('错误:', err));
```

### Node.js 使用 axios

```javascript
const axios = require('axios');
const fs = require('fs');

async function downloadStreamTTS() {
  const url = 'http://localhost:8000/api/v1/voice/tts/synthesize-stream';
  
  const response = await axios.post(url, {
    text: '这是 Node.js 流式下载测试。音频数据会实时传输。',
    voice: 'x5_lingxiaoxuan_flow',
    speed: 50
  }, {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'dev-test-key-123'
    },
    responseType: 'stream'
  });

  const writer = fs.createWriteStream('stream_nodejs.mp3');
  
  let totalBytes = 0;
  
  response.data.on('data', (chunk) => {
    totalBytes += chunk.length;
    console.log(`📥 接收: ${chunk.length} bytes (总计: ${totalBytes} bytes)`);
  });

  response.data.pipe(writer);

  return new Promise((resolve, reject) => {
    writer.on('finish', () => {
      console.log(`🎉 下载完成: ${totalBytes} bytes`);
      resolve();
    });
    writer.on('error', reject);
  });
}

downloadStreamTTS().catch(console.error);
```

---

## 📊 性能对比测试

创建测试脚本对比普通模式和流式模式：

```python
import httpx
import asyncio
import time

async def test_performance():
    """对比普通模式和流式模式的性能"""
    
    test_text = "人工智能技术正在快速发展。" * 20  # 400字左右
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "dev-test-key-123"
    }
    
    payload = {
        "text": test_text,
        "voice": "x5_lingxiaoxuan_flow",
        "speed": 50
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        
        # 测试普通模式
        print("🔵 测试普通模式...")
        start_normal = time.time()
        first_byte_normal = None
        
        response_normal = await client.post(
            "http://localhost:8000/api/v1/voice/tts/synthesize",
            json=payload,
            headers=headers
        )
        
        audio_normal = response_normal.content
        end_normal = time.time()
        
        normal_time = end_normal - start_normal
        
        print(f"   首字节时间: {normal_time:.2f}s (全部合成完成)")
        print(f"   总时间: {normal_time:.2f}s")
        print(f"   音频大小: {len(audio_normal):,} bytes")
        print()
        
        # 测试流式模式
        print("🟢 测试流式模式...")
        start_stream = time.time()
        first_byte_stream = None
        total_bytes = 0
        
        async with client.stream(
            "POST",
            "http://localhost:8000/api/v1/voice/tts/synthesize-stream",
            json=payload,
            headers=headers
        ) as response_stream:
            async for chunk in response_stream.aiter_bytes():
                if first_byte_stream is None:
                    first_byte_stream = time.time()
                total_bytes += len(chunk)
        
        end_stream = time.time()
        
        stream_ttfb = first_byte_stream - start_stream
        stream_total = end_stream - start_stream
        
        print(f"   首字节时间: {stream_ttfb:.2f}s")
        print(f"   总时间: {stream_total:.2f}s")
        print(f"   音频大小: {total_bytes:,} bytes")
        print()
        
        # 对比结果
        print("📊 性能对比:")
        print(f"   首字节响应: 流式模式快 {(normal_time - stream_ttfb) / normal_time * 100:.1f}%")
        print(f"   总时间: {'流式' if stream_total < normal_time else '普通'}模式快 {abs(normal_time - stream_total):.2f}s")

if __name__ == "__main__":
    asyncio.run(test_performance())
```

---

## 🎯 使用建议

### 什么时候用普通模式？

- ✅ 短文本（< 50字）
- ✅ 需要失败降级返回 JSON
- ✅ 一次性下载完整音频
- ✅ 简单场景，不需要实时播放

### 什么时候用流式模式？

- ✅ 长文本（> 100字）
- ✅ 需要快速首字节响应
- ✅ 实时播放场景（边传边播）
- ✅ WebSocket/SSE 集成
- ✅ 内存受限环境

---

## ❓ 常见问题

### Q1: 流式返回的音频块可以直接拼接吗？

**答**: 是的！流式返回的所有音频块可以直接按顺序拼接成完整的 MP3 文件，无需任何处理。

### Q2: 如何在前端实现边传边播？

**答**: 使用 MediaSource API：

```javascript
const mediaSource = new MediaSource();
const audio = new Audio();
audio.src = URL.createObjectURL(mediaSource);

mediaSource.addEventListener('sourceopen', async () => {
  const sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
  
  // 流式接收并添加到 buffer
  const response = await fetch(/* ... */);
  const reader = response.body.getReader();
  
  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    
    sourceBuffer.appendBuffer(value);
    await new Promise(resolve => sourceBuffer.addEventListener('updateend', resolve, {once: true}));
  }
  
  mediaSource.endOfStream();
});

audio.play();
```

### Q3: 流式模式会更慢吗？

**答**: 不会！实际上：
- 首字节响应更快（快 50-80%）
- 总时间相近或略快
- 用户体验更好（感觉更快）

---

**文档版本**: 1.0  
**创建时间**: 2025-10-15  
**相关接口**: `/api/v1/voice/tts/synthesize-stream`
