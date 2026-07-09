# 群消息消失 / 首次登录空白 / 群成员 TypeError — R5修复方案

> 日期: 2026-07-07 | 三轮代码审查 + 端到端数据流追踪

---

## BUG 1: 群聊消息切换会话后消失

### 现象

进入群聊 → 看到历史消息 → 切换到私聊 → 切回群聊 → 消息全部消失。

### ⚙️ 后端根因 — `last_read_id` 游标导致"增量拉取"语义吞噬历史消息

**`/recv-group-msg` 端点（`main.py` 第 950-981 行）** 的默认逻辑：

```python
# 当 before_id=0（默认值）时：
membership = db_fetchone("SELECT last_read_id FROM user_in_group ...")
last = membership["last_read_id"]  # 第一次是0，第二次是上次读到的最大消息ID

messages = db_fetchall("""
    SELECT ... FROM group_messages gm
    WHERE gm.group_id = ? AND gm.id > ?   -- ← ? = last_read_id
    ORDER BY gm.id ASC LIMIT ?
""", (body.group_id, last, body.count))

if messages:
    # 更新游标到返回消息的最大ID
    db_execute("UPDATE user_in_group SET last_read_id = ? ...", (messages[-1]["id"], ...))
```

**问题链路**：

```
第一次进入群聊:
  before_id=0 → 查询 gm.id > 0 → 返回全部消息，last_read_id 更新为最新消息ID(如100)
  → 前端显示正常 ✅

切换到私聊再切回群聊:
  before_id=0 → 查询 gm.id > 100 → 返回0条 → currentMessages = []
  → 消息全部消失 ❌
```

**对比私聊 `/get-private-messages`**：使用 `before_id` 分页，`before_id=0` 始终返回最新消息，不受游标影响。群聊也应该一致。

### ⚙️ 后端修复

**方案 A（推荐）**: 当 `before_id=0` 时返回最近 N 条消息，不管 `last_read_id`。仅用 `last_read_id` 记录未读位置，不用于过滤返回结果。

```python
@app.post("/recv-group-msg")
def recv_group_msg(body: Recv_Group_Msg_Req):
    # ... auth ...
    membership = db_fetchone(
        "SELECT last_read_id FROM user_in_group WHERE group_id=? AND user_id=?",
        (body.group_id, user_id))
    if not membership:
        return {"error": "You are not in this group."}
    
    last_read = membership["last_read_id"]
    
    if body.before_id > 0:
        # 向前翻页：获取 before_id 之前的消息
        messages = db_fetchall("""... WHERE gm.group_id=? AND gm.id < ? ...""",
                               (body.group_id, body.before_id, body.count))
    else:
        # 默认：获取最新 N 条消息（不管 last_read_id）
        messages = db_fetchall("""
            SELECT gm.id, gm.sender_id, u.username, u.nickname, gm.content, gm.sent_at
            FROM group_messages gm
            JOIN users u ON u.id = gm.sender_id
            WHERE gm.group_id = ?
            ORDER BY gm.id DESC
            LIMIT ?
        """, (body.group_id, body.count))
        messages = list(reversed(messages))  # 反转回时间正序
    
    # 仅更新 last_read_id（用于未读计数），不影响消息返回
    if messages:
        max_id = max(m["id"] for m in messages)
        if max_id > last_read:
            db_execute("UPDATE user_in_group SET last_read_id=? WHERE group_id=? AND user_id=?",
                       (max_id, body.group_id, user_id))
    
    has_more = len(messages) == body.count
    return {"messages": [dict(m) for m in messages], "has_more": has_more}
```

**方案 B（最小改动）**: 前端在 `onConversationClicked` 中使用 `before_id=2147483647`（最大整数）代替 `before_id=0`，让后端走"向前翻页"逻辑获取最新消息。但这不解决根本语义问题。

### 🎨 前端配套修改

`MessagesPage.qml` 中群聊消息的加载方式与私聊对齐——切换到新会话时始终获取最新消息：

```qml
// MessagesPage.qml onConversationClicked
onConversationClicked: function(conv) {
    root.currentConversation = conv
    if (conv.type === "private") {
        api.fetchPrivateMessages(conv.target_id, 0, 20)
    } else {
        // 群聊：始终 with before_id=0（后端修复后返回最新消息）
        api.receiveGroupMessages(conv.target_id, 20)
    }
}
```

