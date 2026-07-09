# 消息系统架构与逻辑文档

> TinyBlog (微微博) — 三栏仿QQ消息系统
> 稳定版 v2.3 | 2026-07-07 | YFunction 分支

---

## 一、系统概览

### 1.1 架构图

```
┌──────────────────────────────────────────────────────────────┐
│                    MainPage.qml (主壳)                        │
│  ┌─────────┬──────────────────────────────────────────────┐  │
│  │ 导航栏  │          MessagesPage.qml (消息页)            │  │
│  │ 60px   │  ┌──────────────┬──────────────────────────┐  │  │
│  │        │  │Conversation  │      ChatPanel.qml       │  │  │
│  │  □ 广场 │  │ListPanel     │  ┌────────────────────┐  │  │  │
│  │  ■ 消息 │  │280px         │  │  聊天头部 + ⋯按钮  │  │  │  │
│  │  □ 我的 │  │              │  ├────────────────────┤  │  │  │
│  │        │  │ 🔍搜索 [+]   │  │  MessageBubble × N  │  │  │  │
│  │        │  │              │  │  (Flickable 滚动)   │  │  │  │
│  │        │  │ Conversation │  ├────────────────────┤  │  │  │
│  │        │  │ Item × N     │  │  输入框  [发送]    │  │  │  │
│  │        │  │ (ListView)   │  └────────────────────┘  │  │  │
│  │        │  └──────────────┴──────────────────────────┘  │  │
│  └─────────┴──────────────────────────────────────────────┘  │
│                                                              │
│  [信息面板 Drawer — 300px 右侧滑入]                           │
│  ┌─ 私聊: 头像/用户名/关注状态/删除会话                       │
│  └─ 群聊: 头像/群名/群号/群成员列表/退出群聊                  │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 数据流

```
┌─────────────┐    HTTP REST     ┌──────────────┐    SQLite    ┌────────────┐
│  QML 前端   │ ←──────────────→ │ FastAPI 后端  │ ←─────────→ │  main.db   │
│             │   JSON/Cookie    │  :18999       │             │            │
│ ApiClient   │                  │  main.py      │             │ 7个表      │
│ (C++ 网络层) │                  │  (单体)        │             │            │
└─────────────┘                  └──────────────┘             └────────────┘

核心数据流（用户点击会话）:
  用户点击 ConversationItem
  → MessagesPage.onConversationClicked(conv)
  → 私聊: api.fetchPrivateMessages(target_id, 0, 20)
  → 群聊: api.receiveGroupMessages(target_id, 20)
  → 后端查询 → JSON响应
  → ApiClient 解析 → emit signal
  → MessagesPage.onPrivateMessagesFetched / onGroupMessagesReceived
  → root.currentMessages = messages
  → ChatPanel 属性绑定 → Repeater渲染 MessageBubble
```

### 1.3 状态管理架构

```
MessagesPage (状态中心 — 唯一信号入口)
├── conversations       ← onConversationsFetched + mergeConversationsAndContacts()
├── currentConversation ← onConversationClicked
├── currentMessages     ← onPrivateMessagesFetched / onGroupMessagesReceived
├── searchResults       ← onContactsSearched → 触发searchPopup显示
├── userDetailData      ← onUserDetailFetched → ChatPanel属性绑定
├── groupDetailData     ← onGroupDetailFetched → ChatPanel.onGroupDetailDataChanged
├── _contacts           ← onContactsFetched (好友列表)
├── _followedOnly       ← onContactsFetched (单向关注)
├── _rawConversations   ← onConversationsFetched (原始会话，不直接覆盖)
└── currentUserId       ← onCookieCheckComplete

