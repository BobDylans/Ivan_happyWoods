# Ivan_HappyWoods Development Guidelines# Ivan_happyWoods Development Guidelines



**Project**: Voice-Based AI Agent Interaction System  Auto-generated from all feature plans. Last updated: 2025-10-13

**Status**: Phase 2 Complete (80% Overall)  

**Last Updated**: 2025-10-15  ## Active Technologies

**Version**: 0.2.0-beta- Python 3.11+ + FastAPI, LangGraph, websockets, httpx, uvicorn, pytest (001-voice-interaction-system)

- Python 3.11 + FastAPI, LangGraph, httpx (async), websockets (FastAPI WS), Pydantic v2, uvicorn, pytest, (future: MCP client, STT/TTS providers) (001-voice-interaction-system)

---- In-memory (LangGraph MemorySaver) for sessions in Phase 0–1; no external DB yet (001-voice-interaction-system)



## 🎯 Quick Context for AI Assistants## Project Structure

```

**What is this project?**  src/

Voice-first AI conversation system using LangGraph + FastAPI + iFlytek Voice Services.tests/

```

**Current capabilities:**

- ✅ Text & Voice conversation## Commands

- ✅ Real-time streaming (SSE + WebSocket)cd src; pytest; ruff check .

- ✅ Session management with history

- ✅ Chinese-localized codebase## Code Style

- ⏳ MCP tools (planned Phase 2E)Python 3.11+: Follow standard conventions



**For complete architecture**: Read [PROJECT.md](../PROJECT.md) ⭐## Recent Changes

- 001-voice-interaction-system: Added Python 3.11 + FastAPI, LangGraph, httpx (async), websockets (FastAPI WS), Pydantic v2, uvicorn, pytest, (future: MCP client, STT/TTS providers)

---- 001-voice-interaction-system: Added Python 3.11 + FastAPI, LangGraph, httpx (async), websockets (FastAPI WS), Pydantic v2, uvicorn, pytest, (future: MCP client, STT/TTS providers)

- 001-voice-interaction-system: Added Python 3.11+ + FastAPI, LangGraph, websockets, httpx, uvicorn, pytest

## 📚 Essential Docs (Read First!)

<!-- MANUAL ADDITIONS START -->

| Document | Purpose | When to Read |<!-- MANUAL ADDITIONS END -->

|----------|---------|--------------|
| **[PROJECT.md](../PROJECT.md)** ⭐ | Full architecture & context | Starting any work |
| **[progress.md](../specs/001-voice-interaction-system/progress.md)** | Current status & tasks | Checking progress |
| **[DEVELOPMENT.md](../DEVELOPMENT.md)** | Developer guide | Setting up / debugging |
| **[CHANGELOG.md](../CHANGELOG.md)** | Version history | Understanding changes |
| **[achievements/INDEX.md](../docs/achievements/INDEX.md)** | Dev reports & fixes | Learning patterns |

---

## 🏗️ Tech Stack

### Core
- **Python 3.11+** + **FastAPI** + **LangGraph** + **Pydantic v2**
- **httpx** (async HTTP) + **WebSocket** (FastAPI built-in)
- **uvicorn** (server) + **pytest** (testing)

### Services
- **LLM**: OpenAI-compatible (current: gpt-5-mini)
- **STT/TTS**: iFlytek (科大讯飞)
- **Storage**: LangGraph MemorySaver (in-memory, Phase 1-2)
- **Future**: Redis (Phase 3), MCP Tools (Phase 2E)

---

## 📁 Code Structure

```
src/
├── agent/              # LangGraph workflow
│   ├── graph.py       # VoiceAgent class (375 lines)
│   ├── nodes.py       # Processing nodes (768 lines) ⭐
│   └── state.py       # State model
├── api/                # FastAPI routes
│   ├── main.py        # App entry
│   ├── conversation_routes.py  # Dialog APIs
│   ├── voice_routes.py         # Voice APIs
│   └── middleware.py           # CORS/Auth/Logging
├── services/           # Business logic
│   ├── conversation_service.py
│   └── voice/         # STT/TTS
├── config/             # Configuration
└── utils/              # Helpers (llm_compat.py)

tests/
├── unit/               # Unit tests
└── integration/        # Integration tests

specs/
└── 001-voice-interaction-system/
    ├── spec.md        # Feature spec
    ├── progress.md    # Progress tracking ⭐
    └── tasks.md       # Task breakdown

docs/
└── achievements/       # Dev reports
    ├── INDEX.md       # Achievement index ⭐
    ├── phase2/        # Phase 2 work
    └── optimizations/ # Code quality reports
```

