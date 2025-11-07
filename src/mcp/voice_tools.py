"""
语音交互MCP工具

将TTS/STT功能包装为MCP工具，供AI Agent使用
"""

import asyncio
import base64
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from .base import Tool, ToolParameter, ToolParameterType, ToolResult, ToolExecutionError
from services.voice.tts import IFlytekTTSStreamingService
from services.voice.stt import IFlyTekSTTService, STTConfig
from services.voice.audio_converter import get_audio_converter, AudioConversionError
from config.settings import get_config

logger = logging.getLogger(__name__)


class VoiceSynthesisTool(Tool):
    """
    语音合成工具
    
    将文本转换为语音，支持多种发音人和参数配置
    """
    
    def __init__(self):
        super().__init__()
        self._tts_service = None
        self._tts_streaming_service = None
    
    @property
    def name(self) -> str:
        return "voice_synthesis"
    
    @property
    def description(self) -> str:
        return "将文本转换为语音。支持多种发音人、语速、音量和音调调节。返回MP3格式的音频数据。"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="text",
                type=ToolParameterType.STRING,
                description="要合成的文本内容",
                required=True
            ),
            ToolParameter(
                name="voice",
                type=ToolParameterType.STRING,
                description="发音人选择",
                required=False,
                enum=[
                    "x5_lingxiaoxuan_flow",  # 聆小璇（女声，推荐）
                    "x5_lingfeiyi_flow",     # 聆飞逸（男声）
                    "x5_lingxiaoyue_flow",   # 聆小玥（女声）
                    "x5_lingyuzhao_flow",    # 聆玉昭（女声）
                    "x5_lingyuyan_flow",     # 聆玉言（女声）
                    "x4_lingxiaoxuan_oral",  # 灵小璇（女声）
                    "x4_yeting",             # 叶婷（女声）
                    "x4_lingfeizhe",         # 灵飞哲（男声）
                    "x4_aisjinger"           # 艾斯（男声）
                ],
                default="x5_lingxiaoxuan_flow"
            ),
            ToolParameter(
                name="speed",
                type=ToolParameterType.INTEGER,
                description="语速 (0-100)",
                required=False,
                default=50
            ),
            ToolParameter(
                name="volume",
                type=ToolParameterType.INTEGER,
                description="音量 (0-100)",
                required=False,
                default=50
            ),
            ToolParameter(
                name="pitch",
                type=ToolParameterType.INTEGER,
                description="音调 (0-100)",
                required=False,
                default=50
            ),
            ToolParameter(
                name="streaming",
                type=ToolParameterType.BOOLEAN,
                description="是否使用流式合成（适合长文本）",
                required=False,
                default=False
            ),
            ToolParameter(
                name="output_format",
                type=ToolParameterType.STRING,
                description="输出格式",
                required=False,
                enum=["mp3", "base64"],
                default="mp3"
            )
        ]
    
    async def execute(self, text: str, voice: str = "x5_lingxiaoxuan_flow", 
                     speed: int = 50, volume: int = 50, pitch: int = 50,
                     streaming: bool = False, output_format: str = "mp3", **kwargs) -> ToolResult:
        """执行语音合成"""
        try:
            # 参数验证
            if not text or not text.strip():
                raise ToolExecutionError("文本内容不能为空", self.name)
            
            if len(text) > 10000:
                raise ToolExecutionError(f"文本过长: {len(text)} 字符 (最大 10000)", self.name)
            
            # 参数范围检查
            speed = max(0, min(100, speed))
            volume = max(0, min(100, volume))
            pitch = max(0, min(100, pitch))
            
            logger.info(f"语音合成: 文本长度={len(text)}, 发音人={voice}, 流式={streaming}")
            
            # 获取TTS服务
            if streaming:
                if self._tts_streaming_service is None:
                    config = get_config()
                    self._tts_streaming_service = IFlytekTTSStreamingService(
                        appid=config.speech.tts.appid,
                        api_key=config.speech.tts.api_key,
                        api_secret=config.speech.tts.api_secret,
                        voice=voice,
                        speed=speed,
                        volume=volume,
                        pitch=pitch
                    )
                
                # 流式合成
                audio_chunks = []
                async for chunk in self._tts_streaming_service.synthesize_stream(
                    text=text,
                    vcn=voice,
                    speed=speed,
                    volume=volume,
                    pitch=pitch
                ):
                    audio_chunks.append(chunk)
                
                audio_data = b''.join(audio_chunks)
            else:
                if self._tts_service is None:
                    config = get_config()
                    self._tts_service = IFlytekTTSStreamingService(
                        appid=config.speech.tts.appid,
                        api_key=config.speech.tts.api_key,
                        api_secret=config.speech.tts.api_secret,
                        voice=voice,
                        speed=speed,
                        volume=volume,
                        pitch=pitch
                    )
                
                # 普通合成
                audio_data = await self._tts_service.synthesize(
                    text=text,
                    vcn=voice,
                    speed=speed,
                    volume=volume,
                    pitch=pitch
                )
            
            # 格式化输出
            if output_format == "base64":
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                result_data = {
                    "audio_base64": audio_base64,
                    "audio_size": len(audio_data),
                    "format": "mp3"
                }
            else:
                # 保存为临时文件
                temp_file = Path(f"temp_tts_{voice}.mp3")
                temp_file.write_bytes(audio_data)
                result_data = {
                    "file_path": str(temp_file),
                    "audio_size": len(audio_data),
                    "format": "mp3"
                }
            
            return ToolResult(
                success=True,
                data={
                    "text": text,
                    "voice": voice,
                    "audio_size": len(audio_data),
                    "parameters": {
                        "speed": speed,
                        "volume": volume,
                        "pitch": pitch,
                        "streaming": streaming
                    },
                    **result_data
                },
                metadata={
                    "synthesis_mode": "streaming" if streaming else "normal",
                    "text_length": len(text)
                }
            )
        
        except Exception as e:
            logger.error(f"语音合成失败: {e}")
            return ToolResult(
                success=False,
                error=f"语音合成失败: {str(e)}",
                metadata={"text_length": len(text), "voice": voice}
            )


