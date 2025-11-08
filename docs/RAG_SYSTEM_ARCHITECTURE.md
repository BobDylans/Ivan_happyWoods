# RAG 系统架构分析

📅 **日期**: 2025-11-08  
🎯 **目标**: 全面分析项目中 RAG (Retrieval-Augmented Generation) 系统的集成架构

---

## 📋 目录

1. [概述](#概述)
2. [核心组件](#核心组件)
3. [数据流](#数据流)
4. [集成点](#集成点)
5. [配置管理](#配置管理)
6. [数据库设计](#数据库设计)
7. [API 接口](#api-接口)
8. [Agent 集成](#agent-集成)
9. [向量验证](#向量验证)
10. [最佳实践](#最佳实践)

---

## 概述

### 什么是 RAG？

RAG (Retrieval-Augmented Generation) 是一种结合了**检索**和**生成**的 AI 技术：

1. **检索 (Retrieval)**: 从知识库中检索相关文档片段
2. **增强 (Augmented)**: 将检索到的内容作为上下文
3. **生成 (Generation)**: LLM 基于上下文生成更准确的回答

### 项目中的 RAG 定位

```
用户问题 
    ↓
[RAG 检索] → 从向量数据库检索相关片段
    ↓
[上下文增强] → 将片段注入 LLM prompt
    ↓
[LLM 生成] → 基于知识库生成回答
    ↓
用户得到准确答案
```

### 关键特性

- ✅ **Per-User Collections**: 每个用户独立的知识库
- ✅ **多格式支持**: MD, PDF, DOCX, TXT
- ✅ **向量检索**: 基于 Qdrant 的高效相似度搜索
- ✅ **嵌入服务**: 兼容 OpenAI Embedding API
- ✅ **元数据追踪**: PostgreSQL 存储文档和块的元数据
- ✅ **动态集成**: 运行时无缝集成到对话流程

---

## 核心组件

### 1. 四层架构

```
┌─────────────────────────────────────────────────────┐
│                   API Layer                         │
│  • /api/v1/rag/upload (上传文档)                     │
│  • /api/v1/rag/user/upload (用户上传)                │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│                Service Layer                        │
│  • RAGService (服务门面)                            │
│  • Ingestion (文档处理)                             │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│                Storage Layer                        │
│  • EmbeddingClient (向量生成)                       │
│  • QdrantVectorStore (向量存储)                     │
│  • PostgreSQL (元数据存储)                          │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│                Agent Integration                    │
│  • _retrieve_rag_snippets() (检索)                  │
│  • prepare_llm_messages() (注入)                    │
│  • LLMCaller/LLMStreamer (调用)                     │
└─────────────────────────────────────────────────────┘
```

### 2. 模块职责

#### `src/rag/service.py` - RAG 服务门面

**职责**: 统一的 RAG 操作接口

```python
class RAGService:
    def __init__(self, config: VoiceAgentConfig)
    
    # 核心方法
    async def retrieve(query, user_id, corpus_id, top_k) -> List[RAGResult]
    async def ensure_collection(user_id, corpus_id, recreate)
    def resolve_collection_name(user_id, corpus_id) -> str
    def build_prompt(results: List[RAGResult]) -> str
```

**关键功能**:
- 协调 EmbeddingClient 和 QdrantVectorStore
- 处理 per-user collection 逻辑
- 格式化检索结果为 LLM 可用的 prompt

#### `src/rag/embedding_client.py` - 嵌入向量生成

**职责**: 调用 Embedding API 生成向量

```python
class EmbeddingClient:
    def __init__(self, base_url, api_key, model, timeout)
    
    async def embed_texts(texts: List[str]) -> List[List[float]]
```

**特点**:
- 兼容 OpenAI Embedding API
- 批量处理文本
- 自动构建 `/v1/embeddings` 端点

#### `src/rag/qdrant_store.py` - 向量数据库

**职责**: 管理 Qdrant 向量存储

```python
class QdrantVectorStore:
    def __init__(self, config: RAGConfig, collection_name)
    
    # 集合管理
    async def ensure_collection(vector_size, recreate)
    
    # 向量操作
    async def upsert_chunks(chunks: List[DocumentChunk])
    async def search(query_embedding, top_k, min_score) -> List[RetrievedChunk]
```

**验证机制**:
- ✅ 向量维度检查
- ✅ 数值有效性验证 (NaN/Inf)
- ✅ 类型安全检查
- ✅ 批量处理日志

#### `src/rag/ingestion.py` - 文档摄取

**职责**: 处理文档上传和向量化

```python
async def ingest_files(
    config,
    files,
    user_id,
    corpus_name,
    collection_name,
    db_session
) -> IngestionResult
```

**处理流程**:
1. 解析文档 (PDF/DOCX/MD/TXT)
2. 文本切块 (chunk_text)
3. 批量生成嵌入 (_flush_batch)
4. 存储向量到 Qdrant
5. 记录元数据到 PostgreSQL

**支持的文件类型**:
```python
SUPPORTED_SUFFIXES = {
    ".md", ".markdown", ".mdx",
    ".txt",
    ".pdf",
    ".docx"
}
```

---

## 数据流

### 1. 文档上传流程

```
用户上传文档
    ↓
[API Layer] /api/v1/rag/user/upload
    ├─ 验证用户 ID
    ├─ 检查文件类型和大小
    └─ 保存临时文件
    ↓
[Ingestion] ingest_files()
    ├─ 解析文档内容
    ├─ 文本切块 (300 chars, 60 overlap)
    └─ 生成 DocumentChunk[]
    ↓
[Embedding] embed_texts()
    ├─ 批量调用 Embedding API
    └─ 返回向量 List[List[float]]
    ↓
[Validation] _flush_batch()
    ├─ 验证向量维度
    ├─ 检查数值有效性
    └─ 赋值 chunk.embedding
    ↓
[Qdrant] upsert_chunks()
    ├─ 创建 PointStruct
    └─ 批量写入 Qdrant
    ↓
[PostgreSQL] RAGRepository
    ├─ 创建 RAGCorpus 记录
    ├─ 创建 RAGDocument 记录
    └─ 创建 RAGChunk 记录
    ↓
返回 IngestionResult
    {
        processed_files: 1,
        stored_chunks: 23,
        failed_files: [],
        skipped_files: []
    }
```

### 2. 对话检索流程

```
用户提问: "什么是 RAG？"
    ↓
[Agent] process_message_stream()
    ├─ 创建 AgentState
    └─ 调用 LangGraph workflow
    ↓
[Node] call_llm() / stream_llm_call()
    ↓
[Step 1] _retrieve_rag_snippets(state)
    ├─ 检查 RAG 是否启用
    ├─ 解析 user_id 和 corpus_id
    ├─ 调用 embedding_client.embed_texts([query])
    ├─ 调用 qdrant_store.search(query_vector)
    └─ 返回 List[RAGResult]
    ↓
[Step 2] prepare_llm_messages(state, external_history)
    ├─ 加载系统 prompt
    ├─ 加载对话历史
    └─ 返回 messages[]
    ↓
[Step 3] 注入 RAG 上下文
    ├─ rag_service.build_prompt(rag_results)
    ├─ 创建 system message
    └─ 插入到 messages (在最后一条 user message 之前)
    ↓
[Step 4] 调用 LLM
    ├─ POST {base_url}/v1/chat/completions
    ├─ 携带增强后的 messages
    └─ 返回基于知识库的回答
    ↓
用户收到准确答案
```

### 3. Collection 命名逻辑

```python
# 配置
config.rag.per_user_collections = True
config.rag.collection = "knowledge_base"
config.rag.collection_name_template = "{collection}_{user_id}_{corpus_id}"

# 解析过程
user_id = "user_12345"
corpus_id = "tech_docs"

# 1. 清理字符
sanitized_user = "user-12345"   # 替换非法字符
sanitized_corpus = "tech-docs"

# 2. 格式化模板
collection_name = "knowledge_base_user-12345_tech-docs"

# 3. 转换小写
final_name = "knowledge_base_user-12345_tech-docs"

# 结果: 每个用户的每个 corpus 有独立的 Qdrant collection
```

---

## 集成点

### 1. Agent 集成 (`src/agent/`)

#### LLMCaller (`nodes/llm_caller.py`)

```python
async def call_llm(self, state: AgentState) -> AgentState:
    # 🔍 Step 1: 检索 RAG 片段
    rag_results = await self._retrieve_rag_snippets(state)
    
    # 📝 Step 2: 准备消息历史
    messages = prepare_llm_messages(state, external_history)
    
    # 💉 Step 3: 注入 RAG 上下文
    if rag_results and self._rag_service:
        rag_prompt = self._rag_service.build_prompt(rag_results)
        system_message = {"role": "system", "content": rag_prompt}
        messages.insert(len(messages) - 1, system_message)
    
    # 🤖 Step 4: 调用 LLM
    response = await llm_client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools_schema
    )
```

#### LLMStreamer (`nodes/llm_streamer.py`)

**流式调用版本**，逻辑相同：
- 同样执行 4 步流程
- 使用 `stream=True`
- 逐 token 返回结果

#### AgentNodesBase (`nodes/base.py`)

**共享的 RAG 检索逻辑**:

```python
async def _retrieve_rag_snippets(self, state: AgentState) -> List[Any]:
    # 1. 检查 RAG 是否启用
    if not self._rag_service or not self.config.rag.enabled:
        return []
    
    # 2. 获取查询文本
    query = state.get("user_input", "")
    
    # 3. 解析用户和语料库 ID
    user_id = state.get("user_id")
    corpus_id = state.get("active_corpus_id") or config.rag.default_corpus_name
    
    # 4. 解析 collection 名称
    resolved_collection = self._rag_service.resolve_collection_name(
        user_id=user_id,
        corpus_id=corpus_id
    )
    
    # 5. 执行检索
    results = await self._rag_service.retrieve(
        query,
        user_id=user_id,
        corpus_id=corpus_id,
        collection_name=resolved_collection
    )
    
    # 6. 存储到 state
    state["rag_snippets"] = [
        {
            "text": item.text,
            "score": item.score,
            "source": item.source,
            "metadata": item.metadata
        }
        for item in results
    ]
    
    return results
```

### 2. API 集成 (`src/api/routes.py`)

#### 上传接口

```python
@rag_router.post("/user/upload", response_model=RAGUploadResponse)
async def upload_user_documents(
    user_id: str = Form(...),
    corpus_name: Optional[str] = Form(None),
    corpus_description: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    config = Depends(get_config),
    db_session: AsyncSession = Depends(get_db_session)
):
    return await _handle_rag_upload(
        user_id=user_id,
        corpus_name=corpus_name,
        corpus_description=corpus_description,
        collection_name=None,
        files=files,
        config=config,
        db_session=db_session
    )
```

#### 核心处理函数

```python
async def _handle_rag_upload(
    user_id: str,
    corpus_name: Optional[str],
    corpus_description: Optional[str],
    collection_name: Optional[str],
    files: List[UploadFile],
    config: VoiceAgentConfig,
    db_session: Optional[AsyncSession]
) -> RAGUploadResponse:
    # 1. 验证 RAG 是否启用
    if not config.rag.enabled:
        raise HTTPException(400, "RAG is disabled")
    
    # 2. 验证文件
    for file in files:
        if Path(file.filename).suffix.lower() not in SUPPORTED_SUFFIXES:
            raise HTTPException(400, f"Unsupported file type: {file.filename}")
    
    # 3. 保存临时文件
    temp_dir = Path(config.rag.upload_temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = []
    for file in files:
        temp_path = temp_dir / f"{uuid.uuid4()}_{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        saved_paths.append(temp_path)
    
    # 4. 调用 ingestion
    result = await ingest_files(
        config=config,
        files=saved_paths,
        user_id=user_id,
        corpus_name=corpus_name,
        corpus_description=corpus_description,
        collection_name=collection_name,
        db_session=db_session
    )
    
    # 5. 清理临时文件
    for path in saved_paths:
        path.unlink(missing_ok=True)
    
    # 6. 返回结果
    return RAGUploadResponse(
        success=True,
        message=f"Processed {result.processed_files} files",
        processed_count=result.processed_files,
        stored_chunks=result.stored_chunks,
        failed_files=[...]
    )
```

---

## 配置管理

### 配置结构 (`src/config/models.py`)

```python
class RAGConfig(BaseModel):
    # 🔧 基础配置
    enabled: bool = True
    per_user_collections: bool = True
    
    # 🗄️ 存储配置
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    collection: str = "default_kb"
    collection_name_template: str = "{collection}_{user_id}_{corpus_id}"
    
    # 📦 Corpus 配置
    default_corpus_name: str = "default"
    
    # 🧠 Embedding 配置
    embed_model: str = "text-embedding-3-small"
    embed_dim: int = 1536
    
    # ✂️ 文本处理
    chunk_size: int = 300
    chunk_overlap: int = 60
    
    # 🔍 检索配置
    top_k: int = 5
    min_score: float = 0.15
    
    # 📄 文件处理
    doc_glob: str = "docs/**/*.md;docs/**/*.pdf;docs/**/*.docx"
    pdf_max_pages: int = 25
    docx_max_paragraphs: Optional[int] = None
    
    # 📤 上传配置
    upload_temp_dir: str = "docs/uploads"
    max_upload_size_mb: int = 20
    ingest_batch_size: int = 16
    
    # ⏱️ 网络配置
    request_timeout: int = 15
```

### 环境变量覆盖

```bash
# 启用 RAG
VOICE_AGENT_RAG__ENABLED=true

# Qdrant 连接
VOICE_AGENT_RAG__QDRANT_URL=http://localhost:6333
VOICE_AGENT_RAG__QDRANT_API_KEY=your_key

# Embedding 配置
VOICE_AGENT_RAG__EMBED_MODEL=text-embedding-3-small
VOICE_AGENT_RAG__EMBED_DIM=1536

# Per-User Collections
VOICE_AGENT_RAG__PER_USER_COLLECTIONS=true
VOICE_AGENT_RAG__COLLECTION_NAME_TEMPLATE=kb_{user_id}_{corpus_id}

# 检索参数
VOICE_AGENT_RAG__TOP_K=5
VOICE_AGENT_RAG__MIN_SCORE=0.15
```

---

## 数据库设计

### PostgreSQL Schema

#### 1. `rag_corpora` - 语料库表

```sql
CREATE TABLE rag_corpora (
    corpus_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    corpus_name VARCHAR(255) NOT NULL,
    collection_name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    meta_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_user_corpus UNIQUE (user_id, corpus_name)
);

CREATE INDEX idx_rag_corpora_user ON rag_corpora(user_id);
CREATE INDEX idx_rag_corpora_collection ON rag_corpora(collection_name);
```

**职责**: 管理用户的文档集合

#### 2. `rag_documents` - 文档表

```sql
CREATE TABLE rag_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES rag_corpora(corpus_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    source_path VARCHAR(1024),
    source_url VARCHAR(1024),
    display_name VARCHAR(255) NOT NULL,
    checksum VARCHAR(128),
    size_bytes INTEGER,
    mime_type VARCHAR(255),
    status VARCHAR(32) DEFAULT 'ACTIVE',
    ingestion_id UUID,
    meta_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_rag_documents_corpus ON rag_documents(corpus_id);
CREATE INDEX idx_rag_documents_user ON rag_documents(user_id);
```

**职责**: 存储文档元数据

#### 3. `rag_chunks` - 文本块表

```sql
CREATE TABLE rag_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES rag_documents(document_id) ON DELETE CASCADE,
    corpus_id UUID NOT NULL REFERENCES rag_corpora(corpus_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    point_id VARCHAR(255) NOT NULL,  -- Qdrant point ID
    chunk_index INTEGER NOT NULL,
    text_preview TEXT,
    meta_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_rag_chunks_document ON rag_chunks(document_id);
CREATE INDEX idx_rag_chunks_point ON rag_chunks(point_id);
```

**职责**: 追踪 Qdrant 向量点的元数据

### Qdrant Schema

#### Collection 结构

```python
{
    "name": "kb_user-12345_tech-docs",
    "vectors": {
        "size": 1536,  # 向量维度
        "distance": "Cosine"  # 相似度度量
    }
}
```

#### Point 结构

```python
{
    "id": "550e8400-e29b-41d4-a716-446655440000",  # UUID
    "vector": [0.123, -0.456, ...],  # 1536维向量
    "payload": {
        "text": "RAG 是一种结合了检索和生成的 AI 技术...",
        "source": "docs/rag_intro.md",
        "source_name": "rag_intro.md",
        "source_type": "md",
        "owner_id": "user_12345",
        "corpus_id": "1",
        "collection_name": "kb_user-12345_tech-docs",
        "document_id": "doc_uuid",
        "chunk_index": 0,
        "source_display": "RAG 介绍"
    }
}
```

### 数据关系

```
users (PostgreSQL)
  ↓ 1:N
rag_corpora (PostgreSQL)
  ├─ collection_name → Qdrant Collection
  ↓ 1:N
rag_documents (PostgreSQL)
  ↓ 1:N
rag_chunks (PostgreSQL)
  ├─ point_id → Qdrant Point
  └─ metadata
```

---

## API 接口

### 1. 上传文档 (管理员)

```http
POST /api/v1/rag/upload
Content-Type: multipart/form-data

corpus_name=tech_docs
corpus_description=技术文档集合
collection_name=custom_collection (可选)
files=@file1.pdf
files=@file2.md
```

**响应**:
```json
{
    "success": true,
    "message": "Successfully processed 2 files",
    "corpus_id": "1",
    "collection_name": "custom_collection",
    "processed_count": 2,
    "stored_chunks": 45,
    "results": [
        {
            "filename": "file1.pdf",
            "status": "success",
            "chunks_count": 23,
            "error": null
        },
        {
            "filename": "file2.md",
            "status": "success",
            "chunks_count": 22,
            "error": null
        }
    ]
}
```

### 2. 用户上传文档

```http
POST /api/v1/rag/user/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

user_id=user_12345
corpus_name=my_notes
corpus_description=我的笔记
files=@note1.md
files=@note2.pdf
```

**响应**: 同上

### 3. 对话中自动检索

```http
POST /api/v1/chat
Content-Type: application/json

{
    "message": "什么是 RAG？",
    "session_id": "sess_001",
    "user_id": "user_12345",
    "stream": true
}
```

**内部流程**:
1. Agent 接收消息
2. 自动调用 `_retrieve_rag_snippets()`
3. 检索相关片段
4. 注入到 LLM prompt
5. 返回增强后的回答

**响应** (流式):
```
data: {"type": "start", "session_id": "sess_001"}

data: {"type": "delta", "content": "RAG"}
data: {"type": "delta", "content": " 是一种"}
data: {"type": "delta", "content": "结合了检索和生成的..."}

data: {"type": "rag_context", "snippets": [...]}

data: {"type": "end", "metadata": {...}}
```

---

## Agent 集成

### 1. State 定义 (`src/agent/state.py`)

```python
class AgentState(TypedDict):
    # ... 其他字段
    
    # RAG 相关字段
    rag_snippets: List[Dict[str, Any]]  # 检索到的片段
    active_corpus_id: Optional[str]     # 当前活跃的 corpus
    rag_collection: Optional[str]       # 解析后的 collection 名称
```

### 2. 初始化 (`src/agent/graph.py`)

```python
class VoiceAgent:
    def __init__(self, config: VoiceAgentConfig):
        self.config = config
        self.nodes = AgentNodes(config, trace=self.trace)
        # nodes 内部初始化 RAGService
```

### 3. 节点初始化 (`src/agent/nodes/base.py`)

```python
class AgentNodesBase:
    def __init__(self, config: VoiceAgentConfig, trace: TraceEmitter):
        self.config = config
        self._rag_service = None
        
        # 初始化 RAG service (如果启用)
        if config.rag.enabled:
            try:
                from rag.service import RAGService
                self._rag_service = RAGService(config)
                logger.info("✅ RAG service initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️ RAG service initialization failed: {e}")
                self._rag_service = None
```

### 4. 检索集成

**时机**: 在 `call_llm()` 或 `stream_llm_call()` 开始时

```python
async def call_llm(self, state: AgentState) -> AgentState:
    # Step 1: 检索 RAG 片段
    rag_results = await self._retrieve_rag_snippets(state)
    # → 自动填充 state["rag_snippets"]
    
    # Step 2: 准备消息
    messages = prepare_llm_messages(state, external_history)
    
    # Step 3: 注入 RAG 上下文
    if rag_results and self._rag_service:
        rag_prompt = self._rag_service.build_prompt(rag_results)
        system_message = {"role": "system", "content": rag_prompt}
        # 插入到最后一条 user message 之前
        messages.insert(len(messages) - 1, system_message)
    
    # Step 4: 调用 LLM (携带增强的上下文)
    ...
```

### 5. Prompt 格式化

```python
def build_prompt(self, results: List[RAGResult]) -> str:
    """
    格式化检索结果为 LLM prompt
    """
    if not results:
        return ""
    
    lines = [
        "你可以参考以下知识片段进行回答。如信息与实时事实冲突，请优先使用最新事实：",
    ]
    
    for idx, item in enumerate(results, start=1):
        header = f"[{idx}] 来源: {item.source or 'Unknown'} (score={item.score:.3f})"
        lines.append(header)
        lines.append(item.text.strip())
        lines.append("")
    
    return "\n".join(lines).strip()
```

**示例输出**:
```
你可以参考以下知识片段进行回答。如信息与实时事实冲突，请优先使用最新事实：

[1] 来源: docs/rag_intro.md (score=0.856)
RAG (Retrieval-Augmented Generation) 是一种结合了检索和生成的 AI 技术。
它首先从知识库中检索相关文档，然后将这些文档作为上下文输入给 LLM。

[2] 来源: docs/tech_overview.md (score=0.782)
RAG 系统通常包含三个核心组件：文档存储、向量检索和生成模型。
```

---

## 向量验证

### 1. Ingestion 层验证 (`_flush_batch`)

```python
async def _flush_batch(batch, embedding_client, vector_store, ...):
    # 1. 验证文本非空
    for idx, text in enumerate(texts):
        if not text or not text.strip():
            raise ValueError(f"Chunk {batch[idx].id} has empty text")
    
    # 2. 调用 Embedding API
    embeddings = await embedding_client.embed_texts(texts)
    
    # 3. 验证返回值
    if not isinstance(embeddings, list):
        raise ValueError("Invalid embedding response type")
    
    if len(embeddings) != len(batch):
        raise ValueError(f"Expected {len(batch)} vectors, got {len(embeddings)}")
    
    # 4. 逐个验证向量
    for idx, (chunk, embedding) in enumerate(zip(batch, embeddings)):
        # 4.1 非空检查
        if not embedding:
            raise ValueError(f"Chunk {chunk.id} received empty embedding")
        
        # 4.2 类型检查
        if not isinstance(embedding, list):
            raise ValueError(f"Invalid embedding type: {type(embedding)}")
        
        # 4.3 维度检查
        if len(embedding) != expected_dim:
            raise ValueError(
                f"Dimension mismatch: expected {expected_dim}, got {len(embedding)}"
            )
        
        # 4.4 数值验证
        for i, val in enumerate(embedding):
            if not isinstance(val, (int, float)):
                raise ValueError(f"Non-numeric value at position {i}")
            if val != val:  # NaN check
                raise ValueError(f"NaN value at position {i}")
            if abs(val) == float('inf'):
                raise ValueError(f"Infinite value at position {i}")
        
        # 4.5 赋值
        chunk.embedding = embedding
```

### 2. Qdrant 层验证 (`upsert_chunks`)

```python
async def upsert_chunks(self, chunks: Iterable[DocumentChunk], ...):
    expected_dim = self.config.embed_dim
    
    for idx, chunk in enumerate(chunks):
        # 1. ID 验证
        if not chunk.id or not isinstance(chunk.id, str):
            raise ValueError(f"Invalid chunk ID at index {idx}")
        
        # 2. 文本验证
        if not chunk.text or not isinstance(chunk.text, str):
            logger.warning(f"Chunk {chunk.id} has empty text, skipping")
            continue
        
        # 3. Embedding 存在性
        if not chunk.embedding:
            raise ValueError(f"Chunk {chunk.id} has empty embedding")
        
        # 4. 类型验证
        if not isinstance(chunk.embedding, list):
            raise ValueError(f"Invalid embedding type for {chunk.id}")
        
        # 5. 维度验证
        actual_dim = len(chunk.embedding)
        if actual_dim != expected_dim:
            raise ValueError(
                f"Chunk {chunk.id} dimension mismatch: "
                f"expected {expected_dim}, got {actual_dim}"
            )
        
        # 6. 数值范围检查
        for i, val in enumerate(chunk.embedding):
            if not isinstance(val, (int, float)):
                raise ValueError(f"Non-numeric value in {chunk.id}")
            if not (-1e10 < val < 1e10):
                raise ValueError(f"Extreme value in {chunk.id}: {val}")
    
    # 7. 批量 upsert
    await self._client.upsert(collection_name=..., points=points)
```

### 3. 验证覆盖范围

| 验证项 | Ingestion | Qdrant | 说明 |
|--------|-----------|--------|------|
| **文本非空** | ✅ | ✅ | 防止空内容生成无效向量 |
| **向量数量** | ✅ | ❌ | API 返回数量匹配检查 |
| **向量非空** | ✅ | ✅ | 防止 None 或 [] |
| **类型检查** | ✅ | ✅ | 确保是 List[float] |
| **维度匹配** | ✅ | ✅ | 1536 维度检查 |
| **NaN/Inf** | ✅ | ❌ | 防止无效数值 |
| **极值检查** | ❌ | ✅ | 防止异常大的数值 |

---

## 最佳实践

### 1. 文档上传

```python
# ✅ 好的做法
await upload_documents(
    user_id="user_12345",
    corpus_name="project_docs",
    corpus_description="项目相关文档",
    files=[file1, file2, file3]
)

# ❌ 不好的做法
# 1. 不指定 corpus_name (使用默认值不够语义化)
# 2. 上传过大文件 (超过 max_upload_size_mb)
# 3. 不处理 failed_files (忽略错误)
```

### 2. Collection 管理

```python
# ✅ 启用 per-user collections
config.rag.per_user_collections = True
config.rag.collection_name_template = "kb_{user_id}_{corpus_id}"

# ✅ 不同用户数据隔离
# user_1 → kb_user-1_tech
# user_2 → kb_user-2_tech

# ❌ 所有用户共享一个 collection (数据混淆)
config.rag.per_user_collections = False
```

### 3. 检索参数调优

```python
# 🎯 高精度场景 (法律、医疗)
config.rag.top_k = 3
config.rag.min_score = 0.75  # 只返回高相关度结果

# 🎯 通用对话场景
config.rag.top_k = 5
config.rag.min_score = 0.15  # 允许一些弱相关结果

# 🎯 探索性查询
config.rag.top_k = 10
config.rag.min_score = 0.05  # 广泛检索
```

### 4. 文本切块策略

```python
# ✅ 技术文档 (保留完整语义)
chunk_size = 500
chunk_overlap = 100

# ✅ 对话记录 (较小块)
chunk_size = 300
chunk_overlap = 60

# ✅ 长篇文章 (较大块)
chunk_size = 800
chunk_overlap = 150

# ❌ 过小 (语义碎片化)
chunk_size = 100  # 不推荐

# ❌ 过大 (检索不精确)
chunk_size = 2000  # 不推荐
```

### 5. 错误处理

```python
# ✅ 优雅降级
try:
    rag_results = await _retrieve_rag_snippets(state)
except Exception as e:
    logger.warning(f"RAG retrieval failed: {e}")
    rag_results = []  # 继续处理，不中断对话

# ✅ 详细的错误日志
logger.error(
    f"Failed to upsert chunks: {e}. "
    f"Batch size: {len(batch)}, "
    f"First chunk ID: {batch[0].id if batch else 'N/A'}"
)

# ❌ 直接抛出异常 (中断用户对话)
rag_results = await _retrieve_rag_snippets(state)  # 可能失败
```

### 6. 性能优化

```python
# ✅ 批量处理
ingest_batch_size = 16  # 一次处理 16 个 chunks

# ✅ 适当的超时
request_timeout = 15  # 15 秒

# ✅ 连接池
# EmbeddingClient 和 QdrantClient 内部维护连接池

# ❌ 逐个处理 (太慢)
for chunk in chunks:
    embedding = await embed_texts([chunk.text])  # 不高效

# ✅ 批量处理
embeddings = await embed_texts([c.text for c in chunks])
```

---

## 总结

### 核心架构特点

1. **四层分离**: API → Service → Storage → Agent
2. **模块化设计**: 每个组件职责单一，易于测试
3. **动态集成**: RAG 检索无缝集成到对话流程
4. **数据隔离**: Per-user collections 保证隐私
5. **容错机制**: 多层验证 + 优雅降级

### 数据流总结

```
文档上传 → 解析 → 切块 → 嵌入 → 存储 (Qdrant + PostgreSQL)
                                        ↓
用户提问 → 嵌入 → 检索 → 格式化 → 注入 prompt → LLM 生成 → 回答
```

### 关键优势

- ✅ **准确性**: 基于知识库的回答更可靠
- ✅ **可追溯**: 每个答案都有来源引用
- ✅ **可扩展**: 支持动态添加文档
- ✅ **高性能**: 向量检索 < 100ms
- ✅ **易维护**: 清晰的模块划分

### 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| **向量存储** | Qdrant | 高效相似度搜索 |
| **元数据存储** | PostgreSQL | 文档和块的元数据 |
| **嵌入服务** | OpenAI Compatible API | 生成向量 |
| **Agent框架** | LangGraph | 对话流程编排 |
| **API框架** | FastAPI | HTTP 接口 |
| **文档解析** | pypdf, python-docx | 多格式支持 |

---

这个架构实现了一个**生产级的 RAG 系统**，具备完整的文档管理、向量检索和对话增强能力！🎉