后端修复后，前端无需改动。

---

## BUG 2: 首次登录消息列表空白，需手动操作才能加载

### 现象

新用户首次登录后，左侧第二栏空白。必须通过"+"按钮创建群聊或添加好友后，会话列表才出现。

### 🎨 前端根因 — 竞态条件：`onConversationsFetched` 覆盖 `onContactsFetched` 的结果

**`MessagesPage.qml` 第 220-236 行**：

```javascript
function onLoggedInChanged() {
    if (api.isLoggedIn) {
        if (!root._initialLoadDone) {
            root._initialLoadDone = true
            resetAllState()
            api.checkCookie()
            safeFetchConversations("login")   // ← 异步请求 A
            api.fetchContacts()               // ← 异步请求 B（同时发出）
        }
    }
}
```

**时间线（新用户场景）**：

```
时刻 0: 两个异步请求同时发出
时刻 1: 响应 B 先到 → onContactsFetched → mergeConversationsAndContacts()
         root.conversations = [好友A, 好友B]  ← 合并完毕，列表正常
时刻 2: 响应 A 后到 → onConversationsFetched → root.conversations = []  ← 覆盖！
```

`onConversationsFetched`（第 248 行）：
```javascript
function onConversationsFetched(conversations) {
    root._fetchingConversations = false
    root.conversations = conversations   // ← 直接赋值，不管之前有没有合并过联系人！
}
```

新用户从未收发消息 → `conversations` 表为空 → 后端返回 `[]` → 直接覆盖合并好的联系人列表。

### 🎨 前端修复

**方案 A（推荐）**: `onConversationsFetched` 中也调合并函数。

```javascript
function onConversationsFetched(conversations) {
    root._fetchingConversations = false
    root._rawConversations = conversations   // 存原始数据
    mergeConversationsAndContacts()          // 统一合并，不覆盖
}

function mergeConversationsAndContacts() {
    var merged = (root._rawConversations || []).slice()
    
    // 合并好友（双向关注）
    if (root._contacts) {
        for (var i = 0; i < root._contacts.length; i++) {
            var c = root._contacts[i]
            var exists = false
            for (var j = 0; j < merged.length; j++) {
                if (merged[j].type === "private" && merged[j].target_id === c.id) {
                    exists = true; break
                }
            }
            if (!exists) {
                merged.push({
                    id: -c.id,                    // 负ID表示无消息的占位
                    type: "private",
                    target_id: c.id,
                    target_name: c.nickname || c.username,
                    target_avatar: c.avatar || "",
                    last_message: "",
                    last_message_time: "",
                    unread_count: 0,
                    is_contact_only: true          // 标记：仅联系人，无消息
                })
            }
        }
    }
    
    // 合并单向关注
    if (root._followedOnly) {
        // ... 同理 ...
    }
    
    root.conversations = merged
}
```

**方案 B（更简单）**: 将两个请求串行化，确保顺序。

```javascript
function onLoggedInChanged() {
    if (api.isLoggedIn) {
        if (!root._initialLoadDone) {
            root._initialLoadDone = true
            resetAllState()
            api.checkCookie()
            safeFetchConversations("login")   // 先加载会话
            // fetchContacts 在 onConversationsFetched 成功后再调
        }
    }
}

function onConversationsFetched(conversations) {
    root._fetchingConversations = false
    root.conversations = conversations
    api.fetchContacts()   // ← 后加载联系人，然后合并
}

function onContactsFetched(contacts, followedOnly) {
    root._contacts = contacts
    root._followedOnly = followedOnly
    mergeConversationsAndContacts()
}
```

### ⚙️ 后端 — 无需修改

`/get-conversations` 对空用户返回 `[]` 是正确的。竞态问题是纯前端的。

---

## BUG 3: `ChatPanel.qml:688 TypeError: Cannot read property 'nickname' of undefined`

### 现象

点击"⋯"打开群聊信息面板时，控制台报错：
```
ChatPanel.qml:688: TypeError: Cannot read property 'nickname' of undefined
ChatPanel.qml:699: TypeError: Cannot read property 'nickname' of undefined
ChatPanel.qml:705: TypeError: Cannot read property 'role' of undefined
```

