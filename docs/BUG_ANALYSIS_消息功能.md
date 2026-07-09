# 消息功能 BUG 分析报告

> 基于 2026-07-07 测试反馈和完整代码审查。
> 每个 BUG 标注根因归属：🎨 前端 / ⚙️ 后端 / 🔗 双端。
> **最后更新：2026-07-07 20:45（前端修复完成）**

---

## BUG 1: 好友添加没有好友申请

**现象**: 点击"+"按钮 → "添加好友" → 搜索用户 → 没有任何好友申请流程，直接关注了对方，对方不知情。

### 🔗 根因分析（双端问题）

| 层面 | 问题 |
|------|------|
| ⚙️ 后端 | 系统只有单向 `follow/unfollow` 模型，**不存在好友申请（friend request）机制**。没有 `friend_requests` 表、没有通知机制。"好友"概念仅靠双向关注判定（`INTERSECT` 查询），但被关注方完全不知情。 |
| 🎨 前端 | `ChatPanel.qml` 私聊信息面板中"关注按钮"只是 `// TODO: follow/unfollow` 注释，未实现。`ConversationListPanel.qml` 菜单项 `menuAction` 是 signal 但被当作函数调用（语法错误），导致"添加好友"菜单项点击无效。 |

### ⚙️ 后端需要做什么
1. **新增 `friend_requests` 表**（或复用 `offline_messages` 发系统消息）:
```sql
CREATE TABLE IF NOT EXISTS friend_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user_id INTEGER NOT NULL,
    to_user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | accepted | rejected
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (from_user_id) REFERENCES users(id),
    FOREIGN KEY (to_user_id) REFERENCES users(id),
    UNIQUE(from_user_id, to_user_id)
);
```
2. **新增 3 个端点**:
   - `POST /send-friend-request` — 发送申请（检查是否已是好友、是否已有待处理申请）
   - `POST /get-friend-requests` — 获取待处理申请列表
   - `POST /handle-friend-request` — 接受/拒绝申请（accepted 时自动双向 follow）

### 🎨 前端需要做什么
1. 修复 `ConversationListPanel.qml` 第 169 行：`root.menuAction(index)` → `root.menuAction(index)` 改为 emit 方式，或者改为普通函数调用
2. 在搜索用户结果中加"添加好友"按钮，点击后调用新 API
3. 新增好友申请通知入口（可在会话列表中显示系统消息类型的会话）

---

## BUG 2: 切换账号后聊天窗口没有默认空白

**现象**: 登出再登入另一个账号，聊天窗口仍然显示上一个账号的聊天记录和会话。

### 🎨 根因分析（纯前端）

`MessagesPage.qml` 第 54-61 行：
```javascript
function onLoggedInChanged() {
    if (api.isLoggedIn) {
        api.fetchConversations()
        api.checkCookie()
    }
    // ❌ 没有 else 分支！登出时不清空状态
}
```

**缺少登出时的状态重置**。`currentConversation`、`currentMessages`、`conversations`、`narrowViewIndex` 全部保留旧值。

### 🎨 前端需要做什么
在 `MessagesPage.qml` 的 `onLoggedInChanged` 中增加 else 分支：
```javascript
function onLoggedInChanged() {
    if (api.isLoggedIn) {
        // 先清空再加载
        root.currentConversation = null
        root.currentMessages = []
        root.conversations = []
        root.narrowViewIndex = 0
        api.fetchConversations()
        api.checkCookie()
    } else {
        // 登出：重置所有状态
        root.currentConversation = null
        root.currentMessages = []
        root.conversations = []
        root.narrowViewIndex = 0
    }
}
```

**注意**：`ChatPanel.qml` 也需要重置。建议给 `ChatPanel` 暴露一个 `reset()` 函数，在 MessagesPage 状态清空时同步调用。

---

## BUG 3: 无法搜索到好友

**现象**: 在搜索框输入关键词，没有结果显示。

### 🎨 根因分析（纯前端）

1. `ConversationListPanel.qml` 搜索框防抖 500ms 后调用 `api.searchContacts(keyword, "all")`
2. 后端 `/search-contacts` 端点正常工作（已验证 SQL 逻辑正确）
3. `ApiClient::searchContacts()` 发出 `contactsSearched(users, groups)` 信号
4. **但是！** `MessagesPage.qml` 第 130-133 行只是 `console.log` 搜索结果，**没有任何 UI 弹窗展示**

### 🎨 前端需要做什么
在 `ConversationListPanel.qml` 或 `MessagesPage.qml` 中实现搜索结果下拉弹窗：
- 搜索框下方出现 `Popup` / 浮动列表
- 显示匹配的用户（头像+昵称+关注状态）和群组（头像+群名+成员数）
- 点击用户 → 开始私聊；点击群组 → 加入群聊
- 无结果时显示"未找到"

