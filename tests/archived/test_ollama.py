"""
测试 Ollama OpenAI-Compatible API
"""
import httpx
import json

async def test_ollama_chat():
    url = "http://localhost:11434/v1/chat/completions"
    
    payload = {
        "model": "qwen3:4b",
        "messages": [
            {"role": "user", "content": "你好，请用一句话介绍你自己"}
        ],
        "stream": False
    }
    
    print("📡 测试 Ollama 对话接口...")
    print(f"URL: {url}")
    print(f"模型: {payload['model']}")
    print(f"消息: {payload['messages'][0]['content']}")
    print("\n" + "="*60)
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print("\n✅ 调用成功！")
                print(f"模型: {result['model']}")
                print(f"回复: {result['choices'][0]['message']['content']}")
                print(f"Token 使用: {result.get('usage', {})}")
                return True
            else:
                print(f"\n❌ 调用失败！状态码: {response.status_code}")
                print(f"响应: {response.text}")
                return False
                
        except Exception as e:
            print(f"\n❌ 异常: {e}")
            return False

async def test_ollama_stream():
    url = "http://localhost:11434/v1/chat/completions"
    
    payload = {
        "model": "qwen3:4b",
        "messages": [
            {"role": "user", "content": "数到5"}
        ],
        "stream": True
    }
    
    print("\n\n📡 测试 Ollama 流式接口...")
    print(f"URL: {url}")
    print(f"模型: {payload['model']}")
    print("\n回复: ", end="", flush=True)
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            async with client.stream(
                "POST",
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status_code == 200:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                content = chunk['choices'][0]['delta'].get('content', '')
                                if content:
                                    print(content, end="", flush=True)
                            except:
                                pass
                    print("\n\n✅ 流式调用成功！")
                    return True
                else:
                    print(f"\n❌ 流式调用失败！状态码: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"\n❌ 异常: {e}")
            return False

if __name__ == "__main__":
    import asyncio
    
    async def main():
        # 测试普通对话
        success1 = await test_ollama_chat()
        
        # 测试流式对话
        success2 = await test_ollama_stream()
        
        print("\n" + "="*60)
        if success1 and success2:
            print("🎉 所有测试通过！可以切换到 Ollama！")
        else:
            print("⚠️ 部分测试失败，需要检查配置")
    
    asyncio.run(main())
