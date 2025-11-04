"""
测试项目的对话 API（使用 Ollama）
"""
import requests
import json

def test_conversation_api():
    """测试对话 API"""
    print("=" * 60)
    print("测试: 项目对话 API (Ollama)")
    print("=" * 60)
    
    # 使用正确的端点: /api/v1/chat/
    url = "http://localhost:8000/api/v1/chat/"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "dev-test-key-123"
    }
    payload = {
        "session_id": "test_ollama_session",
        "message": "你好，请用一句话介绍你自己"
    }
    
    try:
        print(f"📡 发送请求到: {url}")
        print(f"🔑 API Key: {headers['X-API-Key']}")
        print(f"💬 消息: {payload['message']}")
        print(f"📦 Session ID: {payload['session_id']}")
        print("\n⏳ 等待响应...")
        
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        print(f"\n✅ 状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n📋 完整响应:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            if "response" in result:
                print(f"\n💬 AI 回复: {result['response']}")
            
            if "session_id" in result:
                print(f"📦 会话 ID: {result['session_id']}")
            
            return True
        else:
            print(f"\n❌ 失败:")
            print(f"响应头: {dict(response.headers)}")
            print(f"响应体: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时（60秒）")
        print("可能原因:")
        print("  1. Ollama 模型正在加载（首次调用需要时间）")
        print("  2. 模型生成速度较慢")
        print("  3. 服务器处理卡住")
        return False
    except Exception as e:
        print(f"❌ 异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_streaming_api():
    """测试流式 API"""
    print("\n" + "=" * 60)
    print("测试: 流式对话 API (Ollama)")
    print("=" * 60)
    
    # 使用流式端点: /api/v1/chat/stream
    url = "http://localhost:8000/api/v1/chat/stream"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "dev-test-key-123"
    }
    payload = {
        "session_id": "test_ollama_stream",
        "message": "数到5"
    }
    
    try:
        print(f"📡 发送流式请求到: {url}")
        print(f"💬 消息: {payload['message']}")
        print("\n⏳ 接收流式响应...")
        print("回复: ", end="", flush=True)
        
        response = requests.post(url, json=payload, headers=headers, stream=True, timeout=60)
        
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # 去掉 'data: ' 前缀
                        if data_str.strip() and data_str != '[DONE]':
                            try:
                                data = json.loads(data_str)
                                if data.get('type') == 'content' and 'content' in data:
                                    print(data['content'], end="", flush=True)
                            except json.JSONDecodeError:
                                pass
            
            print("\n\n✅ 流式响应完成！")
            return True
        else:
            print(f"\n❌ 状态码: {response.status_code}")
            print(f"响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ 异常: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试项目对话 API\n")
    
    # 测试 1: 非流式对话
    success1 = test_conversation_api()
    
    # 测试 2: 流式对话
    if success1:
        success2 = test_streaming_api()
    else:
        print("\n⚠️ 跳过流式测试（非流式测试失败）")
        success2 = False
    
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    print(f"{'✅' if success1 else '❌'} 非流式对话: {'成功' if success1 else '失败'}")
    print(f"{'✅' if success2 else '❌'} 流式对话: {'成功' if success2 else '失败'}")
    
    if success1 and success2:
        print("\n🎉 所有测试通过！Ollama 集成成功！")
    elif success1:
        print("\n⚠️ 非流式工作正常，但流式有问题")
    else:
        print("\n❌ 测试失败，请检查服务器日志")
