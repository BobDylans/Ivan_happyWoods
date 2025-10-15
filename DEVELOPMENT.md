# Ivan_HappyWoods 开发者指南

**欢迎加入 Ivan_HappyWoods 项目!**  
本指南帮助新开发者快速了解项目并开始贡献代码。

---

## 📖 阅读顺序

如果你是第一次接触本项目,建议按以下顺序阅读文档:

1. **[PROJECT.md](./PROJECT.md)** ⭐ - 项目总览和架构说明 (必读)
2. **本文件** - 开发环境搭建和工作流
3. **[specs/001-voice-interaction-system/spec.md](./specs/001-voice-interaction-system/spec.md)** - 功能规格
4. **[specs/001-voice-interaction-system/quickstart.md](./specs/001-voice-interaction-system/quickstart.md)** - 快速开始
5. **[docs/achievements/INDEX.md](./docs/achievements/INDEX.md)** - 开发成果参考

---

## 🚀 快速开始

### 前提条件

确保你的开发环境已安装:

| 工具 | 版本要求 | 用途 | 安装检查 |
|------|----------|------|----------|
| **Python** | 3.11+ | 主要开发语言 | `python --version` |
| **pip** | Latest | 包管理器 | `pip --version` |
| **git** | Latest | 版本控制 | `git --version` |
| **venv** | Built-in | 虚拟环境 | `python -m venv --help` |

### 10 分钟设置

```bash
# 1. 克隆项目
git clone <repository-url>
cd Ivan_happyWoods

# 2. 创建虚拟环境
python -m venv venv

# Windows激活
venv\Scripts\activate

# Linux/Mac激活
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env

# 编辑 .env 文件,填入以下必需项:
# - VOICE_AGENT_LLM__API_KEY (OpenAI API Key)
# - IFLYTEK_APPID (科大讯飞 App ID)
# - IFLYTEK_APIKEY (科大讯飞 API Key)
# - IFLYTEK_APISECRET (科大讯飞 API Secret)

# 5. 验证安装
python -c "import fastapi, langgraph, httpx; print('✅ 依赖安装成功!')"

# 6. 启动服务
python start_server.py

# 7. 访问 API 文档
# 浏览器打开: http://localhost:8000/docs

# 8. 运行测试
python test_conversation.py
```

### 验证环境

```bash
# 健康检查
curl http://localhost:8000/health

# 期望输出:
# {"status":"healthy","version":"0.2.0"}

# 测试对话 API
curl -X POST http://localhost:8000/api/conversation/send \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-001",
    "message": "你好"
  }'
```

---

## 📁 项目结构速查

```
Ivan_HappyWoods/
├── src/                   # 💻 核心源代码
│   ├── agent/            # 🤖 LangGraph 代理 (对话流程)
│   ├── api/              # 🌐 FastAPI 路由 (HTTP/WebSocket API)
│   ├── services/         # 🔧 业务服务 (STT/TTS/Conversation)
│   ├── config/           # ⚙️ 配置管理
│   ├── mcp/              # 🔌 MCP 工具 (Future)
│   └── utils/            # 🛠️ 工具函数
│
├── tests/                 # 🧪 测试代码
│   ├── unit/             # 单元测试
│   └── integration/      # 集成测试
│
├── specs/                 # 📐 功能规格和计划
│   └── 001-voice-interaction-system/
│       ├── spec.md       # 功能规格
│       ├── plan.md       # 实施计划
│       ├── tasks.md      # 任务分解
│       ├── progress.md   # 进度跟踪
│       └── ...
│
├── docs/                  # 📚 项目文档
│   └── achievements/     # 开发成果和报告
│
├── config/                # 📋 配置文件 (Future)
├── logs/                  # 📝 日志输出
│
├── .env                   # 🔐 环境变量 (不提交)
├── .env.example           # 环境变量模板
├── requirements.txt       # Python 依赖
├── pytest.ini             # pytest 配置
│
├── PROJECT.md             # ⭐ 项目总览 (必读!)
├── DEVELOPMENT.md         # 本文件 - 开发指南
├── CHANGELOG.md           # 变更日志
└── start_server.py        # 服务启动脚本
```

### 关键文件说明

