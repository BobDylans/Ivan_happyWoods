# Grafana 可视化仪表板部署指南

**版本**: 1.0.0  
**日期**: 2025-11-10  
**作者**: Voice Agent Team

---

## 📊 概述

本指南将帮助你快速部署 Grafana 可视化仪表板，实现对 Voice Agent 系统的全方位监控。

### 包含的仪表板

1. **系统概览仪表板** - 总体运行状况和关键指标
2. **Agent 性能仪表板** - Agent 节点和工具执行分析
3. **LLM 成本分析仪表板** - LLM 调用和成本监控

---

## 🚀 快速开始 (Docker Compose)

### 方式一：一键启动完整监控栈

我们提供了包含 Voice Agent、Prometheus 和 Grafana 的完整 Docker Compose 配置。

#### 1. 创建 docker-compose.monitoring.yml

```yaml
version: '3.8'

services:
  # Prometheus 服务
  prometheus:
    image: prom/prometheus:latest
    container_name: voice-agent-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    networks:
      - monitoring
    restart: unless-stopped

  # Grafana 服务
  grafana:
    image: grafana/grafana:latest
    container_name: voice-agent-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/var/lib/grafana/dashboards
    networks:
      - monitoring
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:

networks:
  monitoring:
    driver: bridge
```

#### 2. 创建 Prometheus 配置文件

创建 `prometheus.yml`：

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'voice-agent-prod'

scrape_configs:
  - job_name: 'voice-agent'
    static_configs:
      - targets: ['host.docker.internal:8000']  # Windows/Mac
        # - targets: ['172.17.0.1:8000']         # Linux
    metrics_path: '/api/v1/metrics'
    scrape_interval: 15s
```

#### 3. 创建 Grafana 配置目录

```bash
# 创建目录结构
mkdir -p grafana/provisioning/datasources
mkdir -p grafana/provisioning/dashboards

