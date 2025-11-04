"""
直接测试项目中的 Ollama 调用
"""
import asyncio
import httpx

async def test_ollama_with_trust_env():
    """测试使用 trust_env=False 的 Ollama 调用"""
    print("=" * 60)
    print("测试: 使用 trust_env=False 调用 Ollama")
    print("=" * 60)
    
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "qwen3:4b",
        "messages": [
            {"role": "user", "content": "你好，请用一句话介绍你自己"}
        ],
        "stream": False
    }
    
    try:
        # 使用 trust_env=False 禁用代理
        async with httpx.AsyncClient(trust_env=False, timeout=60.0) as client:
            print(f"📡 发送请求到: {url}")
            print(f"📦 Payload: {payload}")
            print(f"🔧 trust_env=False (禁用系统代理)")
            
            response = await client.post(url, json=payload)
            
            print(f"\n✅ 状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"🤖 模型: {result['model']}")
                print(f"💬 回复: {result['message']['content'][:100]}...")
                print(f"📊 Token: prompt={result.get('prompt_eval_count')}, response={result.get('eval_count')}")
                return True
            else:
                print(f"❌ 失败: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ 异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_with_system_proxy():
    """测试使用系统代理的情况（预期失败）"""
    print("\n" + "=" * 60)
    print("测试: 使用系统代理调用 Ollama (预期失败)")
    print("=" * 60)
    
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "qwen3:4b",
        "messages": [{"role": "user", "content": "测试"}],
        "stream": False
    }
    
    try:
        # 使用默认设置（会读取系统代理）
        async with httpx.AsyncClient(timeout=10.0) as client:
            print(f"📡 发送请求到: {url}")
            print(f"🔧 trust_env=True (默认，使用系统代理)")
            
            response = await client.post(url, json=payload)
            print(f"✅ 状态码: {response.status_code}")
            return response.status_code == 200
            
    except Exception as e:
        print(f"❌ 预期的失败: {type(e).__name__}: {e}")
        return False

async def main():
    print("🚀 开始测试 Ollama API 调用\n")
    
    # 测试 1: 使用 trust_env=False（应该成功）
    success1 = await test_ollama_with_trust_env()
    
    # 测试 2: 使用系统代理（预期失败）
    success2 = await test_with_system_proxy()
    
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    print(f"✅ trust_env=False: {'成功' if success1 else '失败'}")
    print(f"{'✅' if not success2 else '❌'} 系统代理: {'成功（异常！）' if success2 else '失败（预期）'}")
    
    if success1:
        print("\n🎉 结论: trust_env=False 方案可行，项目应该能正常工作！")
    else:
        print("\n⚠️ 警告: trust_env=False 仍然失败，可能需要其他方案")

if __name__ == "__main__":
    asyncio.run(main())
