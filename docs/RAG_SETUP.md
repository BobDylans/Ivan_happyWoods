# RAG & Qdrant 集成指南

本指南介绍如何使用 Qdrant 与外部嵌入 API（OpenAI 兼容）为 Ivan_HappyWoods Voice Agent 提供检索增强（RAG）能力。

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

后端提供了 `POST /api/v1/rag/upload` 接口，支持一次性上传多个 `.md` / `.pdf` / `.docx` 文件，服务会将文件写入临时目录（默认 `docs/uploads`），完成向量化后自动删除。

```bash
curl -X POST http://localhost:8000/api/v1/rag/upload \
  -H "X-API-Key: <可选，若启用鉴权>" \
  -F "files=@docs/guide.md" \
  -F "files=@docs/whitepaper.pdf"
```

接口默认限制单个文件大小不超过 `VOICE_AGENT_RAG__MAX_UPLOAD_SIZE_MB`（默认 20MB），可通过 `.env` 调整。响应会返回每个文件的处理状态、落库的向量条数以及简要摘要。

脚本会：

1. 读取 Markdown / PDF / DOCX 文档并按约 300 字符切片；
2. 调用外部 `text-embedding-3-small` 模型生成向量；
3. 将文本及元数据写入 Qdrant（集合默认 `voice_docs`）。

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

## 6. 扩展

- 如需导入更多目录，可修改 `.env` 的 `VOICE_AGENT_RAG__DOC_GLOB` / `VOICE_AGENT_RAG__DOC_GLOBS`，或运行脚本时指定 `--docs-glob`（多个模式用 `,` / `;` 分隔）。
- `VOICE_AGENT_RAG__PDF_MAX_PAGES` 与 `VOICE_AGENT_RAG__DOCX_MAX_PARAGRAPHS` 可限制大文件的页数 / 段落数，防止导入过量文本。
- 若后续要更换向量数据库，只需替换 `rag/qdrant_store.py` 中的实现即可。

完成以上配置后，RAG 功能即可与语音代理无缝协作，帮助模型利用项目文档提供更准确的回答。祝使用愉快！


