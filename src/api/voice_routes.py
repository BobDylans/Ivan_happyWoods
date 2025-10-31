"""
Voice API Routes

FastAPI endpoints for voice services (STT/TTS).
"""

import logging
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from services.voice.stt_simple import IFlytekSTTService, STTConfig, STTResult
from services.voice.tts_simple import IFlytekTTSService
from services.voice.tts_streaming import IFlytekTTSStreamingService
from services.voice.audio_converter import get_audio_converter, AudioConversionError
from config.settings import get_config


logger = logging.getLogger(__name__)


# 创建路由
voice_router = APIRouter(prefix="/voice", tags=["Voice"])


# 请求/响应模型
class STTResponse(BaseModel):
    """STT识别响应"""
    text: str
    success: bool
    error_code: int = 0
    error_message: str = ""
    duration_seconds: Optional[float] = None
    audio_format: Optional[str] = None  # 原始音频格式
    converted: Optional[bool] = None    # 是否进行了格式转换


class TTSRequest(BaseModel):
    """TTS 请求模型"""
    text: str
    voice: str = "x5_lingxiaoxuan_flow"
    speed: int = 50
    volume: int = 50
    pitch: int = 50
    format: str = "mp3"


class TTSResponse(BaseModel):
    """TTS合成响应（失败时返回文本）"""
    success: bool
    audio_size: Optional[int] = None  # 音频字节数
    text: Optional[str] = None        # 失败时返回原文本
    error_message: Optional[str] = None
    voice: Optional[str] = None
    format: Optional[str] = None


# STT服务实例（延迟初始化）
_stt_service: Optional[IFlytekSTTService] = None
_tts_service: Optional[IFlytekTTSService] = None
_tts_streaming_service: Optional[IFlytekTTSStreamingService] = None

# 服务实例化
def get_stt_service() -> IFlytekSTTService:
    """获取STT服务实例（单例）"""
    global _stt_service
    
    if _stt_service is None:
        import os
        
        # 直接从环境变量获取（临时方案，确保能读取到）
        appid = os.getenv("IFLYTEK_APPID", "")
        api_key = os.getenv("IFLYTEK_APIKEY", "")
        api_secret = os.getenv("IFLYTEK_APISECRET", "")
        
        logger.info(f"🔍 STT配置检查: appid={'已设置' if appid else '未设置'}, api_key={'已设置' if api_key else '未设置'}, api_secret={'已设置' if api_secret else '未设置'}")
        
        if not appid or not api_key or not api_secret:
            raise ValueError(f"iFlytek STT configuration missing: appid={bool(appid)}, api_key={bool(api_key)}, api_secret={bool(api_secret)}")
        
        stt_config = STTConfig(
            appid=appid,
            api_key=api_key,
            api_secret=api_secret,
            base_url="wss://iat.cn-huabei-1.xf-yun.com/v1",
            domain="slm",  # 或 "iat"
            language="mul_cn",
            accent="mandarin"
        )
        
        _stt_service = IFlytekSTTService(stt_config)
        logger.info("STT服务已初始化")
    
    return _stt_service


def get_tts_service() -> IFlytekTTSService:
    """获取TTS服务实例（单例）"""
    global _tts_service
    
    if _tts_service is None:
        config = get_config()
        
        _tts_service = IFlytekTTSService(
            appid=config.speech.tts.appid,
            api_key=config.speech.tts.api_key,
            api_secret=config.speech.tts.api_secret,
            voice=config.speech.tts.voice,
            speed=config.speech.tts.speed,
            volume=config.speech.tts.volume,
            pitch=config.speech.tts.pitch
        )
        logger.info("TTS服务已初始化")
    
    return _tts_service


