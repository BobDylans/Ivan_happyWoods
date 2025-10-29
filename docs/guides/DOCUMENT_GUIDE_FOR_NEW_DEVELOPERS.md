# 📖 新开发者文档使用指南

> **目标读者**: 刚加入项目的开发者  
> **阅读时间**: 3 分钟  
> **最后更新**: 2025-10-16

---

## 🎯 重点推荐

### ⭐ 第一优先级：必读文档

**只需 30 分钟，按这个顺序读完这 3 个文档：**

| 序号 | 文档 | 时间 | 目的 |
|------|------|------|------|
| 1 | [README.md](../README.md) | 5 min | 了解项目是什么 |
| 2 | **[QUICK_START.md](../QUICK_START.md)** ⭐ | 15 min | **快速上手（最重要！）** |
| 3 | [PROJECT.md](../PROJECT.md) §概述 §架构 | 10 min | 理解系统设计 |

**完成后你将**:
- ✅ 知道项目的核心价值
- ✅ 能够启动开发环境
- ✅ 理解代码组织结构
- ✅ 掌握基本开发流程

---

## 📚 按场景查找文档

### 场景 1: 我要配置开发环境

**查看**: [QUICK_START.md](../QUICK_START.md) § 5分钟快速开始

包含：
- 安装依赖
- 配置环境变量
- 启动服务
- 测试功能

### 场景 2: 我要开发新功能

**查看顺序**:
1. [QUICK_START.md](../QUICK_START.md) § 典型开发工作流
2. [PROJECT.md](../PROJECT.md) - 理解相关模块
3. [DEVELOPMENT.md](../DEVELOPMENT.md) - 详细开发指南
4. [GIT_GUIDE.md](../GIT_GUIDE.md) - 提交代码规范

### 场景 3: 我要配置数据库（Phase 3A）

**查看**: [docs/database-setup-guide.md](database-setup-guide.md)

包含：
- Docker Compose 配置
- 数据库初始化
- Alembic 迁移
- 故障排除

### 场景 4: 我要测试语音功能

**查看**: [docs/achievements/phase2/TTS_QUICKSTART.md](achievements/phase2/TTS_QUICKSTART.md)

包含：
- 语音合成测试
- 语音识别测试
- 常见问题

### 场景 5: 我要理解对话 API

**查看**: [docs/achievements/phase2/CONVERSATION_API_GUIDE.md](achievements/phase2/CONVERSATION_API_GUIDE.md)

包含：
- API 端点说明
- 请求/响应格式
- 使用示例

### 场景 6: 我遇到错误需要排查

**查看顺序**:
1. [QUICK_START.md](../QUICK_START.md) § 常见陷阱
2. [DEVELOPMENT.md](../DEVELOPMENT.md) § 故障排除
3. `logs/voice-agent-api.log` - 应用日志
4. [docs/achievements/reports/](achievements/reports/) - 错误修复报告

### 场景 7: 我找不到某个文档

**查看**: [DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md)

这是**完整的文档索引**，包含：
- 所有文档列表
- 按主题分类
- 按场景导航
- 文档状态

---

## 🚀 快速参考

### 最常用的 5 个文档

| 文档 | 用途 | 快捷方式 |
|------|------|---------|
| [QUICK_START.md](../QUICK_START.md) | 上手指南 | 🔥 最常用 |
| [PROJECT.md](../PROJECT.md) | 架构参考 | 📐 理解设计 |
| [DEVELOPMENT.md](../DEVELOPMENT.md) | 开发详解 | 🔧 实际开发 |
| [database-setup-guide.md](database-setup-guide.md) | 数据库配置 | 💾 Phase 3A |
| [GIT_GUIDE.md](../GIT_GUIDE.md) | Git 规范 | 📝 提交代码 |
| [optimizations/](achievements/optimizations/) | 性能优化 | ⚡ 优化参考 |

### 文档位置