ChatPanel (纯展示 — 通过属性接收数据)
├── currentConversation ← 来自MessagesPage
├── messages            ← 来自MessagesPage.currentMessages
├── userDetailData      ← 来自MessagesPage
├── groupDetailData     ← 来自MessagesPage → 触发onGroupDetailDataChanged → groupMembersModel
└── _displayMessages    ← 内部乐观更新数组 (不破坏外部messages绑定)
```

---

## 二、QML 组件树

### 2.1 MessagesPage.qml (825行)

**职责**: 消息页根组件，三栏布局 + 信号管理中心 + 状态中央存储。

| 属性 | 类型 | 说明 |
|------|------|------|
| `conversations` | `var[]` | 合并后的会话列表（raw conversations + contacts） |
| `currentConversation` | `var` | `{id, type, target_id, target_name, ...}` |
| `currentMessages` | `var[]` | `[{id, sender_id, sender_name, content, sent_at}]` |
| `searchResults` | `{users, groups}` | 绑定到统一searchPopup |
| `userDetailData` | `var` | 传递给ChatPanel |
| `groupDetailData` | `var` | 传递给ChatPanel |
| `_rawConversations` | `var[]` | 后端原始会话数据 |
| `_contacts` | `var[]` | 好友(双向关注) |
| `_followedOnly` | `var[]` | 单向关注 |
| `_fetchingConversations` | `bool` | 防重复锁（5s超时） |

**关键函数**:
| 函数 | 说明 |
|------|------|
| `safeFetchConversations(source)` | 防抖+超时保护的会话列表刷新 |
| `resetAllState()` | 登出/切换账号时清空所有状态 |
| `mergeConversationsAndContacts()` | 合并原始会话+联系人(好友+单向关注)，去重 |
| `handleSearchUserClick(userData)` | 搜索结果点击→自动关注(若未关注)→聊天 |
| `handleSearchGroupClick(groupData)` | 搜索结果点击→已加入则拉消息/未加入则join |
| `handleMenuAction(index)` | "+"菜单→0添加好友/1创建群聊/2加入群聊 |
| `initPollTimer()` | 30s定时轮询刷新会话列表 |
| `doSearch(keyword, type)` | 统一搜索入口 |

**信号处理 (Connections{target:api})**:
- `onLoggedInChanged` → 首次: resetAllState+checkCookie+双fetch；登出: resetAllState
- `onConversationsFetched` → `_rawConversations = data` → `mergeConversationsAndContacts()`
- `onContactsFetched` → 存`_contacts`/`_followedOnly` → `mergeConversationsAndContacts()`
- `onPrivateMessagesFetched` → `currentMessages = messages`
- `onGroupMessagesReceived` → QVariantList转换 → `currentMessages`
- `onConversationHidden` → 本地过滤删除
- `onErrorOccurred` → `_fetchingConversations = false` (死锁恢复)

**子组件**:
- `ConversationListPanel` × 2 (宽屏/窄屏各一个)
- `ChatPanel` × 2 (宽屏/窄屏各一个)
- `searchPopup` × 1 (统一搜索弹窗, Popup)
- `addFriendDialog` / `createGroupDialog` / `joinGroupDialog` (3个Dialog)

### 2.2 ConversationListPanel.qml (283行)

**职责**: 左侧第二栏，会话列表 + 搜索框 + "+"按钮。

| 信号 | 说明 |
|------|------|
| `conversationClicked(var conv)` | 点击会话项 |
| `menuAction(int index)` | "+"菜单选择 (0/1/2) |
| `addButtonClicked()` | "+"按钮点击 |

**搜索**: 500ms防抖 → `api.searchContacts(kw, "all")`。结果由MessagesPage统一searchPopup展示。

**会话列表**: `ListView` → `ConversationItem` delegate，按 `last_message_time DESC` 排序。

### 2.3 ConversationItem.qml (160行)

**职责**: 单个会话项，64px高。

**显示**: 头像(40x40, 群👥/用户首字母) | 名称+未读红点 | 最后消息预览(单行截断) | 时间(HH:mm或MM-DD)

### 2.4 ChatPanel.qml (797行)

**职责**: 右侧聊天区域 + 信息侧边面板。

**属性**:
| 属性 | 说明 |
|------|------|
| `currentConversation` | 当前会话数据(来自MessagesPage) |
| `messages` | 消息列表(来自MessagesPage绑定) |
| `_displayMessages` | 内部显示数组(乐观更新用,不破坏绑定) |
| `userDetailData` | 用户详情(来自MessagesPage) |
| `groupDetailData` | 群组详情 → `onGroupDetailDataChanged` → `groupMembersModel` |

**关键函数**:
| 函数 | 说明 |
|------|------|
| `sendMessage()` | 乐观追加→`_displayMessages`→api.sendMessage/sendGroupMessage |
| `loadEarlierMessages()` | 游标分页加载更早消息 |

**信息面板 Drawer** (300px, 右侧滑入, 250ms动画):
- **私聊面板**: 大头像80x80 | 用户名 | 关注状态("互关"/"已关注"/"+关注"按钮) | "删除会话"
- **群聊面板**: 群头像 | 群名 | 群号#xxx | 群成员ListView(`groupMembersModel`) | "退出群聊"

**群成员 ListView**: model=`groupMembersModel`(ListModel), delegate使用角色名直接访问(`nickname`, `username`, `role`)。

### 2.5 MessageBubble.qml (134行)

**职责**: 单条消息气泡。

**布局** (R6修复后):
```
对方消息(左对齐):              自己消息(右对齐):
[头像36×36]                    名字(我) 时间 ✓✓  [头像36×36]
  名字  时间                    ┌──────────────┐
  ┌──────────────┐              │ 蓝色气泡 #4a8cf7│
  │ 白色气泡      │              │ 白色文字       │
  │ #333文字      │              └──────────────┘
  └──────────────┘