| 文件 | 说明 | 何时查看 |
|------|------|----------|
| `src/agent/graph.py` | LangGraph 工作流定义 | 修改对话流程时 |
| `src/agent/nodes.py` | 所有处理节点实现 | 添加新节点/修改节点逻辑 |
| `src/api/conversation_routes.py` | 对话 API 端点 | 添加/修改 API 时 |
| `src/services/conversation_service.py` | 会话管理服务 | 修改会话逻辑时 |
| `src/config/models.py` | 配置数据模型 | 添加新配置项时 |
| `.env` | 环境配置 | 配置密钥/参数时 |

---

## 🛠️ 开发工具

### 推荐的 IDE 设置

#### VS Code
```json
// .vscode/settings.json (推荐)
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false
}
```

#### PyCharm
1. File → Settings → Project → Python Interpreter
2. 选择 `./venv/bin/python`
3. Tools → Python Integrated Tools → Testing
4. 设置默认测试 runner 为 pytest

### 代码格式化

```bash
# 安装格式化工具
pip install black ruff mypy

# 格式化代码
black src/ tests/

# 检查代码质量
ruff check src/

# 类型检查
mypy src/
```

### 调试技巧

#### 1. 使用日志调试

```python
# 在代码中添加调试日志
import logging
logger = logging.getLogger(__name__)

logger.debug(f"变量值: {variable}")
logger.info(f"进入函数: my_function")
```

```bash
# 设置详细日志级别
# .env
VOICE_AGENT_LOG_LEVEL=DEBUG
```

#### 2. 使用断点调试

```python
# 在代码中设置断点
import pdb; pdb.set_trace()

# 或使用 IDE 断点功能
```

#### 3. 查看 API 请求

```bash
# 启动服务时查看详细日志
python start_server.py

# 或使用 Postman/Insomnia 测试 API
# API 文档: http://localhost:8000/docs
```

---

## 📝 开发工作流

### 标准流程

```bash
# 1. 同步主分支
git checkout main
git pull origin main

# 2. 创建功能分支
git checkout -b feature/your-feature-name

# 3. 开发功能
# ... 编码 ...

# 4. 运行测试
pytest tests/

# 5. 代码检查
ruff check src/

# 6. 提交代码
git add .
git commit -m "feat: 添加新功能描述"

# 7. 推送分支
git push origin feature/your-feature-name

# 8. 创建 Pull Request (在 GitHub 上)
```

### 提交信息规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**Type 类型:**
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式 (不影响功能)
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具配置

**示例:**
```bash
feat(agent): 添加工具调用支持

实现了 MCP 协议的工具注册和调用机制。
支持动态工具发现和执行。

Closes #123
```

```bash
fix(tts): 修复流式音频断流问题

- 优化音频分片大小
- 添加错误重试机制
- 改进 WebSocket 连接管理

Fixes #456
```

---

## 🧪 测试指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/unit/test_agent.py

# 运行特定测试函数
pytest tests/unit/test_agent.py::test_graph_creation

# 显示详细输出
pytest -v

# 显示测试覆盖率
pytest --cov=src tests/

# 生成 HTML 覆盖率报告
pytest --cov=src --cov-report=html tests/
# 打开 htmlcov/index.html 查看报告
```

### 编写测试

#### 单元测试示例

```python
# tests/unit/test_agent.py
import pytest
from src.agent.nodes import AgentNodes
from src.agent.state import create_initial_state
from src.config.models import VoiceAgentConfig

@pytest.fixture
def agent_nodes():
    """创建 AgentNodes 实例"""
    config = VoiceAgentConfig()
    return AgentNodes(config)

@pytest.mark.asyncio
async def test_process_input(agent_nodes):
    """测试输入处理节点"""
    # Arrange
    state = create_initial_state(
        session_id="test",
        user_input="你好"
    )
    
    # Act
    result = await agent_nodes.process_input(state)
    
    # Assert
    assert result["session_id"] == "test"
    assert result["user_input"] == "你好"
    assert result["next_action"] == "call_llm"
```

#### 集成测试示例

```python
# tests/integration/test_conversation_flow.py
import pytest
from httpx import AsyncClient
from src.api.main import app

