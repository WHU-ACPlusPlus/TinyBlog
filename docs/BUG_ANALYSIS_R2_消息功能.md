# 消息功能 BUG 分析报告 (Round 2)

> 日期: 2026-07-07 | 基于第二轮测试反馈

---

## BUG 1: "+" 搜索结果显示多个重复弹窗

**现象**: 搜索账号后，出现多个相同的搜索结果弹窗叠加显示。

### 🎨 根因分析（纯前端）

`MessagesPage.qml` 中有 **两个** `ConversationListPanel` 实例：

```qml
// 宽屏的
ConversationListPanel {
    id: convListPanelWide
    searchResults: root.searchResults   // ← 都绑定同一个数据源
    // ... 内部有 searchPopup (Popup)
}

// 窄屏的
ConversationListPanel {
    id: convListPanelNarrow
    searchResults: root.searchResults   // ← 都绑定同一个数据源
    // ... 内部也有 searchPopup (Popup)
}
```

每个 `ConversationListPanel` 内部都有一个 `searchPopup`（`Popup` 组件），其 `visible` 都绑定到 `root.searchResults`。当搜索返回结果时：

1. `MessagesPage.onContactsSearched()` → `root.searchResults = {users, groups}`
2. 属性绑定传播到 **两个** `ConversationListPanel` 的 `searchResults`
3. **两个** `searchPopup` 同时变为 `visible`
4. Popup 是顶层 overlay，不受父组件 `visible` 影响 → 两个弹窗叠加显示

### 🎨 修复方案

**方案 A（推荐）**: 将 `searchPopup` 提升到 `MessagesPage` 级别，只保留一个实例。

在 `MessagesPage.qml` 末尾添加一个 `searchPopup` Popup，删除 `ConversationListPanel.qml` 内部的 `searchPopup`。

**方案 B**: 在 `ConversationListPanel` 中添加 `visible` 属性，只在当前模式可见时才显示 popup。

---

## BUG 2: 退出重进后历史消息无法渲染

**现象**: 退出消息页再进入，点击会话后消息区域为空，不显示历史消息。

### 🎨 根因分析（纯前端，双因）

#### 根因 A（主因）: 属性绑定被 `sendMessage()` 永久破坏

`ChatPanel.qml` 第 767 行：
```javascript
var newMsgs = root.messages.slice()
newMsgs.push(optimisticMsg)
root.messages = newMsgs   // ← 💣 破坏绑定！
```

**问题链路**:
```
1. ChatPanel 声明: messages: root.currentMessages  (绑定到 MessagesPage)
2. 用户发送第一条消息 → sendMessage() → root.messages = newMsgs
3. 此时 root.messages 不再是绑定，而是静态 JS 数组
4. MessagesPage.currentMessages 后续任何变化都不会再传递到 ChatPanel
5. 退出重进 → resetAllState() → MessagesPage.currentMessages = []
   但 ChatPanel.messages 的绑定早已断裂，保持不变！
6. 再次获取历史消息 → onPrivateMessagesFetched → currentMessages = messages
   但 ChatPanel.messages 仍然断裂，不会更新！
```

**关键**: `resetAllState()` 只重置 MessagesPage 的属性，但 **ChatPanel 实例不会重建**（在 StackLayout 中持久存在），其内部断裂的绑定无法自动恢复。

#### 根因 B（次因）: `_fetchingConversations` 死锁

`MessagesPage.qml` 第 59-74 行：
```javascript
function safeFetchConversations(source) {
    if (root._fetchingConversations) return  // ← 如果卡住，永久阻塞
    root._fetchingConversations = true
    api.fetchConversations()
}
```

`_fetchingConversations` 只在 `onConversationsFetched()` 中重置为 `false`。如果任何一次 API 调用失败（网络波动、服务端错误），`onConversationsFetched` 永远不会触发，`_fetchingConversations` 永远为 `true`，所有后续请求全部被阻挡。

### 🎨 修复方案

**修复根因 A** — 不破坏绑定：

在 `ChatPanel.qml` 中，增加一个独立的内部数组用于乐观更新，不覆盖 `messages` 属性：