# 复制仪表板文件
cp grafana/dashboards/*.json grafana/provisioning/dashboards/
```

#### 4. 配置 Grafana 数据源

创建 `grafana/provisioning/datasources/prometheus.yml`：

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
```

#### 5. 配置 Grafana 仪表板自动加载

创建 `grafana/provisioning/dashboards/dashboard.yml`：

```yaml
apiVersion: 1

providers:
  - name: 'Voice Agent Dashboards'
    orgId: 1
    folder: 'Voice Agent'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

#### 6. 启动服务

```bash
# 启动 Voice Agent（如果还没启动）
python start_server.py

# 启动监控栈
docker-compose -f docker-compose.monitoring.yml up -d

# 查看日志
docker-compose -f docker-compose.monitoring.yml logs -f
```

#### 7. 访问服务

- **Grafana**: http://localhost:3000
  - 用户名: `admin`
  - 密码: `admin123`

- **Prometheus**: http://localhost:9090

- **Voice Agent Metrics**: http://localhost:8000/api/v1/metrics

---

## 🔧 方式二：手动部署

### 1. 安装 Grafana

#### Windows

```bash
# 使用 Chocolatey
choco install grafana

# 或下载安装包
# https://grafana.com/grafana/download?platform=windows
```

#### macOS

```bash
# 使用 Homebrew
brew install grafana

# 启动服务
brew services start grafana
```

#### Linux (Ubuntu/Debian)

```bash
# 添加 Grafana APT 仓库
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"

# 安装
sudo apt-get update
sudo apt-get install grafana

# 启动服务
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

### 2. 配置 Grafana

#### 访问 Grafana

打开浏览器访问: http://localhost:3000

默认登录信息:
- 用户名: `admin`
- 密码: `admin`

首次登录后会要求修改密码。

#### 添加 Prometheus 数据源

1. 点击左侧菜单的 **⚙️ Configuration** → **Data Sources**
2. 点击 **Add data source**
3. 选择 **Prometheus**
4. 配置数据源:
   - **Name**: `Prometheus`
   - **URL**: `http://localhost:9090`
   - **Access**: `Server (default)`
5. 点击 **Save & Test**

### 3. 导入仪表板

#### 方法 A: 通过 UI 导入 JSON

1. 点击左侧菜单的 **+** → **Import**
2. 点击 **Upload JSON file**
3. 选择仪表板文件:
   - `grafana/dashboards/system-overview.json`
   - `grafana/dashboards/agent-performance.json`
   - `grafana/dashboards/llm-cost-analysis.json`
4. 选择 Prometheus 数据源
5. 点击 **Import**

#### 方法 B: 通过配置文件自动加载

编辑 Grafana 配置文件 (`/etc/grafana/grafana.ini`):

```ini
[dashboards]
versions_to_keep = 20

[paths]
provisioning = /etc/grafana/provisioning
```

创建配置目录并复制文件:

```bash
sudo mkdir -p /etc/grafana/provisioning/dashboards
sudo mkdir -p /var/lib/grafana/dashboards

# 复制仪表板
sudo cp grafana/dashboards/*.json /var/lib/grafana/dashboards/

# 创建配置文件
sudo tee /etc/grafana/provisioning/dashboards/voice-agent.yml > /dev/null <<EOF
apiVersion: 1
providers:
  - name: 'Voice Agent'
    folder: 'Voice Agent'
    type: file
    options:
      path: /var/lib/grafana/dashboards
EOF

# 重启 Grafana
sudo systemctl restart grafana-server
```

---

## 📈 仪表板详细说明

### 1. 系统概览仪表板

**文件**: `system-overview.json`

**包含面板**:
- QPS (每秒请求数) - 实时请求流量
- 请求成功率 - 系统健康度指标
- 活跃会话数 - 当前并发用户
- 平均响应时间 - 按端点分组
- P95/P99 响应时间 - 延迟分布
- 请求量按端点分布 - 饼图
- 错误率趋势 - 4xx/5xx 错误监控
- 请求方法分布 - GET/POST/PUT 等

**适用场景**:
- 日常运维监控
- 快速定位问题
- 性能趋势分析

### 2. Agent 性能仪表板

**文件**: `agent-performance.json`

**包含面板**:
- 节点执行频率 - 各节点调用次数
- 总节点执行次数 - 累计指标
- 工具调用成功率 - 工具健康度
- 节点平均执行时间 - 性能瓶颈识别
- 最慢节点 Top 5 - 表格展示
- 工具调用频率 - 按工具分组
- 工具调用分布 - 饼图
- 工具执行时间对比 - 条形图
- Agent 工作流完整性 - 端到端监控
- 工具调用错误趋势 - 错误追踪
- 节点执行热力图 - 密度可视化

**适用场景**:
- Agent 优化
- 瓶颈分析
- 工具性能评估

### 3. LLM 成本分析仪表板

**文件**: `llm-cost-analysis.json`

**包含面板**:
- LLM 调用频率 - 按模型和提供商分组
- 总 LLM 调用次数 - 累计统计
- LLM 成功率 - 可靠性指标
- LLM 平均响应时间 - 延迟监控
- P95/P99 响应时间 - 尾部延迟
- Token 消耗趋势 - Prompt/Completion 分离
- Token 消耗量 (24小时) - 日使用量
- 各模型 Token 消耗分布 - 饼图
- 模型调用分布 - 使用占比
- 估算成本 - 基于 GPT 定价
- LLM 提供商分布 - 条形图
- Token 使用效率 - Token/请求比率
- LLM 错误率 - 错误监控
- 累计成本趋势 - 成本预测

**适用场景**:
- 成本优化
- 模型选择
- 预算规划

---

## 🎨 仪表板自定义

### 修改刷新间隔

点击右上角的刷新按钮，选择合适的间隔:
- 实时监控: 5s - 10s
- 日常监控: 30s - 1m
- 历史分析: 5m - 1h

### 修改时间范围

点击右上角的时间选择器:
- 实时监控: Last 15 minutes
- 性能分析: Last 1 hour
- 趋势分析: Last 24 hours
- 历史回顾: Last 7 days

### 添加自定义面板

1. 点击右上角的 **Add panel**
2. 选择可视化类型 (Graph, Stat, Table 等)
3. 编写 PromQL 查询
4. 配置面板选项
5. 点击 **Apply**

**示例查询**:

```promql
# 按小时统计请求量
sum(increase(voice_agent_http_server_request_count_total[1h]))

# 平均响应时间趋势
avg(voice_agent_http_server_duration_ms) by (path)

# Token 使用率
rate(voice_agent_llm_token_count_total[5m])
```

---

## 🔔 配置告警

### 在 Grafana 中设置告警

#### 1. 配置通知渠道

**设置 Slack 通知**:

1. 进入 **Alerting** → **Notification channels**
2. 点击 **New channel**
3. 配置:
   - **Name**: `Slack Alerts`
   - **Type**: `Slack`
   - **Webhook URL**: `your_slack_webhook_url`
   - **Channel**: `#alerts`
4. 点击 **Test** 验证
5. 点击 **Save**

**设置邮件通知**:

编辑 `/etc/grafana/grafana.ini`:

```ini
[smtp]
enabled = true
host = smtp.gmail.com:587
user = your_email@gmail.com
password = your_app_password
from_address = your_email@gmail.com
from_name = Voice Agent Alerts

[emails]
welcome_email_on_sign_up = false
templates_pattern = emails/*.html
```

#### 2. 创建告警规则

在仪表板面板中:

1. 点击面板标题 → **Edit**
2. 切换到 **Alert** 标签
3. 点击 **Create Alert**
4. 配置告警条件:

**高错误率告警示例**:

```
WHEN avg() OF query(A, 5m, now) IS ABOVE 0.05
```

**高延迟告警示例**:

```
WHEN avg() OF query(A, 5m, now) IS ABOVE 1000
```

5. 配置通知:
   - **Send to**: 选择通知渠道
   - **Message**: 自定义告警消息

6. 点击 **Save**

---

## 🧪 测试验证

### 1. 生成测试流量

```bash
# 发送测试请求
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/v1/chat \
    -H "Content-Type: application/json" \
    -H "X-API-Key: test_key" \
    -d '{"message": "Hello", "session_id": "test"}' &
done
```

### 2. 验证指标采集

访问 Prometheus:
- URL: http://localhost:9090
- 搜索: `voice_agent_http_server_request_count_total`
- 点击 **Execute**
- 切换到 **Graph** 标签查看趋势

### 3. 验证 Grafana 显示

访问 Grafana:
- URL: http://localhost:3000
- 进入 **Voice Agent** 文件夹
- 打开 **系统概览** 仪表板
- 查看 QPS 面板，应该看到流量峰值

---

## 🛠 故障排查

### 问题 1: Grafana 无法连接 Prometheus

**症状**: 数据源测试失败

**解决方案**:

```bash
# 1. 检查 Prometheus 是否运行
curl http://localhost:9090/-/healthy

# 2. 检查防火墙
sudo ufw allow 9090

# 3. 检查 Docker 网络 (如果使用 Docker)
docker network inspect monitoring
```

### 问题 2: 仪表板显示 "No Data"

**症状**: 面板显示 "No Data"

**解决方案**:

```bash
# 1. 确认 Voice Agent 正在运行
curl http://localhost:8000/api/v1/metrics

# 2. 确认 Prometheus 正在抓取
# 访问 http://localhost:9090/targets
# 检查 voice-agent 目标状态

# 3. 检查指标名称
# 在 Prometheus 中搜索: voice_agent_*
```

### 问题 3: 仪表板显示不正确

**症状**: 数据显示异常或不完整

**解决方案**:

1. 检查 PromQL 查询是否正确
2. 调整时间范围
3. 确认数据源选择正确
4. 检查 Prometheus 数据保留期

---

## 📚 最佳实践

### 1. 性能优化

- **合理设置刷新间隔**: 避免过于频繁的查询
- **限制时间范围**: 大范围查询会影响性能
- **使用变量**: 减少重复的面板配置
- **聚合数据**: 使用 `rate()`、`avg()` 等函数

### 2. 告警策略

- **分级告警**: Critical、Warning、Info
- **避免告警疲劳**: 设置合理的阈值和频率
- **测试告警**: 定期测试告警规则是否生效
- **文档化**: 为每个告警编写处理文档

### 3. 仪表板管理

- **版本控制**: 将仪表板 JSON 纳入 Git
- **命名规范**: 使用清晰的命名
- **文件夹组织**: 按功能模块分类
- **权限管理**: 设置合适的访问权限

### 4. 数据保留

默认 Prometheus 保留 15 天数据。如需延长:

编辑 `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

  # 数据保留时间
storage:
  retention:
    time: 30d
    size: 50GB
```

---

## 📝 相关文档

- [Prometheus 监控指南](./MONITORING_GUIDE.md)
- [PROJECT.md](../../PROJECT.md)
- [CHANGELOG.md](../../CHANGELOG.md)

---

## 🔗 外部资源

- [Grafana 官方文档](https://grafana.com/docs/)
- [PromQL 查询语言](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana 仪表板最佳实践](https://grafana.com/docs/grafana/latest/best-practices/)

---

**维护者**: Voice Agent Team  
**最后更新**: 2025-11-10  
**版本**: 1.0.0

