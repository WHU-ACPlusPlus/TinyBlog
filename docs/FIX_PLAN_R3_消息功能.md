# 消息功能 — 第三轮问题分析与前后端分离修复方案

> 日期: 2026-07-07
> 基于甲方反馈的三个核心问题深度审查

---

## 问题总览

| # | 问题描述 | 根因归属 |
|---|---------|---------|
| 1 | 进入软件后左侧无法显示已关注的用户和已加入的群组 | ⚙️ 后端 + 🎨 前端 |
| 2 | 关注过的人再次搜索仍显示"+关注"按钮 | 🎨 前端主责 + 🎨 前端缺失 |
| 3 | 搜索结果弹出两个窗口，右边覆盖左边 | 🎨 前端 |

---

## 问题 1: 左侧无法显示已关注用户和已加入群组

### 现象

用户期望：登录后左侧第二栏（会话列表）能看到：
- 已加入的群组
- 已关注的用户 / 好友（双向关注）

实际：左侧只显示有过消息往来的会话，没有历史消息的联系人和群组不出现。

### 🎨 前端根因

`MessagesPage.qml` 的会话列表只显示 `/get-conversations` 返回的数据。而 `conversations` 表中的记录**只在发送/接收消息时创建**。单纯关注一个用户（`/follow`）不会创建 conversation 记录，因此该用户不会出现在会话列表中。

当前数据流：
```
/follow → following 表写入 → 结束（不创建 conversation）
/get-conversations → 只查 conversations 表 → 查不到刚关注的用户
```

前端 `ConversationListPanel` 只渲染 `root.conversations` 数组，没有合并"联系人"数据。

### ⚙️ 后端根因

`/get-conversations` 和 `/get-contacts` 是两个**独立端点**。前端只调了前者，没调后者。

`/get-contacts` 端点已正确实现（返回 `mutual` + `followed_only` + `pending_requests`），但前端从未调用它来填充会话列表。

### 🎨 前端修复方案

**方案 A（推荐）**: 在 `MessagesPage.onLoggedInChanged` 中同时加载两套数据，在会话列表中合并显示。

```javascript
// MessagesPage.qml - onLoggedInChanged
function onLoggedInChanged() {
    if (api.isLoggedIn) {
        if (!root._initialLoadDone) {
            root._initialLoadDone = true
            resetAllState()
            api.checkCookie()
            safeFetchConversations("login")
            api.fetchContacts()    // ← 新增：加载联系人列表
        }
    }
}

// 新增信号处理
function onContactsFetched(contacts, followedOnly) {
    // contacts = 好友(双向关注)
    // followedOnly = 单向关注
    root._contacts = contacts
    root._followedOnly = followedOnly
    mergeConversationsAndContacts()
}
```

在 `ConversationListPanel` 中将会话列表与联系人合并显示：有消息的会话按时间排序在顶部，无消息的联系人按昵称排序在下方。

**方案 B（更简单，推荐优先实施）**: 在 `/follow` 时由后端自动创建 conversation 记录。

### ⚙️ 后端修复方案

修改 `/follow` 端点，关注成功后自动创建 conversation 记录：

```python
@app.post("/follow")
def follow(body: Follow_Req):
    # ... 现有逻辑 ...
    db_execute("INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)",
            (user_id, body.followee_id))
    
    # 为双方创建 conversation（无消息的占位会话）
    db_execute("""
        INSERT OR IGNORE INTO conversations (user_id, type, target_id, last_message, last_message_time, unread_count)
        VALUES (?, 'private', ?, '', datetime('now'), 0)
    """, (user_id, body.followee_id))
    
    db_commit()
    return {"status": "success"}
```

同理，`/join-group` 已经修复了，需确认 `/create-group` 也正确创建了 conversation。

### 验证清单

| 场景 | 预期 |
|------|------|
| 关注用户A | A 出现在左侧会话列表，无最后消息 |
| 加入群组B | B 出现在左侧会话列表 |
| 被用户C关注 | 如果C是双向关注（好友），C出现在列表 |
| 重新登录 | 所有已关注用户和群组仍在列表中 |