```qml
// ChatPanel.qml
property var messages: []           // 保持绑定，只从外部设置
property var _displayMessages: []   // 内部显示用（合并真实消息+乐观消息）

// sendMessage() 改为操作 _displayMessages
function sendMessage() {
    var optimisticMsg = { ... }
    var newMsgs = root._displayMessages.slice()
    newMsgs.push(optimisticMsg)
    root._displayMessages = newMsgs
    // ... 发送API ...
}

// Repeater 改用 _displayMessages
Repeater {
    model: root._displayMessages
}

// 同时监听 messages 变化，同步到 _displayMessages
onMessagesChanged: {
    root._displayMessages = root.messages  // 从外部绑定同步
}
```

**修复根因 B** — 添加错误恢复：

```javascript
// MessagesPage.qml - Connections 中增加
function onErrorOccurred(message) {
    console.log("[MessagesPage] API错误: " + message + ", 重置fetch锁")
    root._fetchingConversations = false
}
```

同时在 `safeFetchConversations` 中增加超时保护：
```javascript
function safeFetchConversations(source) {
    // ... existing guards ...
    root._fetchingConversations = true
    // 5秒超时自动解锁
    Qt.callLater(function() {
        if (root._fetchingConversations) {
            console.log("[MessagesPage] fetchConversations超时, 强制解锁")
            root._fetchingConversations = false
        }
    })
    api.fetchConversations()
}
```

---

## BUG 3: 退出重进后左侧会话列表消失

**现象**: 退出消息页再进入，第二栏的会话列表为空。

### 🎨 根因分析（纯前端）

**这是 BUG 2 根因 B 的直接表现。**

由于 `_fetchingConversations` 死锁，`safeFetchConversations("login")` 被跳过，`onConversationsFetched` 永不触发，`root.conversations` 保持 `resetAllState()` 设置的空数组 `[]`。

**此外还有一个潜在问题**: `onLoggedInChanged` 通过 `_initialLoadDone` 标志控制只在"首次"加载。但 `_initialLoadDone` 在以下情况可能状态不对：

```
场景：用户登录 → _initialLoadDone=true → 切换到广场页 → 切换回消息页
结果：MessagesPage 未销毁，_initialLoadDone 仍为 true，不会重新加载会话
```

如果在此期间 `conversations` 因任何原因被清空（如轮询失败导致被覆盖），切换回来时列表就是空的。

### 🎨 修复方案

1. **修复根因 B 的死锁**（同 BUG 2）
2. **增加页面可见性监听**，每次切回消息页时刷新：
```qml
// MessagesPage.qml
onVisibleChanged: {
    if (visible && api.isLoggedIn) {
        console.log("[MessagesPage] 页面变为可见，刷新会话")
        safeFetchConversations("visible")
    }
}
```

---

## 新需求: 单向关注限制发送 1 条消息

**需求**: 单向关注（对方未关注我）时，只能发送 1 条消息。对方回复后解除限制。双向关注（好友）无限制。

### ⚙️ 后端实现

在 `POST /send-msg` 中增加检查逻辑：

```python
@app.post("/send-msg")
def send_msg(body: Send_Msg):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    
    # 检查目标用户是否存在
    target = db_fetchone("SELECT id FROM users WHERE id = ?", (body.to_whom_id,))
    if not target:
        return {"error": "Bad `to_whom_id`"}
    
    # 检查是否双向关注
    is_mutual = db_fetchone("""
        SELECT 1 FROM following f1
        JOIN following f2 ON f1.followee = f2.follower
        WHERE f1.follower = ? AND f1.followee = ? AND f2.followee = ?
    """, (user_id, body.to_whom_id, user_id))
    
    if not is_mutual:
        # 单向关注: 检查对方是否已回复过我（即对方是否给我发过消息）
        has_reply = db_fetchone("""
            SELECT 1 FROM offline_messages
            WHERE sender_id = ? AND receiver_id = ?
        """, (body.to_whom_id, user_id))
        
        if not has_reply:
            # 对方未回复: 检查我是否已发过消息
            my_msg_count = db_fetchone("""
                SELECT COUNT(*) as cnt FROM offline_messages
                WHERE sender_id = ? AND receiver_id = ?
            """, (user_id, body.to_whom_id))
            
            if my_msg_count and my_msg_count["cnt"] >= 1:
                return {"error": "对方尚未回复，只能发送一条消息。请等待对方回复后再发送。"}
    
    # 继续原有发送逻辑...
    db_execute("INSERT INTO offline_messages ...")
    # ... conversations 更新 ...
```

