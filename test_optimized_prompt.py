#!/usr/bin/env python3
"""
测试优化后的系统提示词

验证：
1. 系统提示词正确生成
2. 包含所有优化的模块
3. 上下文感知机制工作正常
"""

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent.nodes import AgentNodes
from agent.state import create_initial_state
from config.settings import get_config


def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def test_basic_prompt():
    """测试基本提示词生成"""
    print_section("测试 1: 基本系统提示词")
    
    try:
        # 加载配置
        config = get_config()
        nodes = AgentNodes(config)
        
        # 创建初始状态
        state = create_initial_state(
            session_id="test_prompt",
            user_input="你好",
            user_id="test_user"
        )
        
        # 生成系统提示词
        messages = nodes._prepare_llm_messages(state)
        system_prompt = messages[0]["content"]
        
        print(f"\n生成的系统提示词长度: {len(system_prompt)} 字符")
        print(f"\n提示词内容:")
        print("-" * 70)
        print(system_prompt)
        print("-" * 70)
        
        # 验证关键部分
        checks = {
            "包含角色定位": "# 角色定位" in system_prompt,
            "包含核心原则": "# 核心原则" in system_prompt,
            "包含工具列表": "# 可用工具" in system_prompt,
            "包含工具策略": "# 工具使用策略" in system_prompt,
            "包含任务框架": "# 任务处理框架" in system_prompt,
            "包含质量标准": "# 响应质量标准" in system_prompt,
        }
        
        print(f"\n✅ 关键模块检查:")
        for check_name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
        
        all_passed = all(checks.values())
        if all_passed:
            print(f"\n🎉 所有关键模块都存在！")
            return True
        else:
            print(f"\n⚠️  部分模块缺失")
            return False
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_aware_search():
    """测试搜索意图的上下文感知"""
    print_section("测试 2: 搜索意图的上下文感知")
    
    try:
        config = get_config()
        nodes = AgentNodes(config)
        
        # 创建搜索意图的状态
        state = create_initial_state(
            session_id="test_search",
            user_input="搜索人工智能",
            user_id="test_user"
        )
        state["current_intent"] = "search"
        
        # 生成系统提示词
        messages = nodes._prepare_llm_messages(state)
        system_prompt = messages[0]["content"]
        
        # 检查是否包含搜索优化提示
        has_search_optimization = "# 搜索任务优化" in system_prompt
        
        if has_search_optimization:
            print("✅ 检测到搜索意图，已添加针对性优化提示")
            
            # 提取搜索优化部分
            if "# 搜索任务优化" in system_prompt:
                start_idx = system_prompt.index("# 搜索任务优化")
                end_idx = system_prompt.find("\n\n", start_idx)
                if end_idx == -1:
                    end_idx = len(system_prompt)
                search_section = system_prompt[start_idx:end_idx]
                print(f"\n搜索优化提示内容:")
                print("-" * 70)
                print(search_section)
                print("-" * 70)
            return True
        else:
            print("❌ 未检测到搜索优化提示")
            return False
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_context_aware_tool_calls():
    """测试工具调用后的上下文感知"""
    print_section("测试 3: 工具调用后的上下文感知")
    
    try:
        config = get_config()
        nodes = AgentNodes(config)
        
        # 创建有工具调用历史的状态
        state = create_initial_state(
            session_id="test_tools",
            user_input="北京天气",
            user_id="test_user"
        )
        
        # 模拟工具调用
        state["tool_calls"] = [
            {
                "id": "call_123",
                "name": "get_weather",
                "arguments": {"location": "北京"}
            }
        ]
        
        # 生成系统提示词
        messages = nodes._prepare_llm_messages(state)
        system_prompt = messages[0]["content"]
        
        # 检查是否包含工具调用后的提示
        has_tool_reminder = "# 当前状态" in system_prompt
        
        if has_tool_reminder:
            print("✅ 检测到工具调用历史，已添加状态提醒")
            
            # 提取状态提醒部分
            if "# 当前状态" in system_prompt:
                start_idx = system_prompt.index("# 当前状态")
                end_idx = system_prompt.find("\n\n", start_idx)
                if end_idx == -1:
                    end_idx = len(system_prompt)
                status_section = system_prompt[start_idx:end_idx]
                print(f"\n状态提醒内容:")
                print("-" * 70)
                print(status_section)
                print("-" * 70)
            return True
        else:
            print("❌ 未检测到状态提醒")
            return False
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_context_aware_long_conversation():
    """测试长对话的上下文感知"""
    print_section("测试 4: 长对话的上下文感知")
    
    try:
        config = get_config()
        nodes = AgentNodes(config)
        
        # 创建长对话状态
        state = create_initial_state(
            session_id="test_long",
            user_input="那它呢？",
            user_id="test_user"
        )
        
        # 添加多条历史消息（超过6条）
        from agent.state import ConversationMessage, MessageRole
        from datetime import datetime
        
        for i in range(8):
            state["messages"].append(
                ConversationMessage(
                    id=f"msg_{i}",
                    role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                    content=f"消息 {i}",
                    timestamp=datetime.now()
                )
            )
        
        # 生成系统提示词
        messages = nodes._prepare_llm_messages(state)
        system_prompt = messages[0]["content"]
        
        # 检查是否包含连贯性提示
        has_continuity_reminder = "# 对话连贯性" in system_prompt
        
        if has_continuity_reminder:
            print(f"✅ 检测到长对话（{len(state['messages'])} 条消息），已添加连贯性提醒")
            
            # 提取连贯性提醒部分
            if "# 对话连贯性" in system_prompt:
                start_idx = system_prompt.index("# 对话连贯性")
                end_idx = system_prompt.find("\n\n", start_idx)
                if end_idx == -1:
                    end_idx = len(system_prompt)
                continuity_section = system_prompt[start_idx:end_idx]
                print(f"\n连贯性提醒内容:")
                print("-" * 70)
                print(continuity_section)
                print("-" * 70)
            return True
        else:
            print("❌ 未检测到连贯性提醒")
            return False
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 18 + "优化后的系统提示词测试" + " " * 23 + "║")
    print("╚" + "=" * 68 + "╝")
    
    results = []
    
    # 运行测试
    results.append(("基本提示词生成", test_basic_prompt()))
    results.append(("搜索意图感知", test_context_aware_search()))
    results.append(("工具调用后感知", test_context_aware_tool_calls()))
    results.append(("长对话感知", test_context_aware_long_conversation()))
    
    # 汇总结果
    print_section("测试结果汇总")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}: {test_name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！优化后的提示词工作正常！")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