---

## BUG 4: 上次添加的群聊再次进入时看不见

**现象**: 加入群聊后正常显示。退出消息页再进入，群聊从会话列表中消失了。

### ⚙️ 根因分析（纯后端）

`POST /join-group`（`main.py` 第 779-798 行）**没有创建 conversations 记录**！

```python
def join_group(body: Join_Group_Req):
    # ...验证 cookie、验证 group 存在...
    db_execute("INSERT OR IGNORE INTO user_in_group (group_id, user_id) VALUES (?, ?)",
            (body.group_id, user_id))
    db_commit()
    return {"status": "success"}
    # ❌ 缺少：INSERT INTO conversations ...
```

对比 `create-group` 端点（第 767-776 行）正确地在创建群后插入了 `conversations` 记录。但 `join-group` 没有。
下次打开消息页时，`/get-conversations` 查询不到该群的会话记录，所以不显示。

### ⚙️ 后端需要做什么
在 `join_group()` 函数末尾（`db_commit()` 之前）增加：
```python
db_execute("""
    INSERT OR IGNORE INTO conversations (user_id, type, target_id, last_message, last_message_time, unread_count)
    VALUES (?, 'group', ?, '', datetime('now'), 0)
""", (user_id, body.group_id))
```

---

## BUG 5: 群成员名称无法显示 + 控制台 TypeError

**错误日志**:
```
qrc:/qt/qml/frontend/ChatPanel.qml:640: TypeError: Cannot read property 'nickname' of undefined
qrc:/qt/qml/frontend/ChatPanel.qml:651: TypeError: Cannot read property 'nickname' of undefined
qrc:/qt/qml/frontend/ChatPanel.qml:657: TypeError: Cannot read property 'role' of undefined
```
（每个成员触发 3 个错误，2 个成员 = 6 个错误）

**现象**: 点击"⋯"打开群聊信息面板，群成员列表每个成员只显示"?"，控制台报上述错误。

### 🔗 根因分析（双端问题）

**直接原因**: ListView delegate 中 `modelData` 是 `undefined`。

**可能成因**:

| 层面 | 可能问题 |
|------|---------|
| ⚙️ 后端 | `/get-group-detail` 返回的 `members` 数组中每个元素的字段名可能与 QML 期望不一致。例如后端用 `nickname` 但实际返回的 key 变成了别的东西（大小写、dict 转换问题等）。需要验证实际 HTTP 响应。 |
| 🎨 前端 | `ChatPanel.qml` 第 778-786 行 `onGroupDetailFetched` 将 `detail.members[i]` 追加到 `ListModel`。但在 Qt 6 QML 中，从 C++ QVariantMap 传递的 JS 对象追加到 `ListModel` 时，属性可能不会自动展开为 role。需要改用显式方式: `groupMembersModel.append({nickname: member.nickname, username: member.username, role: member.role})` |
| 🎨 前端 | MessagesPage 中有 **两个** ChatPanel 实例（wide + narrow），都连接了 `api` 的 `onGroupDetailFetched` 信号。窄屏的 ChatPanel 在 StackLayout 中处于隐藏状态时，其 `groupMembersModel` 可能未正确初始化。 |

### ⚙️ 后端验证
检查 `/get-group-detail` 的实际响应，确认 members 数组元素包含 `nickname`、`username`、`role` 字段：
```bash
curl -X POST http://127.0.0.1:18999/get-group-detail \
  -H "Content-Type: application/json" \
  -d '{"cookie":"<valid_cookie>","group_id":1}'
```

### 🎨 前端修复建议
修改 `ChatPanel.qml` 的 `onGroupDetailFetched` 中追加方式：
```javascript
function onGroupDetailFetched(detail) {
    console.log("[ChatPanel] groupDetailFetched: " + JSON.stringify(detail))
    groupMembersModel.clear()
    if (detail.members && Array.isArray(detail.members)) {
        for (var i = 0; i < detail.members.length; i++) {
            var m = detail.members[i]
            groupMembersModel.append({
                id: m.id || 0,
                username: m.username || "",
                nickname: m.nickname || "",
                avatar: m.avatar || "",
                role: m.role || "member",
                joined_at: m.joined_at || ""
            })
        }
    }
}
```

---

## BUG 6: 发送的消息无法渲染 + 期望气泡布局改造

**现象**: 发送消息后，消息列表中不显示刚发的消息。只有刷新会话列表后再点进去才能看到。

**期望**: 头像在最左/右端 → 侧下方消息气泡 → 气泡上方是名称+时间。

### 🎨 根因分析（纯前端）

