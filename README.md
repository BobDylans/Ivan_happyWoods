# 🎤 Ivan_HappyWoods

> **企业级语音 AI 代理系统** - 基于 LangGraph + FastAPI + 科大讯飞语音

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.6+-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🚀 快速开始

```bash
# 1. 克隆项目
git clone <repository-url>
cd Ivan_happyWoods

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填写必需的 API Keys:
# - VOICE_AGENT_LLM__API_KEY (OpenAI 或兼容 API)
# - IFLYTEK_APPID, IFLYTEK_APIKEY, IFLYTEK_APISECRET (科大讯飞)

# 4. 启动服务
python start_server.py

# 5. 测试
# 浏览器访问: http://localhost:8000/docs (API 文档)
# 或打开: demo/chat_demo.html (聊天界面)
```

---

## ✨ 核心特性

- 🎤 **语音对话**: 科大讯飞 STT/TTS，支持流式响应
- 🤖 **智能代理**: LangGraph 工作流，多步骤推理
- 🔧 **工具调用**: MCP 协议，7+ 内置工具（搜索、计算器、时间等）
- � **对话管理**: 会话历史、上下文记忆（最多20条消息）
- � **流式传输**: SSE + WebSocket 双模式
- 🎨 **Markdown 渲染**: 格式化输出，代码高亮

---

## 📚 文档

- **[PROJECT.md](PROJECT.md)** - 完整项目架构和技术栈 ⭐
- **[CHANGELOG.md](CHANGELOG.md)** - 版本变更历史
- **[docs/](docs/)** - 详细技术文档和指南

---

## 🏗️ 技术栈

| 组件 | 技术 |
|------|------|
| **Web 框架** | FastAPI + Uvicorn |
| **AI 框架** | LangGraph + LangChain |
| **LLM** | OpenAI API (兼容) |
| **语音** | 科大讯飞 STT/TTS |
| **工具协议** | MCP (Model Context Protocol) |

---

##  贡献

欢迎提交 Pull Request 或创建 Issue！

---

## 📝 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

*Version: 0.3.0 | Last Updated: 2025-10-29*

