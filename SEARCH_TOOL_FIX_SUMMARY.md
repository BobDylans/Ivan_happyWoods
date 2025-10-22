# Web Search Tool 修复总结

## 🔍 问题诊断

### 当前问题
用户在使用 web_search 工具搜索"针对特朗普的抗议活动"时，返回的是占位符结果（mock data），而不是真实的搜索结果。

### 根本原因
`src/mcp/tools.py` 中的 `SearchTool` 类目前使用的是 **mock 实现**（第258-299行）：

```python
# Mock search results
mock_results = [
    {
        "title": f"Result {i+1} for '{query}'",
        "snippet": f"This is a mock search result snippet for query: {query}. "
                   f"In production, this would return real search results.",
        "url": f"https://example.com/result{i+1}",
        "rank": i + 1
    }
    for i in range(num_results)
]
```

这就是为什么返回的结果都是"This is a mock search result snippet..."的占位符文本。

---

## 🛠️ 解决方案

### 方案选择：集成 Tavily Search API

项目中已经有 Tavily 相关的测试文件：
- `tests/unit/test_tavily_search.py`
- `tests/integration/test_tavily_api_integration.py`

说明项目计划使用 Tavily API 作为搜索服务提供商。

### Tavily API 优势
1. ✅ 专为 LLM 优化的搜索 API
2. ✅ 返回高质量、结构化的搜索结果
3. ✅ 支持中英文搜索
4. ✅ 提供 AI 生成的答案摘要
5. ✅ 包含相关性评分
6. ✅ 简单易用的 REST API

---

## 📝 实施步骤

### 步骤 1：获取 Tavily API Key

1. 访问 [Tavily官网](https://tavily.com/)
2. 注册账户
3. 获取 API Key
4. 将 API Key 添加到环境变量或配置文件

### 步骤 2：安装依赖

确保项目中已安装 `httpx`（已经在项目中使用）：
```bash
pip install httpx
```

### 步骤 3：更新 `SearchTool` 实现

需要修改 `src/mcp/tools.py` 中的 `SearchTool` 类，将 mock 实现替换为 Tavily API 调用。

#### 修改前（mock）：
```python
async def execute(self, query: str, num_results: int = 5, **kwargs) -> ToolResult:
    # Mock search results
    mock_results = [...]
    return ToolResult(success=True, data={...}, metadata={"source": "mock"})
```

#### 修改后（Tavily）：
```python
async def execute(self, query: str, num_results: int = 5, **kwargs) -> ToolResult:
    # 从配置或环境变量获取 API key
    api_key = os.getenv("TAVILY_API_KEY") or self.config.get("api_key")
    
    # 调用 Tavily API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": num_results,
                "include_answer": True
            }
        )
        
        data = response.json()
        # 返回真实搜索结果
        return ToolResult(success=True, data=data, metadata={"source": "tavily"})
```

### 步骤 4：配置 API Key

#### 方法 1：环境变量（推荐）
在 `.env` 文件中添加：
```bash
TAVILY_API_KEY=tvly-your-api-key-here
```

#### 方法 2：配置文件
在 `config/development.yaml` 中添加：
```yaml
tools:
  search_tool:
    enabled: true
    provider: "tavily"
    api_key: "tvly-your-api-key-here"
    timeout: 15
    max_retries: 2
```

### 步骤 5：测试验证

运行测试：
```bash
# 单元测试
python tests/unit/test_tavily_search.py

# 集成测试
python tests/integration/test_tavily_api_integration.py
```

---

## 🎯 预期效果

修复后，当用户搜索"针对特朗普的抗议活动"时，将返回：

```json
{
  "success": true,
  "data": {
    "query": "针对特朗普的抗议活动",
    "ai_answer": "最近针对特朗普的抗议活动...[真实的AI生成摘要]",
    "results": [
      {
        "title": "真实新闻标题",
        "snippet": "真实的新闻摘要内容",
        "url": "https://real-news-site.com/article",
        "score": 0.95,
        "published_date": "2025-10-20"
      },
      ...
    ],
    "total_results": 5
  },
  "metadata": {
    "source": "tavily",
    "search_time_ms": 234
  }
}
```

---

## 📊 对比：Mock vs Tavily

| 特性 | Mock 实现 | Tavily 实现 |
|------|----------|------------|
| 数据真实性 | ❌ 假数据 | ✅ 真实搜索结果 |
| 时效性 | ❌ 无 | ✅ 最新信息 |
| AI 答案 | ❌ 无 | ✅ 有 |
| 相关性评分 | ❌ 假评分 | ✅ 真实评分 |
| 发布日期 | ❌ 无 | ✅ 有 |
| 中文支持 | ❌ 有限 | ✅ 完整支持 |
| 成本 | ✅ 免费 | ⚠️ 需要 API key |

---

## 🔧 我可以提供的帮助

我可以帮你：

### 选项 1：完整实现 Tavily 集成
- 修改 `src/mcp/tools.py` 中的 `SearchTool` 类
- 添加配置管理
- 添加错误处理和重试逻辑
- 更新测试文件

### 选项 2：提供快速检索方案 + 精确搜索词与渠道清单
- 提供可直接执行的搜索方案
- 提供 Google/X/新闻站点搜索建议
- 提供关键词和监测号/标签

### 选项 3：输出总模板与解析要点
- 提供搜索结果的结构化模板
- 提供如何提取关键信息的指南
- 帮助你快速了解如何检索和解析来源

---

## ⚡ 立即行动建议

**如果你想立即解决问题**，我建议：

1. **立即方案**：我帮你完整实现 Tavily 集成（约 10-15 分钟）
   - 你只需提供 Tavily API Key
   - 我会完成所有代码修改
   - 立即测试验证

2. **临时方案**：在等待 API key 时，我可以先提供搜索方案
   - 提供 Google/X/新闻搜索链接
   - 提供关键词建议
   - 你可以手动搜索获取信息

---

**你希望采用哪个方案？**
1. 我帮你完整实现 Tavily 集成（需要 API key）
2. 我提供快速检索方案（立即可用，无需 API）
3. 两者都要（先提供检索方案，再实现 Tavily）

请告诉我你的选择，我会立即开始！🚀