```
Ivan_happyWoods/
├── 📄 根目录文档（核心）
│   ├── README.md ⭐
│   ├── QUICK_START.md ⭐⭐⭐ 最重要！
│   ├── PROJECT.md ⭐
│   ├── DEVELOPMENT.md ⭐
│   ├── GIT_GUIDE.md
│   ├── CHANGELOG.md
│   └── DOCUMENTATION_INDEX.md
│
└── 📚 docs/ 目录（专题）
    ├── database-setup-guide.md  # 数据库
    ├── AI_ONBOARDING_GUIDE.md   # AI 上下文
    │
    ├── achievements/            # 实施报告
    │   ├── phase2/              # Phase 2 指南
    │   │   ├── TTS_QUICKSTART.md
    │   │   ├── CONVERSATION_API_GUIDE.md
    │   │   └── ...
    │   ├── optimizations/       # 优化报告
    │   └── reports/             # 错误修复
    │
    └── archive/                 # 归档文档
```

---

## 💡 文档使用技巧

### 1. Cursor AI 使用

当使用 Cursor AI 时：

✅ **推荐说法**:
- "参考 QUICK_START.md，帮我配置环境"
- "根据 PROJECT.md 的架构，实现一个新工具"
- "查看 database-setup-guide.md，帮我配置数据库"

❌ **避免说法**:
- "帮我配置" （太模糊，AI 不知道参考哪里）

### 2. 快速搜索

- 使用 IDE 的全局搜索（Ctrl+Shift+F / Cmd+Shift+F）
- 搜索关键词：如 "TTS", "database", "MCP" 等
- 查看 [DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md) 的分类索引

### 3. 文档更新

如果发现文档：
- 过时或错误 → 修改并提交 PR
- 缺失 → 提交 Issue 或自行补充
- 不清楚 → 询问团队并更新文档

**记住**: 文档也是代码的一部分！

---

## ✅ 新手检查清单

完成这些任务，确保你已经掌握文档使用：

### 文档阅读
- [ ] 已阅读 README.md
- [ ] 已阅读 QUICK_START.md（完整）
- [ ] 已浏览 PROJECT.md 的架构部分
- [ ] 知道 DOCUMENTATION_INDEX.md 的作用

### 实践操作
- [ ] 成功启动开发环境（参考 QUICK_START.md）
- [ ] 访问 Swagger UI (`http://localhost:8000/docs`)
- [ ] 知道如何查看日志文件
- [ ] 能找到专题文档（如数据库、语音）

### 开发准备
- [ ] 了解 Git 工作流（GIT_GUIDE.md）
- [ ] 知道如何添加新工具（QUICK_START.md § 场景1）
- [ ] 理解项目目录结构
- [ ] 知道遇到问题如何排查

---

## 🎓 进阶学习

完成基础文档后，可以深入学习：

### Week 1
- 完整阅读 [PROJECT.md](../PROJECT.md)
- 运行所有测试
- 实现一个简单的自定义工具

### Week 2
- 研究 LangGraph 工作流设计
- 学习流式响应机制
- 探索性能优化技巧

### Week 3
- 参与 Phase 3 开发
- 学习数据库集成
- 了解 RAG 架构

**详细路径**: 参见 [QUICK_START.md](../QUICK_START.md) § 进阶学习路径

---

## 🆘 仍然有疑问？

1. **查看** [QUICK_START.md](../QUICK_START.md) § 遇到问题？
2. **搜索** [DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md)
3. **询问** 团队成员
4. **提交** Issue 或在团队频道提问

---

## 📊 文档价值

### 为什么要认真读文档？

| 读文档 ✅ | 不读文档 ❌ |
|----------|------------|
| 30分钟快速上手 | 花2-3天摸索 |
| 避免常见错误 | 重复踩坑 |
| 理解设计意图 | 不知道为什么这样设计 |
| 找到正确答案 | 到处问重复问题 |
| 提高开发效率 | 效率低下 |

**投资 30 分钟读文档 = 节省数天的时间！**

---

## 🎉 总结

记住这 3 个最重要的文档：

1. **README.md** - 项目是什么
2. **QUICK_START.md** ⭐⭐⭐ - 如何上手
3. **DOCUMENTATION_INDEX.md** - 找其他文档

**只要读了这 3 个，你就知道接下来该读什么！**

---

**Happy Coding! 🚀**

---

*本文档版本: v1.0 (2025-10-16)*  
*反馈和建议: 提交 PR 或 Issue*

