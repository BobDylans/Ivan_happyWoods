"""测试 Ollama 工具调用支持"""
import httpx
import json

def test_ollama_tools():
    """测试 Ollama 是否支持工具调用"""
    
    # 测试 1: 基本调用（无工具）
    print("=" * 60)
    print("测试 1: 基本调用（无工具）")
    print("=" * 60)
    
    payload_basic = {
        "model": "qwen3:4b",
        "messages": [{"role": "user", "content": "你好，请用一句话介绍你自己"}],
        "stream": False
    }
    
    try:
        with httpx.Client(trust_env=False) as client:  # 禁用代理
            resp = client.post(
                "http://localhost:11434/api/chat",
                json=payload_basic,
                timeout=30
            )
            print(f"✅ 状态码: {resp.status_code}")
            data = resp.json()
            print(f"💬 AI 回复: {data['message']['content'][:200]}")
            print(f"✅ 基本调用成功\n")
    except Exception as e:
        print(f"❌ 错误: {e}\n")
        return
    
    # 测试 2: 带工具调用（OpenAI 格式）
    print("=" * 60)
    print("测试 2: 带工具调用（OpenAI 格式）")
    print("=" * 60)
    
    tools_openai = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "搜索网络信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词"}
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    
    payload_with_tools = {
        "model": "qwen3:4b",
        "messages": [{"role": "user", "content": "帮我搜索一下今天的天气"}],
        "stream": False,
        "tools": tools_openai
    }
    
    try:
        with httpx.Client(trust_env=False) as client:  # 禁用代理
            resp = client.post(
                "http://localhost:11434/api/chat",
                json=payload_with_tools,
                timeout=30
            )
            print(f"✅ 状态码: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"📦 响应: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                
                message = data.get('message', {})
                if 'tool_calls' in message:
                    print(f"🔧 工具调用: {message['tool_calls']}")
                else:
                    print(f"💬 普通回复: {message.get('content', '')[:200]}")
            else:
                print(f"❌ 错误响应: {resp.text[:500]}")
    except Exception as e:
        print(f"❌ 错误: {e}\n")
        return
    
    # 测试 3: 流式调用（无工具）
    print("\n" + "=" * 60)
    print("测试 3: 流式调用（无工具）")
    print("=" * 60)
    
    payload_stream = {
        "model": "qwen3:4b",
        "messages": [{"role": "user", "content": "用一句话介绍中国"}],
        "stream": True
    }
    
    try:
        with httpx.Client(trust_env=False) as client:  # 禁用代理
            with client.stream(
                'POST',
                "http://localhost:11434/api/chat",
                json=payload_stream,
                timeout=30
            ) as resp:
                print(f"✅ 状态码: {resp.status_code}")
                print(f"📋 Content-Type: {resp.headers.get('content-type')}")
                print(f"💬 流式响应: ", end='', flush=True)
                
                full_text = []
                line_count = 0
                
                for line in resp.iter_lines():
                    if line:
                        line_count += 1
                        try:
                            data = json.loads(line)
                            if 'message' in data:
                                content = data['message'].get('content', '')
                                if content:
                                    print(content, end='', flush=True)
                                    full_text.append(content)
                        except json.JSONDecodeError:
                            print(f"\n⚠️ JSON 解析失败: {line[:100]}")
                
                print(f"\n\n📊 统计:")
                print(f"  - 收到行数: {line_count}")
                print(f"  - 总字符数: {len(''.join(full_text))}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 测试 4: 流式调用（带工具）
    print("\n" + "=" * 60)
    print("测试 4: 流式调用（带工具）")
    print("=" * 60)
    
    payload_stream_tools = {
        "model": "qwen3:4b",
        "messages": [{"role": "user", "content": "帮我搜索一下"}],
        "stream": True,
        "tools": tools_openai
    }
    
    try:
        with httpx.Client(trust_env=False) as client:  # 禁用代理
            with client.stream(
                'POST',
                "http://localhost:11434/api/chat",
                json=payload_stream_tools,
                timeout=30
            ) as resp:
                print(f"✅ 状态码: {resp.status_code}")
                print(f"📋 Content-Type: {resp.headers.get('content-type')}")
                print(f"💬 流式响应: ", end='', flush=True)
                
                full_text = []
                line_count = 0
                
                for line in resp.iter_lines():
                    if line:
                        line_count += 1
                        try:
                            data = json.loads(line)
                            if 'message' in data:
                                content = data['message'].get('content', '')
                                if content:
                                    print(content, end='', flush=True)
                                    full_text.append(content)
                        except json.JSONDecodeError:
                            print(f"\n⚠️ JSON 解析失败: {line[:100]}")
                
                print(f"\n\n📊 统计:")
                print(f"  - 收到行数: {line_count}")
                print(f"  - 总字符数: {len(''.join(full_text))}")
                
                if len(''.join(full_text)) == 0:
                    print(f"⚠️ 流式响应为空！可能是工具参数导致的问题")
    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    test_ollama_tools()
