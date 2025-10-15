"""
iFlytek TTS 服务（严格按照官方 demo 实现）

参考: demo/tts/super smart-tts.py
"""

import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import Optional

import websockets
from websockets.exceptions import WebSocketException

from config.settings import get_config
from services.voice.iflytek_auth import IFlytekAuthenticator

logger = logging.getLogger(__name__)


class IFlytekTTSService:
    """
    科大讯飞 TTS 服务（按官方 demo 实现）
    
    特点:
    - 单次合成（不分句）
    - 按官方 demo 的精确格式构建请求
    - 简化的错误处理
    """
    
    def __init__(
        self,
        appid: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        voice: str = "x5_lingxiaoxuan_flow",
        speed: int = 50,
        volume: int = 50,
        pitch: int = 50
    ):
        """
        初始化 TTS 服务
        
        Args:
            appid: iFlytek APPID
            api_key: iFlytek API Key
            api_secret: iFlytek API Secret
            voice: 发音人
            speed: 语速 (0-100)
            volume: 音量 (0-100)
            pitch: 音调 (0-100)
        """
        config = get_config()
        tts_config = config.speech.tts
        
        # 凭证（优先使用传入参数）
        self.appid = appid or tts_config.appid
        self.api_key = api_key or tts_config.api_key
        self.api_secret = api_secret or tts_config.api_secret
        
        # 语音参数
        self.voice = voice
        self.speed = speed
        self.volume = volume
        self.pitch = pitch
        
        # WebSocket URL（官方 demo 的 URL）
        self.base_url = "wss://cbm01.cn-huabei-1.xf-yun.com/v1/private/mcd9m97e6"
        
        # 创建认证器
        self.authenticator = IFlytekAuthenticator(
            api_key=self.api_key,
            api_secret=self.api_secret
        )
        
        logger.info(f"TTS 服务初始化: voice={self.voice}, appid={self.appid}")
    
    def _build_request(self, text: str) -> dict:
        """
        构建请求（严格按照官方 demo 格式）
        
        Args:
            text: 待合成文本
        
        Returns:
            请求字典
        """
        # Base64 编码文本
        text_base64 = base64.b64encode(text.encode('utf-8')).decode('utf-8')
        
        # 构建请求（完全按照官方 demo）
        request = {
            "header": {
                "app_id": self.appid,
                "status": 2  # 固定为 2
            },
            "parameter": {
                "tts": {
                    "vcn": self.voice,
                    "volume": self.volume,
                    "rhy": 0,
                    "speed": self.speed,
                    "pitch": self.pitch,
                    "bgs": 0,
                    "reg": 0,
                    "rdn": 0,
                    "audio": {
                        "encoding": "lame",
                        "sample_rate": 24000,
                        "channels": 1,
                        "bit_depth": 16,
                        "frame_size": 0
                    }
                }
            },
            "payload": {
                "text": {
                    "encoding": "utf8",
                    "compress": "raw",
                    "format": "plain",
                    "status": 2,
                    "seq": 0,
                    "text": text_base64
                }
            }
        }
        
        return request
    
    async def synthesize(self, text: str, **kwargs) -> bytes:
        """
        合成语音（单次合成）
        
        Args:
            text: 待合成文本
            **kwargs: 可选参数（vcn, speed, volume, pitch）
        
        Returns:
            MP3 音频数据
        
        Raises:
            RuntimeError: 如果合成失败
        """
        # 临时覆盖参数
        original_voice = self.voice
        original_speed = self.speed
        original_volume = self.volume
        original_pitch = self.pitch
        
        try:
            # 应用参数覆盖
            if 'vcn' in kwargs:
                self.voice = kwargs['vcn']
            if 'speed' in kwargs:
                self.speed = kwargs['speed']
            if 'volume' in kwargs:
                self.volume = kwargs['volume']
            if 'pitch' in kwargs:
                self.pitch = kwargs['pitch']
            
            logger.info(f"开始 TTS 合成: {len(text)} 字符")
            
            # 生成认证 URL
            ws_url = self.authenticator.build_auth_url(self.base_url)
            logger.debug(f"WebSocket URL: {ws_url[:100]}...")
            
            # 连接 WebSocket
            audio_chunks = []
            
            async with websockets.connect(
                ws_url,
                ping_interval=None,
                close_timeout=10
            ) as ws:
                # 构建并发送请求
                request = self._build_request(text)
                await ws.send(json.dumps(request))
                logger.debug("请求已发送")
                
                # 接收响应
                async for message in ws:
                    try:
                        data = json.loads(message)
                        
                        # 检查错误
                        code = data["header"]["code"]
                        if code != 0:
                            error_msg = data["header"].get("message", "Unknown error")
                            sid = data["header"].get("sid", "N/A")
                            logger.error(f"TTS 错误: code={code}, msg={error_msg}, sid={sid}")
                            raise RuntimeError(f"TTS 错误 {code}: {error_msg}")
                        
                        # 提取音频数据
                        if "payload" in data and "audio" in data["payload"]:
                            audio_data = data["payload"]["audio"]
                            audio_b64 = audio_data.get("audio", "")
                            status = audio_data.get("status", 0)
                            
                            if audio_b64:
                                # 解码音频
                                audio_chunk = base64.b64decode(audio_b64)
                                audio_chunks.append(audio_chunk)
                                logger.debug(f"接收音频: {len(audio_chunk)} bytes, status={status}")
                            
                            # 检查是否结束
                            if status == 2:
                                logger.info("音频接收完成")
                                break
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON 解析失败: {e}")
                        continue
                    except KeyError as e:
                        logger.error(f"响应格式错误: {e}, data={data}")
                        continue
            
            # 合并音频数据
            full_audio = b''.join(audio_chunks)
            logger.info(f"TTS 合成完成: {len(full_audio)} bytes")
            
            return full_audio
        
        except WebSocketException as e:
            logger.error(f"WebSocket 连接失败: {e}")
            raise RuntimeError(f"WebSocket 连接失败: {e}") from e
        
        except Exception as e:
            logger.error(f"TTS 合成失败: {e}")
            raise
        
        finally:
            # 恢复参数
            self.voice = original_voice
            self.speed = original_speed
            self.volume = original_volume
            self.pitch = original_pitch
    
    async def is_available(self) -> bool:
        """检查服务是否可用"""
        return bool(self.appid and self.api_key and self.api_secret)