@pytest.mark.asyncio
async def test_full_conversation_flow():
    """测试完整对话流程"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 发送消息
        response = await client.post("/api/conversation/send", json={
            "session_id": "test-session",
            "message": "你好"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["session_id"] == "test-session"
```

### 测试原则

1. **每个功能都要有测试**
2. **测试应该独立运行** (不依赖执行顺序)
3. **使用 fixture 共享测试数据**
4. **模拟外部服务** (避免真实 API 调用)
5. **测试覆盖率 > 80%** (目标)

---

## 🔧 常见开发任务

### 添加新的 API 端点

```python
# 1. 在 src/api/models.py 定义请求/响应模型
from pydantic import BaseModel

class MyRequest(BaseModel):
    param1: str
    param2: int

class MyResponse(BaseModel):
    result: str
    status: str

# 2. 在 src/api/my_routes.py 实现路由
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/my", tags=["My Feature"])

@router.post("/endpoint", response_model=MyResponse)
async def my_endpoint(request: MyRequest):
    """API 端点描述"""
    try:
        # 业务逻辑
        result = process_data(request.param1, request.param2)
        return MyResponse(result=result, status="success")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. 在 src/api/main.py 注册路由
from api.my_routes import router as my_router
app.include_router(my_router)

# 4. 编写测试
# tests/unit/test_my_routes.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_my_endpoint():
    # 测试代码...
```

### 添加新的 LangGraph 节点

```python
# 1. 在 src/agent/nodes.py 添加节点方法
class AgentNodes:
    async def my_new_node(self, state: AgentState) -> AgentState:
        """
        新节点功能描述
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        # 节点逻辑
        result = await self._process_something(state)
        
        # 更新状态
        state["my_field"] = result
        state["next_action"] = "next_node_name"
        
        return state

# 2. 在 src/agent/graph.py 注册节点
def _build_graph(self):
    workflow = StateGraph(AgentState)
    
    # 注册新节点
    workflow.add_node("my_new_node", self.nodes.my_new_node)
    
    # 添加边
    workflow.add_edge("previous_node", "my_new_node")
    workflow.add_edge("my_new_node", "next_node")
    
    # ...

# 3. 更新 src/agent/state.py (如需新字段)
class AgentState(TypedDict):
    # 现有字段...
    my_field: Optional[Any]  # 新增字段
```

### 添加新的配置项

```python
# 1. 在 src/config/models.py 更新配置模型
class MyFeatureConfig(BaseModel):
    enabled: bool = True
    param1: str = "default"
    param2: int = 100

class VoiceAgentConfig(BaseModel):
    # 现有配置...
    my_feature: MyFeatureConfig = MyFeatureConfig()

# 2. 在 .env.example 添加环境变量
VOICE_AGENT_MY_FEATURE__ENABLED=true
VOICE_AGENT_MY_FEATURE__PARAM1=value
VOICE_AGENT_MY_FEATURE__PARAM2=200

# 3. 在代码中使用
from src.config.settings import get_config

config = get_config()
if config.my_feature.enabled:
    # 使用配置
    value = config.my_feature.param1
```

### 添加新的依赖包

```bash
# 1. 安装包
pip install package-name

# 2. 更新 requirements.txt
pip freeze > requirements.txt

# 或手动添加到 requirements.txt
echo "package-name==1.2.3" >> requirements.txt

# 3. 在代码中导入使用
import package_name
```

---

## 🐛 调试技巧

### 调试 LangGraph 工作流

```python
# 方法 1: 添加详细日志
class AgentNodes:
    async def my_node(self, state: AgentState) -> AgentState:
        self.logger.debug(f"进入 my_node, state: {state}")
        
        # 处理逻辑
        result = await self._process(state)
        
        self.logger.debug(f"my_node 处理完成, result: {result}")
        return state

# 方法 2: 打印状态变化
state = await node.process_input(state)
print(f"After process_input: next_action={state.get('next_action')}")

state = await node.call_llm(state)
print(f"After call_llm: has_response={bool(state.get('llm_response'))}")
```

### 调试 API 请求

```python
# 方法 1: 在路由中添加日志
@router.post("/endpoint")
async def my_endpoint(request: MyRequest):
    logger.info(f"收到请求: {request}")
    
    try:
        result = await process(request)
        logger.info(f"处理成功: {result}")
        return result
    except Exception as e:
        logger.error(f"处理失败: {e}", exc_info=True)
        raise

