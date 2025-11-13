# Prometheus 监控指南

## 概述

本系统集成了 **Prometheus** 监控，通过 `/api/v1/metrics` 端点提供指标数据，实现对 Voice Agent 系统的全面可观测性。

## 🎯 监控架构

```
┌─────────────────┐
│  Voice Agent    │
│   Application   │
│                 │
│  ┌───────────┐  │
│  │Observability│ │ ← 收集内部指标
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │Prometheus │  │ ← 导出为 Prometheus 格式
│  │ Exporter  │  │
│  └─────┬─────┘  │
└────────┼────────┘
         │
    /api/v1/metrics
         │
         ▼
┌─────────────────┐
│   Prometheus    │ ← 定期抓取指标
│     Server      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Grafana     │ ← 可视化展示
└─────────────────┘
```

## 📊 可用指标

### 1. HTTP 请求指标

| 指标名称 | 类型 | 描述 | 标签 |
|---------|------|------|------|
| `voice_agent_http.server.request_count` | Counter | HTTP 请求总数 | `method`, `path`, `status` |
| `voice_agent_http.server.duration_ms` | Gauge | HTTP 请求响应时间 (毫秒) | `method`, `path`, `status` |

**示例 Prometheus 查询：**
```promql
# 每秒请求数 (QPS)
rate(voice_agent_http_server_request_count[1m])

# P95 响应时间
histogram_quantile(0.95, rate(voice_agent_http_server_duration_ms[5m]))

# 错误率
rate(voice_agent_http_server_request_count{status=~"5.."}[5m])
```

### 2. Agent 工作流指标

| 指标名称 | 类型 | 描述 | 标签 |
|---------|------|------|------|
| `voice_agent_agent.node_execution_count` | Counter | 节点执行次数 | `node` |
| `voice_agent_agent.node_execution_time_ms` | Gauge | 节点执行时间 (毫秒) | `node` |
| `voice_agent_agent.tool_call_count` | Counter | 工具调用次数 | `tool` |

**示例 Prometheus 查询：**
```promql
# 各节点执行频率
rate(voice_agent_agent_node_execution_count[5m])

# 工具调用成功率
rate(voice_agent_agent_tool_call_count{status="success"}[5m]) 
/ 
rate(voice_agent_agent_tool_call_count[5m])
```

### 3. LLM 调用指标

| 指标名称 | 类型 | 描述 | 标签 |
|---------|------|------|------|
| `voice_agent_llm.call_count` | Counter | LLM 调用次数 | `provider`, `model` |
| `voice_agent_llm.duration_ms` | Gauge | LLM 响应时间 (毫秒) | `provider`, `model` |
| `voice_agent_llm.token_count` | Counter | Token 消耗统计 | `provider`, `model`, `type` |

**示例 Prometheus 查询：**
```promql
# LLM 平均响应时间
avg(voice_agent_llm_duration_ms) by (provider, model)

# Token 消耗速率
rate(voice_agent_llm_token_count[1h])
```

### 4. 数据库指标

| 指标名称 | 类型 | 描述 | 标签 |
|---------|------|------|------|
| `voice_agent_database.query_count` | Counter | 数据库查询次数 | `operation` |
| `voice_agent_database.query_duration_ms` | Gauge | 查询执行时间 (毫秒) | `operation` |

**示例 Prometheus 查询：**
```promql
# 数据库查询 QPS
rate(voice_agent_database_query_count[1m])

# 慢查询 (>100ms)
voice_agent_database_query_duration_ms > 100
```

## 🚀 快速开始

### 1. 启动 Voice Agent

```bash
# 确保已安装 prometheus-client
pip install -r requirements.txt

# 启动服务
python start_server.py
```

### 2. 访问 Metrics 端点

```bash
# 查看 Prometheus 格式的指标
curl http://localhost:8000/api/v1/metrics

# 健康检查
curl http://localhost:8000/api/v1/health/prometheus
```

**示例输出：**
```
# HELP voice_agent_http_server_request_count HTTP 请求总数
# TYPE voice_agent_http_server_request_count counter
voice_agent_http_server_request_count{method="POST",path="/api/v1/chat",status="200"} 42.0

# HELP voice_agent_http_server_duration_ms HTTP 请求响应时间 (毫秒)
# TYPE voice_agent_http_server_duration_ms gauge
voice_agent_http_server_duration_ms{method="POST",path="/api/v1/chat",status="200"} 125.3
```

### 3. 配置 Prometheus Server

创建 `prometheus.yml` 配置文件：

```yaml
global:
  scrape_interval: 15s      # 每15秒抓取一次
  evaluation_interval: 15s  # 每15秒评估一次规则

scrape_configs:
  - job_name: 'voice_agent'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/metrics'
    
    # 可选：添加标签
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'voice-agent-prod'
```

### 4. 启动 Prometheus

```bash
# 使用 Docker
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# 访问 Prometheus UI
open http://localhost:9090
```

### 5. 集成 Grafana (可选)

```bash
# 启动 Grafana
docker run -d \
  --name grafana \
  -p 3000:3000 \
  grafana/grafana

# 访问 Grafana UI (默认用户名密码: admin/admin)
open http://localhost:3000
```

**在 Grafana 中配置数据源：**
1. 进入 `Configuration` → `Data Sources`
2. 添加 `Prometheus` 数据源
3. 设置 URL: `http://localhost:9090`
4. 点击 `Save & Test`

## 📈 推荐的监控仪表板

### 1. 系统概览仪表板