### 🎨 前端配合

在 `ChatPanel.qml` 中，单向关注时输入框下方显示提示文字，发送一条后禁用输入框：

```qml
// ChatPanel.qml
property bool canSendMessage: true  // 是否允许发送

// 在信息面板获取用户详情后判断
onUserDetailDataChanged: {
    if (userDetailData && !userDetailData.is_mutual) {
        // 检查是否已发过消息
        canSendMessage = ... // 需要后端返回是否已发过
    } else {
        canSendMessage = true
    }
}
```

---

## 汇总对照表

| # | BUG | 归属 | 根因 | 修改文件 |
|---|-----|------|------|---------|
| 1 | 多个搜索弹窗叠加 | 🎨 前端 | 两个 ConversationListPanel 各有一个 searchPopup | `ConversationListPanel.qml` (移出 popup) 或 `MessagesPage.qml` (统一 popup) |
| 2 | 历史消息不渲染 | 🎨 前端 | `root.messages = newMsgs` 破坏属性绑定 + `_fetchingConversations` 死锁 | `ChatPanel.qml` (不破坏绑定) + `MessagesPage.qml` (错误恢复) |
| 3 | 会话列表消失 | 🎨 前端 | 同上死锁 + 缺少页面可见性刷新 | `MessagesPage.qml` (错误恢复 + onVisibleChanged) |
| 4 | 单向关注限1条 | ⚙️ 后端 | 新功能 | `main.py` (`/send-msg` 增加检查) |

---

## 给后端开发的具体任务

### 任务: `/send-msg` 增加单向关注发送限制

**文件**: `src/backend/main.py`

在 `send_msg()` 函数中，cookie 验证通过后、插入消息前，增加以下逻辑：

```python
# 1. 判断是否双向关注
mutual = db_fetchone("""
    SELECT 1 FROM following f1
    JOIN following f2 ON f1.followee = f2.follower AND f1.follower = f2.followee
    WHERE f1.follower = ? AND f1.followee = ?
""", (user_id, body.to_whom_id))

if not mutual:
    # 2. 对方是否给我发过消息（已回复）
    replied = db_fetchone(
        "SELECT 1 FROM offline_messages WHERE sender_id = ? AND receiver_id = ?",
        (body.to_whom_id, user_id)
    )
    if not replied:
        # 3. 我是否已发过消息
        sent = db_fetchone(
            "SELECT COUNT(*) as cnt FROM offline_messages WHERE sender_id = ? AND receiver_id = ?",
            (user_id, body.to_whom_id)
        )
        if sent and sent["cnt"] >= 1:
            return {"error": "对方尚未回复，只能发送一条消息。"}
```

---

## 给前端开发的具体任务

### 任务 1: 修复搜索弹窗重复（优先级最高，视觉效果明显）

**方案 A（推荐）**: 将 searchPopup 移到 MessagesPage.qml 中，只保留一个。

1. 在 `MessagesPage.qml` 末尾（三个 Dialog 之后）添加 searchPopup
2. 从 `ConversationListPanel.qml` 删除 searchPopup 及其相关信号
3. 搜索结果通过 `MessagesPage.searchResults` 传递给统一 popup

### 任务 2: 修复属性绑定断裂（核心BUG，影响消息渲染）

**文件**: `ChatPanel.qml`

1. 增加 `property var _displayMessages: []` 作为内部显示数组
2. `sendMessage()` 操作 `_displayMessages` 而非 `messages`
3. Repeater model 改为 `root._displayMessages`
4. 增加 `onMessagesChanged` 同步: `_displayMessages = messages`

### 任务 3: 修复 fetchConversations 死锁

**文件**: `MessagesPage.qml`

1. 在 Connections 中增加 `onErrorOccurred` → `_fetchingConversations = false`
2. 在 `safeFetchConversations` 中增加 5 秒超时自动解锁
3. 增加 `onVisibleChanged` 刷新会话列表

### 任务 4: 单向关注 UI 限制

**文件**: `ChatPanel.qml`, `MessageBubble.qml`

1. 输入框下方显示提示: "对方尚未回复，你只能发送一条消息"
2. 发送一条后禁用输入框并显示提示
3. 收到对方回复后恢复输入框