# 方法 2: 使用 Swagger UI
# 访问 http://localhost:8000/docs
# 可以交互式测试 API 并查看请求/响应

# 方法 3: 使用 curl 测试
curl -X POST http://localhost:8000/api/endpoint \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}' \
  -v  # 显示详细信息
```

### 调试异步代码

```python
# 使用 asyncio 调试工具
import asyncio

# 启用调试模式
asyncio.get_event_loop().set_debug(True)

# 捕获未处理的异常
async def main():
    try:
        result = await my_async_function()
    except Exception as e:
        logger.error(f"异步错误: {e}", exc_info=True)
```

---

## 📊 性能优化

### 性能分析

```python
# 使用 time 测量
import time

start = time.time()
result = await my_function()
elapsed = time.time() - start
logger.info(f"函数执行时间: {elapsed:.3f}s")

# 使用 cProfile
import cProfile
cProfile.run('my_function()')
```

### 常见优化技巧

1. **复用 HTTP 客户端**
```python
# ❌ 每次创建新客户端
async def call_api():
    client = httpx.AsyncClient()
    response = await client.get(url)
    await client.aclose()

# ✅ 复用客户端
class MyService:
    def __init__(self):
        self._client = httpx.AsyncClient()
    
    async def call_api(self):
        return await self._client.get(url)
    
    async def cleanup(self):
        await self._client.aclose()
```

2. **使用异步并发**
```python
# ❌ 串行执行
result1 = await task1()
result2 = await task2()

# ✅ 并行执行
results = await asyncio.gather(task1(), task2())
result1, result2 = results
```

3. **缓存频繁请求**
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_function(param):
    # 昂贵计算
    return result
```

---

## 🆘 常见问题

### Q: 服务启动失败,提示端口占用?

```bash
# 查找占用端口的进程 (Windows)
netstat -ano | findstr :8000

# 杀死进程
taskkill /PID <PID> /F

# 或修改端口
# .env
VOICE_AGENT_API__PORT=8001
```

### Q: 导入模块失败?

```bash
# 确保虚拟环境已激活
which python  # Linux/Mac
where python  # Windows

# 重新安装依赖
pip install -r requirements.txt

# 检查 Python 路径
python -c "import sys; print(sys.path)"
```

### Q: LLM 调用超时?

```bash
# 增加超时时间
# .env
VOICE_AGENT_LLM__TIMEOUT=60

# 或检查 API Key 是否正确
echo $VOICE_AGENT_LLM__API_KEY
```

### Q: 如何清除会话数据?

```bash
# 重启服务 (内存存储会清空)
# Ctrl+C 停止服务
python start_server.py

# 或调用清除 API
curl -X DELETE http://localhost:8000/api/conversation/clear/session-id
```

---

## 📚 学习资源

### 项目相关
- [PROJECT.md](./PROJECT.md) - 项目架构和设计决策
- [specs/](./specs/001-voice-interaction-system/) - 功能规格和计划
- [docs/achievements/](./docs/achievements/) - 开发成果和最佳实践

### 技术文档
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [LangGraph 文档](https://python.langchain.com/docs/langgraph)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [httpx 文档](https://www.python-httpx.org/)
- [pytest 文档](https://docs.pytest.org/)

### 科大讯飞
- [科大讯飞开放平台](https://www.xfyun.cn/)
- [语音听写 API 文档](https://www.xfyun.cn/doc/asr/voicedictation/API.html)
- [语音合成 API 文档](https://www.xfyun.cn/doc/tts/online_tts/API.html)

---

## 🤝 贡献指南

### 提交 Pull Request

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交代码 (`git commit -m 'feat: 添加某个功能'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### PR 检查清单

- [ ] 代码符合项目编码规范
- [ ] 添加了必要的测试
- [ ] 所有测试通过
- [ ] 更新了相关文档
- [ ] 提交信息遵循 Conventional Commits
- [ ] 代码已经过自测

---

## 📞 获取帮助

- **文档**: 查看 `docs/` 和 `specs/` 目录
- **API 文档**: http://localhost:8000/docs
- **问题报告**: 创建 GitHub Issue
- **讨论**: 团队沟通渠道

---

*Happy Coding! 🎉*  
*最后更新: 2025-10-15*
