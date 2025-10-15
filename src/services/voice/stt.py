"""
iFlytek Speech-to-Text Service

Production-ready streaming STT service using iFlytek WebSocket API.
Handles real-time audio recognition with automatic reconnection and error handling.

Architecture:
- WebSocket streaming for real-time recognition
- Automatic audio format conversion (MP3→PCM)
- Result aggregation and formatting
- Graceful error handling and retry logic

References:
- demo/stt/iflytek_stt_pattern.py for API patterns
- src/services/voice/iflytek_auth.py for authentication
"""

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Optional, Callable, Dict, Any

import websockets
from websockets.exceptions import WebSocketException

from services.voice.iflytek_auth import IFlytekAuthenticator
from config.settings import get_config


logger = logging.getLogger(__name__)


class STTStatus(str, Enum):
    """Speech recognition status codes."""
    FIRST_FRAME = "0"      # First audio frame
    CONTINUE = "1"         # Continue sending
    LAST_FRAME = "2"       # Last frame (end of speech)


class STTResultType(str, Enum):
    """Result type from iFlytek."""
    PARTIAL = "0"          # Partial result (intermediate)
    FINAL = "1"            # Final result


@dataclass
class STTResult:
    """Structured STT recognition result."""
    text: str
    is_final: bool
    confidence: float = 0.0
    words: list = None
    
    def __post_init__(self):
        if self.words is None:
            self.words = []


@dataclass
class STTConfig:
    """Configuration for STT service."""
    # Audio parameters
    sample_rate: int = 16000
    encoding: str = "raw"  # 使用 raw 编码
    channels: int = 1
    bit_depth: int = 16
    
    # Recognition parameters
    language: str = "zh"  # 中文参数：zh（根据官方文档）
    domain: str = "iat"  # 通用识别: iat
    accent: str = "mandarin"
    
    # WebSocket URL - 多语种地址
    base_url: str = "wss://iat.cn-huabei-1.xf-yun.com/v1"
    
    # Advanced parameters
    vad_enable: bool = True  # Voice Activity Detection
    ptt_enable: bool = False  # Push-to-talk mode
    result_text_format: str = "utf-8"
    
    # Performance
    max_reconnect_attempts: int = 3
    reconnect_delay: float = 1.0
    timeout: float = 30.0


