# 数据库持久化集成 - 详细实施计划

## 📊 当前数据库状态

### ✅ 已有表结构 (5个表)

#### 1. **langgraph_checkpoints** (30条记录)
- ✅ 用途: LangGraph 状态检查点存储
- ✅ 状态: 正在使用中 (PostgreSQLCheckpointer)
- 字段:
  - thread_id (VARCHAR255) - 对话线程ID
  - checkpoint_id (VARCHAR255) - 检查点ID
  - checkpoint_data (bytea) - 二进制状态数据
  - checkpoint_metadata (jsonb) - 元数据
  - created_at (timestamp) - 创建时间

#### 2. **messages** (4条记录)
- ⚠️ 用途: 消息历史存储
- ❌ 状态: **未被使用** (当前使用内存SessionHistoryManager)
- 字段:
  - message_id (uuid) - 主键
  - session_id (VARCHAR255) - 会话ID (外键)
  - timestamp (timestamptz) - 时间戳
  - role (VARCHAR20) - 角色 (user/assistant/system/tool)
  - content (text) - 消息内容
  - message_metadata (jsonb) - 元数据 (注意:代码中是meta_data)
  - created_at (timestamptz) - 创建时间

#### 3. **sessions** (2条记录)
- ⚠️ 用途: 会话信息存储
- ❌ 状态: **未被使用**
- 字段:
  - session_id (VARCHAR255) - 主键
  - user_id (uuid) - 用户ID (外键)
  - created_at (timestamptz) - 创建时间
  - last_activity (timestamptz) - 最后活动
  - status (VARCHAR20) - 状态 (ACTIVE/PAUSED/TERMINATED)
  - context_summary (text) - 上下文摘要
  - session_metadata (jsonb) - 元数据 (注意:代码中是meta_data)

#### 4. **tool_calls** (0条记录)
- ⚠️ 用途: 工具调用记录
- ❌ 状态: **未被使用**
- 字段:
  - call_id (uuid) - 主键
  - session_id (VARCHAR255) - 会话ID (外键)
  - message_id (uuid) - 关联消息ID (外键)
  - tool_name (VARCHAR255) - 工具名称
  - parameters (jsonb) - 输入参数
  - result (jsonb) - 执行结果
  - execution_time_ms (int) - 执行时间(毫秒)
  - timestamp (timestamptz) - 时间戳
  - webhook_url (VARCHAR500) - Webhook URL
  - response_status (int) - 响应状态码
  - response_time_ms (int) - 响应时间

#### 5. **users** (1条记录)
- ⚠️ 用途: 用户账户
- ❌ 状态: **未被使用**
- 字段:
  - id (uuid) - 主键
  - username (VARCHAR255) - 用户名 (唯一)
  - created_at (timestamptz) - 创建时间
  - last_active (timestamptz) - 最后活跃
  - user_metadata (jsonb) - 元数据 (注意:代码中是meta_data)

---

## ⚠️ 关键发现

### 1. **字段命名不一致**
**问题**: 数据库表用 `{table}_metadata`，代码中用 `meta_data`

**证据**:
- 数据库: `message_metadata`, `session_metadata`, `user_metadata`
- 代码: `meta_data` (src/database/models.py)

**影响**: 
- SQLAlchemy 映射会失败
- 插入/查询数据时字段不匹配

**解决方案**:
```python
# 选项1: 修改数据库列名 (推荐)
ALTER TABLE messages RENAME COLUMN message_metadata TO meta_data;
ALTER TABLE sessions RENAME COLUMN session_metadata TO meta_data;
ALTER TABLE users RENAME COLUMN user_metadata TO meta_data;

# 选项2: 修改代码映射
meta_data = Column("message_metadata", JSONB, default=dict, nullable=False)
```

### 2. **数据库已有少量测试数据**
- langgraph_checkpoints: 30条 (LangGraph在使用)
- messages: 4条 (可能是旧测试数据)
- sessions: 2条 (可能是旧测试数据)
- tool_calls: 0条
- users: 1条 (可能是测试用户)

**建议**: 清空测试数据后开始集成

---

## 🎯 三阶段实施计划

### 阶段1: 修复字段映射 + Repository实现 (4小时)

#### 1.1 修复数据库列名 (0.5小时)
**文件**: 数据库迁移脚本