```json
{
  "dashboard": {
    "title": "Voice Agent 系统概览",
    "panels": [
      {
        "title": "QPS (每秒请求数)",
        "targets": [
          {
            "expr": "rate(voice_agent_http_server_request_count[1m])"
          }
        ]
      },
      {
        "title": "平均响应时间",
        "targets": [
          {
            "expr": "avg(voice_agent_http_server_duration_ms)"
          }
        ]
      },
      {
        "title": "错误率",
        "targets": [
          {
            "expr": "rate(voice_agent_http_server_request_count{status=~\"5..\"}[5m])"
          }
        ]
      }
    ]
  }
}
```

### 2. Agent 性能仪表板

- **节点执行频率**: `rate(voice_agent_agent_node_execution_count[5m]) by (node)`
- **节点平均执行时间**: `avg(voice_agent_agent_node_execution_time_ms) by (node)`
- **工具调用分布**: `rate(voice_agent_agent_tool_call_count[5m]) by (tool)`

### 3. LLM 成本分析仪表板

- **Token 消耗趋势**: `rate(voice_agent_llm_token_count[1h])`
- **各模型调用分布**: `rate(voice_agent_llm_call_count[1h]) by (model)`
- **LLM 平均延迟**: `avg(voice_agent_llm_duration_ms) by (provider)`

## 🔔 告警配置

### 1. Prometheus 告警规则

创建 `alerts.yml`：

```yaml
groups:
  - name: voice_agent_alerts
    interval: 30s
    rules:
      # 高错误率告警
      - alert: HighErrorRate
        expr: |
          rate(voice_agent_http_server_request_count{status=~"5.."}[5m]) 
          / 
          rate(voice_agent_http_server_request_count[5m]) 
          > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "错误率超过 5%"
          description: "当前错误率: {{ $value | humanizePercentage }}"

      # 高响应时间告警
      - alert: HighResponseTime
        expr: |
          avg(voice_agent_http_server_duration_ms) > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "平均响应时间超过 1 秒"
          description: "当前响应时间: {{ $value }}ms"

      # LLM 调用失败告警
      - alert: LLMCallFailure
        expr: |
          rate(voice_agent_llm_call_count{status="error"}[5m]) > 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "LLM 调用失败"
          description: "Provider: {{ $labels.provider }}, Model: {{ $labels.model }}"

      # 数据库连接异常告警
      - alert: DatabaseConnectionError
        expr: |
          rate(voice_agent_database_query_count{status="error"}[5m]) > 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "数据库连接异常"
          description: "数据库查询失败率上升"
```

### 2. 集成 Alertmanager

配置 `alertmanager.yml`：

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'team-notifications'

receivers:
  - name: 'team-notifications'
    email_configs:
      - to: 'team@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alertmanager@example.com'
        auth_password: 'your_password'
    
    # Slack 通知
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}'
```

## 🧪 测试监控

### 1. 生成测试流量

```bash
# 发送测试请求
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/v1/chat \
    -H "Content-Type: application/json" \
    -H "X-API-Key: your_api_key" \
    -d '{"message": "Hello, World!", "session_id": "test"}' &
done
```

### 2. 验证指标

```bash
# 查看 HTTP 请求计数
curl http://localhost:8000/api/v1/metrics | grep http_server_request_count

# 查看 Prometheus 健康状态
curl http://localhost:8000/api/v1/health/prometheus
```

## 🛠 故障排查

### 问题 1: `/metrics` 端点返回空数据

**原因**: Observability 没有收集到任何指标

**解决方案**:
```bash
# 1. 确认 Observability 已正确初始化
# 2. 发送几个测试请求生成指标
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test_key" \
  -d '{"message": "test", "session_id": "test"}'

# 3. 再次查看 metrics
curl http://localhost:8000/api/v1/metrics
```

### 问题 2: Prometheus 无法抓取指标

**原因**: 网络连接或配置问题

**解决方案**:
```bash
# 1. 确认 Voice Agent 正在运行
curl http://localhost:8000/api/v1/health

# 2. 确认 Prometheus 可以访问 metrics 端点
curl http://localhost:8000/api/v1/metrics

# 3. 检查 Prometheus 配置
cat prometheus.yml

# 4. 查看 Prometheus 日志
docker logs prometheus
```

### 问题 3: 指标数据不完整

**原因**: Observability 和 PrometheusExporter 数据同步问题

**解决方案**:
```python
# 在代码中手动触发指标更新
from api.metrics_routes import get_prometheus_exporter
from core.dependencies import get_observability

exporter = get_prometheus_exporter()
observability = get_observability(request)
exporter.update_from_observability(observability)
```

## 📚 最佳实践

### 1. 指标命名规范

- 使用统一的命名空间前缀: `voice_agent_`
- 使用下划线分隔: `http_server_request_count`
- 使用有意义的标签: `{method="POST", path="/api/v1/chat"}`

### 2. 合理的抓取间隔

- **开发环境**: 5-10 秒
- **生产环境**: 15-30 秒
- **高负载场景**: 可延长到 60 秒

### 3. 标签使用原则

- **避免高基数标签**: 不要使用 `session_id`, `user_id` 等唯一值作为标签
- **使用有限值标签**: `status`, `method`, `node`, `tool` 等
- **保持标签简洁**: 每个指标不超过 5-7 个标签

### 4. 性能优化

```python
# 批量更新指标，而不是单个更新
exporter.update_from_observability(observability)

# 定期清理旧指标
# Prometheus 会自动处理，无需手动清理
```

## 🔗 相关资源

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/)
- [PromQL 查询指南](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Alertmanager 配置指南](https://prometheus.io/docs/alerting/latest/configuration/)

## 📝 变更日志

| 日期 | 版本 | 变更说明 |
|------|------|---------|
| 2025-11-10 | 1.0.0 | 初始版本，集成 Prometheus 监控 |

---

**维护者**: Voice Agent Team  
**最后更新**: 2025-11-10

