"""
简单测试 Ollama API
"""
import requests
import json

# 测试 1: Ollama 原生 Chat API (推荐)
print("=" * 60)
print("测试 1: Ollama 原生 Chat API (/api/chat)")
print("=" * 60)

url1 = "http://localhost:11434/api/chat"
payload1 = {
    "model": "qwen3:4b",
    "messages": [
        {"role": "user", "content": "你好，请用一句话介绍你自己"}
    ],
    "stream": False
}

try:
    response1 = requests.post(url1, json=payload1, timeout=30)
    print(f"状态码: {response1.status_code}")
    if response1.status_code == 200:
        result = response1.json()
        print(f"✅ Ollama 原生 Chat API 成功！")
        print(f"模型: {result['model']}")
        print(f"回复: {result['message']['content']}")
        print(f"Token: prompt={result.get('prompt_eval_count')}, response={result.get('eval_count')}")
    else:
        print(f"❌ 失败: {response1.text}")
except Exception as e:
    print(f"❌ 异常: {e}")

# 测试 2: 检查服务状态
print("\n" + "=" * 60)
print("测试 2: 检查 Ollama 服务状态")
print("=" * 60)

try:
    response2 = requests.get("http://localhost:11434/api/tags", timeout=5)
    if response2.status_code == 200:
        models = response2.json()['models']
        print(f"✅ 服务正常！已安装 {len(models)} 个模型:")
        for model in models:
            print(f"  - {model['name']} ({model['details']['parameter_size']})")
except Exception as e:
    print(f"❌ 服务异常: {e}")

# 测试 3: 流式响应
print("\n" + "=" * 60)
print("测试 3: 流式 Chat API")
print("=" * 60)

url3 = "http://localhost:11434/api/chat"
payload3 = {
    "model": "qwen3:4b",
    "messages": [{"role": "user", "content": "数到5"}],
    "stream": True
}

try:
    response3 = requests.post(url3, json=payload3, stream=True, timeout=30)
    print(f"状态码: {response3.status_code}")
    if response3.status_code == 200:
        print("回复: ", end="", flush=True)
        for line in response3.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    content = chunk.get('message', {}).get('content', '')
                    if content:
                        print(content, end="", flush=True)
                except:
                    pass
        print("\n✅ 流式调用成功！")
    else:
        print(f"❌ 失败: {response3.text}")
except Exception as e:
    print(f"❌ 异常: {e}")