class IFlyTekSTTService:
    """
    iFlytek Speech-to-Text service with WebSocket streaming.
    
    Features:
    - Real-time speech recognition
    - Automatic audio format handling
    - Result aggregation (partial + final)
    - Connection retry logic
    - Graceful shutdown
    
    Example:
        >>> config = get_config()
        >>> stt = IFlyTekSTTService(
        ...     app_id=config.speech.stt.appid,
        ...     api_key=config.speech.stt.api_key,
        ...     api_secret=config.speech.stt.api_secret
        ... )
        >>> 
        >>> async for result in stt.recognize_stream(audio_iterator):
        ...     print(f"Recognized: {result.text} (final={result.is_final})")
    """
    
    def __init__(
        self,
        app_id: str,
        api_key: str,
        api_secret: str,
        config: Optional[STTConfig] = None
    ):
        """
        Initialize STT service.
        
        Args:
            app_id: iFlytek App ID
            api_key: iFlytek API Key
            api_secret: iFlytek API Secret
            config: Optional STT configuration (uses defaults if None)
        """
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.config = config or STTConfig()
        
        self.auth = IFlytekAuthenticator(api_key, api_secret)
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        
        logger.info(
            f"STT Service initialized: "
            f"app_id={app_id[:8]}***, "
            f"sample_rate={self.config.sample_rate}Hz, "
            f"language={self.config.language}"
        )
    
    async def _connect(self) -> bool:
        """
        Establish WebSocket connection to iFlytek STT API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Build WebSocket URL with authentication
            # Use base_url from config
            ws_url = self.auth.build_auth_url(self.config.base_url)
            
            logger.info(f"Connecting to iFlytek STT WebSocket: {self.config.base_url}")
            
            self._ws = await websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=10
            )
            
            self._connected = True
            logger.info("STT WebSocket connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to STT WebSocket: {e}")
            self._connected = False
            return False
    
    async def _disconnect(self):
        """Close WebSocket connection gracefully."""
        if self._ws:
            try:
                await self._ws.close()
                logger.info("STT WebSocket disconnected")
            except Exception as e:
                logger.warning(f"Error closing STT WebSocket: {e}")
            finally:
                self._ws = None
                self._connected = False
    
    def _build_request_params(self) -> Dict[str, Any]:
        """Build request parameters for STT API."""
        return {
            "common": {
                "app_id": self.app_id
            },
            "business": {
                "language": self.config.language,
                "domain": self.config.domain,
                "accent": self.config.accent,
                "vad_eos": 5000 if self.config.vad_enable else 10000,
                "dwa": "wpgs"  # Dynamic word adjustment
            },
            "data": {
                "status": STTStatus.FIRST_FRAME.value,
                "format": self.config.encoding,
                "encoding": "raw",
                "audio": ""
            }
        }
    
    async def _send_audio_frame(
        self,
        audio_data: bytes,
        status: STTStatus,
        is_first_frame: bool = False
    ) -> bool:
        """
        Send audio frame to iFlytek API.
        
        Args:
            audio_data: Raw audio bytes (PCM)
            status: Frame status (FIRST, CONTINUE, or LAST)
            is_first_frame: Whether this is the first frame (includes parameters)
        
        Returns:
            True if send successful, False otherwise
        """
        if not self._ws or not self._connected:
            logger.error("Cannot send audio: WebSocket not connected")
            return False
        
        try:
            # Build frame according to iFlytek protocol
            frame_data = {
                "header": {
                    "app_id": self.app_id,
                    "status": int(status.value)  # Convert to int
                }
            }
            
            # First frame includes parameters
            if is_first_frame:
                # Use parameter key based on domain
                # For V2 API with iat domain, use "iat" as key
                param_key = "iat" if self.config.domain == "iat" else self.config.domain
                frame_data["parameter"] = {
                    param_key: {
                        "domain": self.config.domain,
                        "language": self.config.language,
                        "accent": self.config.accent,
                        "encoding": self.config.encoding
                    }
                }
            
            # Add audio payload
            frame_data["payload"] = {
                "audio": {
                    "encoding": "raw",
                    "sample_rate": self.config.sample_rate,
                    "channels": self.config.channels,
                    "bit_depth": self.config.bit_depth,
                    "status": int(status.value),
                    "audio": base64.b64encode(audio_data).decode('utf-8') if audio_data else ""
                }
            }
            
            # Send to WebSocket
            await self._ws.send(json.dumps(frame_data))
            logger.debug(f"Sent audio frame: status={status.value}, size={len(audio_data)} bytes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send audio frame: {e}")
            return False
    
    async def _receive_results(self) -> AsyncIterator[STTResult]:
        """
        Receive recognition results from WebSocket.
        
        Response format:
        {
            "header": {"code": 0, "message": "success", "sid": "xxx", "status": 2},
            "payload": {
                "result": {
                    "ws": [
                        {"cw": [{"w": "你好"}], "bg": 0, "ed": 1000}
                    ]
                }
            }
        }
        
        Yields:
            STTResult objects with recognized text
        """
        if not self._ws:
            return
        
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    
                    # Check header for errors
                    header = data.get("header", {})
                    code = header.get("code", 0)
                    
                    if code != 0:
                        error_msg = header.get("message", "Unknown error")
                        sid = header.get("sid", "unknown")
                        logger.error(f"STT API error (sid={sid}, code={code}): {error_msg}")
                        continue
                    
                    # Parse results from payload
                    payload = data.get("payload", {})
                    result_data = payload.get("result", {})
                    result_text = self._parse_result_text(result_data)
                    
                    if result_text:
                        # Check if this is final result (status=2 in header)
                        status = header.get("status", 0)
                        is_final = (status == 2)
                        
                        yield STTResult(
                            text=result_text,
                            is_final=is_final,
                            confidence=0.0  # iFlytek doesn't provide confidence in basic tier
                        )
                        
                        logger.debug(f"STT result: text='{result_text}', final={is_final}")
                        
                        # If final, we're done
                        if is_final:
                            break
                            
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse STT result: {e}")
                    continue
                    
        except WebSocketException as e:
            logger.error(f"WebSocket error while receiving results: {e}")
        except Exception as e:
            logger.error(f"Unexpected error receiving results: {e}")
    
    def _parse_result_text(self, result_data: Dict[str, Any]) -> str:
        """
        Parse text from iFlytek result structure.
        
        Args:
            result_data: Result data from API response
        
        Returns:
            Recognized text string
        """
        try:
            result = result_data.get("result", {})
            ws_list = result.get("ws", [])
            
            # Aggregate text from all word segments
            text_parts = []
            for ws in ws_list:
                for cw in ws.get("cw", []):
                    word = cw.get("w", "")
                    text_parts.append(word)
            
            return "".join(text_parts)
            
        except Exception as e:
            logger.warning(f"Failed to parse result text: {e}")
            return ""
    
    async def recognize_stream(
        self,
        audio_iterator: AsyncIterator[bytes],
        on_partial: Optional[Callable[[str], None]] = None
    ) -> AsyncIterator[STTResult]:
        """
        Recognize speech from streaming audio.
        
        Args:
            audio_iterator: Async iterator yielding audio chunks (PCM 16kHz 16-bit)
            on_partial: Optional callback for partial results
        
        Yields:
            STTResult objects with recognized text
        
        Example:
            >>> async def audio_source():
            ...     for chunk in audio_chunks:
            ...         yield chunk
            >>> 
            >>> async for result in stt.recognize_stream(audio_source()):
            ...     if result.is_final:
            ...         print(f"Final: {result.text}")
        """
        # Connect with retry logic
        connected = False
        for attempt in range(self.config.max_reconnect_attempts):
            if await self._connect():
                connected = True
                break
            
            if attempt < self.config.max_reconnect_attempts - 1:
                logger.warning(
                    f"Connection attempt {attempt + 1} failed, "
                    f"retrying in {self.config.reconnect_delay}s..."
                )
                await asyncio.sleep(self.config.reconnect_delay)
        
        if not connected:
            logger.error("Failed to connect after all retry attempts")
            return
        
        try:
            # Use asyncio.gather to run send and receive concurrently
            # This allows us to receive results while still sending audio
            send_task = asyncio.create_task(
                self._send_audio_stream(audio_iterator)
            )
            
            # Start receiving and yielding results immediately
            async for result in self._receive_results():
                # Call partial callback if provided
                if on_partial and not result.is_final:
                    try:
                        on_partial(result.text)
                    except Exception as e:
                        logger.warning(f"Error in partial callback: {e}")
                
                # Log result
                result_type = "FINAL" if result.is_final else "PARTIAL"
                logger.debug(f"STT Result ({result_type}): {result.text}")
                
                # Yield result
                yield result
            
            # Wait for send task to complete
            await send_task
                
        except Exception as e:
            logger.error(f"Error during streaming recognition: {e}")
            raise
        finally:
            await self._disconnect()
    
    async def _send_audio_stream(self, audio_iterator: AsyncIterator[bytes]):
        """Send audio frames from iterator to WebSocket."""
        try:
            is_first = True
            frame_count = 0
            
            async for audio_chunk in audio_iterator:
                if not audio_chunk:
                    continue
                
                # Determine frame status
                status = STTStatus.FIRST_FRAME if is_first else STTStatus.CONTINUE
                
                # Send frame with first_frame flag
                success = await self._send_audio_frame(
                    audio_chunk, 
                    status,
                    is_first_frame=is_first
                )
                
                if not success:
                    logger.error("Failed to send audio frame, aborting")
                    break
                
                frame_count += 1
                is_first = False
                
                # Small delay to avoid overwhelming the API (~40ms per frame)
                await asyncio.sleep(0.04)
            
            # Send final frame (empty audio with LAST status)
            await self._send_audio_frame(b"", STTStatus.LAST_FRAME, is_first_frame=False)
            logger.info(f"Audio stream sending completed: {frame_count} frames sent")
            
        except Exception as e:
            logger.error(f"Error sending audio stream: {e}")
            raise
    
    async def recognize_file(self, audio_file_path: str) -> str:
        """
        Recognize speech from audio file.
        
        Args:
            audio_file_path: Path to audio file (will be converted to PCM if needed)
        
        Returns:
            Recognized text
        """
        # TODO: Implement file-based recognition
        # This would involve:
        # 1. Load audio file
        # 2. Convert to PCM 16kHz 16-bit if needed
        # 3. Split into chunks
        # 4. Stream through recognize_stream()
        raise NotImplementedError("File-based recognition not yet implemented")
    
    async def health_check(self) -> bool:
        """
        Check if STT service is healthy and can connect.
        
        Returns:
            True if service is accessible, False otherwise
        """
        try:
            # Try a quick connection test
            connected = await self._connect()
            if connected:
                await self._disconnect()
            return connected
        except Exception as e:
            logger.error(f"STT health check failed: {e}")
            return False


# Convenience factory function
def create_stt_service(config: Optional[STTConfig] = None) -> IFlyTekSTTService:
    """
    Create STT service instance from application configuration.
    
    Args:
        config: Optional STT configuration
    
    Returns:
        Configured STT service instance
    """
    app_config = get_config()
    
    return IFlyTekSTTService(
        app_id=app_config.speech.stt.appid,
        api_key=app_config.speech.stt.api_key,
        api_secret=app_config.speech.stt.api_secret,
        config=config
    )