class SpeechRecognitionTool(Tool):
    """
    语音识别工具
    
    将音频文件转换为文本，支持多种音频格式
    """
    
    def __init__(self):
        super().__init__()
        self._stt_service = None
        self._audio_converter = None
    
    @property
    def name(self) -> str:
        return "speech_recognition"
    
    @property
    def description(self) -> str:
        return "将音频文件转换为文本。支持MP3、WAV、M4A等多种音频格式，自动转换为适合识别的格式。"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="audio_data",
                type=ToolParameterType.STRING,
                description="音频文件的Base64编码数据",
                required=True
            ),
            ToolParameter(
                name="audio_format",
                type=ToolParameterType.STRING,
                description="音频格式",
                required=False,
                enum=["mp3", "wav", "m4a", "aac", "ogg", "flac", "webm", "amr"],
                default="mp3"
            ),
            ToolParameter(
                name="language",
                type=ToolParameterType.STRING,
                description="识别语言",
                required=False,
                enum=["zh_cn", "en_us", "mul_cn"],
                default="mul_cn"
            ),
            ToolParameter(
                name="domain",
                type=ToolParameterType.STRING,
                description="识别领域",
                required=False,
                enum=["iat", "slm"],
                default="slm"
            )
        ]
    
    async def execute(self, audio_data: str, audio_format: str = "mp3",
                     language: str = "mul_cn", domain: str = "slm", **kwargs) -> ToolResult:
        """执行语音识别"""
        try:
            # 解码音频数据
            try:
                audio_bytes = base64.b64decode(audio_data)
            except Exception as e:
                raise ToolExecutionError(f"音频数据解码失败: {e}", self.name)
            
            if not audio_bytes:
                raise ToolExecutionError("音频数据为空", self.name)
            
            # 检查文件大小
            max_size = 10 * 1024 * 1024  # 10MB
            if len(audio_bytes) > max_size:
                raise ToolExecutionError(f"音频文件过大: {len(audio_bytes)} bytes (最大 {max_size})", self.name)
            
            logger.info(f"语音识别: 音频大小={len(audio_bytes)} bytes, 格式={audio_format}")
            
            # 获取音频转换器
            if self._audio_converter is None:
                self._audio_converter = get_audio_converter()
            
            # 检测和转换音频格式
            detected_format = self._audio_converter.detect_format(f"audio.{audio_format}", audio_bytes)
            
            if not self._audio_converter.is_supported_format(f"audio.{audio_format}"):
                raise ToolExecutionError(f"不支持的音频格式: {audio_format}", self.name)
            
            # 转换为PCM
            try:
                pcm_data, conversion_info = self._audio_converter.convert_to_pcm(audio_bytes, detected_format)
            except AudioConversionError as e:
                raise ToolExecutionError(f"音频转换失败: {e}", self.name)
            
            # 验证PCM数据
            is_valid, validation_msg = self._audio_converter.validate_audio(pcm_data)
            if not is_valid:
                raise ToolExecutionError(f"音频验证失败: {validation_msg}", self.name)
            
            # 获取STT服务
            if self._stt_service is None:
                config = get_config()
                stt_config = STTConfig(
                    appid=config.speech.stt.appid,
                    api_key=config.speech.stt.api_key,
                    api_secret=config.speech.stt.api_secret,
                    base_url="wss://iat.cn-huabei-1.xf-yun.com/v1",
                    domain=domain,
                    language=language,
                    accent="mandarin"
                )
                self._stt_service = IFlyTekSTTService(stt_config)
            
            # 执行识别
            result = await self._stt_service.recognize(pcm_data)
            
            if result.success:
                return ToolResult(
                    success=True,
                    data={
                        "text": result.text,
                        "confidence": getattr(result, 'confidence', None),
                        "duration_seconds": conversion_info.get('source_duration'),
                        "audio_format": detected_format,
                        "converted": conversion_info['converted']
                    },
                    metadata={
                        "language": language,
                        "domain": domain,
                        "pcm_size": len(pcm_data),
                        "original_size": len(audio_bytes)
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=f"语音识别失败: {result.error_message}",
                    metadata={
                        "error_code": result.error_code,
                        "language": language,
                        "domain": domain
                    }
                )
        
        except ToolExecutionError:
            raise
        except Exception as e:
            logger.error(f"语音识别异常: {e}")
            return ToolResult(
                success=False,
                error=f"语音识别异常: {str(e)}",
                metadata={"audio_format": audio_format}
            )


class VoiceAnalysisTool(Tool):
    """
    语音分析工具
    
    分析音频文件的属性，如时长、格式、质量等
    """
    
    def __init__(self):
        super().__init__()
        self._audio_converter = None
    
    @property
    def name(self) -> str:
        return "voice_analysis"
    
    @property
    def description(self) -> str:
        return "分析音频文件的属性，包括时长、格式、采样率、声道数等信息。"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="audio_data",
                type=ToolParameterType.STRING,
                description="音频文件的Base64编码数据",
                required=True
            ),
            ToolParameter(
                name="audio_format",
                type=ToolParameterType.STRING,
                description="音频格式",
                required=False,
                enum=["mp3", "wav", "m4a", "aac", "ogg", "flac", "webm", "amr"],
                default="mp3"
            )
        ]
    
    async def execute(self, audio_data: str, audio_format: str = "mp3", **kwargs) -> ToolResult:
        """分析音频文件"""
        try:
            # 解码音频数据
            try:
                audio_bytes = base64.b64decode(audio_data)
            except Exception as e:
                raise ToolExecutionError(f"音频数据解码失败: {e}", self.name)
            
            if not audio_bytes:
                raise ToolExecutionError("音频数据为空", self.name)
            
            logger.info(f"语音分析: 音频大小={len(audio_bytes)} bytes, 格式={audio_format}")
            
            # 获取音频转换器
            if self._audio_converter is None:
                self._audio_converter = get_audio_converter()
            
            # 检测格式
            detected_format = self._audio_converter.detect_format(f"audio.{audio_format}", audio_bytes)
            
            # 获取音频信息
            try:
                conversion_info = self._audio_converter.get_audio_info(audio_bytes, detected_format)
            except Exception as e:
                logger.warning(f"无法获取详细音频信息: {e}")
                conversion_info = {
                    "source_format": detected_format,
                    "source_duration": None,
                    "converted": False
                }
            
            return ToolResult(
                success=True,
                data={
                    "file_size": len(audio_bytes),
                    "detected_format": detected_format,
                    "duration_seconds": conversion_info.get('source_duration'),
                    "sample_rate": conversion_info.get('sample_rate'),
                    "channels": conversion_info.get('channels'),
                    "bit_depth": conversion_info.get('bit_depth'),
                    "is_valid": self._audio_converter.is_supported_format(f"audio.{audio_format}")
                },
                metadata={
                    "analysis_timestamp": asyncio.get_event_loop().time(),
                    "conversion_info": conversion_info
                }
            )
        
        except ToolExecutionError:
            raise
        except Exception as e:
            logger.error(f"语音分析异常: {e}")
            return ToolResult(
                success=False,
                error=f"语音分析异常: {str(e)}",
                metadata={"audio_format": audio_format}
            )


# 工厂函数
def create_voice_tools():
    """
    创建所有语音相关工具
    
    Returns:
        List of voice tool instances
    """
    return [
        VoiceSynthesisTool(),
        SpeechRecognitionTool(),
        VoiceAnalysisTool(),
    ]
