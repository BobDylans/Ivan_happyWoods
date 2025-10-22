"""
iFlytek Speech-to-Text Service - Simple Version (非流式)

一次性上传完整音频，等待识别结果返回。
基于官方demo代码改写为async版本。

参考: demo/stt/iflytek_stt_pattern.py (官方示例)
"""

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from typing import Optional

import websockets
from websockets.exceptions import WebSocketException

from services.voice.iflytek_auth import IFlytekAuthenticator


logger = logging.getLogger(__name__)


@dataclass
class STTConfig:
    """STT配置"""
    appid: str
    api_key: str
    api_secret: str
    
    # WebSocket地址
    base_url: str = "wss://iat.cn-huabei-1.xf-yun.com/v1"
    
    # 识别参数（参考官方demo）
    domain: str = "iat"  # slm=超大模型, iat=通用模型
    language: str = "mul_cn"  # mul_cn=多语种中文
    accent: str = "mandarin"
    
    # 音频参数
    sample_rate: int = 16000
    encoding: str = "raw"  # PCM格式


@dataclass
class STTResult:
    """识别结果"""
    text: str
    success: bool
    error_code: int = 0
    error_message: str = ""


class IFlytekSTTService:
    """iFlytek语音识别服务 - 简化版（非流式）"""
    
    def __init__(self, config: STTConfig):
        self.config = config
        # 从环境变量中获取到相关信息
        self.auth = IFlytekAuthenticator(config.api_key, config.api_secret)
    
    async def recognize(self, audio_data: bytes) -> STTResult:
        """
        识别音频（一次性上传完整音频）
        
        Args:
            audio_data: PCM音频数据 (16kHz, 16-bit, mono)
        
        Returns:
            STTResult: 识别结果
        """
        try:
            # 构建认证URL
            ws_url = self.auth.build_auth_url(self.config.base_url)
            
            logger.info(f"连接STT服务: {self.config.base_url}")
            
            # 连接WebSocket
            async with websockets.connect(
                ws_url, 
                ping_interval=None,  # 禁用ping
                close_timeout=10
            ) as ws:
                
                # 发送音频帧
                await self._send_audio_frames(ws, audio_data)
                
                # 接收所有响应，收集识别结果
                result_text = await self._receive_results(ws)
                
                return STTResult(
                    text=result_text,
                    success=True
                )
        # 进行异常处理        
        except WebSocketException as e:
            logger.error(f"WebSocket错误: {e}")
            return STTResult(
                text="",
                success=False,
                error_code=-1,
                error_message=f"连接错误: {str(e)}"
            )
        except Exception as e:
            logger.error(f"识别错误: {e}")
            return STTResult(
                text="",
                success=False,
                error_code=-1,
                error_message=str(e)
            )
    # 具体发送音频文件的方式
    async def _send_audio_frames(self, ws, audio_data: bytes):
        """发送音频帧（按照官方demo的格式）"""
        
        frame_size = 1280  # 每帧大小 (40ms @ 16kHz)
        interval = 0.04    # 发送间隔
        
        # 状态标识
        STATUS_FIRST_FRAME = 0
        STATUS_CONTINUE_FRAME = 1
        STATUS_LAST_FRAME = 2
        
        status = STATUS_FIRST_FRAME
        offset = 0
        
        logger.info(f"开始发送音频: {len(audio_data)} bytes")
        
        while offset < len(audio_data):
            # 读取一帧
            chunk = audio_data[offset:offset + frame_size]
            offset += frame_size
            
            # 判断是否最后一帧
            if offset >= len(audio_data):
                status = STATUS_LAST_FRAME
            
            # 构建消息（严格按照官方demo格式）
            if status == STATUS_FIRST_FRAME:
                # 第一帧包含parameter
                message = {
                    "header": {
                        "status": STATUS_FIRST_FRAME,
                        "app_id": self.config.appid
                    },
                    "parameter": {
                        "iat": {
                            "domain": self.config.domain,
                            "language": self.config.language,
                            "accent": self.config.accent,
                            "result": {
                                "encoding": "utf8",
                                "compress": "raw",
                                "format": "json"
                            }
                        }
                    },
                    "payload": {
                        "audio": {
                            "audio": base64.b64encode(chunk).decode('utf-8'),
                            "sample_rate": self.config.sample_rate,
                            "encoding": self.config.encoding
                        }
                    }
                }
                status = STATUS_CONTINUE_FRAME
                
            elif status == STATUS_CONTINUE_FRAME:
                # 中间帧
                message = {
                    "header": {
                        "status": STATUS_CONTINUE_FRAME,
                        "app_id": self.config.appid
                    },
                    "payload": {
                        "audio": {
                            "audio": base64.b64encode(chunk).decode('utf-8'),
                            "sample_rate": self.config.sample_rate,
                            "encoding": self.config.encoding
                        }
                    }
                }
                
            else:  # STATUS_LAST_FRAME
                # 最后一帧
                message = {
                    "header": {
                        "status": STATUS_LAST_FRAME,
                        "app_id": self.config.appid
                    },
                    "payload": {
                        "audio": {
                            "audio": base64.b64encode(chunk).decode('utf-8'),
                            "sample_rate": self.config.sample_rate,
                            "encoding": self.config.encoding
                        }
                    }
                }
            
            # 发送
            await ws.send(json.dumps(message))
            
            # 等待间隔（模拟实时音频流）
            if status != STATUS_LAST_FRAME:
                await asyncio.sleep(interval)
        
        logger.info(f"音频发送完成")
    # 严格按照官方的方式来接收信息
    async def _receive_results(self, ws) -> str:
        """接收识别结果（按照官方demo的解析方式）"""
        
        all_results = []
        
        try:
            while True:
                # 接收响应
                response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                message = json.loads(response)
                
                # 检查状态码
                header = message.get("header", {})
                code = header.get("code", 0)
                status = header.get("status", 0)
                
                if code != 0:
                    error_msg = header.get("message", "未知错误")
                    logger.error(f"识别错误: code={code}, msg={error_msg}")
                    raise Exception(f"识别错误 {code}: {error_msg}")
                
                # 解析结果（按照官方demo方式）
                payload = message.get("payload")
                if payload:
                    result = payload.get("result")
                    if result:
                        # 结果是base64编码的JSON
                        text_base64 = result.get("text", "")
                        if text_base64:
                            # 解码
                            text_json = base64.b64decode(text_base64).decode('utf-8')
                            text_data = json.loads(text_json)
                            
                            # 提取文本
                            ws_array = text_data.get("ws", [])
                            for ws_item in ws_array:
                                for cw in ws_item.get("cw", []):
                                    w = cw.get("w", "")
                                    all_results.append(w)
                
                # status=2 表示最后一帧结果
                if status == 2:
                    logger.info(f"识别完成")
                    break
                    
        except asyncio.TimeoutError:
            logger.warning(f"接收响应超时")
        except WebSocketException:
            logger.info(f"WebSocket连接已关闭")
        
        # 拼接所有结果
        final_text = "".join(all_results)
        logger.info(f"识别结果: {final_text}")
        
        return final_text


