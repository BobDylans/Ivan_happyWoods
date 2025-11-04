"""
测试会话删除功能

验证 HybridSessionManager 的会话删除能力（内存 + 数据库）
"""
import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.hybrid_session_manager import initialize_session_manager, get_session_manager
from src.database.connection import get_async_session, init_db
from src.config.settings import ConfigManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def setup_database():
    """初始化数据库连接"""
    try:
        # 加载配置
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # 初始化数据库 (传入 DatabaseConfig 对象，而不是 URL 字符串)
        await init_db(config.database, echo=False)
        logger.info("✅ 数据库初始化成功")
        return True
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}", exc_info=True)
        return False


async def test_session_deletion():
    """测试会话删除功能"""
    
    # 初始化 session manager
    async with get_async_session() as db_session:
        await initialize_session_manager(db_session)
    
    manager = get_session_manager()
    if not manager:
        logger.error("❌ 无法获取 session manager")
        return
    
    try:
        test_session_id = "test_delete_session_001"
        
        # 1. 添加一些测试消息
        logger.info("=" * 60)
        logger.info("步骤 1: 添加测试消息")
        logger.info("=" * 60)
        
        await manager.add_message(
            session_id=test_session_id,
            role="user",
            content="这是第一条测试消息"
        )
        
        await manager.add_message(
            session_id=test_session_id,
            role="assistant",
            content="这是回复消息"
        )
        
        # 2. 验证消息存在
        logger.info("\n" + "=" * 60)
        logger.info("步骤 2: 验证消息存在")
        logger.info("=" * 60)
        
        history = await manager.get_history(test_session_id)
        logger.info(f"✅ 会话历史长度: {len(history)}")
        for i, msg in enumerate(history, 1):
            logger.info(f"  消息 {i}: [{msg['role']}] {msg['content'][:50]}...")
        
        # 3. 获取统计信息（删除前）
        logger.info("\n" + "=" * 60)
        logger.info("步骤 3: 删除前的统计信息")
        logger.info("=" * 60)
        
        stats = manager.get_stats()
        logger.info(f"📊 活跃会话数: {stats['active_sessions']}")
        logger.info(f"📊 数据库模式: {'启用' if stats['database_enabled'] else '禁用'}")
        logger.info(f"📊 降级模式: {'是' if stats['fallback_mode'] else '否'}")
        logger.info(f"📊 缓存命中: {stats['cache_hits']}, 未命中: {stats['cache_misses']}")
        
        # 4. 删除会话
        logger.info("\n" + "=" * 60)
        logger.info("步骤 4: 删除会话")
        logger.info("=" * 60)
        
        await manager.clear_session(test_session_id)
        logger.info(f"✅ 会话已删除: {test_session_id}")
        
        # 5. 验证删除结果
        logger.info("\n" + "=" * 60)
        logger.info("步骤 5: 验证删除结果")
        logger.info("=" * 60)
        
        history_after = await manager.get_history(test_session_id)
        logger.info(f"📭 删除后的会话历史长度: {len(history_after)}")
        
        if len(history_after) == 0:
            logger.info("✅ 会话删除成功！内存和数据库均已清空")
        else:
            logger.error(f"❌ 删除失败！仍有 {len(history_after)} 条消息")
        
        # 6. 获取统计信息（删除后）
        stats_after = manager.get_stats()
        logger.info(f"\n📊 删除后活跃会话数: {stats_after['active_sessions']}")
        logger.info(f"📊 总缓存命中: {stats_after['cache_hits']}, 未命中: {stats_after['cache_misses']}")
        
        # 7. 测试删除不存在的会话
        logger.info("\n" + "=" * 60)
        logger.info("步骤 6: 测试删除不存在的会话")
        logger.info("=" * 60)
        
        await manager.clear_session("non_existent_session_999")
        logger.info("✅ 删除不存在的会话不会抛出异常")
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 所有测试完成！")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        raise


async def test_batch_deletion():
    """测试批量删除功能"""
    
    manager = get_session_manager()
    if not manager:
        logger.error("❌ 无法获取 session manager")
        return
    
    try:
        logger.info("\n" + "=" * 60)
        logger.info("测试批量删除")
        logger.info("=" * 60)
        
        # 创建多个会话
        session_ids = [f"batch_test_{i}" for i in range(5)]
        
        for sid in session_ids:
            await manager.add_message(
                session_id=sid,
                role="user",
                content=f"测试消息 - 会话 {sid}"
            )
        
        logger.info(f"✅ 创建了 {len(session_ids)} 个测试会话")
        
        # 批量删除
        for sid in session_ids:
            await manager.clear_session(sid)
        
        logger.info(f"✅ 已删除 {len(session_ids)} 个会话")
        
        # 验证
        remaining = 0
        for sid in session_ids:
            history = await manager.get_history(sid)
            remaining += len(history)
        
        if remaining == 0:
            logger.info("✅ 批量删除成功！")
        else:
            logger.error(f"❌ 批量删除失败！仍有 {remaining} 条消息")
        
    except Exception as e:
        logger.error(f"❌ 批量删除测试失败: {e}", exc_info=True)


async def main():
    """主函数"""
    logger.info("🚀 开始测试会话删除功能\n")
    
    # 初始化数据库
    if not await setup_database():
        logger.error("❌ 数据库初始化失败，终止测试")
        return
    
    # 测试 1: 基础删除功能
    await test_session_deletion()
    
    # 等待一下
    await asyncio.sleep(1)
    
    # 测试 2: 批量删除
    await test_batch_deletion()
    
    logger.info("\n✅ 所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
