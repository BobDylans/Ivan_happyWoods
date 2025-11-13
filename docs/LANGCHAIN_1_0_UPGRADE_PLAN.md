# LangChain 1.0 升级执行计划

> 版本：2025-11-12  
> 负责人：语音代理平台小组  
> 关联文件：`requirements.txt`、`src/agent/*`、`src/utils/llm_compat.py`、`docs/PROJECT.md`

---

## 1. 背景与动机

- 目前依赖仍停留在 `langchain==0.3.27`、`langchain-core==0.3.76`，缺失 1.0 长期支持与 bug 修复。
- LLM 调用、工具执行、消息构造均为自研逻辑，无法复用 LangChain Expression Language (LCEL) 的 `Runnable`、`StructuredTool`、`RunnableWithMessageHistory` 等能力。
- LangChain 1.0 在可观测性（LangSmith tracing）、多模型适配、批量/流式接口方面提供稳定 API，可显著降低维护成本。

**升级目标**
1. 依赖迁移至 LangChain 1.0 系列，并确保 LangGraph 版本兼容。
2. 用 LCEL 重写核心链路，使 `VoiceAgent` 的 LLM/工具节点都以 `Runnable` 形式存在。
3. 将 MCP 工具注册改造成标准 `StructuredTool`，交由 LangGraph `ToolNode` 调度。
4. 完成端到端回归（pytest、mypy、手工语音+RAG 测试），并更新 PROJECT/ROADMAP 文档。

成功标准：测试全部通过，Prometheus 指标与 LangSmith Trace 同步，生产配置无需倒退。

---

## 2. 范围

**包含**
- `requirements.txt` 依赖升级与兼容性修复。
- `src/utils/llm_compat.py`、`src/agent/nodes/*`、`src/agent/graph.py` 的 LCEL 重构。
- MCP 工具注册 / `ToolHandler` 与 LangChain `StructuredTool` 对齐。
- 观测链路接入 `RunnableConfig`，并补充文档/回归测试。

**不包含**
- 大规模业务逻辑改写（如 Agent prompt 策略、会话数据库 schema）。
- 非 LangChain 相关依赖（FastAPI、Qdrant 等）的升级。

---

## 3. 执行阶段

### 阶段 A：准备与调研（0.5 周）
| 任务 | 说明 | 产出 |
| --- | --- | --- |
| 依赖审计 | 逐项确认与 LangChain 绑定的三方库版本（如 `langchain-openai`、`langchain-community`、`langgraph`） | 依赖矩阵、升级风险清单 |
| 分支与环境 | 创建 `feat/langchain-1-upgrade` 分支，准备独立虚拟环境 | 可重复安装说明 |
| 基线测试 | 在升级前运行 `pytest`、`mypy`、`python start_server.py` | 现状测试记录 |

### 阶段 B：依赖与 API 适配（1 周）
1. **升级 requirements**：将 LangChain 相关包锁定到 `>=1.0,<2.0`，同步 `langgraph` 到最新兼容版本。
2. **修复导入**：处理 1.0 中移动/拆分的模块（如 loader、embeddings）。
3. **LLM 适配**：用 `ChatOpenAI` + `RunnableConfig` 替代 `prepare_llm_params`，并保留模型默认值校验。
4. **基础验证**：运行核心单元测试、启动服务器、人工调用 `/api/v1/conversation/send` 。

### 阶段 C：链路重构（1.5 周）
| 子任务 | 重点 |
| --- | --- |
| LLM 节点 LCEL 化 | `AgentNodes.call_llm` / `llm_streamer` 使用 `ChatPromptTemplate` + `RunnableSequence`，并用 `RunnableWithMessageHistory` 挂接 `SessionManager`。 |
| 工具节点 | 将 MCP 工具注册输出转换为 `StructuredTool`，LangGraph 使用 `ToolNode` 驱动循环，`ToolHandler` 仅负责持久化与指标。 |
| Config/Tracing | 在 `VoiceAgent` 构建图时统一传入 `RunnableConfig`（含 LangSmith callbacks、tags、metadata），保留 Prometheus 指标。 |
| 回归测试 | 新增/更新单测覆盖 LCEL pipeline，重点关注流式输出、工具重入、RAG 注入等路径。 |

### 阶段 D：验证与发布（0.5 周）
1. **完整测试**：`pytest`, `pytest tests/integration -m integration`, `python -m mypy src`。
2. **性能抽样**：记录 LLM 延迟、工具调用成功率，与旧版本对比（至少 20 次会话）。
3. **文档更新**：`PROJECT.md`、`ROADMAP.md`、`CHANGELOG.md` 新增升级条目；补充 `docs/` 中的运行指南。
4. **发布流程**：提交 PR（Conventional Commit），附测试结果与回滚方案；经 code review 后合并部署。

---

## 4. 时间表（示例）
| 周次 | 里程碑 |
| --- | --- |
| Week 1 | 完成阶段 A & B，依赖升级 + 基础验证通过 |
| Week 2 | 完成阶段 C（LLM/工具重构），新增测试全部绿灯 |
| Week 3 | 阶段 D 验证、文档同步、上线评审 |

---

## 5. 风险与缓解
| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 第三方依赖冲突（如 `langgraph` 的 checkpoint API 变化） | 构建失败或运行异常 | 预先在独立 venv 验证；必要时锁定特定 patch 版本并记录原因 |
| LCEL 重构引入逻辑差异 | 回归 bug、对话质量下降 | 保留旧节点实现作为 fallback，灰度期间开启配置开关 |
| 观测链路双写失败（Prometheus vs LangSmith） | 指标不一致、排障困难 | 在 Stage 环境先跑两天，确认双通道数据可对齐才切生产 |
| 工具注册 Schema 变化 | 前端/调用方不兼容 | 在 API 响应中同时暴露旧格式（deprecated）与新 schema，提供迁移指南 |

---

## 6. 验收清单
- [ ] `requirements.txt` 已升级并在 CI 中可安装。
- [ ] `VoiceAgent` 图中所有 LLM/工具节点均由 LCEL Runnable 驱动。
- [ ] `ToolNode` 成功执行 MCP 工具，结果可持久化且可被观测。
- [ ] `pytest`、`mypy`、`python start_server.py` 全部通过。
- [ ] `PROJECT.md`/`ROADMAP.md`/`CHANGELOG.md` 已更新，新增版本号及说明。
- [ ] LangSmith Trace 与 Prometheus 指标均可看到完整对话。

---

## 7. 附录：参考资料
- LangChain 1.0 官方概览：https://docs.langchain.com/oss/python/langchain/overview
- LangChain Expression Language：https://docs.langchain.com/oss/python/langchain/expression_language
- 项目当前架构：`PROJECT.md`
- 近期变更记录：`CHANGELOG.md`

