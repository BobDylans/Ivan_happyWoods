"""
测试 Tavily API 配置
"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_env_variables():
    """测试环境变量是否正确加载"""
    print("=" * 60)
    print("🔍 检查环境变量配置")
    print("=" * 60)
    
    # 加载 .env.ollama 文件
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env.ollama"
    
    if env_path.exists():
        print(f"✅ 找到配置文件: {env_path}")
        load_dotenv(env_path)
    else:
        print(f"❌ 配置文件不存在: {env_path}")
        return
    
    # 检查 TAVILY_API_KEY
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        print(f"✅ TAVILY_API_KEY: {tavily_key[:15]}...")
    else:
        print("❌ TAVILY_API_KEY 未设置")
    
    # 检查嵌套路径
    nested_key = os.getenv("VOICE_AGENT_TOOLS__SEARCH_TOOL__API_KEY")
    if nested_key:
        print(f"✅ VOICE_AGENT_TOOLS__SEARCH_TOOL__API_KEY: {nested_key[:15]}...")
    else:
        print("❌ VOICE_AGENT_TOOLS__SEARCH_TOOL__API_KEY 未设置")
    
    # 检查其他配置
    timeout = os.getenv("VOICE_AGENT_TOOLS__SEARCH_TOOL__TIMEOUT", "15")
    print(f"✅ Timeout: {timeout}s")
    
    max_results = os.getenv("VOICE_AGENT_TOOLS__SEARCH_TOOL__MAX_RESULTS", "5")
    print(f"✅ Max Results: {max_results}")

def test_search_tool():
    """测试 SearchTool 初始化"""
    print("\n" + "=" * 60)
    print("🔧 测试 SearchTool 初始化")
    print("=" * 60)
    
    from mcp.init_tools import initialize_default_tools
    
    try:
        tools = initialize_default_tools()
        print(f"✅ 成功初始化 {len(tools)} 个工具")
        print(f"📋 工具列表: {', '.join(tools)}")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()

async def test_real_search():
    """测试真实的搜索调用"""
    print("\n" + "=" * 60)
    print("🌐 测试真实搜索功能")
    print("=" * 60)
    
    from mcp.registry import get_tool_registry
    
    registry = get_tool_registry()
    search_tool = registry.get("web_search")  # 修复: 使用 get() 而不是 get_tool()
    
    if not search_tool:
        print("❌ SearchTool 未注册")
        return
    
    print("✅ SearchTool 已注册")
    
    # 执行测试搜索
    print("\n🔍 执行搜索: 'Python tutorial'")
    result = await search_tool.execute(query="Python tutorial", num_results=3)
    
    if result.success:
        print(f"✅ 搜索成功!")
        print(f"📊 返回 {result.data.get('total_results', 0)} 个结果")
        
        if result.metadata.get("source") == "mock":
            print("⚠️  使用的是 Mock 数据（API Key 未生效）")
        else:
            print("✅ 使用的是真实 Tavily API")
            
        # 显示第一个结果
        results = result.data.get("results", [])
        if results:
            print(f"\n📄 第一个结果:")
            print(f"   标题: {results[0].get('title', 'N/A')}")
            print(f"   摘要: {results[0].get('snippet', 'N/A')[:100]}...")
            print(f"   URL: {results[0].get('url', 'N/A')}")
    else:
        print(f"❌ 搜索失败: {result.error}")

if __name__ == "__main__":
    import asyncio
    
    # 测试环境变量
    test_env_variables()
    
    # 测试工具初始化
    test_search_tool()
    
    # 测试真实搜索
    print("\n" + "=" * 60)
    print("▶️  运行异步测试...")
    print("=" * 60)
    asyncio.run(test_real_search())
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
