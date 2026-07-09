# 群消息渲染 / 头像 / 群成员 — BUG分析与前后端修复方案

> 日期: 2026-07-07 | 基于深度代码审查

---

## BUG A: 群消息无法渲染（显示"气泡+问号"）

### 现象

点击群聊会话后，消息区域每条消息只显示一个带"?"的气泡，此前如果有私聊消息则显示在上方。

### 🎨 前端根因 — `GroupMessageInfo` C++ 结构体对 QML 不可见

**完整链路追踪**：

```
步骤1: 后端 /recv-group-msg 返回 JSON
  → {messages: [{id, sender_id, username, nickname, content, sent_at}, ...]}
  → ✅ 每条消息有 nickname 字段

步骤2: ApiClient::receiveGroupMessages() 解析 (api_client.cpp:768)
  → QList<GroupMessageInfo> msgs;
  → for (...) msgs.append(groupMsgFromJson(...))
  → emit groupMessagesReceived(msgs)    // ← ❌ QList<GroupMessageInfo>
  
步骤3: 信号签名 (api_client.h:157)
  → void groupMessagesReceived(const QList<GroupMessageInfo>& messages);
  → ❌ GroupMessageInfo 没有 Q_GADGET 宏，QML JS 引擎无法访问其字段！

步骤4: MessagesPage.onGroupMessagesReceived (MessagesPage.qml:243)
  → messages[i].nickname  →  undefined  (QML 读不到 C++ struct 字段)
  → messages[i].username  →  undefined
  → sender_name: messages[i].nickname || messages[i].username  →  undefined

步骤5: MessageBubble 渲染 (MessageBubble.qml:55)
  → text: root.senderName ? root.senderName.charAt(0) : "?"
  → senderName 为空 → 显示 "?"
```

**根本原因**: `GroupMessageInfo` 在 `api_types.h` 中定义为普通 C++ struct，只有 `Q_DECLARE_METATYPE`，没有 `Q_GADGET` + `Q_PROPERTY`。在 QML 中，`QList<GroupMessageInfo>` 传递后，每个元素是 opaque C++ 对象，JS 无法读取任何字段。

**对比：私聊消息为什么正常？** `fetchPrivateMessages()` 用的是 `QVariantList`——每个元素是 `QVariantMap`（JSON 对象），到达 QML 后自动转为 JS 对象，字段可直接访问。

### 🎨 修复（对齐私聊消息模式）

**文件 1: `api_client.h` 第 157 行 — 改信号签名**

```cpp
// 修改前:
void groupMessagesReceived(const QList<GroupMessageInfo>& messages);

// 修改后:
void groupMessagesReceived(const QVariantList& messages);
```

**文件 2: `api_client.cpp` 第 758-770 行 — 改用 QVariantList**

```cpp
void ApiClient::receiveGroupMessages(int group_id, int count) {
    QJsonObject body = withCookie({{"group_id", group_id}, {"count", count}});
    QNetworkReply* reply = postJson("/recv-group-msg", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;

        QVariantList messages;
        for (const auto& v : obj["messages"].toArray()) {
            QJsonObject o = v.toObject();
            QVariantMap item;
            item["id"] = o["id"].toInt();
            item["sender_id"] = o["sender_id"].toInt();
            item["username"] = o["username"].toString();
            item["nickname"] = o["nickname"].toString();
            item["content"] = o["content"].toString();
            item["sent_at"] = o["sent_at"].toString();
            messages.append(item);
        }
        emit groupMessagesReceived(messages);
    });
}
```

**文件 3: `MessagesPage.qml` 第 243-255 行 — 直接使用（无需额外转换，字段已可访问）**

现有代码保持不动，因为改成 `QVariantList` 后 `messages[i].nickname` 即可正常访问。

### ⚙️ 后端 — 无需修改

`/recv-group-msg` 返回的 JSON 字段完整：`{id, sender_id, username, nickname, content, sent_at}`。

---

## BUG B: 用户头像无法渲染

### 现象

所有头像位置（消息气泡旁、聊天头部、会话列表、群成员列表、信息面板）都显示为灰色圆圈 + 首字母，没有实际图片。

### 🎨 前端根因 — 代码库中从未使用 Image 组件渲染头像

经审查，整个消息系统中**所有6处"头像"**全部使用 `Rectangle(circle) + Text(首字母)` 模式，无一使用 `Image`：

| 位置 | 文件 | 当前渲染 |
|------|------|---------|
| 消息气泡头像 | `MessageBubble.qml:49` | `Rectangle(36x36)` + `Text(首字母或"？")` |
| 聊天头部对方头像 | `ChatPanel.qml:159` | `Rectangle(36x36)` + `Text(首字母或"👥")` |
| 私聊详情大头像 | `ChatPanel.qml:470` | `Rectangle(80x80)` + `Text(首字母)` |
| 群聊详情群头像 | `ChatPanel.qml:614` | `Rectangle(80x80)` + `Text("👥")` |
| 群成员列表头像 | `ChatPanel.qml:670` | `Rectangle(32x32)` + `Text(首字母)` |
| 会话列表头像 | `ConversationItem.qml:60` | `Rectangle(40x40)` + `Text(首字母或"👥")` |

