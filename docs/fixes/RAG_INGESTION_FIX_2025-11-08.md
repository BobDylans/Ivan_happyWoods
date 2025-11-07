# RAG 文档上传问题修复报告

**日期**: 2025-11-08  
**问题**: RAG 文档上传失败，包含数据库会话错误和 PDF 文件解析错误

## 问题描述

### 问题 1: 数据库会话获取方式已弃用
**错误信息**:
```
RAG metadata persistence disabled: get_async_session() is deprecated and no longer uses global state.
```

**原因**: 
- `src/rag/ingestion.py` 中的 `ingest_files` 函数尝试使用已弃用的 `get_async_session()` 方法
- 新的架构要求通过依赖注入获取数据库会话，而不是创建全局会话

### 问题 2: PDF 文件解析失败
**错误信息**:
```
Failed to load D:\Projects\ivanHappyWoods\backEnd\docs\uploads\49997d4d138649d08b260a4e1dffe928.pdf: Stream has ended unexpectedly
```

**原因**:
- PDF 文件可能损坏或不完整
- `pypdf` 库在严格模式下无法处理格式不规范的 PDF

## 解决方案

### 1. 修复数据库会话问题

#### 修改 `src/rag/ingestion.py`
- **添加 `db_session` 参数**: `ingest_files` 函数现在接受可选的 `db_session` 参数
- **移除弃用调用**: 不再尝试调用 `get_async_session()`，而是使用传入的会话
- **优雅降级**: 如果没有提供会话，则跳过数据库持久化但继续向量存储

**关键代码更改**:
```python
async def ingest_files(
    config: VoiceAgentConfig,
    files: Sequence[Path],
    *,
    # ... 其他参数 ...
    db_session: Optional[Any] = None,  # 新增参数
) -> IngestionResult:
    # ...
    session = db_session  # 使用传入的会话
    if owner_uuid and config.database.enabled and session:
        # 使用提供的会话进行数据库操作
```

#### 修改 `src/api/routes.py`
- **导入依赖**: 添加 `get_db_session` 和 `AsyncSession` 导入
- **更新端点**: 两个上传端点 (`/upload` 和 `/user/upload`) 现在通过依赖注入获取数据库会话
- **传递会话**: 将会话传递给 `_handle_rag_upload` 和 `ingest_files`

**关键代码更改**:
```python
from core.dependencies import (
    # ...
    get_db_session,
)
from sqlalchemy.ext.asyncio import AsyncSession

@rag_router.post("/upload", response_model=RAGUploadResponse)
async def upload_documents(
    # ...
    db_session: AsyncSession = Depends(get_db_session),  # 依赖注入
) -> RAGUploadResponse:
    return await _handle_rag_upload(
        # ...
        db_session=db_session,  # 传递会话
    )
```

### 2. 增强 PDF 文件解析

#### 修改 `src/rag/ingestion.py` 中的 `_extract_pdf_text`
- **非严格模式**: 使用 `PdfReader(path, strict=False)` 来容忍格式错误
- **错误处理**: 捕获 PDF 打开失败的异常并提供清晰的错误信息
- **页面级容错**: 如果单个页面提取失败，记录警告但继续处理其他页面
- **准确计数**: 更新 `page_count` 以反映实际成功提取的页面数

**关键代码更改**:
```python
def _extract_pdf_text(path: Path, max_pages: Optional[int]) -> Tuple[str, Dict[str, Any]]:
    _ensure_dependency("pypdf", PdfReader is not None)
    try:
        reader = PdfReader(str(path), strict=False)  # 非严格模式
    except Exception as exc:
        raise ValueError(f"Failed to open PDF file: {exc}") from exc
    
    # ...
    collected: List[str] = []
    for index in range(limit):
        try:
            page = reader.pages[index]
            text = page.extract_text() or ""
            collected.append(text)
        except Exception as exc:
            logger.warning("Failed to extract text from page %s of %s: %s", index + 1, path.name, exc)
            continue  # 跳过问题页面但继续处理
    
    metadata = {
        # ...
        "page_count": len(collected),  # 实际提取的页面数
        # ...
    }
```

## 修改文件列表

1. **src/rag/ingestion.py**
   - 添加 `db_session` 参数到 `ingest_files`
   - 移除 `get_async_session()` 调用
   - 增强 `_extract_pdf_text` 的错误处理

2. **src/api/routes.py**
   - 导入 `get_db_session` 和 `AsyncSession`
   - 更新 `_handle_rag_upload` 接受 `db_session` 参数
   - 更新 `/upload` 和 `/user/upload` 端点使用依赖注入

## 测试建议

### 测试数据库集成
```bash
# 上传测试文档（需要有效的用户 UUID）
curl -X POST "http://localhost:8000/api/v1/rag/user/upload" \
  -F "files=@test_doc.txt" \
  -F "user_id=00000000-0000-0000-0000-000000000001" \
  -F "corpus_name=test_corpus"
```

### 测试 PDF 容错性
```bash
# 上传可能损坏的 PDF（不会阻止整个流程）
curl -X POST "http://localhost:8000/api/v1/rag/upload" \
  -F "files=@possibly_malformed.pdf"
```

## 影响范围

- **向后兼容**: ✅ `db_session` 是可选参数，不破坏现有调用
- **离线脚本**: ⚠️ `scripts/rag_ingest.py` 不受影响（它不使用数据库持久化）
- **API 端点**: ✅ 现在正确使用依赖注入获取数据库会话
- **错误处理**: ✅ 增强了 PDF 解析的容错性

## 后续改进建议

1. **文件验证**: 在上传时预先验证 PDF 文件完整性
2. **更详细日志**: 记录每个成功提取的页面和跳过的页面
3. **重试机制**: 对于网络上传的文件，可以考虑重新下载损坏的文件
4. **用户反馈**: 在 API 响应中返回部分成功的页面信息

## 相关文档

- [数据库依赖注入指南](../guides/DATABASE_INTEGRATION_PLAN.md)
- [RAG 设置文档](../RAG_SETUP.md)
- [代码重构总结](../CODE_REFACTORING_SUMMARY.md)

---

**修复状态**: ✅ 已完成  
**验证状态**: ⏳ 待用户测试确认

