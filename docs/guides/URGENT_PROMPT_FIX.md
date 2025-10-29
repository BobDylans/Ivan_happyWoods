# 🚨 紧急修复：系统提示词格式问题

**问题**: 当前 `src/agent/nodes.py` 中的搜索结果示例使用了 `####` 标题，这会导致前端列表渲染失败。

---

## 🔧 需要修改的位置

**文件**: `src/agent/nodes.py`  
**行号**: ~730-745  
**方法**: `_build_optimized_system_prompt()`

---

## ❌ 当前错误的示例 (约第730行)

```markdown
### 📰 Detailed Findings

#### 1. **Trump Confirms 2025 Japan Visit**
- 📅 **Published**: 2025-01-15
- 📝 **Key Points**: Trump announced via social media...
- 🔗 **Source**: [The Japan Times](https://example.com/article1)

#### 2. **US-Japan Trade Talks Accelerate**
- 📅 **Published**: 2025-01-10
- 📝 **Key Points**: Japanese officials preparing...
- 🔗 **Source**: [Reuters](https://example.com/article2)
```

**问题**: 使用了 `#### 1.` 和 `#### 2.`，前端 react-markdown 会将其渲染为标题，导致下面的列表失效。

---

## ✅ 正确的格式

```markdown
### 📰 Detailed Findings

**1. Trump Confirms 2025 Japan Visit**

- 📅 Published: 2025-01-15;
- 📝 Key Points: Trump announced via social media his visit to Japan in April 2025 for bilateral discussions;
- 🔗 Source: [The Japan Times](https://example.com/article1).

**2. US-Japan Trade Talks Accelerate**

- 📅 Published: 2025-01-10;
- 📝 Key Points: Japanese officials preparing for high-level negotiations during the visit;
- 🔗 Source: [Reuters](https://example.com/article2).

---

💡 **Key Insight**: First post-presidency visit signaling continued alliance priorities.
```

---

## 🔑 关键变更点

### 变更 1: 标题格式
```markdown
❌ #### 1. **Title**
✅ **1. Title**
```

### 变更 2: 添加空行
```markdown
**1. Title**
              ← 必须有这个空行
- List item;
```

### 变更 3: 列表项格式
```markdown
❌ - 📅 **Published**: 2025-01-15
✅ - 📅 Published: 2025-01-15;  (无需加粗label，加分号)
```

### 变更 4: 结果之间空行
```markdown
- Last item.
              ← 必须有这个空行
**2. Next Result**
```

---

## 📋 完整的替换模板

在 `src/agent/nodes.py` 中找到这段代码（约第722-748行），替换为：

````python
**✅ GOOD (Frontend-compatible format):**
```markdown
## 🔍 Search Results: Trump's Japan Visit 2025

### 📊 Executive Summary

Former President Trump confirmed plans to visit Japan in spring 2025, focusing on trade and security cooperation discussions.

### 📰 Detailed Findings

**1. Trump Confirms 2025 Japan Visit**

- 📅 Published: 2025-01-15;
- 📝 Key Points: Trump announced via social media his visit to Japan in April 2025 for bilateral trade and security talks;
- 🔗 Source: [The Japan Times](https://example.com/article1).

**2. US-Japan Trade Talks Accelerate**

- 📅 Published: 2025-01-10;
- 📝 Key Points: Japanese officials preparing for high-level negotiations during Trump's visit, focusing on trade sectors;
- 🔗 Source: [Reuters Asia](https://example.com/article2).

**3. Regional Security on Agenda**

- 📅 Published: 2025-01-08;
- 📝 Key Points: Meeting expected to address North Korea concerns and strengthen defense cooperation;
- 🔗 Source: [Nikkei Asian Review](https://example.com/article3).

---

💡 **Key Insight**: This marks Trump's first post-presidency visit to Japan, signaling renewed focus on the US-Japan alliance.
```
````

---

## 🎯 为什么这样修改？

### 根据 `MARKDOWN-RENDERING-GUIDE.md` 规则：

1. **列表渲染**: react-markdown 需要列表项前有空行才能正确渲染
2. **标题冲突**: `####` 会被识别为标题，阻止下方列表正常渲染
3. **格式统一**: 使用 `**粗体**` + 空行 + 列表 的组合是最可靠的格式

### Frontend 渲染规则摘要：

```markdown
# ✅ 正确 - 会渲染为列表
**Item Title**

- List item 1;
- List item 2.

# ❌ 错误 - 列表渲染失败
#### Item Title
- List item 1
- List item 2
```

---

## 🧪 验证步骤

修改后，测试：

```bash
# 1. 重启服务
python start_server.py

# 2. 打开浏览器测试
# 输入: "搜索特朗普访问日本2025的新闻"

# 3. 检查前端显示
✅ 应该看到正确的列表项目符号 (•)
✅ 每个结果有清晰的视觉分隔
✅ 链接可以点击
✅ 没有渲染异常
```

---

## 📝 额外优化建议

### 1. 在 Step 3 中添加前端渲染要求

找到 "### Step 3: What You MUST DO ✅" 部分，添加：

```python
### Step 3: What You MUST DO ✅
- ✅ Extract ai_answer if present
- ✅ Parse ALL results - show actual content
- ✅ **Use `**Number. Title**` format** (NOT `#### Number. Title`)
- ✅ **Add blank line after each result title**
- ✅ **Use `-` with space**: `- Item;` (NOT `-Item`)
- ✅ **End list items with `;`** (except last with `.`)
- ✅ **Blank line between results**
- ✅ Make links clickable: `[Text](URL)`
```

### 2. 在 Step 2 模板中明确标注

在模板示例开头添加注释：

```markdown
### Step 2: Structure Your Response (REQUIRED FORMAT)
**CRITICAL: Follow these rules for frontend rendering:**
1. Use `**Number. Title**` NOT `#### Number. Title`
2. Blank line after title before list
3. Space after `-` in lists
4. Semicolons for list items

Template:
```

---

## ⚠️ 如果手动修改困难

由于文件编码或格式问题，如果直接替换困难，可以：

1. **方案 A**: 创建新文件 `src/agent/prompts.py`，单独管理所有提示词
2. **方案 B**: 使用 VS Code 的"查找并替换"功能（Ctrl+H），确保勾选"正则表达式"选项
3. **方案 C**: 临时将该部分注释掉，测试简化版提示词

---

## 📞 需要帮助？

如果修改后仍有问题，检查：
1. 前端控制台是否有 React 错误
2. 后端日志中 LLM 返回的原始 Markdown
3. 使用在线 Markdown 预览工具验证格式

---

**优先级**: 🔴 HIGH - 直接影响用户体验  
**预估时间**: 5分钟  
**影响范围**: 所有搜索功能的结果展示