### 🎨 前端根因 — `ListModel` 委托中用 `modelData` 而非 `model`

Qt 6 QML 中，数据访问方式取决于模型类型：

| 模型类型 | 委托中访问方式 | `modelData` 是否有效 |
|---------|---------------|---------------------|
| JS 数组 (`model: [1,2,3]`) | `modelData` | ✅ |
| `ListModel` | `model.roleName` 或直接 `roleName` | ❌ `undefined` |
| C++ model | `model.roleName` | ❌ `undefined` |

**ChatPanel.qml 群成员列表（第 676-713 行）**:

```qml
ListView {
    model: groupMembersModel   // ← ListModel!

    delegate: Rectangle {
        Text {
            // 第 688 行 — ❌ modelData 对 ListModel 无效
            text: modelData.nickname ? modelData.nickname.charAt(0) : "?"
        }
        Text {
            // 第 699 行 — ❌
            text: modelData.nickname || modelData.username || ""
        }
        Text {
            // 第 705 行 — ❌
            text: modelData.role === "owner" ? qsTr("群主") :
                  modelData.role === "admin" ? qsTr("管理员") : qsTr("成员")
        }
    }
}
```

**对比正确用法——消息气泡 `Repeater`（ChatPanel.qml 第 267-280 行）**:

```qml
Repeater {
    model: root._displayMessages   // ← JS 数组

    MessageBubble {
        senderName: modelData.sender_name || ""   // ✅ modelData 对 JS 数组有效
    }
}
```

### 🎨 前端修复

将群成员委托中的 `modelData.xxx` 全部改为直接 `xxx`（ListModel 的角色名可直接访问）：

```qml
ListView {
    model: groupMembersModel

    delegate: Rectangle {
        width: groupMemberList.width
        height: 44
        color: "transparent"

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 8
            spacing: 10

            // 头像
            Rectangle {
                Layout.preferredWidth: 32; Layout.preferredHeight: 32
                radius: 16; color: "#e0e0e0"
                Text {
                    anchors.centerIn: parent
                    text: nickname ? nickname.charAt(0) : "?"          // ← 直接 nickname
                    font.pixelSize: 12; color: "#888"
                }
            }

            ColumnLayout {
                Layout.fillWidth: true; spacing: 2

                Text {
                    text: nickname || username || ""                    // ← 直接 nickname/username
                    font.pixelSize: 13; color: "#333"
                }
                Text {
                    text: role === "owner" ? qsTr("群主") :             // ← 直接 role
                          role === "admin" ? qsTr("管理员") : qsTr("成员")
                    font.pixelSize: 10; color: "#aaa"
                }
            }
        }
    }
}
```

### ⚙️ 后端 — 无需修改

`/get-group-detail` 返回的成员数据格式正确，包含 `nickname`、`username`、`role` 字段。

---

## 修复任务清单

### ⚙️ 后端

| # | 文件 | 改动 | 优先级 |
|---|------|------|--------|
| 1 | `main.py` `/recv-group-msg` | `before_id=0` 时返回最新 N 条消息（不用 `last_read_id` 过滤）；仅用 `last_read_id` 计未读数 | 🔴 高 |

### 🎨 前端

| # | 文件 | 改动 | 优先级 |
|---|------|------|--------|
| 1 | `MessagesPage.qml` | `onConversationsFetched` 改为调 `mergeConversationsAndContacts()` 而非直接赋值 | 🔴 高 |
| 2 | `MessagesPage.qml` | 增加 `_rawConversations` 属性，合并逻辑同时考虑原始会话和联系人 | 🔴 高 |
| 3 | `ChatPanel.qml:688-705` | 群成员委托中 `modelData.nickname` → `nickname`, `modelData.role` → `role` | 🔴 高 |

---

## 验证清单

| 场景 | 预期 |
|------|------|
| 进入群聊 → 看到历史消息 → 切到私聊 → 切回群聊 | 历史消息仍显示，不消失 |
| 新用户首次登录 | 左侧显示已关注的用户（如有），可点击空白会话开始聊天 |
| 点击"⋯" → 群聊信息面板 | 群成员列表正常显示昵称+角色，无 TypeError |
| 群聊发消息后退出重进 | 历史消息仍存在 |
