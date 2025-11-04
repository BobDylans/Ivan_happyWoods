"""测试 tool_choice 参数"""
import httpx
import json

def test_tool_choice():
    """测试 tool_choice 参数是否导致问题"""
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "搜索",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    }
                }
            }
        }
    ]
    
    # 测试 1: 不带 tool_choice
    print("="*60)
    print("测试 1: 带 tools，不带 tool_choice")
    print("="*60)
    
    payload1 = {
        "model": "qwen3:4b",
        "messages": [{"role": "user", "content": "帮我搜索一下"}],
        "stream": True,
        "tools": tools
    }
    
    try:
        with httpx.Client(trust_env=False) as client:
            with client.stream('POST', "http://localhost:11434/api/chat", json=payload1, timeout=30) as resp:
                print(f"✅ 状态码: {resp.status_code}")
                
                full_text = []
                for line in resp.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if 'message' in data:
                                content = data['message'].get('content', '')
                                if content:
                                    full_text.append(content)
                        except:
                            pass
                
                result = ''.join(full_text)
                print(f"💬 响应: {result[:100]}")
                print(f"📊 字符数: {len(result)}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 测试 2: 带 tool_choice="auto"
    print("\n" + "="*60)
    print("测试 2: 带 tools + tool_choice='auto'")
    print("="*60)
    
    payload2 = {
        "model": "qwen3:4b",
        "messages": [{"role": "user", "content": "帮我搜索一下"}],
        "stream": True,
        "tools": tools,
        "tool_choice": "auto"  # 添加这个参数
    }
    
    try:
        with httpx.Client(trust_env=False) as client:
            with client.stream('POST', "http://localhost:11434/api/chat", json=payload2, timeout=30) as resp:
                print(f"✅ 状态码: {resp.status_code}")
                
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
                                    full_text.append(content)
                        except:
                            pass
                
                result = ''.join(full_text)
                print(f"💬 响应: {result[:100]}")
                print(f"📊 行数: {line_count}, 字符数: {len(result)}")
                
                if len(result) == 0:
                    print(f"\n❌ 找到问题！tool_choice='auto' 导致空响应")
                    print(f"💡 Ollama 可能不支持 tool_choice 参数")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    test_tool_choice()