```

**属性**: `messageId`, `senderId`, `senderName`, `senderAvatar`, `content`, `sentAt`, `isMine`, `isRead`

**头像**: 优先显示`Image`(base64图片),回落`Rectangle`+首字母`Text`。

---

## 三、数据库表结构

### 3.1 消息相关表

```sql
-- 私聊消息 (持久化存储)
offline_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    sent_at TEXT DEFAULT (datetime('now')),
    content TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,        -- R4: 标记已读,替代阅后即焚
    FOREIGN KEY (sender_id) → users, FOREIGN KEY (receiver_id) → users
)

-- 群聊消息
group_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    content TEXT,
    sent_at TEXT DEFAULT (datetime('now'))
)

-- 统一会话表 (私聊+群聊)
conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT DEFAULT 'private',       -- 'private' | 'group'
    target_id INTEGER NOT NULL,        -- 私聊:对方user_id / 群聊:group_id
    last_message TEXT DEFAULT '',
    last_message_time TEXT DEFAULT '',
    unread_count INTEGER DEFAULT 0,
    is_hidden INTEGER DEFAULT 0,       -- 软删除标记
    UNIQUE(user_id, type, target_id)
)

-- 群组
groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    owner_id INTEGER NOT NULL,
    avatar TEXT DEFAULT '',            -- R4: 新增头像
    created_at TEXT DEFAULT (datetime('now'))
)

-- 群成员关系
user_in_group (
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT DEFAULT 'member',        -- 'owner' | 'admin' | 'member'
    last_read_id INTEGER DEFAULT 0,    -- 仅用于未读计数,不用于过滤消息
    joined_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (group_id, user_id)
)

-- 好友申请
friend_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user_id INTEGER NOT NULL,
    to_user_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',     -- 'pending' | 'accepted' | 'rejected'
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(from_user_id, to_user_id)
)

-- 关注关系 (双向关注=好友)
following (
    follower INTEGER NOT NULL,         -- 关注者
    followee INTEGER NOT NULL,         -- 被关注者
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (follower, followee)
)
```

---

## 四、API 接口完整清单

### 4.1 会话管理

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/get-conversations` | `{cookie}` | `{conversations: [{id, type, target_id, target_name, target_avatar, last_message, last_message_time, unread_count}]}` |
| POST | `/hide-conversation` | `{cookie, conversation_id}` | `{status: "success"}` |

