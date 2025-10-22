"""
检查会话历史管理器

这个脚本模拟SessionHistoryManager的行为，验证记忆功能
"""

import sys
sys.path.insert(0, 'src')

from utils.session_manager import SessionHistoryManager

# 创建会话管理器实例
manager = SessionHistoryManager(max_history=20, ttl_hours=24)

# 模拟对话
session_id = "test_session_123"

print("\n" + "="*60)
print("测试会话历史管理器")
print("="*60)

# 第一轮对话
print("\n第一轮对话:")
manager.add_message(session_id, "user", "我叫张三")
manager.add_message(session_id, "assistant", "你好，张三！很高兴认识你。")

# 获取历史
history = manager.get_history(session_id)
print(f"✅ 历史记录长度: {len(history)}")
for i, msg in enumerate(history, 1):
    print(f"  {i}. {msg['role']}: {msg['content'][:50]}...")

# 第二轮对话
print("\n第二轮对话:")
manager.add_message(session_id, "user", "你还记得我叫什么名字吗？")
manager.add_message(session_id, "assistant", "当然记得，你叫张三。")

# 获取历史
history = manager.get_history(session_id)
print(f"✅ 历史记录长度: {len(history)}")
for i, msg in enumerate(history, 1):
    print(f"  {i}. {msg['role']}: {msg['content'][:50]}...")

# 测试历史记录限制
print("\n\n测试会话限制:")
manager2 = SessionHistoryManager(max_history=3, ttl_hours=24)
session_id2 = "test_session_456"

for i in range(10):
    manager2.add_message(session_id2, "user", f"消息 {i}")

history2 = manager2.get_history(session_id2)
print(f"✅ 添加了10条消息，最大限制3条，实际保存: {len(history2)} 条")
for i, msg in enumerate(history2, 1):
    print(f"  {i}. {msg['role']}: {msg['content']}")

print("\n✨ 会话历史管理器测试完成！")
print("="*60 + "\n")

