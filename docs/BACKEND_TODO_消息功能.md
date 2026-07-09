# 消息功能 — 后端待实现清单

> 本文档由前端开发生成，列出前端已完成的接口调用，以及后端需要实现的端点和修改。
> 生成日期：2026-07-07

---

## 一、前端已实现的内容

### 1.1 QML 组件（5个文件）

| 文件 | 状态 | 说明 |
|------|------|------|
| `MessagesPage.qml` | ✅ 完成 | 三栏布局主页面，含响应式（700px断点）、30s轮询、对话框 |
| `ConversationListPanel.qml` | ✅ 完成 | 会话列表 + 搜索框（500ms防抖）+ "+"菜单 |
| `ConversationItem.qml` | ✅ 完成 | 单会话项：头像/名称/预览/时间/红点 |
| `ChatPanel.qml` | ✅ 完成 | 聊天区：头部/消息列表/输入框/侧边信息面板(Drawer) |
| `MessageBubble.qml` | ✅ 完成 | 消息气泡：自己蓝色/对方白色 |

### 1.2 C++ 层更新

| 文件 | 状态 | 说明 |
|------|------|------|
| `api_types.h` | ✅ 完成 | 新增 `ConversationInfo`、`ContactSearchResult`；扩展 `MessageInfo`(id/sender_name/is_read)、`GroupInfo`(avatar) |
| `api_client.h` | ✅ 完成 | 新增 7 个方法声明 + 7 个信号声明 |
| `api_client.cpp` | ✅ 完成 | 新增 7 个桩实现（已连接真实端点，等待后端就绪） |
| `CMakeLists.txt` | ✅ 完成 | 注册 4 个新 QML 文件 |

---

## 二、后端需要实现的端点

### 2.1 全新端点（7个）⚠️ 高优先级

| 端点 | 用途 | 前端调用位置 |
|------|------|-------------|
| `POST /get-conversations` | 获取会话列表 | `MessagesPage.qml` 登录后、轮询时 |
| `POST /get-private-messages` | 获取私聊历史（游标分页） | `ChatPanel.qml` 点击会话时 |
| `POST /search-contacts` | 搜索用户/群组 | `ConversationListPanel.qml` 搜索框 |
| `POST /get-contacts` | 获取联系人列表（好友/仅关注） | （对话框内使用） |
| `POST /hide-conversation` | 隐藏/删除私聊会话 | `ChatPanel.qml` 侧边面板"删除会话"按钮 |
| `POST /get-user-detail` | 获取用户详情（侧边面板） | `ChatPanel.qml` 打开信息面板时 |
| `POST /get-group-detail` | 获取群组详情（侧边面板） | `ChatPanel.qml` 打开信息面板时 |

### 2.2 现有端点修改（5个）⚠️ 高优先级

| 端点 | 修改内容 | 影响 |
|------|---------|------|
| `POST /send-msg` | 增加 conversations 表同步（UPSERT 发送方+接收方） | 会话列表数据来源 |
| `POST /recv-msg` | 弃用阅后即焚，改为 `/get-private-messages` | 旧消息接收逻辑 |
| `POST /send-group-msg` | 增加 conversations 表同步（群内所有成员） | 群聊会话更新 |
| `POST /create-group` | 创建群时初始化 conversations 记录 | 新建群聊 |
| `POST /leave-group` | 退出时隐藏 conversations 记录 | 退出群聊 |

### 2.3 现有端点小修改（1个）⚠️ 中优先级

| 端点 | 修改内容 |
|------|---------|
| `POST /get-follow-list` | 返回数据增加 `avatar` 字段 |

---

## 三、数据库迁移（第1步）

```sql
-- 1. 私聊消息增加 is_read
ALTER TABLE offline_messages ADD COLUMN is_read INTEGER NOT NULL DEFAULT 0;

-- 2. 群组增加头像
ALTER TABLE groups ADD COLUMN avatar TEXT NOT NULL DEFAULT '';

-- 3. 创建会话表
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL DEFAULT 'private',
    target_id INTEGER NOT NULL,
    last_message TEXT DEFAULT '',
    last_message_time TEXT DEFAULT '',
    unread_count INTEGER DEFAULT 0,
    is_hidden INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, type, target_id)
);
```

---

## 四、数据格式约定

### /get-conversations 返回格式

```json
{
  "conversations": [
    {
      "id": 1,
      "type": "private",
      "target_id": 2,
      "target_name": "张三",
      "target_avatar": "",
      "last_message": "好的，明天见",
      "last_message_time": "2026-07-07 14:30:00",
      "unread_count": 3
    }
  ]
}
```

### /get-private-messages 返回格式

```json
{
  "messages": [
    {
      "id": 42,
      "sender_id": 1,
      "sender_name": "我",
      "content": "你好",
      "sent_at": "2026-07-07 10:00:00",
      "is_read": 1
    }
  ],
  "has_more": false
}
```

> **重要**：`messages` 数组按 `id DESC` 倒序返回（最新在前），前端直接渲染。

---

## 五、已知限制（前端改进建议）

1. **群聊历史翻页**：当前 `recv-group-msg` 不支持 `before_id` 游标分页，`ChatPanel.qml` 中群聊"加载更早消息"会提示暂不支持。
2. **搜索结果弹窗**：`ConversationListPanel.qml` 中搜索结果的 UI 展示尚未实现（`searchResultsReceived` 信号已连接但无弹出层）。
3. **图片消息**：当前仅支持纯文本消息，媒体消息需要后续扩展。
4. **实时推送**：当前使用 30s 轮询，WebSocket 推送可后续优化。

---

## 六、实现顺序建议

```
第1步: 数据库迁移（ALTER TABLE + CREATE TABLE conversations）
第2步: 新增 7 个 API 端点
第3步: 修改现有 5+1 个端点
完成以上后 → 前端即可正常工作
```