### 4.2 私聊消息

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/send-msg` | `{cookie, to_whom_id, content}` | `{status: "success"}` |
| POST | `/get-private-messages` | `{cookie, with_user_id, before_id=0, count=20}` | `{messages: [{id, sender_id, sender_name, sender_avatar, content, sent_at}], has_more}` |
| POST | `/recv-msg` | `{cookie}` | ⚠️已弃用,用`/get-private-messages`替代 |

### 4.3 群聊管理

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/create-group` | `{cookie, name}` | `{group_id}` |
| POST | `/join-group` | `{cookie, group_id}` | `{status: "success"}` |
| POST | `/leave-group` | `{cookie, group_id}` | `{status: "success"}` |
| POST | `/send-group-msg` | `{cookie, group_id, content}` | `{status: "success"}` |
| POST | `/recv-group-msg` | `{cookie, group_id, count=20, before_id=0}` | `{messages: [{id, sender_id, username, nickname, avatar, content, sent_at}], has_more}` |
| POST | `/get-group-members` | `{cookie, group_id}` | `{members: [{id, username, nickname, role, joined_at}]}` |
| POST | `/get-my-groups` | `{cookie}` | `{groups: [{id, name, owner_id, role, joined_at}]}` |
| POST | `/get-group-detail` | `{cookie, group_id}` | `{id, name, avatar, owner_id, created_at, member_count, members, my_role}` |
| POST | `/update-group` | `{cookie, group_id, name?, avatar?}` | `{status: "success"}` (仅群主) |

### 4.4 搜索与联系人

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/search-contacts` | `{cookie, keyword, type="all"}` | `{users: [{id, username, nickname, avatar, is_following, is_mutual}], groups: [{id, name, avatar, owner_id, is_member}]}` |
| POST | `/get-contacts` | `{cookie}` | `{mutual: [...], followed_only: [...], pending_requests: [...]}` |
| POST | `/get-user-detail` | `{cookie, user_id}` | `{id, username, nickname, avatar, signature, post_count, follower_count, followee_count, is_following, is_mutual}` |

### 4.5 好友申请

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/send-friend-request` | `{cookie, to_user_id}` | `{status: "success"}` |
| POST | `/get-friend-requests` | `{cookie}` | `{incoming: [...], outgoing: [...]}` |
| POST | `/handle-friend-request` | `{cookie, request_id, action}` | `{status: "success"}` |

### 4.6 关键约定

- **方法**: 几乎所有端点使用 `POST`（仅 `/avatar` 用 `GET`）
- **认证**: cookie 通过 JSON body 的 `"cookie"` 字段传递
- **错误格式**: HTTP 200 + `{"error": "描述"}`（非标准 HTTP 状态码）
- **数据库**: `db_execute/db_fetchone/db_fetchall/db_commit` + 全局 `db_lock`
- **后端结构**: 单文件 `main.py`，FastAPI 单体应用

---

## 五、关键状态流转

### 5.1 首次登录加载

```
用户登录成功
→ api.isLoggedIn = true
→ MessagesPage.onLoggedInChanged
→ _initialLoadDone==false → resetAllState()
→ api.checkCookie()
→ safeFetchConversations("login")    ─┐ 两个异步请求同时发出
→ api.fetchContacts()                ─┘
    ↓                                    ↓
响应A: onConversationsFetched        响应B: onContactsFetched
→ _rawConversations = data           → _contacts/_followedOnly 存储
→ mergeConversationsAndContacts()    → mergeConversationsAndContacts()
    ↓                                    ↓
        两者都调用同一个合并函数:
        merged = _rawConversations + _contacts(无消息占位) + _followedOnly(无消息占位)
        root.conversations = merged → ConversationListPanel 刷新
```

### 5.2 点击会话加载消息

```
用户点击 ConversationItem
→ MessagesPage.onConversationClicked(conv)
→ root.currentConversation = conv
→ 私聊: api.fetchPrivateMessages(conv.target_id, 0, 20)
→ 群聊: api.receiveGroupMessages(conv.target_id, 20)
→ 后端响应 → ApiClient emit signal
→ MessagesPage.onPrivateMessagesFetched / onGroupMessagesReceived
→ root.currentMessages = messages
→ ChatPanel.messages 绑定更新 → Repeater 渲染 MessageBubble
```

### 5.3 发送消息

```
用户输入文字 → 点击发送
→ ChatPanel.sendMessage()
→ 乐观追加到 _displayMessages (临时负数ID, 立刻渲染)
→ api.sendMessage(target_id, text) 或 api.sendGroupMessage(group_id, text)
→ 后端: INSERT消息 + UPSERT双方conversations + 更新last_message/unread
→ api.onMessageSent / onGroupMessageSent
→ MessagesPage: safeFetchConversations("msgSent") → 刷新会话列表排序
```

### 5.4 登出清空

