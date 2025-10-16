#!/usr/bin/env python3
"""
测试MCP语音工具的注册和功能

验证：
1. TTS工具（语音合成）是否已注册
2. STT工具（语音识别）是否已注册
3. 语音分析工具是否已注册
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "dev-test-key-123"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


def wait_for_server(timeout=30):
    """等待服务器启动"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/health",
                headers=HEADERS,
                timeout=2
            )
            if response.status_code == 200:
                print("✅ 服务器已启动")
                return True
        except:
            pass
        time.sleep(1)
    
    print("❌ 服务器启动超时")
    return False


def test_mcp_tool_list():
    """测试获取MCP工具列表"""
    print("\n" + "="*60)
    print("📋 获取MCP工具列表")
    print("="*60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/tools",
            headers=HEADERS,
            timeout=10
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            tools = data.get("tools", [])
            print(f"✅ 已注册 {len(tools)} 个MCP工具:")
            
            tool_names = []
            for tool in tools:
                if isinstance(tool, dict):
                    tool_name = tool.get("name", "unknown")
                    tool_names.append(tool_name)
                    print(f"  - {tool_name}")
                else:
                    tool_names.append(str(tool))
                    print(f"  - {tool}")
            
            # 检查voice相关工具
            voice_tools = [t for t in tool_names if "voice" in t.lower() or "speech" in t.lower()]
            if voice_tools:
                print(f"\n🎤 找到 {len(voice_tools)} 个语音工具:")
                for tool in voice_tools:
                    print(f"  ✅ {tool}")
            else:
                print("\n❌ 未找到语音工具")
            
            return tool_names
        else:
            print(f"❌ 获取工具列表失败: {response.status_code}")
            try:
                print(f"   错误: {response.json()}")
            except:
                print(f"   响应: {response.text[:200]}")
            return []
    
    except Exception as e:
        print(f"❌ 异常: {e}")
        return []


def test_mcp_tool_schemas():
    """测试获取MCP工具模式"""
    print("\n" + "="*60)
    print("📊 获取MCP工具模式")
    print("="*60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/tools/schemas",
            headers=HEADERS,
            timeout=10
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            schemas = data.get("schemas", [])
            print(f"✅ 获取了 {len(schemas)} 个工具模式")
            
            # 查找voice工具模式
            voice_schemas = [s for s in schemas if "voice" in s.get("function", {}).get("name", "").lower() or "speech" in s.get("function", {}).get("name", "").lower()]
            
            if voice_schemas:
                print(f"\n🎤 找到 {len(voice_schemas)} 个语音工具模式:")
                for schema in voice_schemas:
                    func_name = schema.get("function", {}).get("name", "unknown")
                    func_desc = schema.get("function", {}).get("description", "")
                    print(f"\n  📌 {func_name}")
                    print(f"     描述: {func_desc[:60]}...")
            else:
                print("\n❌ 未找到语音工具模式")
            
            return schemas
        else:
            print(f"❌ 获取工具模式失败: {response.status_code}")
            return []
    
    except Exception as e:
        print(f"❌ 异常: {e}")
        return []


def test_voice_synthesis_tool():
    """测试语音合成工具"""
    print("\n" + "="*60)
    print("🎤 测试语音合成工具 (voice_synthesis)")
    print("="*60)
    
    test_cases = [
        {
            "name": "简单文本",
            "text": "你好，我是MCP语音合成工具。",
            "voice": "x5_lingxiaoxuan_flow"
        },
        {
            "name": "自定义参数",
            "text": "这是一个测试。",
            "voice": "x5_lingxiaoxuan_flow",
            "speed": 60,
            "volume": 70
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test_case['name']}")
        print(f"文本: {test_case['text']}")
        
        payload = {
            "text": test_case["text"],
            "voice": test_case.get("voice", "x5_lingxiaoxuan_flow"),
            "speed": test_case.get("speed", 50),
            "volume": test_case.get("volume", 50),
            "pitch": test_case.get("pitch", 50),
            "streaming": False,
            "output_format": "base64"
        }
        
        try:
            # 测试MCP工具执行端点
            response = requests.post(
                f"{BASE_URL}/api/v1/tools/execute/voice_synthesis",
                headers=HEADERS,
                json=payload,
                timeout=30
            )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    result_data = data.get("result", {}).get("data", {})
                    audio_size = result_data.get('audio_size', 0)
                    print(f"✅ 成功: 生成了 {audio_size} 字节的音频")
                else:
                    print(f"❌ 工具执行失败: {data.get('error', '未知错误')}")
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                try:
                    print(f"   错误: {response.json()}")
                except:
                    print(f"   响应: {response.text[:200]}")
        
        except Exception as e:
            print(f"❌ 异常: {e}")
        
        time.sleep(1)


def test_speech_recognition_tool():
    """测试语音识别工具"""
    print("\n" + "="*60)
    print("🎙️ 测试语音识别工具 (speech_recognition)")
    print("="*60)
    
    # 首先生成一个测试音频
    print("\n步骤 1: 生成测试音频...")
    tts_payload = {
        "text": "这是一个测试音频文件。",
        "voice": "x5_lingxiaoxuan_flow",
        "streaming": False,
        "output_format": "base64"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/tools/execute/voice_synthesis",
            headers=HEADERS,
            json=tts_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                audio_data = data.get("result", {}).get("data", {}).get("audio_base64", "")
                print(f"✅ 测试音频已生成 ({len(audio_data)} bytes of base64)")
                
                # 现在测试STT
                print("\n步骤 2: 识别生成的音频...")
                stt_payload = {
                    "audio_data": audio_data,
                    "audio_format": "mp3"
                }
                
                response2 = requests.post(
                    f"{BASE_URL}/api/v1/tools/execute/speech_recognition",
                    headers=HEADERS,
                    json=stt_payload,
                    timeout=30
                )
                
                print(f"状态码: {response2.status_code}")
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    if data2.get("success"):
                        result_data = data2.get("result", {}).get("data", {})
                        print(f"✅ 识别成功: {result_data.get('text', '')}")
                    else:
                        error_msg = data2.get("result", {}).get("error", data2.get('error', '未知错误'))
                        print(f"❌ 识别失败: {error_msg}")
                else:
                    print(f"❌ HTTP错误: {response2.status_code}")
            else:
                print(f"❌ 无法生成测试音频: {data.get('error')}")
        else:
            print(f"❌ 生成音频失败: {response.status_code}")
    
    except Exception as e:
        print(f"❌ 异常: {e}")


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "🎤 MCP语音工具测试" + " "*20 + "║")
    print("╚" + "="*58 + "╝")
    
    try:
        # 等待服务器启动
        if not wait_for_server():
            return
        
        # 1. 获取工具列表
        tools = test_mcp_tool_list()
        
        # 2. 获取工具模式
        schemas = test_mcp_tool_schemas()
        
        # 3. 测试语音合成工具
        if "voice_synthesis" in tools:
            test_voice_synthesis_tool()
        else:
            print("\n⚠️  voice_synthesis 工具未找到，跳过测试")
        
        # 4. 测试语音识别工具
        if "speech_recognition" in tools:
            test_speech_recognition_tool()
        else:
            print("\n⚠️  speech_recognition 工具未找到，跳过测试")
        
        print("\n" + "="*60)
        print("✅ MCP语音工具测试完成！")
        print("="*60)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")


if __name__ == "__main__":
    main()
