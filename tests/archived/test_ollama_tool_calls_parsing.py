"""测试 Ollama tool_calls 响应格式"""
import httpx
import json

def test_ollama_tool_response():
    """测试 Ollama 返回的 tool_calls 格式"""
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "搜索网络信息。当用户询问最新新闻、实时信息或需要查找资料时使用。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    
    # 测试问题：明确需要搜索的问题
    test_queries = [
        "帮我搜索一下特朗普最新新闻",
        "search for Trump latest news",
        "请用搜索工具查找今天的天气",
    ]
    
    for query in test_queries:
        print("\n" + "="*60)
        print(f"测试查询: {query}")
        print("="*60)
        
        payload = {
            "model": "qwen3:4b",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个智能助手。当用户需要查找信息时，你应该使用 web_search 工具。"
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "stream": False,
            "tools": tools
        }
        
        try:
            with httpx.Client(trust_env=False, timeout=60) as client:
                resp = client.post(
                    "http://localhost:11434/api/chat",
                    json=payload
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    message = data.get('message', {})
                    
                    print(f"\n📦 完整响应:")
                    print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
                    
                    # 检查 tool_calls
                    if 'tool_calls' in message:
                        print(f"\n✅ 检测到 tool_calls!")
                        print(f"🔧 Tool Calls: {json.dumps(message['tool_calls'], indent=2, ensure_ascii=False)}")
                        
                        # 分析格式
                        for tc in message['tool_calls']:
                            print(f"\n  工具名称: {tc.get('function', {}).get('name')}")
                            print(f"  工具参数: {tc.get('function', {}).get('arguments')}")
                    else:
                        print(f"\n❌ 没有 tool_calls")
                        print(f"💬 普通回复: {message.get('content', '')[:200]}")
                        
                        # 检查是否有其他可能的工具调用字段
                        print(f"\n🔍 Message 中的所有字段: {list(message.keys())}")
                else:
                    print(f"❌ 错误: HTTP {resp.status_code}")
                    print(resp.text[:500])
                    
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    print("\n" + "="*60)
    print("🎯 结论")
    print("="*60)
    print("如果 Ollama 返回了 tool_calls，检查项目代码是否正确解析")
    print("如果没有返回 tool_calls，可能需要:")
    print("  1. 更清晰的系统提示词")
    print("  2. 更明确的用户问题")
    print("  3. 或者 Ollama 模型本身不支持工具调用")

if __name__ == "__main__":
    test_ollama_tool_response()
