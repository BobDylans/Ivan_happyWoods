"""
Conversation Service

编排 STT → Agent → TTS 的完整对话流程，支持灵活的输入输出模式。
"""

import json
import logging
import uuid
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime
from enum import Enum

from services.voice.stt_simple import IFlytekSTTService, STTResult
from services.voice.tts_streaming import IFlytekTTSStreamingService
from services.voice.audio_converter import get_audio_converter, AudioConversionError
from agent.graph import VoiceAgent


logger = logging.getLogger(__name__)


def serialize_datetime(obj: Any) -> Any:
    """递归转换字典中的 datetime 对象为 ISO 字符串"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetime(item) for item in obj]
    return obj


class InputMode(str, Enum):
    """输入模式"""
    TEXT = "text"      # 文本输入
    AUDIO = "audio"    # 语音输入


class OutputMode(str, Enum):
    """输出模式"""
    TEXT = "text"              # 仅文本
    AUDIO = "audio"            # 仅音频（流式）
    BOTH = "both"              # 文本 + 音频


class ConversationService:
    """
    对话服务
    
    负责编排完整的对话流程：
    1. 处理输入（文本或语音 → 文本）
    2. 调用智能体获取回复
    3. 生成输出（文本或流式语音）
    """
    
    def __init__(
        self,
        agent: VoiceAgent,
        stt_service: IFlytekSTTService,
        tts_service: IFlytekTTSStreamingService
    ):
        """
        初始化对话服务
        
        Args:
            agent: LangGraph 智能体实例
            stt_service: 语音识别服务
            tts_service: 流式语音合成服务
        """
        self.agent = agent
        self.stt_service = stt_service
        self.tts_service = tts_service
        self.audio_converter = get_audio_converter()
        
        logger.info("ConversationService 初始化成功")
    
    async def process_input(
        self,
        text: Optional[str] = None,
        audio_data: Optional[bytes] = None,
        audio_filename: Optional[str] = None,
        input_mode: InputMode = InputMode.TEXT
    ) -> tuple[str, Dict[str, Any]]:
        """
        处理用户输入，统一转换为文本
        
        Args:
            text: 文本输入
            audio_data: 音频数据（二进制）
            audio_filename: 音频文件名（用于格式检测）
            input_mode: 输入模式
        
        Returns:
            (用户输入文本, 元数据)
        
        Raises:
            ValueError: 输入验证失败
        """
        metadata = {
            "input_mode": input_mode.value,
            "timestamp": datetime.now().isoformat()
        }
        
        if input_mode == InputMode.TEXT:
            # 文本输入
            if not text or not text.strip():
                raise ValueError("文本输入不能为空")
            
            logger.info(f"文本输入: {text[:100]}...")
            return text.strip(), metadata
        
        elif input_mode == InputMode.AUDIO:
            # 语音输入
            if not audio_data:
                raise ValueError("音频数据不能为空")
            
            logger.info(f"音频输入: 大小={len(audio_data)} bytes, 文件名={audio_filename}")
            
            try:
                # 1. 检测音频格式
                audio_format = self.audio_converter.detect_format(
                    audio_filename or "audio", 
                    audio_data
                )
                metadata["audio_format"] = audio_format
                
                # 2. 转换为 PCM
                pcm_data, conversion_info = self.audio_converter.convert_to_pcm(
                    audio_data, 
                    audio_format
                )
                metadata["audio_converted"] = conversion_info["converted"]
                metadata["audio_duration"] = conversion_info.get("source_duration", 0)
                
                # 3. 验证音频
                is_valid, msg = self.audio_converter.validate_audio(pcm_data)
                if not is_valid:
                    raise ValueError(f"音频验证失败: {msg}")
                
                # 4. STT 识别
                logger.info("开始语音识别...")
                stt_result: STTResult = await self.stt_service.recognize(pcm_data)
                
                if not stt_result.success:
                    raise ValueError(f"语音识别失败: {stt_result.error_message}")
                
                recognized_text = stt_result.text.strip()
                logger.info(f"语音识别成功: {recognized_text}")
                
                metadata["stt_success"] = True
                return recognized_text, metadata
            
            except AudioConversionError as e:
                logger.error(f"音频转换失败: {e}")
                raise ValueError(f"音频转换失败: {str(e)}")
            except Exception as e:
                logger.error(f"语音识别失败: {e}", exc_info=True)
                raise ValueError(f"语音识别失败: {str(e)}")
        
        else:
            raise ValueError(f"不支持的输入模式: {input_mode}")
    
    async def get_agent_response(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_manager: Optional[Any] = None
    ) -> tuple[str, str, Dict[str, Any]]:
        """
        公开方法：调用智能体获取回复
        
        Args:
            user_input: 用户输入文本
            session_id: 会话ID（用于多轮对话）
            user_id: 用户ID
            session_manager: 会话历史管理器（可选）
        
        Returns:
            (智能体回复文本, 会话ID, 元数据)
        """
        return await self._call_agent(
            user_input=user_input,
            session_id=session_id,
            user_id=user_id,
            session_manager=session_manager
        )
    
    async def _call_agent(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_manager: Optional[Any] = None
    ) -> tuple[str, str, Dict[str, Any]]:
        """
        调用智能体获取回复
        
        Args:
            user_input: 用户输入文本
            session_id: 会话ID（用于多轮对话）
            user_id: 用户ID
            session_manager: 会话历史管理器（可选）
        
        Returns:
            (智能体回复文本, 会话ID, 元数据)
        """
        # 生成会话 ID（如果没有）
        if not session_id:
            session_id = f"conv_{uuid.uuid4().hex[:12]}"
        
        logger.info(f"调用智能体: session_id={session_id}, input={user_input[:100]}...")
        
        # 🔍 获取会话历史（如果提供了 session_manager）
        external_history = None
        if session_manager:
            try:
                history = await session_manager.get_history(session_id)
                if history:
                    external_history = history
                    logger.info(f"📜 已加载 {len(history)} 条历史消息")
            except Exception as e:
                logger.warning(f"获取会话历史失败: {e}")
        
        try:
            # 调用智能体（带会话记忆）
            result = await self.agent.process_message(
                user_input=user_input,
                session_id=session_id,
                user_id=user_id or "anonymous",
                external_history=external_history  # ✅ 传递历史记录
            )
            
            # 提取回复
            agent_response = result.get("response", "")
            
            if not agent_response:
                agent_response = "抱歉，我没有理解你的问题，请重新表达。"
            
            logger.info(f"智能体回复: {agent_response[:100]}...")
            
            # 💾 保存新消息到会话历史（如果提供了 session_manager）
            if session_manager:
                try:
                    await session_manager.add_message(session_id, "user", user_input)
                    await session_manager.add_message(session_id, "assistant", agent_response)
                    logger.info("✅ 已保存对话到会话历史")
                except Exception as e:
                    logger.warning(f"保存会话历史失败: {e}")
            
            # 序列化所有 datetime 对象
            metadata = serialize_datetime({
                "session_id": session_id,
                "agent_success": result.get("success", True),
                "response_length": len(agent_response),
                "timestamp": result.get("timestamp", datetime.now().isoformat()),
                "message_count": result.get("message_count", 0),
                "agent_metadata": result.get("metadata", {})
            })
            
            return agent_response, session_id, metadata
        
        except Exception as e:
            logger.error(f"智能体调用失败: {e}", exc_info=True)
            error_response = f"抱歉，处理您的请求时出现了错误：{str(e)}"
            metadata = {
                "session_id": session_id,
                "agent_success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return error_response, session_id, metadata
    
    async def generate_output_text(
        self,
        response_text: str
    ) -> Dict[str, Any]:
        """
        生成文本输出
        
        Args:
            response_text: 智能体回复文本
        
        Returns:
            输出数据字典
        """
        return {
            "text": response_text,
            "output_mode": OutputMode.TEXT.value,
            "timestamp": datetime.now().isoformat()
        }
    
    async def generate_output_audio_stream(
        self,
        response_text: str,
        voice: str = "x5_lingxiaoxuan_flow",
        speed: int = 50,
        volume: int = 50,
        pitch: int = 50
    ) -> AsyncGenerator[bytes, None]:
        """
        生成流式音频输出
        
        Args:
            response_text: 智能体回复文本
            voice: 发音人
            speed: 语速
            volume: 音量
            pitch: 音调
        
        Yields:
            音频数据块
        """
        logger.info(f"开始流式TTS合成: 文本长度={len(response_text)}, 发音人={voice}")
        
        try:
            async for audio_chunk in self.tts_service.synthesize_stream(
                text=response_text,
                vcn=voice,
                speed=speed,
                volume=volume,
                pitch=pitch
            ):
                if audio_chunk:
                    yield audio_chunk
            
            logger.info("流式TTS合成完成")
        
        except Exception as e:
            logger.error(f"流式TTS失败: {e}", exc_info=True)
            raise ValueError(f"语音合成失败: {str(e)}")
    
    async def process_conversation(
        self,
        # 输入参数
        text: Optional[str] = None,
        audio_data: Optional[bytes] = None,
        audio_filename: Optional[str] = None,
        input_mode: InputMode = InputMode.TEXT,
        # 输出参数
        output_mode: OutputMode = OutputMode.TEXT,
        voice: str = "x5_lingxiaoxuan_flow",
        speed: int = 50,
        volume: int = 50,
        pitch: int = 50,
        # 会话参数
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_manager: Optional[Any] = None  # ✅ 添加 session_manager 参数
    ) -> Dict[str, Any]:
        """
        处理完整的对话流程（非流式）
        
        适用于 output_mode = TEXT 或 BOTH（但返回完整音频）
        
        Args:
            text: 文本输入
            audio_data: 音频输入
            audio_filename: 音频文件名
            input_mode: 输入模式
            output_mode: 输出模式
            voice: TTS发音人
            speed: TTS语速
            volume: TTS音量
            pitch: TTS音调
            session_id: 会话ID
            user_id: 用户ID
        
        Returns:
            对话结果字典
        """
        result = {
            "success": True,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # 1. 处理输入
            user_input, input_metadata = await self.process_input(
                text=text,
                audio_data=audio_data,
                audio_filename=audio_filename,
                input_mode=input_mode
            )
            result["user_input"] = user_input
            result["input_metadata"] = input_metadata
            
            # 2. 获取智能体回复
            agent_response, session_id, agent_metadata = await self._call_agent(
                user_input=user_input,
                session_id=session_id,
                user_id=user_id,
                session_manager=session_manager  # ✅ 传递 session_manager
            )
            result["agent_response"] = agent_response
            result["session_id"] = session_id
            result["agent_metadata"] = agent_metadata
            
            # 3. 生成输出
            result["output_mode"] = output_mode.value
            
            if output_mode == OutputMode.TEXT:
                # 仅文本
                result["text"] = agent_response
            
            elif output_mode == OutputMode.AUDIO:
                # 仅音频 - 这里不适合非流式，应该用流式端点
                result["error"] = "音频输出请使用流式端点 /conversation/message-stream"
                result["success"] = False
            
            elif output_mode == OutputMode.BOTH:
                # 文本 + 音频（完整音频，非流式）
                result["text"] = agent_response
                
                # 合成完整音频
                audio_chunks = []
                async for chunk in self.generate_output_audio_stream(
                    response_text=agent_response,
                    voice=voice,
                    speed=speed,
                    volume=volume,
                    pitch=pitch
                ):
                    audio_chunks.append(chunk)
                
                complete_audio = b"".join(audio_chunks)
                result["audio_data"] = complete_audio
                result["audio_size"] = len(complete_audio)
                result["voice"] = voice
            
            return result
        
        except Exception as e:
            logger.error(f"对话处理失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }


# 全局服务实例
_conversation_service: Optional[ConversationService] = None


def initialize_conversation_service(
    agent: VoiceAgent,
    stt_service: IFlytekSTTService,
    tts_service: IFlytekTTSStreamingService
) -> ConversationService:
    """
    初始化对话服务（单例）
    
    Args:
        agent: 智能体实例
        stt_service: STT服务实例
        tts_service: TTS流式服务实例
    
    Returns:
        ConversationService实例
    """
    global _conversation_service
    
    if _conversation_service is None:
        _conversation_service = ConversationService(
            agent=agent,
            stt_service=stt_service,
            tts_service=tts_service
        )
        logger.info("全局 ConversationService 已初始化")
    
    return _conversation_service


def get_conversation_service() -> Optional[ConversationService]:
    """获取全局对话服务实例"""
    return _conversation_service
