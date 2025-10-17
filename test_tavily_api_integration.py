#!/usr/bin/env python3
"""
测试 Tavily 搜索工具通过 API 端点的集成

验证：
1. 通过 FastAPI 端点调用 Tavily 搜索
2. 完整的请求-响应流程
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "dev-test-key-123"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


def wait_for_server(timeout=30):
    """等待服务器启动"""
    print("⏳ 等待服务器启动...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/health",
                headers=HEADERS,
                timeout=2
            )
            if response.status_code == 200:
                print("✅ 服务器已启动")
                return True
        except:
            pass
        time.sleep(1)
    
    print("❌ 服务器启动超时")
    return False


def test_search_via_api():
    """通过 API 测试搜索功能"""
    print("\n" + "="*60)
    print("🔍 通过 API 端点测试 Tavily 搜索")
    print("="*60)
    
    test_queries = [
        ("Python programming", 3),
        ("人工智能最新进展", 5),
        ("latest AI news 2025", 3),
    ]
    
    for query, num_results in test_queries:
        print(f"\n📝 查询: {query} (结果数: {num_results})")
        
        payload = {
            "query": query,
            "num_results": num_results
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/tools/execute/web_search",
                headers=HEADERS,
                json=payload,
                timeout=30
            )
            
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # 响应格式: {tool, data, metadata} 或 {tool, error, error_code}
                if "data" in data and not data.get("error"):
                    result_data = data.get("data", {})
                    results = result_data.get("results", [])
                    ai_answer = result_data.get("ai_answer", "")
                    
                    print(f"   ✅ 成功获得 {len(results)} 个结果")
                    
                    if ai_answer:
                        print(f"   🤖 AI 答案: {ai_answer[:80]}...")
                    
                    # 显示第一个结果
                    if results:
                        first = results[0]
                        print(f"   📌 首个结果:")
                        print(f"      标题: {first.get('title', 'N/A')[:50]}...")
                        print(f"      链接: {first.get('url', 'N/A')[:50]}...")
                        print(f"      评分: {first.get('score', 0):.3f}")
                else:
                    print(f"   ❌ 工具执行失败: {data.get('error', '未知错误')}")
            else:
                print(f"   ❌ HTTP 错误: {response.status_code}")
                print(f"      {response.text[:200]}")
        
        except Exception as e:
            print(f"   ❌ 异常: {e}")
        
        time.sleep(1)  # Rate limiting


def test_tool_list():
    """验证 web_search 工具在工具列表中"""
    print("\n" + "="*60)
    print("📋 验证工具列表")
    print("="*60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/tools",
            headers=HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            tools = data.get("tools", [])
            
            tool_names = [t.get("name") if isinstance(t, dict) else str(t) for t in tools]
            
            if "web_search" in tool_names:
                print("✅ web_search 工具已注册")
                
                # 找到 web_search 的详细信息
                for tool in tools:
                    if isinstance(tool, dict) and tool.get("name") == "web_search":
                        print(f"\n工具详情:")
                        print(f"  名称: {tool.get('name')}")
                        print(f"  描述: {tool.get('description', 'N/A')[:60]}...")
                        print(f"  参数: {len(tool.get('parameters', []))} 个")
                        break
            else:
                print("❌ web_search 工具未找到")
                print(f"   已注册的工具: {', '.join(tool_names)}")
        else:
            print(f"❌ 获取工具列表失败: {response.status_code}")
    
    except Exception as e:
        print(f"❌ 异常: {e}")


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "🔍 Tavily 搜索 API 集成测试" + " "*17 + "║")
    print("╚" + "="*58 + "╝")
    
    try:
        # 等待服务器
        if not wait_for_server():
            print("\n⚠️  请先启动服务器: python start_server.py")
            return
        
        # 测试工具列表
        test_tool_list()
        
        # 测试搜索功能
        test_search_via_api()
        
        print("\n" + "="*60)
        print("✅ API 集成测试完成！")
        print("="*60)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")


if __name__ == "__main__":
    main()

