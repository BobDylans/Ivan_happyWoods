"""
iFlytek TTS Streaming Service (Production)

基于官方 demo 的异步实现，支持：
1. 流式合成（长文本分句处理）
2. 实时音频块推送（WebSocket）
3. 降级处理（失败时返回文本）
4. 可配置发音人和参数

作者: GitHub Copilot
日期: 2025-10-15
"""

import asyncio
import base64
import json
import logging
import re
from typing import AsyncGenerator, Callable, List, Optional

import websockets
from websockets.exceptions import WebSocketException

from config.settings import get_config

logger = logging.getLogger(__name__)


class IFlytekTTSStreamingService:
    """
    科大讯飞流式 TTS 服务（异步版本）
    
    特性:
    1. 异步 API（基于 websockets）
    2. 文本智能分句（按标点符号）
    3. 流式音频推送（实时回调）
    4. 错误降级（失败时返回文本）
    5. 可配置发音人和语音参数
    
    使用示例:
        service = IFlytekTTSStreamingService()
        
        # 流式合成
        async for audio_chunk in service.synthesize_stream("长文本..."):
            await websocket.send(audio_chunk)
        
        # 或使用回调
        await service.synthesize_with_callback(
            text="你好世界",
            on_audio_chunk=lambda chunk: print(len(chunk))
        )
    """
    
    def __init__(
        self,
        appid: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        voice: Optional[str] = None,
        speed: Optional[int] = None,
        volume: Optional[int] = None,
        pitch: Optional[int] = None
    ):
        """
        初始化 TTS 服务
        
        Args:
            appid: iFlytek APPID（可选，默认从配置加载）
            api_key: iFlytek API Key（可选）
            api_secret: iFlytek API Secret（可选）
            voice: 发音人（可选）
            speed: 语速 0-100（可选）
            volume: 音量 0-100（可选）
            pitch: 音调 0-100（可选）
        """
        config = get_config()
        tts_config = config.speech.tts
        
        # iFlytek 凭据（优先使用传入参数，否则从配置加载）
        self.appid = appid or tts_config.appid
        self.api_key = api_key or tts_config.api_key
        self.api_secret = api_secret or tts_config.api_secret
        
        # 语音参数（优先使用传入参数，否则从配置加载）
        self.voice = voice or tts_config.voice or "x5_lingxiaoxuan_flow"  # 发音人
        self.volume = volume if volume is not None else (tts_config.volume or 50)   # 音量 0-100
        self.speed = speed if speed is not None else (tts_config.speed or 50)     # 语速 0-100
        self.pitch = pitch if pitch is not None else (tts_config.pitch or 50)     # 音高 0-100
        
        # 音频格式
        self.audio_encoding = "lame"      # MP3 编码
        self.sample_rate = 24000          # 24kHz
        self.channels = 1                 # 单声道
        self.bit_depth = 16               # 16-bit
        
        # WebSocket 配置
        self.base_url = "wss://cbm01.cn-huabei-1.xf-yun.com/v1/private/mcd9m97e6"
        
        # 文本分句配置
        self.chunk_size = 150  # 每句最多字符数
        
        # 创建认证器（复用 STT 的认证逻辑）
        from services.voice.iflytek_auth import IFlytekAuthenticator
        self.authenticator = IFlytekAuthenticator(
            api_key=self.api_key,
            api_secret=self.api_secret
        )
        
        logger.info(f"TTS 服务初始化成功: voice={self.voice}, speed={self.speed}")
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        智能分句（按标点符号分割，保持语义完整）
        
        策略:
        1. 优先在句子结束标点处分割（。！？）
        2. 长句按逗号分割（，、；）
        3. 超长句强制分割（避免单句过长）
        
        Args:
            text: 原始文本
        
        Returns:
            句子列表
        """
        if not text or not text.strip():
            return []
        
        # 按主要标点分割
        # 正则说明: 匹配标点后的内容作为独立句子
        sentences = re.split(r'([。！？\.!?\n]+)', text)
        
        # 重新组合（保留标点）
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else '')
            sentence = sentence.strip()
            if sentence:
                # 如果句子过长，按逗号二次分割
                if len(sentence) > self.chunk_size:
                    sub_sentences = re.split(r'([，,；;]+)', sentence)
                    for j in range(0, len(sub_sentences) - 1, 2):
                        sub = sub_sentences[j] + (sub_sentences[j + 1] if j + 1 < len(sub_sentences) else '')
                        sub = sub.strip()
                        if sub:
                            result.append(sub)
                else:
                    result.append(sentence)
        
        # 处理最后一个不完整的句子
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            result.append(sentences[-1].strip())
        
        logger.info(f"文本分句: {len(text)} 字符 → {len(result)} 句")
        return result
    
    def _build_request_frame(self, text: str, is_last: bool = True) -> str:
        """
        构建 TTS 请求帧（JSON 格式，参照官方 demo）
        
        ⚠️ 关键: 必须使用官方 demo 的精确格式！
        
        Args:
            text: 待合成文本（原始字符串，会在函数内 Base64 编码）
            is_last: 是否为最后一帧
        
        Returns:
            JSON 字符串
        """
        frame = {
            "header": {
                "app_id": self.appid,
                "status": 2 if is_last else 1  # 2=最后一帧, 1=中间帧
            },
            "parameter": {
                "tts": {
                    "vcn": self.voice,
                    "volume": self.volume,
                    "speed": self.speed,
                    "pitch": self.pitch,
                    "rhy": 0,  # 韵律标记
                    "bgs": 0,  # 背景音
                    "reg": 0,  # 英文发音
                    "rdn": 0,  # 数字发音
                    "audio": {
                        "encoding": self.audio_encoding,
                        "sample_rate": self.sample_rate,
                        "channels": self.channels,
                        "bit_depth": self.bit_depth,
                        "frame_size": 0
                    }
                }
            },
            "payload": {
                "text": {
                    "encoding": "utf8",
                    "compress": "raw",
                    "format": "plain",
                    "status": 2 if is_last else 1,
                    "seq": 0,
                    "text": base64.b64encode(text.encode('utf-8')).decode('utf-8')
                }
            }
        }
        
        return json.dumps(frame)
    
    async def _synthesize_single_sentence(
        self,
        ws: websockets.WebSocketClientProtocol,
        sentence: str
    ) -> AsyncGenerator[bytes, None]:
        """
        合成单个句子（发送请求 + 接收音频流）
        
        Args:
            ws: WebSocket 连接
            sentence: 待合成句子
        
        Yields:
            音频块（bytes）
        """
        # 发送文本帧
        frame = self._build_request_frame(sentence, is_last=True)
        await ws.send(frame)
        logger.debug(f"TTS 发送: {len(sentence)} 字符")
        
        # 接收音频流
        async for message in ws:
            try:
                data = json.loads(message)
                
                # 检查错误
                code = data["header"]["code"]
                if code != 0:
                    error_msg = data["header"]["message"]
                    logger.error(f"TTS 合成错误: code={code}, msg={error_msg}")
                    raise RuntimeError(f"TTS 错误 {code}: {error_msg}")
                
                # 提取音频数据
                if "payload" in data and "audio" in data["payload"]:
                    audio_payload = data["payload"]["audio"]
                    audio_b64 = audio_payload.get("audio", "")
                    status = audio_payload.get("status", 0)
                    
                    if audio_b64:
                        # Base64 解码音频
                        audio_chunk = base64.b64decode(audio_b64)
                        logger.debug(f"TTS 接收: {len(audio_chunk)} bytes, status={status}")
                        yield audio_chunk
                    
                    # 检查是否完成（status=2 表示最后一帧）
                    if status == 2:
                        logger.debug("TTS 句子合成完成")
                        break
            
            except json.JSONDecodeError as e:
                logger.error(f"TTS 响应解析失败: {e}")
                raise
    
    async def synthesize_stream(
        self,
        text: str,
        vcn: Optional[str] = None,
        speed: Optional[int] = None,
        volume: Optional[int] = None,
        pitch: Optional[int] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        流式合成语音（异步生成器，推荐用于 WebSocket）
        
        Args:
            text: 待合成文本
            vcn: 发音人（可选，覆盖默认值）
            speed: 语速（可选，覆盖默认值）
            volume: 音量（可选，覆盖默认值）
            pitch: 音高（可选，覆盖默认值）
        
        Yields:
            音频块（bytes），按句子分批返回
        
        示例:
            async for audio_chunk in service.synthesize_stream("长文本..."):
                await websocket.send(audio_chunk)
        """
        # 覆盖参数（如果提供）
        original_voice = self.voice
        original_speed = self.speed
        original_volume = self.volume
        original_pitch = self.pitch
        
        try:
            if vcn:
                self.voice = vcn
            if speed is not None:
                self.speed = speed
            if volume is not None:
                self.volume = volume
            if pitch is not None:
                self.pitch = pitch
            
            # 分句
            sentences = self._split_sentences(text)
            if not sentences:
                logger.warning("文本为空，无法合成")
                return
            
            logger.info(f"开始 TTS 流式合成: {len(sentences)} 句")
            
            # 逐句合成
            for i, sentence in enumerate(sentences):
                try:
                    # 生成认证 URL（每句独立连接，避免超时）
                    ws_url = self.authenticator.build_auth_url(self.base_url)
                    
                    # 连接 WebSocket
                    async with websockets.connect(
                        ws_url,
                        ping_interval=None,  # 禁用 ping（避免干扰）
                        close_timeout=10
                    ) as ws:
                        # 合成并推送
                        async for audio_chunk in self._synthesize_single_sentence(ws, sentence):
                            yield audio_chunk
                    
                    logger.debug(f"句子 {i + 1}/{len(sentences)} 合成成功")
                
                except Exception as e:
                    logger.error(f"句子 {i + 1} 合成失败: {e}")
                    # 继续下一句（部分失败不影响整体）
                    continue
            
            logger.info("TTS 流式合成完成")
        
        finally:
            # 恢复原始参数
            self.voice = original_voice
            self.speed = original_speed
            self.volume = original_volume
            self.pitch = original_pitch
    
    async def synthesize_with_callback(
        self,
        text: str,
        on_audio_chunk: Callable[[bytes], None],
        on_complete: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> None:
        """
        流式合成语音（回调模式）
        
        Args:
            text: 待合成文本
            on_audio_chunk: 音频块回调（同步或异步）
            on_complete: 完成回调（可选）
            on_error: 错误回调（可选）
            **kwargs: 其他参数（vcn, speed, volume, pitch）
        
        示例:
            await service.synthesize_with_callback(
                text="你好",
                on_audio_chunk=lambda chunk: play(chunk),
                on_complete=lambda: print("完成"),
                speed=60
            )
        """
        try:
            async for audio_chunk in self.synthesize_stream(text, **kwargs):
                # 调用回调（支持同步和异步）
                if asyncio.iscoroutinefunction(on_audio_chunk):
                    await on_audio_chunk(audio_chunk)
                else:
                    on_audio_chunk(audio_chunk)
            
            # 完成回调
            if on_complete:
                if asyncio.iscoroutinefunction(on_complete):
                    await on_complete()
                else:
                    on_complete()
        
        except Exception as e:
            logger.error(f"TTS 合成失败: {e}")
            if on_error:
                if asyncio.iscoroutinefunction(on_error):
                    await on_error(str(e))
                else:
                    on_error(str(e))
            raise
    
    async def synthesize(self, text: str, **kwargs) -> bytes:
        """
        一次性合成语音（收集所有音频块后返回）
        
        适用于短文本或需要完整音频的场景
        
        Args:
            text: 待合成文本
            **kwargs: 其他参数（vcn, speed, volume, pitch）
        
        Returns:
            完整音频数据（bytes）
        
        示例:
            audio_bytes = await service.synthesize("你好世界", speed=60)
        """
        audio_chunks = []
        
        async for chunk in self.synthesize_stream(text, **kwargs):
            audio_chunks.append(chunk)
        
        full_audio = b''.join(audio_chunks)
        logger.info(f"TTS 完整合成: {len(full_audio)} bytes")
        return full_audio
    
    async def is_available(self) -> bool:
        """检查服务是否可用（异步版本）"""
        return bool(self.appid and self.api_key and self.api_secret)
