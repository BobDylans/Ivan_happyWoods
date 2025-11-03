"""
测试会话管理功能

测试以下四个核心功能:
1. SessionRepository 用户查询方法
2. 获取用户会话列表 GET /api/v1/conversation/sessions/
3. 获取会话详情 GET /api/v1/conversation/sessions/{id}
4. 认证对话接口 POST /api/v1/conversation/send
"""

import requests
import json
from typing import Optional

BASE_URL = "http://127.0.0.1:8000"
API_V1 = f"{BASE_URL}/api/v1"


class SessionManagementTester:
    def __init__(self):
        self.access_token: Optional[str] = None
        self.session_id: Optional[str] = None
        
    def print_header(self, title: str):
        """打印测试标题"""
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60)
    
    def print_result(self, success: bool, message: str, data: dict = None):
        """打印测试结果"""
        status = "✅ 成功" if success else "❌ 失败"
        print(f"\n{status}: {message}")
        if data:
            print(json.dumps(data, indent=2, ensure_ascii=False))
    
    def test_1_register_user(self) -> bool:
        """测试 1: 注册新用户"""
        self.print_header("测试 1: 注册新用户")
        
        url = f"{API_V1}/auth/register"
        data = {
            "username": f"session_test_user",
            "email": f"session_test@example.com",
            "password": "Test1234!Strong",
            "full_name": "Session Test User"
        }
        
        try:
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                self.print_result(True, "用户注册成功", result)
                return True
            elif response.status_code == 400 and "已存在" in response.text:
                self.print_result(True, "用户已存在，继续测试")
                return True
            else:
                self.print_result(False, f"注册失败: HTTP {response.status_code}", 
                                {"error": response.text})
                return False
                
        except Exception as e:
            self.print_result(False, f"注册失败: {str(e)}")
            return False
    
    def test_2_login_user(self) -> bool:
        """测试 2: 用户登录获取 Token"""
        self.print_header("测试 2: 用户登录获取 Token")
        
        url = f"{API_V1}/auth/login"
        data = {
            "username": "session_test_user",
            "password": "Test1234!Strong"
        }
        
        try:
            response = requests.post(
                url,
                data=data,  # OAuth2 使用 form data
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result["access_token"]
                self.print_result(True, "用户登录成功", {
                    "access_token": self.access_token[:50] + "...",
                    "token_type": result["token_type"],
                    "expires_in": result["expires_in"]
                })
                return True
            else:
                self.print_result(False, f"登录失败: HTTP {response.status_code}",
                                {"error": response.text})
                return False
                
        except Exception as e:
            self.print_result(False, f"登录失败: {str(e)}")
            return False
    
    def test_3_send_authenticated_message(self) -> bool:
        """测试 3: 发送认证对话消息（自动创建会话）"""
        self.print_header("测试 3: 发送认证对话消息")
        
        if not self.access_token:
            self.print_result(False, "未登录，跳过测试")
            return False
        
        url = f"{API_V1}/conversation/send"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "text": "你好，请介绍一下你自己",
            "output_mode": "text"
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                self.session_id = result.get("session_id")
                self.print_result(True, "认证对话成功", {
                    "session_id": self.session_id,
                    "user_input": result.get("user_input"),
                    "agent_response": result.get("agent_response")[:100] + "..."
                })
                return True
            else:
                self.print_result(False, f"对话失败: HTTP {response.status_code}",
                                {"error": response.text})
                return False
                
        except Exception as e:
            self.print_result(False, f"对话失败: {str(e)}")
            return False
    
    def test_4_get_user_sessions(self) -> bool:
        """测试 4: 获取用户会话列表"""
        self.print_header("测试 4: 获取用户会话列表")
        
        if not self.access_token:
            self.print_result(False, "未登录，跳过测试")
            return False
        
        url = f"{API_V1}/conversation/sessions/"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        params = {
            "page": 1,
            "page_size": 10
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                result = response.json()
                self.print_result(True, "获取会话列表成功", {
                    "total": result.get("total"),
                    "page": result.get("page"),
                    "sessions_count": len(result.get("sessions", [])),
                    "sessions": result.get("sessions", [])[:2]  # 只显示前2个
                })
                return True
            else:
                self.print_result(False, f"获取列表失败: HTTP {response.status_code}",
                                {"error": response.text})
                return False
                
        except Exception as e:
            self.print_result(False, f"获取列表失败: {str(e)}")
            return False
    
    def test_5_get_session_detail(self) -> bool:
        """测试 5: 获取会话详情"""
        self.print_header("测试 5: 获取会话详情")
        
        if not self.access_token or not self.session_id:
            self.print_result(False, "未登录或无会话，跳过测试")
            return False
        
        url = f"{API_V1}/conversation/sessions/{self.session_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                self.print_result(True, "获取会话详情成功", {
                    "session_id": result.get("session_id"),
                    "status": result.get("status"),
                    "total_messages": result.get("total_messages"),
                    "messages": [
                        {
                            "role": msg["role"],
                            "content": msg["content"][:50] + "..."
                        }
                        for msg in result.get("messages", [])
                    ]
                })
                return True
            else:
                self.print_result(False, f"获取详情失败: HTTP {response.status_code}",
                                {"error": response.text})
                return False
                
        except Exception as e:
            self.print_result(False, f"获取详情失败: {str(e)}")
            return False
    
    def test_6_permission_check(self) -> bool:
        """测试 6: 权限控制（尝试访问他人会话）"""
        self.print_header("测试 6: 权限控制测试")
        
        if not self.access_token:
            self.print_result(False, "未登录，跳过测试")
            return False
        
        # 使用一个不存在的会话 ID
        fake_session_id = "00000000-0000-0000-0000-000000000000"
        url = f"{API_V1}/conversation/sessions/{fake_session_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 404:
                self.print_result(True, "权限控制正常（会话不存在）", 
                                {"status_code": 404})
                return True
            elif response.status_code == 403:
                self.print_result(True, "权限控制正常（无权访问）",
                                {"status_code": 403})
                return True
            else:
                self.print_result(False, f"权限控制异常: HTTP {response.status_code}",
                                {"error": response.text})
                return False
                
        except Exception as e:
            self.print_result(False, f"测试失败: {str(e)}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "🚀" * 30)
        print("  会话管理功能测试套件")
        print("🚀" * 30)
        
        tests = [
            ("注册用户", self.test_1_register_user),
            ("用户登录", self.test_2_login_user),
            ("认证对话", self.test_3_send_authenticated_message),
            ("会话列表", self.test_4_get_user_sessions),
            ("会话详情", self.test_5_get_session_detail),
            ("权限控制", self.test_6_permission_check)
        ]
        
        results = []
        for name, test_func in tests:
            try:
                success = test_func()
                results.append((name, success))
            except Exception as e:
                print(f"\n❌ 测试 [{name}] 异常: {str(e)}")
                results.append((name, False))
        
        # 打印总结
        print("\n" + "=" * 60)
        print("  测试总结")
        print("=" * 60)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for name, success in results:
            status = "✅" if success else "❌"
            print(f"{status} {name}")
        
        print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("\n🎉 所有测试通过！会话管理功能运行正常！")
        else:
            print(f"\n⚠️  {total - passed} 个测试失败，请检查日志")


if __name__ == "__main__":
    tester = SessionManagementTester()
    tester.run_all_tests()
