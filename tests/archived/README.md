# 归档测试文件

本目录包含开发过程中的临时测试脚本，已归档保存以备参考。

## 📋 文件说明

### Ollama 集成测试
- `test_ollama.py` - Ollama 基础功能测试
- `test_ollama_direct.py` - Ollama 直接 API 调用测试
- `test_ollama_simple.py` - Ollama 简化测试
- `test_ollama_params.py` - Ollama 参数验证测试
- `test_ollama_tools.py` - Ollama 工具调用测试
- `test_ollama_tool_calls_parsing.py` - Ollama 工具调用解析测试

### Tavily 搜索测试
- `test_tavily_config.py` - Tavily 配置验证测试
- `test_tavily_direct.py` - Tavily 直接 API 调用测试

### 功能测试
- `test_auth_api.py` - API 认证功能测试
- `test_user_binding.py` - 用户绑定功能测试
- `test_session_management.py` - 会话管理功能测试
- `test_project_api.py` - 项目 API 测试
- `test_tool_choice.py` - 工具选择测试

## ⚠️ 注意事项

1. **这些是临时测试文件** - 主要用于开发调试
2. **不建议直接运行** - 可能依赖特定的环境配置
3. **参考价值** - 可作为功能实现的参考示例
4. **正式测试** - 请使用 `tests/unit/` 和 `tests/integration/` 中的测试

## 🔧 正式测试位置

正式的测试文件位于：
- `tests/unit/` - 单元测试
- `tests/integration/` - 集成测试

## 📅 归档信息

- **归档日期**: 2025-11-04
- **原因**: 清理项目根目录，整理测试文件结构
- **文件数量**: 13 个临时测试脚本

---

*如需恢复某个测试文件，可以从此目录复制回项目根目录*
