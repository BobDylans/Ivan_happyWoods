# RAG & Qdrant 集成指南

本指南介绍如何使用 Qdrant 与外部嵌入 API（OpenAI 兼容）为 Ivan_HappyWoods Voice Agent 提供检索增强（RAG）能力。

## 目录

- [架构概览](#架构概览)
- [前置准备](#1-前置准备)
- [配置环境](#2-配置-env)
- [导入文档](#3-导入文档到-qdrant)
- [运行与验证](#4-运行与验证)
- [常见问题](#5-常见问题)
- [故障排查](#6-故障排查)
- [性能调优](#7-性能调优)
- [扩展](#8-扩展)

---

## 架构概览

RAG 模块采用模块化设计，各组件职责清晰：

```
┌─────────────────────────────────────────────────────────┐
│                     RAG Architecture                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │   Agent      │─────▶│  RAGService  │                │
│  │   Nodes      │      │              │                │
│  └──────────────┘      └───────┬──────┘                │
│                                │                         │
│       ┌────────────────────────┼────────────────┐       │
│       │                        │                 │       │
│       ▼                        ▼                 ▼       │
│  ┌──────────┐        ┌─────────────┐    ┌──────────┐   │
│  │ Embedding│        │   Qdrant    │    │ Ingestion│   │
│  │  Client  │        │ VectorStore │    │  Utils   │   │
│  └──────────┘        └─────────────┘    └──────────┘   │
│       │                      │                 │         │
│       ▼                      ▼                 ▼         │
│  ┌──────────────────────────────────────────────────┐   │
│  │          External Services                       │   │
│  │  • OpenAI Embeddings API                        │   │
│  │  • Qdrant Vector Database (Docker)             │   │
│  │  • PostgreSQL (Metadata, Optional)             │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| **EmbeddingClient** | `src/rag/embedding_client.py` | 调用外部嵌入 API，将文本转换为向量 |
| **QdrantVectorStore** | `src/rag/qdrant_store.py` | Qdrant 客户端封装，管理集合和向量存储 |
| **RAGService** | `src/rag/service.py` | 高级检索服务，组合 Embedding + Qdrant |
| **Ingestion** | `src/rag/ingestion.py` | 文档加载、分块、向量化批处理 |
| **RAGRepository** | `src/database/repositories/rag_repository.py` | 元数据持久化（可选） |

### 数据流

1. **文档导入**：
   ```
   文档文件 → 文本提取 → 分块 → 生成向量 → 存入 Qdrant → 记录元数据（可选）
   ```

2. **检索流程**：
   ```
   用户查询 → 生成查询向量 → Qdrant 相似度搜索 → 返回相关文本片段 → 注入 LLM 提示
   ```

---

## 1. 前置准备

- 启动 `docker-compose` 中的 `qdrant` 服务：
  ```bash
  docker-compose up -d qdrant
  ```
- 准备好外部 LLM/Embedding 服务的 `base_url` 与 `api_key`（与对话使用的接口相同）。

## 2. 配置 `.env`

在 `.env` 中新增/确认以下变量（示例）：

```ini
# Qdrant 向量库
VOICE_AGENT_RAG__ENABLED=true
VOICE_AGENT_RAG__QDRANT_URL=http://localhost:6333
VOICE_AGENT_RAG__QDRANT_API_KEY=
VOICE_AGENT_RAG__COLLECTION=voice_docs
VOICE_AGENT_RAG__PER_USER_COLLECTIONS=false
VOICE_AGENT_RAG__COLLECTION_NAME_TEMPLATE="{collection}_{user_id}_{corpus_id}"
VOICE_AGENT_RAG__DEFAULT_CORPUS_NAME=default

# 检索参数
VOICE_AGENT_RAG__CHUNK_SIZE=300
VOICE_AGENT_RAG__CHUNK_OVERLAP=60
VOICE_AGENT_RAG__TOP_K=5
VOICE_AGENT_RAG__MIN_SCORE=0.15

# 嵌入模型（OpenAI text-embedding-3-small → 1536 维）
VOICE_AGENT_RAG__EMBED_MODEL=text-embedding-3-small
VOICE_AGENT_RAG__EMBED_DIM=1536
VOICE_AGENT_RAG__REQUEST_TIMEOUT=15

# 文档导入（默认同时处理 Markdown / PDF / DOCX）
VOICE_AGENT_RAG__DOC_GLOB="docs/**/*.md;docs/**/*.pdf;docs/**/*.docx"
# 可选：使用 VOICE_AGENT_RAG__DOC_GLOBS 逐项指定多个 glob
# 可选：限制大文件体积
VOICE_AGENT_RAG__PDF_MAX_PAGES=25
VOICE_AGENT_RAG__DOCX_MAX_PARAGRAPHS=
```

> 对话 LLM 设置请同时指向外部接口，例如：
> ```ini
> VOICE_AGENT_LLM__PROVIDER=openai
> VOICE_AGENT_LLM__BASE_URL=https://api.openai.com/v1
> VOICE_AGENT_LLM__API_KEY=sk-...
> VOICE_AGENT_LLM__MODELS__DEFAULT=gpt-5-mini
> VOICE_AGENT_LLM__MODELS__FAST=gpt-5-mini
> VOICE_AGENT_LLM__MODELS__CREATIVE=gpt-5-mini
> ```

## 3. 导入文档到 Qdrant

运行脚本将 `docs/` 目录内容转入向量库（默认会处理 `.md`、`.pdf`、`.docx`）：

```bash
source venv/Scripts/activate            # Windows PowerShell 对应 .\venv\Scripts\Activate.ps1
python scripts/rag_ingest.py            # 默认遍历 docs/**/*.md/.pdf/.docx

# 可选参数
python scripts/rag_ingest.py --recreate         # 重建集合
python scripts/rag_ingest.py --docs-glob "docs/handbook/**/*.md;docs/specs/**/*.pdf"
 python scripts/rag_ingest.py --batch-size 8

# 如果使用代理（Clash 等），脚本会自动把 Qdrant 主机加入 NO_PROXY，确保 502 不再出现。
```

### 通过 API 上传文档

后端提供了两个上传接口：

- `POST /api/v1/rag/upload`：兼容旧版调用，可选传入 `user_id`、`corpus_name` 等参数。
- `POST /api/v1/rag/user/upload`：推荐使用的新接口，需要 `user_id`（表单字段），并在首次上传时自动创建对应用户/知识库的集合。

两者均支持一次性上传多个 `.md` / `.markdown` / `.mdx` / `.txt` / `.pdf` / `.docx` 文件，服务会将文件写入临时目录（默认 `docs/uploads`），完成向量化后自动删除。

```bash
curl -X POST "http://localhost:8000/api/v1/rag/user/upload" \
  -H "X-API-Key: <可选，若启用鉴权>" \
  -F "user_id=<uuid>" \
  -F "corpus_name=manual" \
  -F "files=@docs/guide.md" \
  -F "files=@docs/whitepaper.pdf"
```

接口默认限制单个文件大小不超过 `VOICE_AGENT_RAG__MAX_UPLOAD_SIZE_MB`（默认 20MB），可通过 `.env` 调整。响应会返回每个文件的处理状态、落库的向量条数以及简要摘要。

脚本会：

1. 读取 Markdown / PDF / DOCX 文档并按约 300 字符切片；
2. 调用外部 `text-embedding-3-small` 模型生成向量；
3. 将文本及元数据写入 Qdrant（默认集合 `voice_docs`；若启用 `PER_USER_COLLECTIONS`，会根据模板自动拼接用户/知识库专属集合名）。

> **提示**：当 `VOICE_AGENT_RAG__PER_USER_COLLECTIONS=true` 时，所有检索与导入都需要提供 `user_id`（UUID 格式）。可选的 `corpus_name` / `corpus_id` 会参与集合名生成，帮助同一用户维护多个知识库。

## 4. 运行与验证

1. 重新启动后端服务：
   ```bash
   python start_server.py
   ```
2. 访问 `http://127.0.0.1:8000/api/v1/health`，会看到 `rag` 组件状态（Qdrant 可达时显示 “Qdrant reachable”）。
3. 对话时，Agent 会在调用 LLM 之前自动检索 Qdrant，并将匹配片段注入系统提示。

## 5. 常见问题

| 问题 | 解决方案 |
|------|-----------|
| 健康检查显示 RAG disabled | 确认 `.env` 中 `VOICE_AGENT_RAG__ENABLED=true` |
| 检索无结果 | 检查是否已运行 `rag_ingest.py`，以及 Qdrant 中存在向量 |
| 嵌入请求超时 | 调整 `VOICE_AGENT_RAG__REQUEST_TIMEOUT` 或减小 `--batch-size` |
| 向量维度不匹配 | 确保 `EMBED_DIM` 与实际模型输出一致（如 `text-embedding-3-small` = 1536） |

---

## 6. 故障排查

### 6.1 向量维度不匹配错误

**症状**：
```
ValueError: Embedding dimensionality mismatch: expected 1536, got 3072
```
或 Qdrant 返回 `Web input… expected dim: 1536, got 3072`

**原因**：配置中的嵌入模型已更改（如从 `text-embedding-3-small` 切换到 `text-embedding-3-large`），但 Qdrant 集合仍按旧维度创建。

**解决方案**：
1. 确认当前使用的嵌入模型和维度：
   ```bash
   # text-embedding-3-small → 1536
   # text-embedding-3-large → 3072
   # text-embedding-ada-002 → 1536
   ```
2. 更新 `.env` 确保一致：
   ```ini
   VOICE_AGENT_RAG__EMBED_MODEL=text-embedding-3-large
   VOICE_AGENT_RAG__EMBED_DIM=3072
   ```
3. 删除旧集合并重新导入：
   ```bash
   # 方式 1：通过 Qdrant API
   curl -X DELETE http://localhost:6333/collections/voice_docs
   
   # 方式 2：使用 --recreate 参数
   python scripts/rag_ingest.py --recreate
   ```

### 6.2 嵌入服务超时

**症状**：
```
httpx.TimeoutException
```
日志显示 `RAG ingestion failed:` 但无详细错误信息。

**原因**：嵌入 API 响应慢于 `REQUEST_TIMEOUT` 设置（默认 15 秒）。

**解决方案**：
1. 增加超时时间：
   ```ini
   VOICE_AGENT_RAG__REQUEST_TIMEOUT=60
   ```
2. 减小批处理大小：
   ```bash
   python scripts/rag_ingest.py --batch-size 4
   ```
3. 检查网络连接和代理配置。

### 6.3 Qdrant 连接失败

**症状**：
```
ConnectionError: [Errno 111] Connection refused
```

**检查清单**：
1. 确认 Qdrant 容器正在运行：
   ```bash
   docker ps | grep qdrant
   ```
2. 检查端口映射：
   ```bash
   docker logs qdrant
   ```
3. 验证 URL 配置：
   ```ini
   VOICE_AGENT_RAG__QDRANT_URL=http://localhost:6333
   ```
4. 如果使用代理，确保 `localhost` 在 `NO_PROXY` 中（脚本会自动配置）。

### 6.4 向量数据损坏

**症状**：Qdrant 返回 `Service internal error… OutputTooSmall`

**原因**：历史上传时写入了空向量或错误的向量。

**解决方案**：
```bash
# 删除损坏的集合
curl -X DELETE http://localhost:6333/collections/voice_docs

# 重新导入
python scripts/rag_ingest.py --recreate
```

### 6.5 用户不存在错误

**症状**：
```
User <uuid> does not exist; cannot ingest documents.
```

**原因**：启用了数据库元数据记录，但上传文档时指定的 `user_id` 在 `users` 表中不存在。

**解决方案**：
1. 先创建用户（通过注册接口或数据库）
2. 或禁用数据库：
   ```ini
   VOICE_AGENT_DATABASE__ENABLED=false
   ```

---

## 7. 性能调优

### 7.1 批处理大小

- **默认**：16 个文档块/批次
- **建议**：
  - 本地测试：4-8
  - 生产环境：16-32（根据 Embedding API 速率限制调整）
- **配置**：
  ```ini
  VOICE_AGENT_RAG__INGEST_BATCH_SIZE=16
  ```

### 7.2 分块参数

影响检索精度和存储成本的平衡：

| 参数 | 默认值 | 说明 | 调优建议 |
|------|--------|------|----------|
| `CHUNK_SIZE` | 300 | 每个文本块的字符数 | 技术文档：300-500；长文本：800-1000 |
| `CHUNK_OVERLAP` | 60 | 块之间的重叠字符数 | 保持 15-20% 的重叠率 |
| `TOP_K` | 5 | 检索返回的最大片段数 | 对话：3-5；总结：10-15 |
| `MIN_SCORE` | 0.15 | 最低相似度阈值 | 严格：0.3；宽松：0.1 |

### 7.3 大文件限制

防止单个文档占用过多资源：

```ini
# PDF 文件最大页数（None = 无限制）
VOICE_AGENT_RAG__PDF_MAX_PAGES=50

# DOCX 文件最大段落数
VOICE_AGENT_RAG__DOCX_MAX_PARAGRAPHS=200

# 上传文件大小限制（MB）
VOICE_AGENT_RAG__MAX_UPLOAD_SIZE_MB=20
```

### 7.4 按用户隔离集合

启用后每个用户拥有独立的向量集合：

```ini
VOICE_AGENT_RAG__PER_USER_COLLECTIONS=true
VOICE_AGENT_RAG__COLLECTION_NAME_TEMPLATE="{collection}_{user_id}_{corpus_id}"
```

**优点**：数据隔离、安全性高  
**缺点**：管理复杂度增加、存储成本上升

---

## 8. 扩展

- 如需导入更多目录，可修改 `.env` 的 `VOICE_AGENT_RAG__DOC_GLOB` / `VOICE_AGENT_RAG__DOC_GLOBS`，或运行脚本时指定 `--docs-glob`（多个模式用 `,` / `;` 分隔）。
- `VOICE_AGENT_RAG__PDF_MAX_PAGES` 与 `VOICE_AGENT_RAG__DOCX_MAX_PARAGRAPHS` 可限制大文件的页数 / 段落数，防止导入过量文本。
- 若后续要更换向量数据库，只需替换 `rag/qdrant_store.py` 中的实现即可。

完成以上配置后，RAG 功能即可与语音代理无缝协作，帮助模型利用项目文档提供更准确的回答。祝使用愉快！