```sql
-- migrations/fix_metadata_columns.sql
ALTER TABLE messages RENAME COLUMN message_metadata TO meta_data;
ALTER TABLE sessions RENAME COLUMN session_metadata TO meta_data;
ALTER TABLE users RENAME COLUMN user_metadata TO meta_data;
```

**执行**:
```bash
psql -h 127.0.0.1 -U agent_user -d voice_agent -f migrations/fix_metadata_columns.sql
```

#### 1.2 完善 ConversationRepository (2小时)
**文件**: src/database/repositories/conversation_repository.py

**需要实现的方法**:
```python
class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # 会话管理
    async def get_or_create_session(
        self, 
        session_id: str, 
        user_id: Optional[str] = None
    ) -> Session:
        """获取或创建会话"""
        
    async def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        
    async def update_session_activity(self, session_id: str) -> None:
        """更新会话活动时间"""
        
    async def update_session_summary(
        self, 
        session_id: str, 
        summary: str
    ) -> None:
        """更新会话摘要"""
    
    # 消息管理
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> Message:
        """保存单条消息"""
        
    async def save_messages_batch(
        self,
        messages: List[Dict]
    ) -> List[Message]:
        """批量保存消息"""
        
    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Message]:
        """获取会话消息历史"""
        
    async def get_messages_after(
        self,
        session_id: str,
        timestamp: datetime
    ) -> List[Message]:
        """获取指定时间后的消息"""
        
    async def count_session_messages(self, session_id: str) -> int:
        """统计会话消息数"""
    
    # 清理操作
    async def clear_session(self, session_id: str) -> int:
        """清除会话所有消息"""
        
    async def delete_old_messages(
        self,
        days: int = 30
    ) -> int:
        """删除旧消息"""
```

#### 1.3 实现 ToolCallRepository (1小时)
**文件**: src/database/repositories/tool_call_repository.py (新建)

```python
class ToolCallRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_tool_call(
        self,
        session_id: str,
        tool_name: str,
        parameters: Dict,
        result: Dict,
        execution_time_ms: int,
        message_id: Optional[str] = None
    ) -> ToolCall:
        """保存工具调用记录"""
        
    async def get_session_tool_calls(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[ToolCall]:
        """获取会话的工具调用历史"""
        
    async def get_tool_call_stats(
        self,
        tool_name: Optional[str] = None,
        days: int = 7
    ) -> Dict:
        """获取工具调用统计"""
```

#### 1.4 单元测试 (0.5小时)
**文件**: tests/unit/test_repositories.py (新建)

---

### 阶段2: 混合SessionManager实现 (3小时)

#### 2.1 创建 HybridSessionManager (2小时)
**文件**: src/utils/session_manager.py (更新)

**设计思路**:
```python
from typing import List, Dict, Optional
from collections import deque
from datetime import datetime, timedelta
from database.repositories.conversation_repository import ConversationRepository

class HybridSessionManager:
    """
    混合会话管理器
    - 优先使用数据库存储
    - 内存缓存热数据(最近20条)
    - 数据库失败时降级到纯内存模式
    """
    
    def __init__(
        self,
        repo: ConversationRepository,
        max_history: int = 20,
        ttl_hours: int = 24,
        enable_db: bool = True
    ):
        self.repo = repo
        self.max_history = max_history
        self.ttl = timedelta(hours=ttl_hours)
        self.enable_db = enable_db
        
        # 内存缓存 (session_id -> deque of messages)
        self._cache: Dict[str, deque] = {}
        
        # 数据库可用性标志
        self._db_available = True
        
        # 统计信息
        self._stats = {
            "cache_hits": 0,
            "db_reads": 0,
            "db_writes": 0,
            "db_errors": 0
        }
    
    async def get_history(
        self,
        session_id: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取会话历史
        1. 检查内存缓存
        2. 缓存未命中则从数据库加载
        3. 数据库失败则返回缓存的数据
        """
        
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        添加消息
        1. 立即添加到内存缓存
        2. 异步写入数据库
        3. 数据库失败不影响用户体验
        """
        
    async def clear_session(self, session_id: str) -> None:
        """清除会话历史"""
        
    async def get_stats(self) -> Dict:
        """获取统计信息"""
        
    def _add_to_cache(
        self,
        session_id: str,
        message: Dict
    ) -> None:
        """添加到内存缓存"""
        
    async def _load_from_db(self, session_id: str) -> List[Dict]:
        """从数据库加载历史"""
        
    async def _save_to_db(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict]
    ) -> None:
        """保存到数据库"""
```

