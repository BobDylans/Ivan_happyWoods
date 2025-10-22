"""
Conversation API Routes

智能对话接口，支持文本/语音输入，文本/语音输出。
"""

import json
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from services.conversation_service import (
    get_conversation_service,
    ConversationService,
    InputMode,
    OutputMode
)


logger = logging.getLogger(__name__)


# 自定义 JSON 编码器处理 datetime 对象
class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# 创建路由
conversation_router = APIRouter(prefix="/conversation", tags=["Conversation"])


# 请求/响应模型
class ConversationRequest(BaseModel):
    """对话请求（纯文本输入）"""
    text: str = Field(..., description="用户输入文本")
    output_mode: str = Field(default="text", description="输出模式: text, audio, both")
    voice: str = Field(default="x5_lingxiaoxuan_flow", description="TTS发音人")
    speed: int = Field(default=50, ge=0, le=100, description="语速")
    volume: int = Field(default=50, ge=0, le=100, description="音量")
    pitch: int = Field(default=50, ge=0, le=100, description="音调")
    session_id: Optional[str] = Field(default=None, description="会话ID（多轮对话）")
    user_id: Optional[str] = Field(default=None, description="用户ID")


class ConversationResponse(BaseModel):
    """对话响应"""
    success: bool = Field(..., description="是否成功")
    session_id: str = Field(..., description="会话ID")
    user_input: str = Field(..., description="用户输入")
    agent_response: str = Field(..., description="智能体回复")
    output_mode: str = Field(..., description="输出模式")
    input_metadata: Optional[dict] = Field(default=None, description="输入元数据")
    agent_metadata: Optional[dict] = Field(default=None, description="智能体元数据")
    audio_size: Optional[int] = Field(default=None, description="音频大小（字节）")
    voice: Optional[str] = Field(default=None, description="使用的发音人")
    error: Optional[str] = Field(default=None, description="错误信息")
    timestamp: str = Field(..., description="时间戳")


# 依赖注入
def get_conv_service() -> ConversationService:
    """获取对话服务实例"""
    service = get_conversation_service()
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="对话服务未初始化，请检查服务器配置"
        )
    return service


@conversation_router.post(
    "/message",
    response_model=ConversationResponse,
    summary="发送对话消息（文本输入）",
    description="发送文本消息给智能体，支持文本或语音回复"
)
async def send_text_message(
    request: ConversationRequest,
    service: ConversationService = Depends(get_conv_service),
    fastapi_request: Request = None  # ✅ 添加 Request 依赖
) -> ConversationResponse:
    """
    文本输入对话接口
    
    **输入**: 文本
    **输出**: 可选文本/语音/两者
    
    **示例 1 - 文本对话**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/conversation/message" \\
         -H "Content-Type: application/json" \\
         -H "X-API-Key: dev-test-key-123" \\
         -d '{
           "text": "你好，请介绍一下你自己",
           "output_mode": "text"
         }'
    ```
    
    **示例 2 - 文本输入，语音回复（使用流式端点）**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/conversation/message-stream" \\
         -H "Content-Type: application/json" \\
         -H "X-API-Key: dev-test-key-123" \\
         -d '{
           "text": "给我讲个笑话",
           "output_mode": "audio",
           "voice": "x5_lingxiaoxuan_flow"
         }' \\
         --output joke.mp3
    ```
    
    **示例 3 - 多轮对话**:
    ```bash
    # 第一轮
    curl -X POST "http://localhost:8000/api/v1/conversation/message" \\
         -H "Content-Type: application/json" \\
         -H "X-API-Key: dev-test-key-123" \\
         -d '{"text": "我叫小明"}' | jq -r '.session_id' > session.txt
    
    # 第二轮（使用相同 session_id）
    curl -X POST "http://localhost:8000/api/v1/conversation/message" \\
         -H "Content-Type: application/json" \\
         -H "X-API-Key: dev-test-key-123" \\
         -d "{
           \\"text\\": \\"你还记得我叫什么名字吗？\\",
           \\"session_id\\": \\"$(cat session.txt)\\"
         }"
    ```
    
    **响应示例**:
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
    """
    try:
        # 验证输出模式
        try:
            output_mode = OutputMode(request.output_mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的输出模式: {request.output_mode}。支持: text, audio, both"
            )
        
        # 对于音频输出，建议使用流式端点
        if output_mode == OutputMode.AUDIO:
            raise HTTPException(
                status_code=400,
                detail="音频输出请使用流式端点: POST /api/v1/conversation/message-stream"
            )
        
        # 处理对话
        result = await service.process_conversation(
            text=request.text,
            input_mode=InputMode.TEXT,
            output_mode=output_mode,
            voice=request.voice,
            speed=request.speed,
            volume=request.volume,
            pitch=request.pitch,
            session_id=request.session_id,
            user_id=request.user_id,
            session_manager=getattr(fastapi_request.app.state, 'session_manager', None)  # ✅ 传递 session_manager
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "处理失败"))
        
        return ConversationResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"对话处理失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"对话处理失败: {str(e)}")


