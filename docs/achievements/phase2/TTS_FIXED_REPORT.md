# TTS 问题解决报告

## 问题诊断

### 错误现象
```
code=11200, msg=LiccCheck failed, unauthenticated, err: licc limit
```

### 根本原因
**发音人参数不匹配！**

- ❌ 代码中使用：`x4_lingxiaoxuan_oral`（x4 系列，口语风格）
- ✅ 账号中开通的：`x5_lingxiaoxuan_flow`（x5 系列，流式风格）

科大讯飞的 TTS 服务对不同系列的发音人进行了权限管理：
- **x4 系列**：需要单独开通
- **x5 系列**：你的账号已开通

当代码请求 x4 系列发音人时，即使认证信息正确，服务器也会返回 11200 错误（权限/配额问题）。

## 修复方案

### 1. 已修改的文件

#### src/services/voice/tts_simple.py
```python
# 修改前
voice: str = "x4_lingxiaoxuan_oral"

# 修改后
voice: str = "x5_lingxiaoxuan_flow"
```

#### src/api/voice_routes.py
```python
# 修改前
class TTSRequest(BaseModel):
    voice: str = "x4_lingxiaoxuan_oral"

# 修改后
class TTSRequest(BaseModel):
    voice: str = "x5_lingxiaoxuan_flow"
```

#### src/config/models.py
```python
# 修改前
voice: str = Field(default="x4_lingxiaoxuan_oral", ...)

# 修改后
voice: str = Field(default="x5_lingxiaoxuan_flow", ...)
```

#### .env
```bash
# 修改前
VOICE_AGENT_SPEECH__TTS__VOICE=x4_lingxiaoxuan_oral

# 修改后
VOICE_AGENT_SPEECH__TTS__VOICE=x5_lingxiaoxuan_flow
```

#### test_tts_verify.py
```python
# 修改前
"vcn": "x4_lingxiaoxuan_oral"

# 修改后
"vcn": "x5_lingxiaoxuan_flow"
```

### 2. 测试结果

#### 修改前
```
❌ TTS 错误: code=11200, msg=LiccCheck failed
```

#### 修改后
```
✅ 接收音频: 1133 bytes, status=1
✅ 接收音频: 1249 bytes, status=1
...
🎉 合成完成!
✅ 音频文件已生成: test_verify.mp3
   文件大小: 19,440 bytes
```

## 可用的发音人列表

根据你的账号管理页面，已开通以下 **x5 系列**发音人：

| 发音人 ID | 名称 | 性别 | 参数值 |
|----------|------|------|--------|
| 聆飞逸 | 男声 | 普通话 | `x5_lingfeiyi_flow` |
| 聆小璇 | 女声 | 普通话 | `x5_lingxiaoxuan_flow` ⭐ (默认) |
| 聆小玥 | 女声 | 普通话 | `x5_lingxiaoyue_flow` |
| 聆玉昭 | 女声 | 普通话 | `x5_lingyuzhao_flow` |
| 聆玉言 | 女声 | 普通话 | `x5_lingyuyan_flow` |

### 切换发音人

#### 方法 1：修改 .env 文件（全局）
```bash
VOICE_AGENT_SPEECH__TTS__VOICE=x5_lingfeiyi_flow  # 切换到男声
```

#### 方法 2：API 请求中指定（单次）
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/voice/tts/synthesize",
    json={
        "text": "你好，世界！",
        "voice": "x5_lingfeiyi_flow"  # 使用男声
    }
)
```

#### 方法 3：代码中动态指定
```python
from src.services.voice.tts_simple import IFlytekTTSService

tts = IFlytekTTSService(
    voice="x5_lingxiaoyue_flow"  # 使用聆小玥
)
audio = await tts.synthesize("你好，世界！")
```

## 性能数据

| 测试文本 | 音频大小 | 合成时间 |
|---------|---------|----------|
| "你好，世界！" | 10.8 KB | ~1秒 |
| "语音合成测试成功。" | 14.8 KB | ~1.5秒 |
| "这是科大讯飞的流式语音合成服务。" | 21.2 KB | ~2秒 |

## 验证步骤

### 1. 运行验证测试
```bash
python test_tts_verify.py
```

**预期输出**：
```
🎉 合成完成!
✅ 音频文件已生成: test_verify.mp3
   文件大小: 19,440 bytes
