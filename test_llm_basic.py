"""
简单的 LLM 功能测试脚本

用于验证 OpenAI LLM 调用是否正常工作
"""
import asyncio
import logging
from src.config.settings import ConfigManager
from src.agent.graph import create_voice_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_llm_basic():
    """测试基本的 LLM 对话功能"""
    try:
        logger.info("=" * 60)
        logger.info("测试 1: 加载配置")
        logger.info("=" * 60)
        
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        logger.info(f"✅ 配置加载成功")
        logger.info(f"  LLM Provider: {config.llm.provider}")
        logger.info(f"  LLM Base URL: {config.llm.base_url}")
        logger.info(f"  Default Model: {config.llm.models.default}")
        logger.info(f"  Database Enabled: {config.database.enabled}")
        
        logger.info("\n" + "=" * 60)
        logger.info("测试 2: 初始化 Voice Agent")
        logger.info("=" * 60)
        
        agent = create_voice_agent()
        logger.info(f"✅ Voice Agent 初始化成功")
        
        logger.info("\n" + "=" * 60)
        logger.info("测试 3: 发送测试消息")
        logger.info("=" * 60)
        
        test_message = "你好，请用一句话介绍你自己。"
        session_id = "test_session_001"
        
        logger.info(f"发送消息: {test_message}")
        logger.info(f"会话 ID: {session_id}")
        
        # 调用 agent
        result = await agent.ainvoke(
            {
                "user_input": test_message,
                "session_id": session_id,
                "external_history": []
            },
            config={"configurable": {"thread_id": session_id}}
        )
        
        logger.info("\n" + "=" * 60)
        logger.info("测试结果")
        logger.info("=" * 60)
        
        if result and "final_response" in result:
            logger.info(f"✅ 收到 AI 回复:")
            logger.info(f"  {result['final_response'][:200]}...")
            logger.info(f"\n✅ 所有测试通过！LLM 功能正常")
            return True
        else:
            logger.error(f"❌ 未收到有效回复")
            logger.error(f"  Result: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = asyncio.run(test_llm_basic())
    exit(0 if success else 1)