def get_tts_streaming_service() -> IFlytekTTSStreamingService:
    """获取流式TTS服务实例（单例）"""
    global _tts_streaming_service
    
    if _tts_streaming_service is None:
        import os
        
        # 直接从环境变量获取（临时方案）
        appid = os.getenv("IFLYTEK_TTS_APPID", "")
        api_key = os.getenv("IFLYTEK_TTS_APIKEY", "")
        api_secret = os.getenv("IFLYTEK_TTS_APISECRET", "")
        
        logger.info(f"🔍 TTS配置检查: appid={'已设置' if appid else '未设置'}, api_key={'已设置' if api_key else '未设置'}, api_secret={'已设置' if api_secret else '未设置'}")
        
        if not appid or not api_key or not api_secret:
            raise ValueError(f"iFlytek TTS configuration missing: appid={bool(appid)}, api_key={bool(api_key)}, api_secret={bool(api_secret)}")
        
        _tts_streaming_service = IFlytekTTSStreamingService(
            appid=appid,
            api_key=api_key,
            api_secret=api_secret,
            voice="x4_lingxiaoxuan_oral",  # 默认音色
            speed=50,  # 默认语速
            volume=50,  # 默认音量
            pitch=50   # 默认音调
        )
        logger.info("流式TTS服务已初始化")
    
    return _tts_streaming_service

# 声明请求路径
@voice_router.post(
    "/stt/recognize",
    response_model=STTResponse,
    summary="语音识别",
    description="上传音频文件进行语音识别，返回文本结果。支持多种音频格式自动转换。"
)
async def recognize_speech(
    audio: UploadFile = File(..., description="音频文件（支持 MP3, WAV, M4A, AAC, OGG, FLAC 等格式）")
) -> STTResponse:
    """
    语音转文字接口
    
    **支持的音频格式**（自动转换为PCM）:
    - ✅ MP3
    - ✅ WAV
    - ✅ M4A (AAC)
    - ✅ AAC
    - ✅ OGG
    - ✅ FLAC
    - ✅ WEBM
    - ✅ AMR
    - ✅ PCM (原始格式，无需转换)
    
    **音频要求**:
    - 时长: < 60秒
    - 大小: < 10MB
    - 自动转换为: 16kHz, 16-bit, 单声道 PCM
    
    **示例**:
    ```bash
    # 上传 MP3 文件
    curl -X POST "http://localhost:8000/api/v1/voice/stt/recognize" \\
         -H "X-API-Key: dev-test-key-123" \\
         -F "audio=@sample.mp3"
    
    # 上传 WAV 文件
    curl -X POST "http://localhost:8000/api/v1/voice/stt/recognize" \\
         -H "X-API-Key: dev-test-key-123" \\
         -F "audio=@sample.wav"
    ```
    
    **响应示例**:
    ```json
    {
        "text": "你好，我希望你能介绍一下你自己。",
        "success": true,
        "duration_seconds": 4.48,
        "audio_format": "mp3",
        "converted": true
    }
    ```
    """
    try:
        # 1. 读取音频数据
        audio_data = await audio.read()
        
        if not audio_data:
            raise HTTPException(status_code=400, detail="音频文件为空")
        
        # 2. 检查文件大小（限制10MB）
        max_size = 10 * 1024 * 1024  # 10MB
        if len(audio_data) > max_size:
            raise HTTPException(
                status_code=400, 
                detail=f"音频文件过大: {len(audio_data)} bytes (最大 {max_size} bytes)"
            )
        
        filename = audio.filename or "unknown"
        logger.info(f"收到音频识别请求: {filename}, 大小: {len(audio_data)} bytes")
        
        # 3. 音频格式转换
        converter = get_audio_converter()
        
        # 检测格式
        audio_format = converter.detect_format(filename, audio_data)
        logger.info(f"检测到音频格式: {audio_format}")
        
        # 检查是否支持
        if not converter.is_supported_format(filename):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的音频格式: {audio_format}。支持的格式: {', '.join(converter.SUPPORTED_FORMATS)}"
            )
        
        # 转换为PCM
        try:
            pcm_data, conversion_info = converter.convert_to_pcm(audio_data, audio_format)
            
            logger.info(
                f"音频转换完成: {conversion_info['source_format']} -> PCM, "
                f"时长: {conversion_info.get('source_duration', 0):.2f}秒, "
                f"转换: {'是' if conversion_info['converted'] else '否'}"
            )
            
        except AudioConversionError as e:
            logger.error(f"音频转换失败: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"音频转换失败: {str(e)}。请确保音频格式正确且已安装 ffmpeg。"
            )
        
        # 4. 验证PCM数据
        is_valid, validation_msg = converter.validate_audio(pcm_data)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"音频验证失败: {validation_msg}")
        
        # 5. 获取STT服务
        stt_service = get_stt_service()
        
        # 6. 执行识别
        logger.info(f"开始语音识别，PCM数据大小: {len(pcm_data)} bytes")
        result: STTResult = await stt_service.recognize(pcm_data)
        
        # 7. 计算时长
        duration = conversion_info.get('source_duration') or len(pcm_data) / (16000 * 2)
        
        # 8. 返回结果
        if result.success:
            logger.info(f"识别成功: {result.text}")
            return STTResponse(
                text=result.text,
                success=True,
                duration_seconds=duration,
                audio_format=audio_format,
                converted=conversion_info['converted']
            )
        else:
            logger.error(f"识别失败: {result.error_message}")
            return STTResponse(
                text="",
                success=False,
                error_code=result.error_code,
                error_message=result.error_message,
                duration_seconds=duration,
                audio_format=audio_format,
                converted=conversion_info['converted']
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"语音识别异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}")