**后端确实返回了头像数据**：`/get-avatar` 返回 `{user_id, avatar, signature}`，`avatar` 字段为 base64 编码的图片数据。`/get-conversations` 也返回 `target_avatar`（虽然目前为空字符串，因为没人上传过头像）。

### 🎨 修复

在每个头像位置叠加 `Image` 组件，有头像数据时显示图片，无数据时回落首字母。

**示例 — MessageBubble.qml 头像区域（第 49-57 行）**：

```qml
// 修改前:
Rectangle {
    width: 36; height: 36; radius: 18; color: "#e0e0e0"
    anchors.verticalCenter: parent.verticalCenter
    Text {
        anchors.centerIn: parent
        text: root.senderName ? root.senderName.charAt(0) : "?"
        font.pixelSize: 14; color: "#888"
    }
}

// 修改后:
Rectangle {
    width: 36; height: 36; radius: 18; color: "#e0e0e0"
    anchors.verticalCenter: parent.verticalCenter
    clip: true

    Image {
        anchors.fill: parent
        source: root.senderAvatar ? "data:image/png;base64," + root.senderAvatar : ""
        fillMode: Image.PreserveAspectCrop
        visible: root.senderAvatar !== ""
    }
    Text {
        anchors.centerIn: parent
        text: root.senderName ? root.senderName.charAt(0) : "?"
        font.pixelSize: 14; color: "#888"
        visible: root.senderAvatar === ""   // 无头像时显示首字母
    }
}
```

**MessageBubble 需新增属性** `senderAvatar`：

```qml
property string senderAvatar: ""   // base64 头像数据
```

**数据传递链**：需要在消息数据中包含 `sender_avatar` 字段。

- **后端** `/recv-group-msg` 和 `/get-private-messages`：SQL 查询中增加 `u.avatar` 字段
- **ApiClient**：解析时携带 avatar 字段
- **MessagesPage** `onGroupMessagesReceived` / `onPrivateMessagesFetched`：传递 avatar 到消息对象
- **MessageBubble**：新增 `senderAvatar` 属性并渲染

### ⚙️ 后端修复

**文件**: `src/backend/main.py`

**`/recv-group-msg` SQL 查询增加 avatar**：

```python
# 修改前:
SELECT gm.id, gm.sender_id, u.username, u.nickname, gm.content, gm.sent_at

# 修改后:
SELECT gm.id, gm.sender_id, u.username, u.nickname, u.avatar, gm.content, gm.sent_at
```

**`/get-private-messages` SQL 查询增加 avatar**：

```python
# 修改前:
SELECT m.id, m.sender_id, u.nickname as sender_name, m.content, m.sent_at, m.is_read

# 修改后:  
SELECT m.id, m.sender_id, u.nickname as sender_name, u.avatar as sender_avatar, m.content, m.sent_at, m.is_read
```

### 🎨 ApiClient 修复

**`api_client.cpp`** — 两个方法都要增加 avatar 字段透传：

1. `receiveGroupMessages()` — 在 `item` map 中增加 `item["avatar"] = o["avatar"].toString()`
2. `fetchPrivateMessages()` — 在 `item` map 中增加 `item["sender_avatar"] = o["sender_avatar"].toString()`

### 🎨 MessageBubble 修复

1. 增加 `property string senderAvatar: ""`
2. ChatPanel Repeater 中增加 `senderAvatar: modelData.sender_avatar || modelData.avatar || ""`
3. 头像区域改成 Image + Text 回落模式

---

## BUG C: 群成员无法渲染

### 现象

点击"⋯"打开群聊信息面板，群成员列表不显示任何成员。

### 🔗 分析 — 数据流代码正确，需确认运行时间题

数据流经审查是完整的：

```
后端 /get-group-detail → {members: [{id, username, nickname, avatar, role, joined_at}]}
  ↓
ApiClient fetchGroupDetail() → emit groupDetailFetched(QVariantMap)
  ↓
MessagesPage.onGroupDetailFetched → root.groupDetailData = detail
  ↓
ChatPanel.groupDetailData 绑定 → onGroupDetailDataChanged → groupMembersModel.append(...)
  ↓
ListView(model: groupMembersModel) → delegate 渲染
```

### 🎨 可能问题点与修复

#### 问题点 1: `property var` 绑定可能不触发 `onChanged`

在 Qt 6 QML 中，`property var` 的 `onXxxChanged` 只有在**整个对象引用**变化时触发。如果 `QVariantMap` 被赋值但 QML 没检测到引用变化，Handler 不会执行。

