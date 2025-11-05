"""
测试启动脚本 - 直接测试导入和配置
"""
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("=" * 60)
print("测试 1: 导入配置模块")
print("=" * 60)

try:
    from config.settings import ConfigManager
    print("✅ config.settings 导入成功")
except Exception as e:
    print(f"❌ config.settings 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("测试 2: 加载配置")
print("=" * 60)

try:
    config_manager = ConfigManager()
    config = config_manager.get_config()
    print("✅ 配置加载成功")
    print(f"  Database Enabled: {config.database.enabled}")
    print(f"  LLM Provider: {config.llm.provider}")
    print(f"  LLM Model: {config.llm.models.default}")
except Exception as e:
    print(f"❌ 配置加载失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("测试 3: 导入 FastAPI 应用")
print("=" * 60)

try:
    from api.main import app
    print("✅ FastAPI 应用导入成功")
except Exception as e:
    print(f"❌ FastAPI 应用导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ 所有测试通过！")
print("=" * 60)
print("\n提示: 可以运行 'python start_server.py' 启动服务")