---

## 问题 2: 关注后搜索仍显示"+关注"

### 现象（甲方原话）

> "关注过的人在下一次搜索，显示的还是关注按钮。甲方非常生气。"

### ⚙️ 后端分析 — 后端无问题

`/search-contacts` 端点（`main.py` 第 1476-1518 行）的 SQL 查询**已正确实现**：

```sql
SELECT u.id, u.username, u.nickname, u.avatar,
       (SELECT 1 FROM following WHERE follower = ? AND followee = u.id) AS is_following,
       ...
FROM users u
WHERE u.id != ? AND (u.username LIKE ? OR u.nickname LIKE ?)
```

参数 `?` 绑定为当前用户 `user_id`。关注后在 `following` 表中存在记录，`is_following` 会返回 `1`（→ `true`）。

**后端不需要修改。**

### 🎨 前端根因 — 双重问题

#### 子问题 A: 搜索结果的"+关注"文字是纯装饰

`MessagesPage.qml` 搜索结果的用户行（第 469 行）：
```qml
Text {
    text: modelData.is_mutual ? qsTr("好友") : modelData.is_following ? qsTr("已关注") : qsTr("+关注")
    font.pixelSize: 12; color: modelData.is_following ? "#999" : "#4a8cf7"
    // ← 没有 MouseArea！纯展示，不可点击！
}
```

整行的 `MouseArea`（第 474 行）点击后会调用 `handleSearchUserClick`：
```javascript
function handleSearchUserClick(userData) {
    searchPopup.close()
    root.searchResults = ({ users: [], groups: [] })
    api.fetchPrivateMessages(userData.id, 0, 20)  // ← 直接聊天，不管关注状态！
    if (root.isNarrowMode) root.narrowViewIndex = 1
}
```

**点击搜索结果用户后直接打开聊天，完全不检查 `is_following` 状态，也不调用 `api.follow()`。**

#### 子问题 B: ChatPanel 私聊信息面板的关注按钮从未实现

`ChatPanel.qml` 第 562 行：
```qml
MouseArea {
    onClicked: {
        console.log("[ChatPanel] 关注按钮被点击")
        // TODO: follow/unfollow 逻辑   ← 从未实现！
    }
}
```

#### 合起来的问题链路

```
用户搜索 "张三" → 结果显示 "+关注"（因为还没关注）
→ 用户点击"张三"这一行 → 直接打开聊天窗口（没有先关注！）
→ 用户在聊天窗口发消息 → 消息发过去了，但关注关系没建立
→ 用户再次搜索 "张三" → 仍然显示 "+关注"（因为确实没关注）
→ 用户大怒："我不是已经点过了吗！"
```

### 🎨 前端修复方案

**修改 `handleSearchUserClick`**，根据关注状态执行不同逻辑：

```javascript
function handleSearchUserClick(userData) {
    searchPopup.close()
    root.searchResults = ({ users: [], groups: [] })
    
    if (userData.is_mutual) {
        // 已是好友 → 直接聊天
        api.fetchPrivateMessages(userData.id, 0, 20)
        if (root.isNarrowMode) root.narrowViewIndex = 1
    } else if (userData.is_following) {
        // 已关注但非好友（对方没回关）→ 可以聊天（单向关注限1条）
        api.fetchPrivateMessages(userData.id, 0, 20)
        if (root.isNarrowMode) root.narrowViewIndex = 1
    } else {
        // 未关注 → 先关注，再创建对话
        api.follow(userData.id)
        // 等 onFollowSuccess 后再打开聊天（或乐观处理）
        api.fetchPrivateMessages(userData.id, 0, 20)
        if (root.isNarrowMode) root.narrowViewIndex = 1
    }
}
```

**修改搜索结果的"+关注"文字**，加上可点击的 MouseArea：

