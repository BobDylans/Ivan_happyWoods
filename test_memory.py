"""
测试记忆功能

验证多轮对话中的会话记忆是否正常工作
"""

import requests
import json
import time

# API 配置
BASE_URL = "http://127.0.0.1:8000"
API_KEY = "dev-test-key-123"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def test_memory_via_chat_stream():
    """测试 /api/v1/chat 流式端点的记忆功能"""
    print("\n" + "="*60)
    print("测试场景：/api/v1/chat POST 流式端点的多轮对话记忆")
    print("="*60)
    
    # 生成唯一的 session_id
    session_id = f"test_memory_{int(time.time())}"
    print(f"\n📝 会话ID: {session_id}\n")
    
    # 第一轮对话：告诉AI一个信息
    print("👤 用户: 我叫张三")
    response1 = requests.post(
        f"{BASE_URL}/api/v1/chat/stream",
        headers=headers,
        json={
            "message": "我叫张三",
            "session_id": session_id
        },
        stream=True
    )
    
    if response1.status_code != 200:
        print(f"❌ 请求失败: {response1.status_code}")
        print(response1.text)
        return
    
    print("🤖 助手: ", end="", flush=True)
    full_response1 = ""
    for line in response1.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    if data.get('type') == 'delta' and 'content' in data:
                        content = data['content']
                        print(content, end="", flush=True)
                        full_response1 += content
                except json.JSONDecodeError:
                    pass
    print("\n")
    
    # 等待一下
    time.sleep(2)
    
    # 第二轮对话：测试AI是否记得
    print("👤 用户: 你还记得我叫什么名字吗？")
    response2 = requests.post(
        f"{BASE_URL}/api/v1/chat/stream",
        headers=headers,
        json={
            "message": "你还记得我叫什么名字吗？",
            "session_id": session_id
        },
        stream=True
    )
    
    if response2.status_code != 200:
        print(f"❌ 请求失败: {response2.status_code}")
        print(response2.text)
        return
    
    print("🤖 助手: ", end="", flush=True)
    full_response2 = ""
    for line in response2.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    if data.get('type') == 'delta' and 'content' in data:
                        content = data['content']
                        print(content, end="", flush=True)
                        full_response2 += content
                except json.JSONDecodeError:
                    pass
    print("\n")
    
    # 验证结果
    if "张三" in full_response2:
        print("✅ 记忆功能正常！AI记得用户的名字。")
    else:
        print("❌ 记忆功能失败！AI没有记得用户的名字。")
        print(f"完整回复: {full_response2}")


def test_memory_via_conversation():
    """测试 /api/v1/conversation/message 端点的记忆功能"""
    print("\n" + "="*60)
    print("测试场景：/api/v1/conversation/message 端点的多轮对话记忆")
    print("="*60)
    
    # 生成唯一的 session_id
    session_id = f"test_conv_{int(time.time())}"
    print(f"\n📝 会话ID: {session_id}\n")
    
    # 第一轮对话
    print("👤 用户: 我今年25岁")
    response1 = requests.post(
        f"{BASE_URL}/api/v1/conversation/message",
        headers=headers,
        json={
            "text": "我今年25岁",
            "session_id": session_id,
            "output_mode": "text"
        }
    )
    
    if response1.status_code != 200:
        print(f"❌ 请求失败: {response1.status_code}")
        print(response1.text)
        return
    
    result1 = response1.json()
    print(f"🤖 助手: {result1.get('agent_response', 'N/A')}\n")
    
    # 等待一下
    time.sleep(2)
    
    # 第二轮对话
    print("👤 用户: 我多大了？")
    response2 = requests.post(
        f"{BASE_URL}/api/v1/conversation/message",
        headers=headers,
        json={
            "text": "我多大了？",
            "session_id": session_id,
            "output_mode": "text"
        }
    )
    
    if response2.status_code != 200:
        print(f"❌ 请求失败: {response2.status_code}")
        print(response2.text)
        return
    
    result2 = response2.json()
    agent_response = result2.get('agent_response', '')
    print(f"🤖 助手: {agent_response}\n")
    
    # 验证结果
    if "25" in agent_response:
        print("✅ 记忆功能正常！AI记得用户的年龄。")
    else:
        print("❌ 记忆功能失败！AI没有记得用户的年龄。")


if __name__ == "__main__":
    print("\n🧪 开始测试记忆功能...\n")
    
    # 测试1：chat 流式端点
    try:
        test_memory_via_chat_stream()
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    time.sleep(2)
    
    # 测试2：conversation 端点
    try:
        test_memory_via_conversation()
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print("\n✨ 测试完成！\n")

