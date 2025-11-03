# 会话管理功能测试指南

## 🎯 概述

会话管理功能已集成到 `auth_demo.html` 中，可以通过浏览器进行完整的端到端测试。

## 📋 测试前准备

### 1. 启动服务器
```bash
python start_server.py
```

### 2. 打开测试页面
在浏览器中打开: `file:///d:/Projects/ivanHappyWoods/backEnd/auth_demo.html`

或直接双击 `auth_demo.html` 文件。

## 🧪 测试流程

### 步骤 1: 注册用户
1. 在左侧"📝 用户注册"部分填写信息:
   - 用户名: `session_test_user`
   - 邮箱: `session_test@example.com`
   - 密码: `Test1234!Strong`
   - 全名: `Session Test User` (可选)

2. 点击"注册"按钮

3. **预期结果**: 
   - 显示注册成功消息
   - 或显示"用户已存在"（如果之前注册过）

### 步骤 2: 用户登录
1. 在左侧"🔑 用户登录"部分:
   - 用户名: `session_test_user`
   - 密码: `Test1234!Strong`

2. 点击"登录"按钮

3. **预期结果**:
   - 顶部状态变为 "✓ 已登录"
   - 显示 Access Token 和 Refresh Token
   - 自动获取用户信息

### 步骤 3: 发送对话消息
1. 在右侧"💬 测试对话接口（JWT 认证）"部分

2. 保持默认消息或输入自定义消息

3. 点击"发送对话（使用 JWT）"按钮

4. **预期结果**:
   - 显示对话成功
   - 返回 session_id
   - 返回 AI 回复内容

### 步骤 4: 获取会话列表
1. 在右侧"📋 会话管理（Session Management）"部分

2. 点击"获取会话列表"按钮

3. **预期结果**:
   ```json
   {
     "message": "✅ 获取会话列表成功",
     "total": 1,
     "page": 1,
     "page_size": 10,
     "has_more": false,
     "sessions": [
       {
         "session_id": "xxx-xxx-xxx",
         "status": "ACTIVE",
         "message_count": 2,
         "created_at": "2025-11-03T...",
         "last_activity": "2025-11-03T..."
       }
     ]
   }
   ```

4. **自动保存**: 第一个 session_id 会自动保存用于下一步测试

### 步骤 5: 获取会话详情
1. 继续在"📋 会话管理"部分

2. 点击"获取会话详情"按钮

3. **预期结果**:
   ```json
   {
     "message": "✅ 获取会话详情成功",
     "session_id": "xxx-xxx-xxx",
     "status": "ACTIVE",
     "total_messages": 2,
     "created_at": "2025-11-03T...",
     "last_activity": "2025-11-03T...",
     "messages": [
       {
         "role": "user",
         "content": "你好，请介绍一下自己",
         "created_at": "2025-11-03T..."
       },
       {
         "role": "assistant",
         "content": "你好！我是一个AI助手...",
         "created_at": "2025-11-03T..."
       }
     ]
   }
   ```

## ✅ 测试验证清单

### 基础功能
- [ ] 用户注册成功
- [ ] 用户登录获取 JWT Token
- [ ] JWT Token 正确显示

### 对话功能
- [ ] 发送对话消息成功
- [ ] 自动创建会话
- [ ] 返回 AI 回复

### 会话列表
- [ ] 获取会话列表成功
- [ ] 显示正确的会话数量
- [ ] 显示正确的消息数量
- [ ] 分页信息正确

### 会话详情
- [ ] 获取会话详情成功
- [ ] 显示所有消息
- [ ] 消息顺序正确（时间升序）
- [ ] 消息内容完整

### 权限控制
- [ ] 只能看到自己的会话
- [ ] 访问他人会话返回 403/404

## 🔧 API 端点说明

### 1. 获取会话列表
```
GET /api/v1/conversation/sessions/
```

**请求头**:
```
Authorization: Bearer <access_token>
```

**查询参数**:
- `page`: 页码（默认 1）
- `page_size`: 每页数量（默认 20，最大 100）
- `status`: 会话状态过滤（可选: ACTIVE, PAUSED, TERMINATED）

### 2. 获取会话详情
```
GET /api/v1/conversation/sessions/{session_id}
```

**请求头**:
```
Authorization: Bearer <access_token>
```

### 3. 认证对话
```
POST /api/v1/conversation/send
```

**请求头**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体**:
```json
{
  "text": "你好",
  "output_mode": "text"
}
```

## 🐛 常见问题

### Q1: 点击按钮无响应
**原因**: 未登录或 Token 过期

**解决**: 
1. 检查顶部状态是否为"✓ 已登录"
2. 如果未登录，先完成登录
3. 如果 Token 过期，点击"刷新 Token"或重新登录

### Q2: 获取会话列表返回空
**原因**: 没有创建任何会话

**解决**: 先发送一条对话消息，系统会自动创建会话

### Q3: 获取会话详情失败
**原因**: Session ID 不存在或不属于当前用户

**解决**:
1. 先点击"获取会话列表"
2. 系统会自动保存第一个 session_id
3. 然后点击"获取会话详情"

### Q4: 权限错误 (403)
**原因**: 尝试访问其他用户的会话

**解决**: 这是正常的权限控制，只能访问自己的会话

## 📊 性能基准

- **会话列表查询**: < 200ms
- **会话详情查询**: < 300ms (含消息)
- **对话接口**: < 2s (含 LLM 调用)

## 🔒 安全说明

1. **JWT 认证**: 所有会话管理接口都需要有效的 JWT Token
2. **用户隔离**: 只能访问自己创建的会话
3. **自动绑定**: 会话自动绑定到当前登录用户
4. **无 API Key**: 这些接口使用 JWT 认证，不需要 X-API-Key 头

## 📝 数据说明

### 会话状态
- `ACTIVE`: 活跃会话
- `PAUSED`: 暂停会话
- `TERMINATED`: 终止会话

### 消息角色
- `user`: 用户消息
- `assistant`: AI 回复消息
- `system`: 系统消息（如提示词）

## 🎉 测试成功标准

完成以上所有步骤后，如果:
1. ✅ 所有功能按钮都能正常响应
2. ✅ 返回的数据格式正确
3. ✅ 消息内容完整准确
4. ✅ 权限控制正常工作

**恭喜！会话管理功能测试通过！** 🎊

---

**创建时间**: 2025-11-03  
**最后更新**: 2025-11-03  
**维护者**: Ivan_HappyWoods Team
