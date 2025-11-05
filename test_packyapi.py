"""
测试 PackyAPI 连接
"""
import asyncio
import httpx

async def test_packyapi():
    """测试 PackyAPI Claude 模型"""
    api_key = "sk-5qiL7w108rpBDDnifbCmxU3VqcfKtLMzIYjJgUFlCeF8GM3I"
    base_url = "https://www.packyapi.com/v1"
    model = "claude-3-5-haiku-20241022"
    
    print("=" * 60)
    print("测试 PackyAPI 连接")
    print("=" * 60)
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print()
    
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "你好，请用一句话介绍你自己"}
        ],
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    print("发送测试请求...")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"✅ 成功！")
                print(f"\nAI 回复:")
                print(f"{content}")
                print()
                return True
            else:
                print(f"❌ 错误 {response.status_code}")
                print(f"响应: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_packyapi())
    print("=" * 60)
    if success:
        print("✅ PackyAPI 连接测试通过！")
    else:
        print("❌ PackyAPI 连接测试失败")
    print("=" * 60)