```qml
// 将 Text 替换为可点击的按钮
Rectangle {
    Layout.preferredWidth: 60; Layout.preferredHeight: 28; radius: 14
    color: modelData.is_following ? "#f0f0f0" : "#e8f0fe"
    
    Text {
        anchors.centerIn: parent
        text: modelData.is_mutual ? qsTr("好友") : modelData.is_following ? qsTr("已关注") : qsTr("+关注")
        font.pixelSize: 12
        color: modelData.is_following ? "#999" : "#4a8cf7"
    }
    
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            if (!modelData.is_following) {
                // 未关注 → 执行关注
                api.follow(modelData.id)
                // 乐观更新显示
                modelData.is_following = true
            }
        }
    }
}
```

**实现 ChatPanel 私聊信息面板的关注按钮**：

```qml
// ChatPanel.qml 私聊信息面板中
MouseArea {
    anchors.fill: parent
    cursorShape: Qt.PointingHandCursor
    onClicked: {
        if (root.userDetailData) {
            if (root.userDetailData.is_mutual) {
                // 已是好友，不做操作（或可选取消关注）
                console.log("[ChatPanel] 已是好友")
            } else if (root.userDetailData.is_following) {
                // 已关注 → 取消关注
                api.unfollow(root.userDetailData.id)
            } else {
                // 未关注 → 关注
                api.follow(root.userDetailData.id)
            }
        }
    }
}
```

### 验证清单

| 场景 | 预期 |
|------|------|
| 搜索未关注用户 → 点击"+关注"按钮 | 执行关注，按钮变为"已关注" |
| 搜索未关注用户 → 点击整行 | 先关注再打开聊天 |
| 搜索已关注用户 | 显示"已关注"(灰色)，点击整行直接聊天 |
| 搜索好友(双向关注) | 显示"好友"(灰色)，点击直接聊天 |
| 退出重进后搜索 | 关注状态正确保留 |
| 私聊信息面板点关注按钮 | 可以关注/取消关注 |

---

## 问题 3: 搜索结果弹出两个窗口

### 现象

> "搜索还是会蹦出来两个用户名称搜索结果，右边的搜索结果覆盖在左边的上面"

### 🎨 前端根因

**这是一个架构层面的问题，100% 前端责任。**

经过代码审查确认：当前源码中 `MessagesPage.qml` 只有**一个** `searchPopup`（Popup），`ConversationListPanel.qml` 的搜索弹窗**已被移除**。

但如果用户在**旧构建**上测试（修复后未重新编译），旧代码中的 `ConversationListPanel.qml` 仍保留着搜索弹窗，会出现双弹窗。

除此之外，还有两个**底层设计问题**会导致类似症状：

#### 根因 A: ConversationListPanel 搜索框仍在独立发送搜索请求

`ConversationListPanel.qml` 第 90 行的搜索框：
```javascript
onTextChanged: {
    // ... 500ms debounce ...
    api.searchContacts(kw, "all")  // ← 仍会触发搜索！
}
```

虽然是 MessagesPage 的统一 `searchPopup` 展示结果，但如果有两处代码都处理 `onContactsSearched` 信号（比如 MessagesPage 的 Connections 和某个残留的 handler），就会创建两份结果数据，或者两个弹窗各绑一份。

**当前代码已通过将弹窗统一到 MessagesPage 解决了显示重复问题。需确保彻底移除 ConversationListPanel 的旧弹窗代码并重新编译。**

#### 根因 B: MessagesPage 有两个 ConversationListPanel，同时接收搜索结果

```qml
// 宽屏
ConversationListPanel { id: convListPanelWide; ... }
// 窄屏
ConversationListPanel { id: convListPanelNarrow; ... }
```

两个面板的搜索框都可以输入。如果用户先在宽屏面板的搜索框输入、再切到窄屏（反之亦然），两个搜索框的内容不同，可能先后触发搜索。

**但这不是双弹窗的直接原因，因为弹窗已统一到 MessagesPage 级别。**

### 🎨 前端修复方案

**核心原则**: 搜索请求和结果展示必须**单一入口、单一出口**。