# 目前还没有实现，但是很快就会了
@voice_router.post(
    "/tts/synthesize",
    response_class=Response,
    summary="语音合成",
    description="将文本转换为语音（支持流式合成，失败时返回JSON文本）"
)
async def synthesize_speech(request: TTSRequest):
    """
    文字转语音接口（流式合成）
    
    **特性**:
    - ✅ 流式合成（长文本自动分句）
    - ✅ MP3 格式输出（24kHz, mono, 16-bit）
    - ✅ 可配置发音人和参数
    - ✅ 失败降级（返回JSON文本）
    
    **参数**:
    - text: 要合成的文本（自动分句处理）
    - voice: 发音人（默认: x4_lingxiaoxuan_oral）
    - speed: 语速 (0-100, 默认50)
    - volume: 音量 (0-100, 默认50)
    - pitch: 音调 (0-100, 默认50)
    - format: 音频格式 (目前仅支持 mp3)
    
    **发音人选项**:
    - x4_lingxiaoxuan_oral: 灵小璇（女声，推荐）
    - x4_yeting: 叶婷（女声）
    - x4_lingfeizhe: 灵飞哲（男声）
    - x4_aisjinger: 艾斯（男声）
    
    **示例 1 - 下载音频文件**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/voice/tts/synthesize" \\
         -H "Content-Type: application/json" \\
         -H "X-API-Key: dev-test-key-123" \\
         -d '{"text": "你好，世界！这是一段测试语音。"}' \\
         --output output.mp3
    ```
    
    **示例 2 - 自定义参数**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/voice/tts/synthesize" \\
         -H "Content-Type: application/json" \\
         -H "X-API-Key: dev-test-key-123" \\
         -d '{
           "text": "你好，我是语音助手",
           "voice": "x4_lingxiaoxuan_oral",
           "speed": 60,
           "volume": 70,
           "pitch": 55
         }' \\
         --output custom_voice.mp3
    ```
    
    **成功响应**: 
    - Content-Type: audio/mpeg
    - 二进制音频数据（MP3格式）
    
    **失败响应** (JSON):
    ```json
    {
        "success": false,
        "text": "你好，世界",
        "error_message": "WebSocket连接失败: ...",
        "voice": "x4_lingxiaoxuan_oral",
        "format": "mp3"
    }
    ```
    """
    try:
        # 1. 参数验证
        if not request.text or not request.text.strip():
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "text": request.text,
                    "error_message": "文本不能为空",
                    "voice": request.voice,
                    "format": request.format
                }
            )
        
        # 限制文本长度（5000字符）
        max_length = 5000
        if len(request.text) > max_length:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "text": request.text,
                    "error_message": f"文本过长: {len(request.text)} 字符 (最大 {max_length})",
                    "voice": request.voice,
                    "format": request.format
                }
            )
        
        logger.info(f"收到TTS合成请求: 文本长度={len(request.text)}, 发音人={request.voice}")
        
        # 2. 获取TTS服务
        tts_service = get_tts_service()
        
        # 3. 执行合成
        try:
            audio_data = await tts_service.synthesize(
                text=request.text,
                vcn=request.voice,
                speed=request.speed,
                volume=request.volume,
                pitch=request.pitch
            )
            
            # 4. 返回音频（MP3格式）
            logger.info(f"TTS合成成功: 音频大小={len(audio_data)} bytes")
            
            return Response(
                content=audio_data,
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f"attachment; filename=speech_{request.voice}.mp3",
                    "X-Audio-Size": str(len(audio_data)),
                    "X-Voice": request.voice
                }
            )
        
        except Exception as synthesis_error:
            # 5. 合成失败 - 降级返回文本
            error_message = str(synthesis_error)
            logger.error(f"TTS合成失败（降级返回文本）: {error_message}")
            
            return JSONResponse(
                status_code=200,  # 降级方案不算错误
                content={
                    "success": False,
                    "text": request.text,
                    "error_message": error_message,
                    "voice": request.voice,
                    "format": request.format
                }
            )
    
    except Exception as e:
        logger.error(f"TTS接口异常: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "text": request.text if request else "",
                "error_message": f"服务器内部错误: {str(e)}",
                "voice": request.voice if request else "unknown",
                "format": request.format if request else "mp3"
            }
        )