#### 2.2 修改 main.py 初始化 (0.5小时)
**文件**: src/api/main.py

```python
from utils.session_manager import HybridSessionManager, SessionHistoryManager

# 在 lifespan 启动流程中完成初始化
if hasattr(app.state, "db_session_factory"):
    session_manager = HybridSessionManager(
        session_factory=app.state.db_session_factory,
        memory_limit=20,
        ttl_hours=24,
        enable_database=True,
    )
    AppState.set_session_manager(app, session_manager)
    logger.info("HybridSessionManager 初始化 (memory + database)")
else:
    session_manager = HybridSessionManager(
        session_factory=None,
        memory_limit=20,
        ttl_hours=24,
        enable_database=False,
    )
    AppState.set_session_manager(app, session_manager)
    logger.info("HybridSessionManager 初始化 (memory-only mode)")
```

#### 2.3 集成测试 (0.5小时)
**文件**: tests/integration/test_hybrid_session.py (新建)

---

### 阶段3: API层修改 + 工具调用集成 (4小时)

#### 3.1 修改 API 路由为异步 (2小时)
**文件**: src/api/routes.py

**修改点**:
```python
# 4个端点需要修改:
# 1. chat_message() - POST /chat/ (Line ~133, 164)
# 2. chat_message_stream() - POST /chat/stream (Line ~204, 244)
# 3. chat_message_stream_get() - GET /chat/stream (Line ~293)
# 4. chat_ws() - WebSocket /chat/ws (Line ~380, 413)

# 示例修改 (chat_message):
@chat_router.post("/", response_model=ChatResponse)
async def chat_message(request: ChatRequest, req: Request):
    # 当前 (同步)
    external_history = session_manager.get_history(session_id)
    
    # 修改为 (异步)
    external_history = await session_manager.get_history(session_id)
    
    # ... agent processing ...
    
    # 当前 (同步)
    session_manager.add_message(session_id, "user", request.message)
    session_manager.add_message(session_id, "assistant", full_response)
    
    # 修改为 (异步)
    await session_manager.add_message(session_id, "user", request.message)
    await session_manager.add_message(session_id, "assistant", full_response)
```

#### 3.2 工具调用记录集成 (1.5小时)
**文件**: src/agent/nodes.py

```python
async def handle_tools(self, state: AgentState) -> AgentState:
    """执行工具调用"""
    # ... existing tool execution ...
    
    # 🆕 保存工具调用记录
    if hasattr(self, 'tool_call_repo') and self.tool_call_repo:
        try:
            await self.tool_call_repo.save_tool_call(
                session_id=state["session_id"],
                tool_name=tool_call["name"],
                parameters=tool_call["arguments"],
                result=result,
                execution_time_ms=int(execution_time * 1000),
                message_id=state.get("current_message_id")  # 可选
            )
        except Exception as e:
            self.logger.warning(f"Failed to save tool call: {e}")
    
    # ... rest of code ...
```

#### 3.3 健康检查增强 (0.5小时)
**文件**: src/api/routes.py

```python
@health_router.get("/", response_model=HealthResponse)
async def health_check(request: Request):
    # ... existing code ...
    
    # 🆕 数据库健康检查
    db_health = await _check_database_health()
    components.append(db_health)
    
    # ... rest of code ...

async def _check_database_health() -> ComponentHealth:
    """检查数据库健康"""
    try:
        from database.connection import check_db_health
        is_healthy = await check_db_health()
        
        if is_healthy:
            from database.connection import get_db_stats
            stats = await get_db_stats()
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                message=f"Connected (pool: {stats.get('total_connections', 0)})"
            )
        else:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message="Connection failed"
            )
    except Exception as e:
        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Error: {str(e)}"
        )
```

---

## 🧪 测试验证计划