**修复**: 在 `MessagesPage.onGroupDetailFetched` 中强制创建新对象：

```javascript
function onGroupDetailFetched(detail) {
    // 强制创建新 JS 对象，确保 QML 检测到引用变化
    root.groupDetailData = JSON.parse(JSON.stringify(detail))
}
```

#### 问题点 2: `Array.isArray()` 对 QVariantList 可能返回 false

**修复**: 改用 `length` 检查：

```qml
// ChatPanel.qml onGroupDetailDataChanged
onGroupDetailDataChanged: {
    groupMembersModel.clear()
    // 修改前: if (groupDetailData && groupDetailData.members && Array.isArray(groupDetailData.members))
    // 修改后:
    if (groupDetailData && groupDetailData.members && groupDetailData.members.length > 0) {
        for (var i = 0; i < groupDetailData.members.length; i++) {
            var m = groupDetailData.members[i]
            if (m && m.id) {  // 增加有效性检查
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
}
```

#### 问题点 3: ListView 在 Drawer 中高度塌缩

群聊信息面板布局（ChatPanel.qml）：
```
Drawer(300px宽)
  ColumnLayout
    Rectangle(群头像80px)
    Text(群名称)
    Text(群号)
    Text(群成员 标题)
    ListView(model: groupMembersModel)  ← Layout.fillHeight: true
    Button(退出群聊)
```

如果上面元素总高度接近 Drawer 高度，`ListView` 的 `Layout.fillHeight: true` 可能让它得到接近0的高度。

**修复**: 给 ListView 设置 `Layout.minimumHeight: 100` 或使用 `Layout.preferredHeight`：

```qml
ListView {
    id: groupMemberList
    model: groupMembersModel
    Layout.fillWidth: true
    Layout.fillHeight: true
    Layout.minimumHeight: 80     // 新增：最小高度
    clip: true
    // ...
}
```

### ⚙️ 后端 — 无需修改

`/get-group-detail` 返回数据格式正确，包含 `members` 数组及每个成员的 `nickname`、`username`、`role` 字段。

---

## 修复任务清单

### ⚙️ 后端 (src/backend/main.py)

| # | 文件 | 改动 | 优先级 |
|---|------|------|--------|
| 1 | `main.py` `/recv-group-msg` | SQL 增加 `u.avatar` 字段 | 🔴 高 |
| 2 | `main.py` `/get-private-messages` | SQL 增加 `u.avatar as sender_avatar` 字段 | 🔴 高 |

### 🎨 前端 (src/frontend)

| # | 文件 | 改动 | 优先级 |
|---|------|------|--------|
| 1 | `api_client.h:157` | `groupMessagesReceived` 信号签名改为 `QVariantList` | 🔴 高 |
| 2 | `api_client.cpp:758-770` | `receiveGroupMessages()` 构建 `QVariantList` 而非 `QList<GroupMessageInfo>` | 🔴 高 |
| 3 | `api_client.cpp` | `receiveGroupMessages()` 和 `fetchPrivateMessages()` 透传 `avatar` 字段 | 🔴 高 |
| 4 | `MessageBubble.qml` | 新增 `senderAvatar` 属性；头像区域加 `Image` 组件 | 🔴 高 |
| 5 | `ChatPanel.qml` (Repeater) | 向 MessageBubble 传递 `senderAvatar` 字段 | 🔴 高 |
| 6 | `ChatPanel.qml:onGroupDetailDataChanged` | 改用 `length > 0` 替代 `Array.isArray`；加 `id` 有效性检查 | 🟡 中 |
| 7 | `ChatPanel.qml:groupMemberList` | 加 `Layout.minimumHeight: 80` 防塌缩 | 🟡 中 |
| 8 | `MessagesPage.qml:onGroupDetailFetched` | 用 `JSON.parse(JSON.stringify(detail))` 强制触发 onChanged | 🟡 中 |
| 9 | `ChatPanel.qml` (全部6处头像) | 叠加 `Image` 组件显示实际头像 | 🟢 低 |
| 10 | `ConversationItem.qml` | 叠加 `Image` 组件显示会话头像 | 🟢 低 |

---

## 验证清单

| 场景 | 预期结果 |
|------|---------|
| 点击群聊 → 查看历史消息 | 每条消息显示发送者昵称（非"?"），气泡正常渲染 |
| 群聊中发送消息 | 消息立即显示，昵称为"我" |
| 用户上传过头像 | 消息气泡旁、聊天头部显示实际头像图片 |
| 用户未上传头像 | 回落为灰色圆圈 + 首字母 |
| 点击"⋯" → 群聊信息面板 | 群成员列表正常显示，每行有昵称和角色 |
| 私聊消息气泡 | 头像和昵称正常显示 |