**问题 A — 消息不渲染**:
`ChatPanel.qml` 的 `sendMessage()` 函数（第 708-732 行）调用 `api.sendMessage()` 后只清空输入框，**没有乐观更新消息列表**。`onMessageSent` 信号只调 `api.fetchConversations()`（刷新会话列表），不刷新消息列表。要看到新消息，必须关闭当前会话再重新打开。

**问题 B — 气泡布局不符合预期**:
当前 `MessageBubble.qml` 的布局:
```
[头像] [发送者名]           (对方消息)
[头像] [气泡(内容)]
       [时间 ✓✓]
```
期望布局:
```
[头像]  [发送者名]  [时间]   (名称+时间在气泡上方)
        [气泡(内容)]
```

### 🎨 前端需要做什么

**A. 乐观更新消息列表**（`ChatPanel.qml`）:
```javascript
function sendMessage() {
    var text = sendTextArea.text.trim()
    if (text.length === 0 || !root.currentConversation) return

    // 乐观追加到消息列表
    var optimisticMsg = {
        id: Date.now(),                    // 临时ID
        sender_id: root.currentUserId,
        sender_name: "我",
        content: text,
        sent_at: new Date().toISOString(), // 临时时间
        is_read: false,
        isMine: true
    }
    var newMsgs = root.messages.slice()
    newMsgs.push(optimisticMsg)
    root.messages = newMsgs
    sendTextArea.text = ""

    // 异步发送
    if (root.currentConversation.type === "private") {
        api.sendMessage(root.currentConversation.target_id, text)
    } else {
        api.sendGroupMessage(root.currentConversation.target_id, text)
    }
}
```
并在 `onMessageSent` / `onGroupMessageSent` 中刷新真实消息列表（用后端返回的真实ID和时间替换临时消息）。

**B. 重新设计 MessageBubble.qml 布局**:
```
┌────────────────────────────────────────────┐
│ 对方消息 (左对齐)                            │
│ ┌────┐                                    │
│ │头像│  张三          14:30                │
│ └────┘  ┌──────────────────────┐          │
│         │ 消息气泡（白色圆角）     │          │
│         └──────────────────────┘          │
│                                            │
│ 自己消息 (右对齐)                            │
│                    李四(我)  14:31  ┌────┐ │
│  ┌──────────────────────┐         │头像│ │
│  │ 消息气泡（蓝色圆角）     │         └────┘ │
│  └──────────────────────┘                  │
└────────────────────────────────────────────┘
```

关键改动:
1. **头像移到 Row 的最外端**（对方左，自己右），不放在气泡旁边
2. **名称+时间移到气泡上方**，作为一行显示
3. **自己消息也要显示名称**，格式如"李四(我)"
4. 气泡宽度自适应文字内容

---

## 附录 A: 汇总对照表

| # | BUG | 归属 | 严重度 | 修复状态 | 修改文件 |
|---|-----|------|--------|---------|---------|
| 1 | 好友添加没有好友申请 | 🔗 双端 | 🔴 高 | ⏳ 待后端 | `main.py`(新表+3端点), 前端: 搜索结果弹窗已支持 |
| 2 | 切换账号聊天不空白 | 🎨 前端 | 🟡 中 | ✅ 已修复 | `MessagesPage.qml` (resetAllState + else分支) |
| 3 | 无法搜索好友 | 🎨 前端 | 🟡 中 | ✅ 已修复 | `ConversationListPanel.qml` (搜索结果Popup) |
| 4 | 群聊再次进入消失 | ⚙️ 后端 | 🔴 高 | ✅ 已修复 | `main.py` (`join_group`增加conversations) |
| 5 | 群成员名称不显示 | 🔗 双端 | 🔴 高 | ✅ 已修复 | `ChatPanel.qml` (onGroupDetailDataChanged + 显式append) |
| 6 | 消息不渲染+气泡布局 | 🎨 前端 | 🔴 高 | ✅ 已修复 | `ChatPanel.qml` (乐观更新), `MessageBubble.qml` (布局重设计) |

## 附录 B: 额外发现的问题

| # | 问题 | 文件 | 行号 | 修复状态 |
|---|------|------|------|---------|
| E1 | `ChatPanel.qml` `userDetail` 属性不存在 | ChatPanel.qml | 773 | ✅ 已修复 (改为root级userDetailData) |
| E2 | `ConversationListPanel.qml` `menuAction(index)` — QML中signal可正常调用 | ConversationListPanel.qml | 169 | ✅ 非Bug |
| E3 | MessagesPage 两个ChatPanel都连`api`信号 | MessagesPage.qml + ChatPanel.qml | — | ✅ 已修复 (统一到MessagesPage) |
| E4 | 群聊翻页不支持 | ChatPanel.qml | 749 | ⏳ 待后端增强recv-group-msg |
| E5 | 搜索结果无UI弹窗 | MessagesPage.qml | 130-133 | ✅ 已修复 (同BUG3) |