```
搜索来源（多个）         结果展示（唯一）
┌─────────────────┐     ┌──────────────┐
│ ConvPanel 搜索框 │────→│              │
│ addFriendDialog │────→│ searchPopup  │
│ (未来可能的更多) │────→│  (MessagesPage)│
└─────────────────┘     └──────────────┘
        ↓                      ↑
   api.searchContacts()  onContactsSearched()
                              ↓
                      root.searchResults
```

1. **确认 ConversationListPanel 旧弹窗已彻底删除**（检查 git diff 或文件内容）
2. **在 ConversationListPanel 搜索框中增加防重复机制**，如果 `addFriendDialog` 已打开则不触发搜索
3. **统一搜索入口**: 所有搜索都走 `MessagesPage.doSearch(keyword, type)` 函数，而不是各自直接调 `api.searchContacts()`

```javascript
// MessagesPage.qml - 统一搜索入口
function doSearch(keyword, type) {
    if (!keyword || keyword.length === 0) return
    console.log("[MessagesPage] 统一搜索: kw=" + keyword + " type=" + type)
    root._lastSearchKeyword = keyword
    api.searchContacts(keyword, type)
}
```

然后 `ConversationListPanel` 和 `addFriendDialog` 都改为调用 `root.doSearch()` 而非直接调 `api.searchContacts()`。

### ⚙️ 后端不需要修改

搜索端点在本次问题中无缺陷。

---

## 前后端修复任务清单

### ⚙️ 后端 (src/backend/main.py)

| # | 改动 | 优先级 |
|---|------|--------|
| 1 | `/follow` 端点：关注成功后自动 `INSERT OR IGNORE INTO conversations` 创建占位会话 | 🔴 高 |
| 2 | 验证 `/join-group` 和 `/create-group` 已正确创建 conversation | 🟡 中 |
| 3 | 验证 `/search-contacts` 的 `is_following` 逻辑（已确认正确，无需修改） | ✅ 已验证 |

### 🎨 前端 (src/frontend/*.qml)

| # | 文件 | 改动 | 优先级 |
|---|------|------|--------|
| 1 | `MessagesPage.qml` | `handleSearchUserClick`: 增加关注状态判断，未关注时先 `api.follow()` | 🔴 高 |
| 2 | `MessagesPage.qml` | 搜索结果中"+关注"文字改为可点击按钮，点击执行 `api.follow()` | 🔴 高 |
| 3 | `MessagesPage.qml` | `onLoggedInChanged`: 同时调 `api.fetchContacts()` 加载联系人 | 🔴 高 |
| 4 | `MessagesPage.qml` | 新增 `onContactsFetched` 信号处理，合并联系人到会话列表 | 🔴 高 |
| 5 | `MessagesPage.qml` | 新增 `doSearch()` 统一搜索入口函数 | 🟡 中 |
| 6 | `ConversationListPanel.qml` | 搜索框改用 `root.doSearch()` 而非直接调 `api.searchContacts()` | 🟡 中 |
| 7 | `ConversationListPanel.qml` | `addFriendDialog` 打开时禁止搜索框触发搜索 | 🟡 中 |
| 8 | `ChatPanel.qml` | 私聊信息面板关注按钮：实现 `follow/unfollow` 逻辑 | 🔴 高 |
| 9 | `ConversationListPanel.qml` | 增加联系人分区（有消息的会话 + 无消息的联系人） | 🟢 低 |
| 10 | 确保 CMakeLists.txt 注册所有 QML 文件，重新编译 | 🔴 高 |

---

## 甲方验收标准

| 场景 | 操作 | 预期结果 |
|------|------|---------|
| 登录 | 打开软件 | 左侧显示所有已关注用户和已加入群组 |
| 搜索关注 | "+"→"添加好友"→搜索"张三"→点击"+关注" | 关注成功，按钮变"已关注" |
| 再次搜索 | 退出后重新搜索"张三" | 显示"已关注"，不是"+关注" |
| 发消息 | 点击搜索结果中的"张三" | 未关注先关注再聊天，已关注直接聊天 |
| 搜索结果窗口 | 搜索任意关键词 | 只弹出一个结果窗口，无重叠 |
| 退出重进 | 关闭软件重新打开 | 所有关注关系和会话列表保持不变 |
