"""
Voice Agent API 服务启动脚本

使用 Python 直接启动 FastAPI 服务，无需 uvicorn 命令行工具
"""

import sys
import os
import logging
import asyncio
from pathlib import Path

# 添加 src 目录到 Python 路径
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Set environment for development
os.environ.setdefault("VOICE_AGENT_ENVIRONMENT", "development")


def setup_logging():
    """Configure logging for the application."""
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/voice-agent-api.log", mode="a")
        ]
    )


async def check_dependencies():
    """Check if all required dependencies are available."""
    print("🔍 检查依赖...")
    
    # Load environment variables first
    try:
        from dotenv import load_dotenv
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
            print("✅ 环境变量已从 .env 加载")
        else:
            print("⚠️  .env 文件未找到，使用系统环境变量")
    except Exception as e:
        print(f"⚠️  dotenv: {e}")
    
    # Check configuration
    try:
        from config.settings import get_config

        config = get_config()
        print(f"✅ Configuration: OK (Environment: {config.environment})")
        print(f"   LLM: {config.llm.provider.value} - {config.llm.models.default}")
        print(f"   Voice: STT={config.speech.stt.provider.value}, TTS={config.speech.tts.provider.value}")
    except Exception as e:
        print(f"❌ Configuration: {e}")
        return False
    
    # Check agent core
    try:
        from agent.state import create_initial_state
        from agent.nodes import AgentNodes
        print("✅ Agent core: OK")
    except Exception as e:
        print(f"⚠️  Agent core: {e}")
    
    # Check FastAPI
    try:
        from fastapi import FastAPI
        print("✅ FastAPI: OK")
    except Exception as e:
        print(f"❌ FastAPI: {e}")
        return False
    
    return True


def main():
    """Main entry point."""
    print("Starting Voice Agent API Server...")
    print("=" * 50)
    
    setup_logging()
    
    # Check dependencies
    if not asyncio.run(check_dependencies()):
        print("Dependency check failed. Please install required packages.")
        sys.exit(1)
    
    print("All dependencies OK")
    print("Starting server on http://127.0.0.1:8000")
    print("API Documentation: http://127.0.0.1:8000/docs")
    print("Health Check: http://127.0.0.1:8000/api/v1/health")
    print("=" * 50)
    
    try:
        import uvicorn
        
        # Start the server
        uvicorn.run(
            "api.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True,
            reload_dirs=["src"]
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()