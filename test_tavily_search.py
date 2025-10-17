#!/usr/bin/env python3
"""
测试 Tavily 搜索工具

验证：
1. SearchTool 使用 Tavily API 正常工作
2. 搜索结果格式正确
3. AI 生成的答案可用
"""

import asyncio
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp.tools import SearchTool
from mcp.base import ToolResult


async def test_search_basic():
    """测试基本搜索功能"""
    print("\n" + "="*60)
    print("🔍 测试 1: 基本搜索功能")
    print("="*60)
    
    search_tool = SearchTool()
    
    query = "What is Python programming language"
    print(f"\n查询: {query}")
    
    result = await search_tool.execute(query=query, num_results=3)
    
    if result.success:
        print(f"✅ 搜索成功！")
        print(f"\n📊 结果统计:")
        print(f"  - 查询: {result.data['query']}")
        print(f"  - 结果数: {result.data['total_results']}")
        print(f"  - 数据源: {result.metadata['source']}")
        
        if result.data.get('ai_answer'):
            print(f"\n🤖 AI 生成的答案:")
            print(f"  {result.data['ai_answer'][:200]}...")
        
        print(f"\n📝 搜索结果:")
        for i, res in enumerate(result.data['results'], 1):
            print(f"\n  结果 {i}:")
            print(f"    标题: {res['title'][:60]}...")
            print(f"    摘要: {res['snippet'][:80]}...")
            print(f"    链接: {res['url'][:60]}...")
            print(f"    评分: {res['score']:.3f}")
        
        return True
    else:
        print(f"❌ 搜索失败: {result.error}")
        if result.metadata:
            print(f"   详情: {result.metadata}")
        return False


async def test_search_chinese():
    """测试中文搜索"""
    print("\n" + "="*60)
    print("🔍 测试 2: 中文搜索")
    print("="*60)
    
    search_tool = SearchTool()
    
    query = "人工智能的最新发展"
    print(f"\n查询: {query}")
    
    result = await search_tool.execute(query=query, num_results=5)
    
    if result.success:
        print(f"✅ 中文搜索成功！")
        print(f"  - 结果数: {result.data['total_results']}")
        
        if result.data.get('ai_answer'):
            print(f"\n🤖 AI 答案:")
            print(f"  {result.data['ai_answer'][:150]}...")
        
        print(f"\n📝 前3个结果:")
        for i, res in enumerate(result.data['results'][:3], 1):
            print(f"\n  {i}. {res['title'][:50]}...")
            print(f"     {res['url'][:50]}...")
        
        return True
    else:
        print(f"❌ 中文搜索失败: {result.error}")
        return False


async def test_search_num_results():
    """测试结果数量控制"""
    print("\n" + "="*60)
    print("🔍 测试 3: 结果数量控制")
    print("="*60)
    
    search_tool = SearchTool()
    
    test_cases = [1, 3, 5, 10]
    
    for num in test_cases:
        print(f"\n请求 {num} 个结果...")
        result = await search_tool.execute(query="AI news", num_results=num)
        
        if result.success:
            actual = result.data['total_results']
            print(f"  ✅ 请求 {num} 个，实际获得 {actual} 个")
            if actual != num:
                print(f"     ⚠️  注意: 实际结果数可能少于请求数")
        else:
            print(f"  ❌ 失败: {result.error}")
            return False
    
    return True


async def test_search_error_handling():
    """测试错误处理"""
    print("\n" + "="*60)
    print("🔍 测试 4: 错误处理")
    print("="*60)
    
    search_tool = SearchTool()
    
    # 测试空查询
    print(f"\n测试空查询...")
    result = await search_tool.execute(query="", num_results=3)
    
    if result.success:
        print(f"  ✅ 空查询也能处理")
    else:
        print(f"  ✅ 正确处理空查询错误: {result.error[:50]}...")
    
    return True


async def test_search_schema():
    """测试工具模式"""
    print("\n" + "="*60)
    print("🔍 测试 5: 工具模式 (OpenAI Schema)")
    print("="*60)
    
    search_tool = SearchTool()
    schema = search_tool.to_openai_schema()
    
    print(f"\n工具名称: {schema['function']['name']}")
    print(f"描述: {schema['function']['description'][:60]}...")
    print(f"\n参数:")
    for param_name, param_info in schema['function']['parameters']['properties'].items():
        required = param_name in schema['function']['parameters'].get('required', [])
        print(f"  - {param_name} ({param_info['type']}): {param_info.get('description', 'No description')[:40]}...")
        print(f"    必需: {'是' if required else '否'}")
    
    return True


async def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "🔍 Tavily 搜索工具测试" + " "*18 + "║")
    print("╚" + "="*58 + "╝")
    
    try:
        results = []
        
        # 运行测试
        results.append(("基本搜索", await test_search_basic()))
        await asyncio.sleep(1)  # Rate limiting
        
        results.append(("中文搜索", await test_search_chinese()))
        await asyncio.sleep(1)
        
        results.append(("结果数量控制", await test_search_num_results()))
        await asyncio.sleep(1)
        
        results.append(("错误处理", await test_search_error_handling()))
        
        results.append(("工具模式", await test_search_schema()))
        
        # 汇总结果
        print("\n" + "="*60)
        print("📊 测试结果汇总")
        print("="*60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {status}: {test_name}")
        
        print(f"\n总计: {passed}/{total} 测试通过")
        
        if passed == total:
            print("\n🎉 所有测试通过！Tavily 搜索工具工作正常！")
        else:
            print(f"\n⚠️  有 {total - passed} 个测试失败")
        
        return passed == total
    
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        return False
    
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

