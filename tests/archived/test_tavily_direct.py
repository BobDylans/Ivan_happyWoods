"""
直接测试 Tavily API Key
"""
import httpx
import asyncio

async def test_tavily_api():
    """直接调用 Tavily API 测试"""
    
    # 从 .env 读取 API Key
    import os
    from dotenv import load_dotenv
    from pathlib import Path
    
    # 明确指定 .env 文件（优先级最高）
    env_path = Path(__file__).parent / ".env"
    print(f"📁 加载配置文件: {env_path}")
    print(f"📁 文件是否存在: {env_path.exists()}")
    
    # 清除环境变量缓存
    if "TAVILY_API_KEY" in os.environ:
        del os.environ["TAVILY_API_KEY"]
    
    # 重新加载
    load_dotenv(env_path, override=True)
    
    api_key = os.getenv("TAVILY_API_KEY")
    
    print("=" * 60)
    print("🔑 Tavily API Key 测试")
    print("=" * 60)
    print(f"API Key: {api_key}")
    print(f"Length: {len(api_key) if api_key else 0}")
    print(f"Starts with: {api_key[:10] if api_key else 'N/A'}...")
    print()
    
    if not api_key:
        print("❌ 未找到 TAVILY_API_KEY")
        return
    
    # 测试 API 调用
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key.strip(),  # 去除可能的空格
        "query": "test query",
        "max_results": 1
    }
    
    print("🌐 调用 Tavily API...")
    print(f"URL: {url}")
    print(f"Query: {payload['query']}")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
            
            print(f"📊 Response Status: {response.status_code}")
            print(f"📋 Response Headers: {dict(response.headers)}")
            print()
            
            if response.status_code == 200:
                data = response.json()
                print("✅ API 调用成功!")
                print(f"返回结果数: {len(data.get('results', []))}")
                if data.get('results'):
                    print(f"第一个结果标题: {data['results'][0].get('title', 'N/A')}")
            else:
                print(f"❌ API 调用失败: {response.status_code}")
                print(f"错误详情: {response.text}")
                
                if response.status_code == 401:
                    print()
                    print("💡 401 错误说明:")
                    print("   - API Key 可能无效或已过期")
                    print("   - 请访问 https://app.tavily.com/ 检查你的 API Key")
                    print("   - 确认 API Key 格式正确（应以 'tvly-' 开头）")
                    print("   - 检查账户是否还有剩余配额")
    
    except httpx.TimeoutException:
        print("❌ 请求超时")
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tavily_api())
