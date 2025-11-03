"""
测试用户绑定功能

验证会话是否正确绑定到用户
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"
API_V1 = f"{BASE_URL}/api/v1"


def test_user_binding():
    """测试用户-会话绑定"""
    
    print("=" * 70)
    print("  测试用户-会话绑定功能")
    print("=" * 70)
    
    # 1. 登录获取 Token
    print("\n📝 步骤 1: 用户登录...")
    login_url = f"{API_V1}/auth/login"
    login_data = {
        "username": "session_test_user",
        "password": "Test1234!Strong"
    }
    
    try:
        response = requests.post(
            login_url,
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            print(f"❌ 登录失败: {response.status_code}")
            print(f"   错误: {response.text}")
            return False
        
        result = response.json()
        access_token = result["access_token"]
        print(f"✅ 登录成功")
        print(f"   Token: {access_token[:50]}...")
        
    except Exception as e:
        print(f"❌ 登录失败: {str(e)}")
        return False
    
    # 2. 发送对话（不提供 session_id，测试自动创建）
    print("\n💬 步骤 2: 发送对话消息（不提供 session_id）...")
    chat_url = f"{API_V1}/conversation/send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    chat_data = {
        "text": "测试用户绑定功能",
        "output_mode": "text"
        # 注意：没有提供 session_id
    }
    
    try:
        response = requests.post(chat_url, json=chat_data, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ 对话失败: {response.status_code}")
            print(f"   错误: {response.text}")
            return False
        
        result = response.json()
        session_id = result.get("session_id")
        print(f"✅ 对话成功")
        print(f"   Session ID: {session_id}")
        print(f"   回复: {result.get('agent_response', '')[:100]}...")
        
    except Exception as e:
        print(f"❌ 对话失败: {str(e)}")
        return False
    
    # 3. 获取会话列表，验证 user_id 是否绑定
    print("\n📋 步骤 3: 获取会话列表，验证用户绑定...")
    sessions_url = f"{API_V1}/conversation/sessions/"
    
    try:
        response = requests.get(sessions_url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ 获取会话列表失败: {response.status_code}")
            print(f"   错误: {response.text}")
            return False
        
        result = response.json()
        sessions = result.get("sessions", [])
        
        if not sessions:
            print(f"❌ 会话列表为空")
            return False
        
        print(f"✅ 获取会话列表成功 (共 {len(sessions)} 个会话)")
        
        # 查找刚创建的会话
        target_session = None
        for s in sessions:
            if s["session_id"] == session_id:
                target_session = s
                break
        
        if not target_session:
            print(f"❌ 未找到刚创建的会话: {session_id}")
            return False
        
        print(f"\n🔍 会话信息:")
        print(f"   Session ID: {target_session['session_id']}")
        print(f"   User ID: {target_session['user_id']}")
        print(f"   状态: {target_session['status']}")
        print(f"   消息数量: {target_session['message_count']}")
        print(f"   创建时间: {target_session['created_at']}")
        
        # 验证 user_id 不为空
        if not target_session['user_id']:
            print(f"\n❌ 失败: user_id 为空，会话未正确绑定用户！")
            return False
        
        print(f"\n✅ 成功: user_id 已正确绑定！")
        return True
        
    except Exception as e:
        print(f"❌ 获取会话列表失败: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_user_binding()
    
    print("\n" + "=" * 70)
    if success:
        print("  🎉 测试通过！用户-会话绑定功能正常！")
    else:
        print("  ⚠️  测试失败！请检查日志！")
    print("=" * 70)
