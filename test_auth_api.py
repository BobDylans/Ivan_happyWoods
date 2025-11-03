#!/usr/bin/env python
"""测试认证 API"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1/auth"

def test_register():
    """测试用户注册"""
    print("=" * 70)
    print("测试用户注册")
    print("=" * 70)
    
    url = f"{BASE_URL}/register"
    data = {
        "username": "testuser3",
        "email": "test3@example.com",
        "password": "Test1234",
        "full_name": "测试用户3"
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            print("\n[SUCCESS] 用户注册成功！")
            return True
        else:
            print(f"\n[ERROR] 注册失败！")
            try:
                error_detail = response.json()
                print(f"错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                pass
            return False
    except Exception as e:
        print(f"[ERROR] 请求异常: {e}")
        return False

def test_login():
    """测试用户登录"""
    print("\n" + "=" * 70)
    print("测试用户登录")
    print("=" * 70)
    
    url = f"{BASE_URL}/login"
    data = {
        "username": "testuser3",
        "password": "Test1234"
    }
    
    try:
        # 注意：登录使用 form-data，不是 JSON
        response = requests.post(url, data=data, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n[SUCCESS] 用户登录成功！")
            print(f"Access Token: {result.get('access_token', 'N/A')[:50]}...")
            print(f"Token Type: {result.get('token_type', 'N/A')}")
            print(f"Expires In: {result.get('expires_in', 'N/A')} 秒")
            return result.get('access_token')
        else:
            print(f"\n[ERROR] 登录失败！")
            try:
                error_detail = response.json()
                print(f"错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                pass
            return None
    except Exception as e:
        print(f"[ERROR] 请求异常: {e}")
        return None

def test_get_current_user(access_token):
    """测试获取当前用户信息"""
    print("\n" + "=" * 70)
    print("测试获取用户信息")
    print("=" * 70)
    
    url = f"{BASE_URL}/me"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n[SUCCESS] 获取用户信息成功！")
            print(f"User ID: {result.get('user_id', 'N/A')}")
            print(f"Username: {result.get('username', 'N/A')}")
            print(f"Email: {result.get('email', 'N/A')}")
            print(f"Full Name: {result.get('full_name', 'N/A')}")
            print(f"Is Active: {result.get('is_active', 'N/A')}")
            return True
        else:
            print(f"\n[ERROR] 获取用户信息失败！")
            try:
                error_detail = response.json()
                print(f"错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                pass
            return False
    except Exception as e:
        print(f"[ERROR] 请求异常: {e}")
        return False

if __name__ == "__main__":
    print("开始测试认证 API...\n")
    
    # 测试注册
    if test_register():
        # 测试登录
        access_token = test_login()
        
        if access_token:
            # 测试获取用户信息
            test_get_current_user(access_token)
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