@voice_router.post(
    "/tts/synthesize-stream",
    response_class=StreamingResponse,
    summary="语音合成（流式）",
    description="将文本转换为语音，以流式方式实时返回音频数据"
)
async def synthesize_speech_stream(request: TTSRequest):
    """
    文字转语音接口（流式版本）
    
    **与普通版本的区别**:
    - ✅ 实时流式返回音频块（边合成边传输）
    - ✅ 适合长文本（自动分句处理）
    - ✅ 更快的首字节响应（TTFB）
    - ✅ 支持 Server-Sent Events 集成
    
    **使用场景**:
    - 长文本合成（> 100字）
    - 需要快速响应的场景
    - WebSocket/SSE 实时播放
    - 边合成边播放的应用
    
    **参数**:
    - text: 要合成的文本（会自动分句）
    - voice: 发音人（默认: x5_lingxiaoxuan_flow）
    - speed: 语速 (0-100, 默认50)
    - volume: 音量 (0-100, 默认50)
    - pitch: 音调 (0-100, 默认50)
    
    **发音人选项**（x5 系列）:
    - x5_lingxiaoxuan_flow: 聆小璇（女声，推荐）⭐
    - x5_lingfeiyi_flow: 聆飞逸（男声）
    - x5_lingxiaoyue_flow: 聆小玥（女声）
    - x5_lingyuzhao_flow: 聆玉昭（女声）
    - x5_lingyuyan_flow: 聆玉言（女声）
    
    **示例 1 - 使用 curl 下载流式音频**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/voice/tts/synthesize-stream" \\
         -H "Content-Type: application/json" \\
         -H "X-API-Key: dev-test-key-123" \\
         -d '{
           "text": "人工智能是计算机科学的一个重要分支。它致力于理解智能的实质，并生产出能以人类智能相似的方式做出反应的智能机器。",
           "voice": "x5_lingxiaoxuan_flow",
           "speed": 50
         }' \\
         --output stream_output.mp3
    ```
    
    **示例 2 - Python 流式接收**:
    ```python
    import httpx
    
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/api/v1/voice/tts/synthesize-stream",
            json={"text": "长文本...", "voice": "x5_lingxiaoxuan_flow"},
            headers={"X-API-Key": "dev-test-key-123"}
        ) as response:
            with open("stream.mp3", "wb") as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)
                    print(f"收到 {len(chunk)} 字节")
    ```
    
    **示例 3 - JavaScript fetch 流式播放**:
    ```javascript
    const response = await fetch('http://localhost:8000/api/v1/voice/tts/synthesize-stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'dev-test-key-123'
      },
      body: JSON.stringify({
        text: '你好，这是流式语音合成测试。',
        voice: 'x5_lingxiaoxuan_flow'
      })
    });
    
    const reader = response.body.getReader();
    const chunks = [];
    
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      chunks.push(value);
      console.log(`收到 ${value.length} 字节`);
    }
    
    // 合并所有块并播放
    const blob = new Blob(chunks, {type: 'audio/mpeg'});
    const audio = new Audio(URL.createObjectURL(blob));
    audio.play();
    ```
    
    **响应格式**:
    - Content-Type: audio/mpeg
    - Transfer-Encoding: chunked
    - X-Voice: 使用的发音人
    - X-Text-Length: 原始文本长度
    
    **性能对比**:
    | 文本长度 | 普通模式首字节 | 流式模式首字节 | 优势 |
    |---------|--------------|--------------|------|
    | 50字 | ~1s | ~0.5s | 快 50% |
    | 200字 | ~3s | ~0.8s | 快 73% |
    | 500字 | ~7s | ~1.2s | 快 83% |
    
    **注意事项**:
    - 流式返回的音频块可直接拼接为完整 MP3
    - 适合实时场景，如语音助手、播报系统
    - 长文本会自动分句处理，确保自然停顿
    """
    try:
        # 1. 验证文本
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="文本不能为空")
        
        # 文本长度限制（流式模式支持更长文本）
        max_length = 10000  # 流式模式支持 10000 字符
        if len(request.text) > max_length:
            raise HTTPException(
                status_code=400,
                detail=f"文本过长: {len(request.text)} 字符 (流式模式最大 {max_length})"
            )
        
        logger.info(f"收到流式TTS请求: 文本长度={len(request.text)}, 发音人={request.voice}")
        
        # 2. 获取流式TTS服务
        tts_service = get_tts_streaming_service()
        
        # 3. 创建异步生成器
        async def audio_stream_generator():
            """生成音频流"""
            try:
                # 使用流式合成方法
                async for audio_chunk in tts_service.synthesize_stream(
                    text=request.text,
                    vcn=request.voice,
                    speed=request.speed,
                    volume=request.volume,
                    pitch=request.pitch
                ):
                    if audio_chunk:
                        logger.debug(f"流式TTS: 推送音频块 {len(audio_chunk)} bytes")
                        yield audio_chunk
                
                logger.info(f"流式TTS完成: 文本={request.text[:50]}...")
            
            except Exception as e:
                logger.error(f"流式TTS生成异常: {e}", exc_info=True)
                # 流式传输中的错误无法返回 JSON，只能记录日志
                raise
        
        # 4. 返回流式响应
        return StreamingResponse(
            audio_stream_generator(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=speech_stream_{request.voice}.mp3",
                "X-Voice": request.voice,
                "X-Text-Length": str(len(request.text)),
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式TTS接口异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"流式TTS服务错误: {str(e)}"
        )


@voice_router.get(
    "/status",
    summary="语音服务状态",
    description="获取STT/TTS服务状态"
)
async def get_voice_status() -> dict:
    """
    获取语音服务状态
    
    返回STT和TTS服务的可用性状态。
    
    **响应示例**:
    ```json
    {
        "stt": {
            "available": true,
            "provider": "iflytek",
            "base_url": "wss://iat.cn-huabei-1.xf-yun.com/v1",
            "error": null
        },
        "tts": {
            "available": true,
            "provider": "iflytek",
            "voice": "x4_lingxiaoxuan_oral",
            "error": null
        }
    }
    ```
    """
    try:
        # 检查STT服务
        stt_available = False
        stt_error = None
        
        try:
            stt_service = get_stt_service()
            stt_available = await stt_service.is_available()
        except Exception as e:
            stt_error = str(e)
        
        # 检查TTS服务
        tts_available = False
        tts_error = None
        tts_voice = None
        
        try:
            tts_service = get_tts_service()
            tts_available = await tts_service.is_available()
            tts_voice = tts_service.voice
        except Exception as e:
            tts_error = str(e)
        
        return {
            "stt": {
                "available": stt_available,
                "provider": "iflytek",
                "base_url": "wss://iat.cn-huabei-1.xf-yun.com/v1",
                "error": stt_error
            },
            "tts": {
                "available": tts_available,
                "provider": "iflytek",
                "voice": tts_voice or "x4_lingxiaoxuan_oral",
                "error": tts_error
            }
        }
    
    except Exception as e:
        logger.error(f"获取语音服务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