@conversation_router.post(
    "/message-audio",
    response_model=ConversationResponse,
    summary="发送对话消息（语音输入）",
    description="上传语音消息给智能体，支持文本或语音回复"
)
async def send_audio_message(
    audio: UploadFile = File(..., description="音频文件"),
    output_mode: str = Form(default="text", description="输出模式: text, audio, both"),
    voice: str = Form(default="x5_lingxiaoxuan_flow", description="TTS发音人"),
    speed: int = Form(default=50, ge=0, le=100, description="语速"),
    volume: int = Form(default=50, ge=0, le=100, description="音量"),
    pitch: int = Form(default=50, ge=0, le=100, description="音调"),
    session_id: Optional[str] = Form(default=None, description="会话ID"),
    user_id: Optional[str] = Form(default=None, description="用户ID"),
    service: ConversationService = Depends(get_conv_service),
    fastapi_request: Request = None  # ✅ 添加 Request 依赖
) -> ConversationResponse:
    """
    语音输入对话接口
    
    **输入**: 语音文件（自动识别）
    **输出**: 可选文本/语音/两者
    
    **示例 1 - 语音输入，文本回复**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/conversation/message-audio" \\
         -H "X-API-Key: dev-test-key-123" \\
         -F "audio=@question.mp3" \\
         -F "output_mode=text"
    ```
    
    **示例 2 - 语音输入，语音回复（使用流式端点）**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/conversation/message-audio-stream" \\
         -H "X-API-Key: dev-test-key-123" \\
         -F "audio=@question.wav" \\
         -F "output_mode=audio" \\
         -F "voice=x5_lingxiaoxuan_flow" \\
         --output response.mp3
    ```
    
    **示例 3 - 完整语音对话（Python）**:
    ```python
    import requests
    
    # 录制或准备音频文件
    audio_file = "user_question.mp3"
    
    # 发送语音，获取语音回复
    with open(audio_file, "rb") as f:
        response = requests.post(
            "http://localhost:8000/api/v1/conversation/message-audio-stream",
            files={"audio": f},
            data={
                "output_mode": "audio",
                "voice": "x5_lingxiaoxuan_flow",
                "session_id": "my_session_123"
            },
            headers={"X-API-Key": "dev-test-key-123"},
            stream=True
        )
    
    # 保存语音回复
    with open("agent_response.mp3", "wb") as f:
        for chunk in response.iter_content(chunk_size=4096):
            f.write(chunk)
    
    # 播放音频...
    ```
    
    **响应示例**:
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
        },
        "timestamp": "2025-10-15T10:30:00"
    }
    ```
    """
    try:
        # 验证输出模式
        try:
            output_mode_enum = OutputMode(output_mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的输出模式: {output_mode}。支持: text, audio, both"
            )
        
        # 对于音频输出，建议使用流式端点
        if output_mode_enum == OutputMode.AUDIO:
            raise HTTPException(
                status_code=400,
                detail="音频输出请使用流式端点: POST /api/v1/conversation/message-audio-stream"
            )
        
        # 读取音频数据
        audio_data = await audio.read()
        
        if not audio_data:
            raise HTTPException(status_code=400, detail="音频文件为空")
        
        # 处理对话
        result = await service.process_conversation(
            audio_data=audio_data,
            audio_filename=audio.filename,
            input_mode=InputMode.AUDIO,
            output_mode=output_mode_enum,
            voice=voice,
            speed=speed,
            volume=volume,
            pitch=pitch,
            session_id=session_id,
            user_id=user_id,
            session_manager=getattr(fastapi_request.app.state, 'session_manager', None)  # ✅ 传递 session_manager
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "处理失败"))
        
        return ConversationResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"语音对话处理失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"语音对话处理失败: {str(e)}")