### 测试1: 数据库读写验证
```python
# test_db_persistence.py
async def test_message_persistence():
    # 1. 发送消息
    response = await client.post("/api/v1/chat/", json={
        "session_id": "test_001",
        "message": "测试数据库持久化"
    })
    assert response.status_code == 200
    
    # 2. 查询数据库
    async with get_async_session() as session:
        repo = ConversationRepository(session)
        messages = await repo.get_session_messages("test_001")
        assert len(messages) >= 2  # user + assistant
        assert messages[0].role == "user"
        assert messages[0].content == "测试数据库持久化"
```

### 测试2: 服务重启数据恢复
```bash
# 1. 发送对话
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"session_id":"restart_test","message":"记住我叫张三"}'

# 2. 重启服务
# (停止并重新启动 python start_server.py)

# 3. 验证历史恢复
curl -X POST http://localhost:8000/api/v1/chat/ \
  -d '{"session_id":"restart_test","message":"我叫什么名字？"}'

# 预期: AI回复 "你叫张三"
```

### 测试3: 数据库故障降级
```python
# test_db_fallback.py
async def test_database_fallback():
    # 1. 模拟数据库故障
    # (停止PostgreSQL容器)
    
    # 2. 发送消息 (应该降级到内存模式)
    response = await client.post("/api/v1/chat/", json={
        "session_id": "fallback_test",
        "message": "测试降级模式"
    })
    assert response.status_code == 200
    
    # 3. 验证内存缓存工作
    # (同一session的后续消息应该有历史上下文)
```

### 测试4: 性能对比
```python
# benchmark.py
import time

async def benchmark_memory_vs_db():
    # 内存模式
    start = time.time()
    for i in range(100):
        await memory_manager.add_message("test", "user", f"Message {i}")
    memory_time = time.time() - start
    
    # 数据库模式
    start = time.time()
    for i in range(100):
        await hybrid_manager.add_message("test", "user", f"Message {i}")
    db_time = time.time() - start
    
    print(f"Memory: {memory_time:.3f}s")
    print(f"Database: {db_time:.3f}s")
    print(f"Overhead: {(db_time/memory_time - 1) * 100:.1f}%")
    
    # 目标: 数据库模式增加延迟 < 50ms per 100 messages
```

---

## 📊 工作量估算

| 阶段 | 任务 | 工作量 | 优先级 |
|------|------|--------|--------|
| 阶段1.1 | 修复数据库列名 | 0.5h | P0 🔴 |
| 阶段1.2 | ConversationRepository | 2h | P0 🔴 |
| 阶段1.3 | ToolCallRepository | 1h | P1 🟡 |
| 阶段1.4 | Repository单元测试 | 0.5h | P0 🔴 |
| 阶段2.1 | HybridSessionManager | 2h | P0 🔴 |
| 阶段2.2 | main.py集成 | 0.5h | P0 🔴 |
| 阶段2.3 | 混合模式测试 | 0.5h | P0 🔴 |
| 阶段3.1 | API路由异步修改 | 2h | P0 🔴 |
| 阶段3.2 | 工具调用记录 | 1.5h | P1 🟡 |
| 阶段3.3 | 健康检查增强 | 0.5h | P2 🟢 |
| **总计** | | **11h** | |

---

## 🚀 开始实施建议

### 第一步: 修复列名 (5分钟)
```bash
# 执行SQL脚本修复列名
psql -h 127.0.0.1 -U agent_user -d voice_agent -c "
ALTER TABLE messages RENAME COLUMN message_metadata TO meta_data;
ALTER TABLE sessions RENAME COLUMN session_metadata TO meta_data;
ALTER TABLE users RENAME COLUMN user_metadata TO meta_data;
"
```

### 第二步: 验证修复
```bash
python check_db_tables.py
# 检查列名是否已修改为 meta_data
```

### 第三步: 开始实现 ConversationRepository
从最核心的Repository开始实现...

---

## ✅ 成功标准

1. ✅ **功能完整**: 
   - 消息历史持久化到数据库
   - 服务重启后历史不丢失
   - 工具调用记录保存

2. ✅ **性能可接受**:
   - 数据库模式延迟增加 < 50ms
   - 热数据访问速度与内存模式相当

3. ✅ **稳定可靠**:
   - 数据库故障时自动降级
   - 不影响核心对话功能
   - 错误日志清晰

4. ✅ **代码质量**:
   - 单元测试覆盖率 > 80%
   - 集成测试通过
   - 无Critical错误

---

需要我开始实施吗？我建议从**修复列名**开始！