---

## ⚡ Commands

```bash
# Run
python start_server.py              # Dev server
python test_conversation.py         # Test dialog

# Test
pytest                              # All tests
pytest tests/unit/test_agent.py     # Specific test
pytest --cov=src                    # With coverage

# Quality
ruff check src/                     # Lint
black src/ tests/                   # Format

# Health check
curl http://localhost:8000/health
```

---

## 📝 Code Conventions

### Naming
- **Classes**: `PascalCase` (e.g., `VoiceAgent`)
- **Functions**: `snake_case` (e.g., `process_input`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_HISTORY_MESSAGES`)
- **Private**: `_leading_underscore` (e.g., `_ensure_http_client`)

### LangGraph Nodes
```python
async def my_node(self, state: AgentState) -> AgentState:
    """节点功能描述 (Chinese)"""
    # Process
    state["next_action"] = "next_node"
    return state
```

### API Routes
```python
@router.post("/endpoint", response_model=MyResponse)
async def my_endpoint(request: MyRequest):
    """API 描述 (Chinese)"""
    # Implementation
```

### Localization
- **Docstrings**: Chinese
- **Error messages**: Chinese (user-facing)
- **Logs**: Chinese
- **Code**: English (variables, functions)

---

## 🎯 Recent Major Changes

### Phase 2D (2025-10-15) ✅
- ✅ Code deduplication (-50% duplicate code)
- ✅ Resource management (async context manager)
- ✅ Chinese localization (22+ methods)
- ✅ LLM compatibility fixes (GPT-5 series)

### Phase 2C (2025-10-14) ✅
- ✅ Conversation API (history/clear endpoints)
- ✅ API Key authentication
- ✅ Streaming history persistence

### Phase 2A/B (2025-10-14) ✅
- ✅ iFlytek STT/TTS integration
- ✅ WebSocket voice streaming
- ✅ TTS optimization (<500ms TTFB)

**Full history**: [CHANGELOG.md](../CHANGELOG.md)

---

## 🚧 Current State

```
Phase 1: Core Foundation        ████████████████████ 100% ✅
Phase 2A: Voice Integration     ████████████████████ 100% ✅
Phase 2B: Streaming TTS         ████████████████████ 100% ✅
Phase 2C: Conversation API      ████████████████████ 100% ✅
Phase 2D: Code Optimization     ████████████████████ 100% ✅
Phase 2E: MCP Tools             ░░░░░░░░░░░░░░░░░░░░   0% ⏳
Phase 3: Production Ready       ░░░░░░░░░░░░░░░░░░░░   0% 📋
```

**Details**: [progress.md](../specs/001-voice-interaction-system/progress.md)

---

## 🔑 Key Design Decisions

### 1. LangGraph for Workflow
**Why**: State management + extensibility + debuggability  
**Trade-off**: Learning curve vs maintainability

### 2. iFlytek for Voice
**Why**: Chinese optimization + low latency + cost-effective  
**Trade-off**: Less docs vs better CN performance

### 3. In-Memory Sessions (Temp)
**Why**: MVP simplicity  
**Limit**: Restart = data loss  
**Plan**: Redis in Phase 3

### 4. Chinese Localization
**Why**: User experience + team efficiency  
**Scope**: Docs/errors/logs in Chinese; code in English

### 5. Extract Method Pattern
**Why**: DRY + testability  
**Result**: -50% duplicate, better maintainability

---

## 🐛 Known Issues

- ⚠️ **Memory storage**: Sessions lost on restart (Phase 3: Redis)
- ⚠️ **No MCP tools**: Not yet available (Phase 2E: planned)
- ⚠️ **Test coverage**: ~60% (target: 80%)

**Workarounds**: Avoid restarts; core features tested

---

## 🧠 Special Instructions for AI

### LLM Model Handling
```python
# GPT-5 series: NO temperature parameter
if not model.startswith("gpt-5"):
    params["temperature"] = temperature

# See: src/utils/llm_compat.py
```

### Resource Management
```python
# Use async context manager
async with AgentNodes(config) as nodes:
    result = await nodes.process_input(state)
    # Auto cleanup

# Or explicit cleanup
await nodes.cleanup()
```

### Code Localization Rules
- **Docstrings**: Chinese (e.g., `"""处理用户输入"""`)
- **User errors**: Chinese (e.g., `"抱歉,处理失败"`)
- **Logs**: Chinese (e.g., `logger.info("开始处理")`)
- **Code**: English (e.g., `def process_input()`)

### Common Patterns

**Adding LangGraph Node:**
```python
# 1. In nodes.py
async def my_node(self, state: AgentState) -> AgentState:
    """节点描述"""
    # Logic
    state["next_action"] = "next_node"
    return state

# 2. In graph.py
workflow.add_node("my_node", self.nodes.my_node)
workflow.add_edge("prev_node", "my_node")
```

**Adding API Endpoint:**
```python
# 1. Define models in api/models.py
class MyRequest(BaseModel):
    param: str

# 2. Create route in api/my_routes.py
@router.post("/endpoint")
async def my_endpoint(request: MyRequest):
    """端点描述"""
    # Implementation

# 3. Register in api/main.py
app.include_router(my_router)
```

---

## 📚 Where to Find Things

| Need | File Location |
|------|---------------|
| Add API endpoint | `src/api/conversation_routes.py` or new file |
| Modify dialog flow | `src/agent/graph.py` + `src/agent/nodes.py` |
| Configure LLM | `src/config/models.py` or `.env` |
| Voice services | `src/services/voice/` |
| Tests | `tests/unit/` or `tests/integration/` |
| Specs | `specs/001-voice-interaction-system/` |
| Dev reports | `docs/achievements/` |

---

## 🎓 AI Assistant Learning Path

### Starting Work
1. Read PROJECT.md's "Copilot Context Refresh"
2. Check progress.md for current status
3. Review CHANGELOG.md for recent changes
4. Understand code org in PROJECT.md

### Making Changes
1. Follow patterns in similar files
2. Use Chinese for user-facing content
3. Apply Extract Method for reuse
4. Add resource cleanup
5. Update docs

### Troubleshooting
1. Check docs/achievements/reports/ for fixes
2. Review error patterns in nodes.py
3. Check LLM compat in utils/llm_compat.py
4. Use /docs endpoint for API docs

---

<!-- MANUAL ADDITIONS START -->

## 🔧 Project-Specific Notes

### Dependencies
- **LangGraph**: For workflow orchestration
- **iFlytek**: Requires AppID + APIKey + APISecret
- **LLM**: OpenAI-compatible endpoint
- **Current model**: gpt-5-mini (supports temperature)

### Environment Setup
```bash
# Required .env variables
VOICE_AGENT_LLM__API_KEY=xxx
VOICE_AGENT_LLM__BASE_URL=https://api.openai-proxy.org/v1
VOICE_AGENT_LLM__MODELS__DEFAULT=gpt-5-mini

IFLYTEK_APPID=xxx
IFLYTEK_APIKEY=xxx
IFLYTEK_APISECRET=xxx
```

### Testing Strategy
- Unit tests: Mock external services
- Integration tests: Test full flows
- Async tests: Use `@pytest.mark.asyncio`
- Coverage target: 80%

### Performance Tips
- Reuse HTTP clients (`_ensure_http_client`)
- Use async gather for parallel ops
- Cache frequent calls
- Optimize chunk sizes for streaming

<!-- MANUAL ADDITIONS END -->

---

*Maintained by: Ivan_HappyWoods Team*  
*For questions: See DEVELOPMENT.md or GitHub Issues*