```
用户登出
→ api.isLoggedIn = false
→ MessagesPage.onLoggedInChanged (else分支)
→ _initialLoadDone = false
→ resetAllState() → 清空: conversations/currentConversation/currentMessages/
                    searchResults/userDetailData/groupDetailData/
                    _contacts/_followedOnly/_rawConversations/
                    currentUserId/narrowViewIndex/_fetchingConversations
```

### 5.5 搜索结果点击

```
搜索 "张三" → api.searchContacts("张三", "all")
→ onContactsSearched(users, groups) → root.searchResults 赋值
→ searchPopup 自动显示 (visible绑定searchResults非空)
→ 用户点击某个用户:
  → handleSearchUserClick(userData)
  → 若 is_mutual → 直接聊天
  → 若 is_following → 直接聊天
  → 若 未关注 → api.follow(userData.id) → 再聊天
→ searchPopup关闭 + 切换到聊天视图
```

---

## 六、BUG 修复历史 (R1-R5)

| 轮次 | BUG | 根因 | 修复 |
|------|-----|------|------|
| R1 | 好友添加无申请 | 只有follow,无friend_request表 | 新增friend_requests表+3端点 |
| R1 | 切换账号聊天不空白 | onLoggedInChanged无登出分支 | 加else分支resetAllState() |
| R1 | 无法搜索好友 | 搜索结果无UI弹窗 | 实现统一searchPopup |
| R1 | 群聊再次进入消失 | join-group未创建conversation | join-group加INSERT conversations |
| R1 | 群成员名称TypeError | onGroupDetailFetched直接append QVariantMap | 改用显式属性append |
| R2 | 多个搜索弹窗 | 两个ConversationListPanel各有searchPopup | 移入MessagesPage统一管理 |
| R2 | 历史消息不渲染 | sendMessage() root.messages=赋值破坏绑定 | 改用_displayMessages内部数组 |
| R2 | 会话列表消失 | _fetchingConversations死锁 | 加onErrorOccurred恢复+5s超时 |
| R3 | api未定义 | Popup深层嵌套中上下文属性不可达 | 提取handleSearchUserClick到root函数 |
| R3 | 搜索结果重复 | searchTimer.triggered.connect累积 | 移入if(!searchTimer)守卫 |
| R3 | 注册页被错误信息污染 | LoginFlow监听全局errorOccurred | 移除全局监听,清理follow/unfollow滥用 |
| R4 | 群消息显示问号 | GroupMessageInfo无Q_GADGET,QML读不到字段 | receiveGroupMessages改用QVariantList |
| R4 | 头像不渲染 | 代码库无Image组件 | 增加Image+base64渲染+首字母回落 |
| R4 | 群成员不渲染 | Array.isArray可能失败+ListView高度塌缩 | length检查+minimumHeight |
| R5 | 群消息切换后消失 | last_read_id游标过滤 | before_id=0返回最新N条完整消息 |
| R5 | 首次登录空白 | onConversationsFetched覆盖onContactsFetched | 统一mergeConversationsAndContacts() |
| R5 | 群成员TypeError L688 | ListModel委托用modelData.xxx | 改为直接xxx(角色名访问) |

---

## 七、开发约定速查

| 领域 | 约定 |
|------|------|
| **QML控件** | `QtQuick.Controls.Basic` 禁止 Material/Fusion |
| **响应式** | 700px 断点, `isNarrowMode` 判断 |
| **API调用** | `Connections { target: api; function onXxx(...) {} }` 不轮询 |
| **属性绑定** | 子组件通过属性接收数据, 不直接调API |
| **信号管理** | MessagesPage 唯一 Connections 入口, ChatPanel 不连api信号 |
| **乐观更新** | 操作 `_displayMessages`, 不破坏 `messages` 属性绑定 |
| **错误处理** | `onErrorOccurred` → `_fetchingConversations = false` 防死锁 |
| **搜索** | 统一入口 `doSearch()`, 统一弹窗 `searchPopup` |
| **间距** | 4px/8px 倍数, 圆角8-12px |
| **动画** | Behavior/Transition, 150-300ms, eased |
| **后端SQL** | `db_execute/db_fetchone/db_fetchall/db_commit` + `db_lock` |
| **后端结构** | 单文件 `main.py`, FastAPI 单体 |