@conversation_router.post(
    "/message-stream",
    response_class=StreamingResponse,
    summary="发送对话消息（文本输入，流式语音输出）",
    description="发送文本消息，以流式方式接收语音回复"
)
async def send_text_message_stream(
    request: ConversationRequest,
    service: ConversationService = Depends(get_conv_service),
    fastapi_request: Request = None  # ✅ 添加 Request 依赖
):
    """
    文本输入，流式语音输出
    
    **适用场景**:
    - 文本输入，需要实时语音回复
    - 长文本回复需要边生成边播放
    - 降低首字节响应时间
    
    **示例**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/conversation/message-stream" \\
         -H "Content-Type: application/json" \\
         -H "X-API-Key: dev-test-key-123" \\
         -d '{
           "text": "给我讲一个关于人工智能的故事",
           "output_mode": "audio",
           "voice": "x5_lingxiaoxuan_flow",
           "speed": 50
         }' \\
         --output story.mp3
    ```
    
    **响应**:
    - Content-Type: audio/mpeg
    - Transfer-Encoding: chunked
    - 流式返回音频数据
    """
    try:
        # 验证输出模式（流式只支持 audio）
        try:
            output_mode = OutputMode(request.output_mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的输出模式: {request.output_mode}"
            )
        
        if output_mode != OutputMode.AUDIO:
            raise HTTPException(
                status_code=400,
                detail="流式端点仅支持 output_mode=audio"
            )
        
        # 1. 处理输入（文本）
        user_input, input_metadata = await service.process_input(
            text=request.text,
            input_mode=InputMode.TEXT
        )
        
        # 2. 获取智能体回复
        agent_response, session_id, agent_metadata = await service.get_agent_response(
            user_input=user_input,
            session_id=request.session_id,
            user_id=request.user_id,
            session_manager=getattr(fastapi_request.app.state, 'session_manager', None)  # ✅ 传递 session_manager
        )
        
        logger.info(f"流式输出: session={session_id}, response={agent_response[:100]}...")
        
        # 3. 流式生成音频
        async def audio_generator():
            """生成音频流"""
            try:
                async for chunk in service.generate_output_audio_stream(
                    response_text=agent_response,
                    voice=request.voice,
                    speed=request.speed,
                    volume=request.volume,
                    pitch=request.pitch
                ):
                    yield chunk
            except Exception as e:
                logger.error(f"流式音频生成失败: {e}")
                raise
        
        # 返回流式响应
        # 对中文进行 URL 编码以避免 HTTP 头部编码错误
        from urllib.parse import quote
        user_input_encoded = quote(user_input[:100])
        
        return StreamingResponse(
            audio_generator(),
            media_type="audio/mpeg",
            headers={
                "X-Session-Id": session_id,
                "X-User-Input": user_input_encoded,
                "X-Voice": request.voice,
                "Content-Disposition": f"attachment; filename=response_{session_id}.mp3"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式对话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"流式对话失败: {str(e)}")


@conversation_router.post(
    "/message-audio-stream",
    response_class=StreamingResponse,
    summary="发送对话消息（语音输入，流式语音输出）",
    description="上传语音消息，以流式方式接收语音回复（完整语音对话）"
)
async def send_audio_message_stream(
    audio: UploadFile = File(..., description="音频文件"),
    voice: str = Form(default="x5_lingxiaoxuan_flow", description="TTS发音人"),
    speed: int = Form(default=50, description="语速"),
    volume: int = Form(default=50, description="音量"),
    pitch: int = Form(default=50, description="音调"),
    session_id: Optional[str] = Form(default=None, description="会话ID"),
    user_id: Optional[str] = Form(default=None, description="用户ID"),
    service: ConversationService = Depends(get_conv_service),
    fastapi_request: Request = None  # ✅ 添加 Request 依赖
):
    """
    完整的语音对话（语音输入 → 语音输出）
    
    **流程**:
    1. 上传语音文件
    2. 自动语音识别（STT）
    3. 智能体处理
    4. 流式语音合成（TTS）
    5. 返回语音回复
    
    **适用场景**:
    - 完整的语音交互体验
    - 语音助手应用
    - 车载语音系统
    - 智能音箱对话
    
    **示例 1 - 完整语音对话**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/conversation/message-audio-stream" \\
         -H "X-API-Key: dev-test-key-123" \\
         -F "audio=@my_question.mp3" \\
         -F "voice=x5_lingxiaoxuan_flow" \\
         -F "speed=50" \\
         --output agent_reply.mp3
    ```
    
    **示例 2 - 持续对话（Python）**:
    ```python
    import requests
    from pathlib import Path
    
    session_id = None
    
    def voice_chat(audio_file: str):
        global session_id
        
        with open(audio_file, "rb") as f:
            data = {"voice": "x5_lingxiaoxuan_flow"}
            if session_id:
                data["session_id"] = session_id
            
            response = requests.post(
                "http://localhost:8000/api/v1/conversation/message-audio-stream",
                files={"audio": f},
                data=data,
                headers={"X-API-Key": "dev-test-key-123"},
                stream=True
            )
            
            # 获取会话ID
            session_id = response.headers.get("X-Session-Id")
            
            # 保存回复
            output_file = f"reply_{Path(audio_file).stem}.mp3"
            with open(output_file, "wb") as out:
                for chunk in response.iter_content(chunk_size=4096):
                    out.write(chunk)
            
            print(f"回复已保存: {output_file}")
            print(f"会话ID: {session_id}")
            return output_file
    
    # 第一轮对话
    voice_chat("question1.mp3")
    
    # 第二轮对话（使用相同session_id）
    voice_chat("question2.mp3")
    ```
    
    **响应**:
    - Content-Type: audio/mpeg
    - X-Session-Id: 会话ID
    - X-User-Input: 识别的用户输入文本（截断）
    - X-Voice: 使用的发音人
    - 流式返回音频数据
    """
    try:
        # 读取音频数据
        audio_data = await audio.read()
        
        if not audio_data:
            raise HTTPException(status_code=400, detail="音频文件为空")
        
        # 1. 处理输入（语音 → 文本）
        user_input, input_metadata = await service.process_input(
            audio_data=audio_data,
            audio_filename=audio.filename,
            input_mode=InputMode.AUDIO
        )
        
        logger.info(f"语音识别结果: {user_input}")
        
        # 2. 获取智能体回复
        agent_response, session_id_result, agent_metadata = await service.get_agent_response(
            user_input=user_input,
            session_id=session_id,
            user_id=user_id,
            session_manager=getattr(fastapi_request.app.state, 'session_manager', None)  # ✅ 传递 session_manager
        )
        
        logger.info(f"智能体回复: {agent_response[:100]}...")
        
        # 3. 流式生成音频
        async def audio_generator():
            """生成音频流"""
            try:
                async for chunk in service.generate_output_audio_stream(
                    response_text=agent_response,
                    voice=voice,
                    speed=speed,
                    volume=volume,
                    pitch=pitch
                ):
                    yield chunk
            except Exception as e:
                logger.error(f"流式音频生成失败: {e}")
                raise
        
        # 返回流式响应
        # 对中文进行 URL 编码以避免 HTTP 头部编码错误
        from urllib.parse import quote
        user_input_encoded = quote(user_input[:100])
        
        return StreamingResponse(
            audio_generator(),
            media_type="audio/mpeg",
            headers={
                "X-Session-Id": session_id_result,
                "X-User-Input": user_input_encoded,
                "X-Voice": voice,
                "X-Audio-Format": input_metadata.get("audio_format", "unknown"),
                "Content-Disposition": f"attachment; filename=response_{session_id_result}.mp3"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"语音对话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"语音对话失败: {str(e)}")


@conversation_router.get(
    "/status",
    summary="对话服务状态",
    description="检查对话服务的可用性"
)
async def get_conversation_status() -> dict:
    """
    获取对话服务状态
    
    **响应示例**:
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
    """
    try:
        service = get_conversation_service()
        
        if service is None:
            return {
                "service": "conversation",
                "available": False,
                "error": "服务未初始化"
            }
        
        # 检查各组件状态
        components = {
            "stt": service.stt_service is not None,
            "agent": service.agent is not None,
            "tts": service.tts_service is not None
        }
        
        available = all(components.values())
        
        return {
            "service": "conversation",
            "available": available,
            "components": components,
            "error": None if available else "部分组件不可用"
        }
    
    except Exception as e:
        logger.error(f"检查服务状态失败: {e}")
        return {
            "service": "conversation",
            "available": False,
            "error": str(e)
        }
