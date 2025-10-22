"""
测试 Tavily 搜索集成

验证 web_search 工具是否正确集成了 Tavily API
"""

import asyncio
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp.tools import SearchTool
from config.settings import get_config


async def test_tavily_search():
    """测试 Tavily 搜索功能"""
    print("\n" + "="*70)
    print("🔍 测试 Tavily 搜索集成")
    print("="*70)
    
    # 加载配置
    config = get_config()
    search_config = {}
    if hasattr(config, 'tools') and hasattr(config.tools, 'search_tool'):
        search_config = config.tools.search_tool.model_dump()
    
    print(f"\n📋 配置信息:")
    print(f"  - Provider: {search_config.get('provider', 'N/A')}")
    print(f"  - API Key: {'✅ 已配置' if search_config.get('api_key') else '❌ 未配置'}")
    print(f"  - Search Depth: {search_config.get('search_depth', 'basic')}")
    print(f"  - Max Results: {search_config.get('max_results', 5)}")
    
    # 创建 SearchTool
    search_tool = SearchTool(config=search_config)
    
    # 测试查询列表
    test_queries = [
        ("针对特朗普的抗议活动", 3),
        ("latest AI news 2025", 3),
        ("Python programming tutorial", 2),
    ]
    
    for query, num_results in test_queries:
        print(f"\n" + "-"*70)
        print(f"📝 查询: {query}")
        print(f"   结果数: {num_results}")
        print("-"*70)
        
        try:
            result = await search_tool.execute(query=query, num_results=num_results)
            
            if result.success:
                print(f"✅ 搜索成功！")
                print(f"\n📊 元数据:")
                print(f"  - 数据源: {result.metadata.get('source', 'N/A')}")
                print(f"  - 响应时间: {result.metadata.get('response_time', 0)} ms")
                
                # 显示 AI 答案
                if result.data.get('ai_answer'):
                    print(f"\n🤖 AI 生成的答案:")
                    answer = result.data['ai_answer']
                    # 截断过长的答案
                    if len(answer) > 300:
                        answer = answer[:300] + "..."
                    print(f"  {answer}")
                
                # 显示搜索结果
                print(f"\n📰 搜索结果 ({len(result.data['results'])} 条):")
                for i, res in enumerate(result.data['results'], 1):
                    print(f"\n  [{i}] {res['title'][:60]}")
                    print(f"      摘要: {res['snippet'][:100]}...")
                    print(f"      链接: {res['url'][:60]}")
                    print(f"      评分: {res['score']:.3f}")
                    if res.get('published_date'):
                        print(f"      日期: {res['published_date']}")
            else:
                print(f"❌ 搜索失败: {result.error}")
                if result.metadata:
                    print(f"   元数据: {result.metadata}")
        
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            import traceback
            traceback.print_exc()
        
        # 避免频繁请求
        await asyncio.sleep(1)
    
    print("\n" + "="*70)
    print("✨ 测试完成！")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_tavily_search())