async def recognize_audio_file(
    audio_file_path: str,
    appid: str,
    api_key: str,
    api_secret: str
) -> STTResult:
    """
    便捷函数：识别音频文件
    
    Args:
        audio_file_path: PCM音频文件路径
        appid: iFlytek APPID
        api_key: iFlytek API Key
        api_secret: iFlytek API Secret
    
    Returns:
        STTResult: 识别结果
    """
    # 读取音频文件
    with open(audio_file_path, 'rb') as f:
        audio_data = f.read()
    
    # 创建配置
    config = STTConfig(
        appid=appid,
        api_key=api_key,
        api_secret=api_secret
    )
    
    # 创建服务并识别
    service = IFlytekSTTService(config)
    return await service.recognize(audio_data)


# 测试代码
if __name__ == "__main__":
    import sys
    from pathlib import Path
    from dotenv import load_dotenv
    import os
    
    # 加载环境变量
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    # 获取配置
    appid = os.getenv("IFLYTEK_APPID")
    api_key = os.getenv("IFLYTEK_APIKEY")
    api_secret = os.getenv("IFLYTEK_APISECRET")
    
    if not all([appid, api_key, api_secret]):
        print("❌ 请在.env文件中配置 IFLYTEK_APPID、IFLYTEK_APIKEY、IFLYTEK_APISECRET")
        sys.exit(1)
    
    # 测试音频文件
    audio_file = Path(__file__).parent.parent.parent.parent / "demo" / "stt" / "sample_audio.pcm"
    
    if not audio_file.exists():
        print(f"❌ 音频文件不存在: {audio_file}")
        sys.exit(1)
    
    print("=" * 70)
    print("🎤 STT识别测试（非流式）")
    print("=" * 70)
    print(f"\n📁 音频文件: {audio_file}")
    print(f"   大小: {audio_file.stat().st_size} bytes")
    print(f"\n🚀 开始识别...\n")
    
    # 运行识别
    async def main():
        result = await recognize_audio_file(
            str(audio_file),
            appid,
            api_key,
            api_secret
        )
        
        print("=" * 70)
        print("📊 识别结果")
        print("=" * 70)
        
        if result.success:
            print(f"\n✅ 识别成功")
            print(f"\n识别文本:")
            print(f"『{result.text}』")
        else:
            print(f"\n❌ 识别失败")
            print(f"   错误码: {result.error_code}")
            print(f"   错误信息: {result.error_message}")
        
        print("\n" + "=" * 70)
    
    asyncio.run(main())