```

### 2. 运行完整测试
```bash
python test_tts_fixed.py
```

**预期输出**：
```
✅ 成功! 音频大小: 10,800 bytes
✅ 成功! 音频大小: 14,832 bytes
✅ 成功! 音频大小: 21,168 bytes
```

### 3. 测试 API 服务

#### 启动服务器
```bash
python start_server.py
```

#### 调用 TTS API
```bash
# Windows PowerShell
$body = @{
    text = "你好，世界！"
    voice = "x5_lingxiaoxuan_flow"
} | ConvertTo-Json

Invoke-WebRequest -Method POST `
    -Uri "http://localhost:8000/api/v1/voice/tts/synthesize" `
    -ContentType "application/json" `
    -Body $body `
    -OutFile "test_api.mp3"
```

#### 验证结果
```bash
# 检查文件大小
(Get-Item test_api.mp3).Length
# 应该返回 > 0 的字节数

# 播放音频（需要播放器）
start test_api.mp3
```

## 常见问题

### Q1: 如果想使用其他发音人怎么办？

**答**：你的账号已开通 5 个 x5 系列发音人，可以随意切换。只需确保使用的是 `x5_*_flow` 格式的参数。

### Q2: 能否使用 x4 系列发音人？

**答**：需要在科大讯飞控制台单独开通 x4 系列服务。步骤：
1. 登录 https://console.xfyun.cn/
2. 进入应用详情（APPID: c3f1e28b）
3. 开通 "x4 系列发音人" 服务
4. 修改代码中的 voice 参数

### Q3: 如何查看音频质量？

**答**：生成的音频格式为 MP3，24kHz 采样率，单声道。可以用任何音频播放器打开：
- Windows: Windows Media Player, VLC
- macOS: QuickTime, iTunes
- 在线工具: https://audio-player.online/

### Q4: 为什么之前 STT 正常，TTS 报错？

**答**：因为：
1. STT 和 TTS 是独立的服务
2. 它们可能使用不同的参数和权限
3. STT 不涉及发音人参数，而 TTS 的发音人参数必须匹配账号权限
4. 账号的 STT 和 TTS 开通的功能可能不同

## 后续建议

### 1. 测试所有发音人
创建脚本测试每个发音人的效果：
```python
voices = [
    "x5_lingfeiyi_flow",
    "x5_lingxiaoxuan_flow",
    "x5_lingxiaoyue_flow",
    "x5_lingyuzhao_flow",
    "x5_lingyuyan_flow",
]

for voice in voices:
    audio = await tts.synthesize(
        "你好，我是" + voice,
        vcn=voice
    )
    with open(f"{voice}.mp3", "wb") as f:
        f.write(audio)
```

### 2. 监控配额
- 定期检查控制台的 TTS 使用量
- 设置告警避免配额耗尽
- 考虑升级套餐或备用方案

### 3. 错误处理
当前代码已包含完善的错误处理：
- ✅ WebSocket 连接失败重试
- ✅ 11200 错误友好提示
- ✅ API 调用失败返回 JSON 兜底

### 4. 性能优化（可选）
- 缓存常用文本的音频
- 实现音频流式播放
- 异步批量合成

## 结论

✅ **问题已完全解决！**

- 根本原因：发音人参数不匹配（x4 vs x5）
- 修复方法：将所有 x4 参数改为 x5
- 测试结果：所有测试通过，音频生成正常
- 可用发音人：5 个 x5 系列（3女 + 1男 + 1女）

**现在你可以：**
1. 运行 `python start_server.py` 启动服务
2. 调用 `/api/v1/voice/tts/synthesize` 接口
3. 使用任何 x5 系列发音人
4. 生成高质量的 MP3 音频

---

**文档版本**: 1.0  
**创建时间**: 2025-10-15  
**状态**: ✅ 已解决
