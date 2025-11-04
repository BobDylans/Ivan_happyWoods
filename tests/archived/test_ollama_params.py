"""测试 Ollama 对不同参数的响应"""
import httpx
import json

def test_parameter(param_name, param_value, description):
    """测试单个参数"""
    print(f"\n{'='*60}")
    print(f"测试: {description}")
    print(f"参数: {param_name}={param_value}")
    print(f"{'='*60}")
    
    payload = {
        "model": "qwen3:4b",
        "messages": [{"role": "user", "content": "用一句话介绍你自己"}],
        "stream": True
    }
    
    # 添加测试参数
    payload[param_name] = param_value
    
    print(f"📤 Payload: {json.dumps(payload, ensure_ascii=False)}")
    
    try:
        with httpx.Client(trust_env=False) as client:
            with client.stream(
                'POST',
                "http://localhost:11434/api/chat",
                json=payload,
                timeout=30
            ) as resp:
                print(f"✅ 状态码: {resp.status_code}")
                print(f"📋 Content-Type: {resp.headers.get('content-type')}")
                
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
                        except json.JSONDecodeError:
                            pass
                
                result = ''.join(full_text)
                print(f"💬 响应内容: {result}")
                print(f"📊 统计: 行数={line_count}, 字符数={len(result)}")
                
                if len(result) == 0:
                    print(f"❌ 响应为空！参数 {param_name} 可能不被支持")
                else:
                    print(f"✅ 响应正常")
                    
    except Exception as e:
        print(f"❌ 错误: {e}")

def main():
    print("🧪 测试 Ollama 参数兼容性")
    
    # 测试 1: 无额外参数（基线）
    test_parameter(
        "temperature",
        0.7,
        "baseline - 带 temperature（OpenAI 常用）"
    )
    
    # 测试 2: max_tokens（OpenAI 格式）
    test_parameter(
        "max_tokens",
        100,
        "OpenAI: max_tokens"
    )
    
    # 测试 3: max_completion_tokens（GPT-5 格式）
    test_parameter(
        "max_completion_tokens",
        100,
        "GPT-5: max_completion_tokens"
    )
    
    # 测试 4: 同时带多个参数
    print(f"\n{'='*60}")
    print(f"测试: 同时带多个参数（模拟项目实际情况）")
    print(f"{'='*60}")
    
    payload_complex = {
        "model": "qwen3:4b",
        "messages": [{"role": "user", "content": "你好"}],
        "stream": True,
        "temperature": 0.7,
        "max_completion_tokens": 16384,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "测试工具",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]
    }
    
    print(f"📤 Payload Keys: {list(payload_complex.keys())}")
    
    try:
        with httpx.Client(trust_env=False) as client:
            with client.stream(
                'POST',
                "http://localhost:11434/api/chat",
                json=payload_complex,
                timeout=30
            ) as resp:
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
                        except json.JSONDecodeError:
                            pass
                
                result = ''.join(full_text)
                print(f"💬 响应内容: {result}")
                print(f"📊 统计: 行数={line_count}, 字符数={len(result)}")
                
                if len(result) == 0:
                    print(f"❌ 响应为空！某些参数导致了问题")
                    print(f"💡 可能的原因:")
                    print(f"   - max_completion_tokens 不被 Ollama 支持")
                    print(f"   - 参数组合导致冲突")
                else:
                    print(f"✅ 响应正常")
                    
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    print("\n" + "="*60)
    print("🎯 结论建议")
    print("="*60)
    print("如果 max_completion_tokens 导致空响应:")
    print("  1. 修改 prepare_llm_params() 函数")
    print("  2. 检测 Ollama provider 时不添加 max_* 参数")
    print("  3. 或者使用 Ollama 支持的参数（如 num_predict）")

if __name__ == "__main__":
    main()
