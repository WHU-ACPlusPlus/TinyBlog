# 后端 API 问题报告

> 发自：前端开发  
> 致：后端开发  
> 日期：2026-07-07  
> 状态：**请逐条确认并修复**

---

## 🔴 P0 — 阻塞性问题（前端无法正常工作）

### 1. `last_read_id` 状态污染，群消息永远返回空

**端点**: `POST /recv-group-msg`

**问题**: `user_in_group.last_read_id` 在每次调用后被更新为最新消息 ID。之后再次访问同一群组，查询条件是 `id > last_read_id`，如果期间没有新消息，**永远返回空数组**。

**复现**: 
1. YFunction 首次进入技术交流群 → 后端返回全部 11 条消息 → `last_read_id` 被设为 39
2. 切换群组后再切回来 → 前端调用 `recv-group-msg` → 后端查 `id > 39` → **返回 0 条**
3. 前端缓存兜底能撑住，但如果用户换了设备或清缓存，消息全部丢失

**期望**: 
- 提供 `before_id` 游标参数支持向后翻页（和 `post-fetch` 一样）
- 或者增加 `from_beginning: bool` 参数强制从头拉取

```python
# 现在（有问题）:
messages = db_fetchall("""
    SELECT ... FROM group_messages gm
    WHERE gm.group_id = ? AND gm.id > ?   # ← last_read_id 越大越拉不到
    ORDER BY gm.id ASC LIMIT ?
""", (group_id, last_read_id, count))

# 应该是:
messages = db_fetchall("""
    SELECT ... FROM group_messages gm
    WHERE gm.group_id = ?
      AND (? = 0 OR gm.id < ?)    # ← before_id 游标
    ORDER BY gm.id DESC LIMIT ?
""", (group_id, before_id, before_id, count))
```

---

### 2. `recv-msg` 响应格式不一致

**端点**: `POST /recv-msg`

**问题**: `with_user_id=0` 和 `with_user_id>0` 返回的 JSON 结构不同，字段名也不一样：

| 参数 | 返回字段 |
|---|---|
| `with_user_id=0` | `{"messages": [...], "unread_count": N}` |
| `with_user_id>0` | `{"messages": [...], "count": N, "next_cursor": C}` |

前端需要写两套解析逻辑。而且 `unread_count` vs `count` 命名没有规律。

**期望**: 统一返回格式，或者至少统一字段名。

---

### 3. 接口返回数据缺少头像字段

| 端点 | 缺少的字段 |
|---|---|
| `POST /get-follow-list` | `avatar`, `signature` |
| `POST /get-group-members` | `avatar` |

这两个接口的 SQL 只 SELECT 了 `id, username, nickname`，users 表明明有 `avatar` 和 `signature` 列但不返回。前端只能用首字母拼色块代替头像。

**期望**: SELECT 里加上 `u.avatar, u.signature`。

---

## 🟡 P1 — 严重影响体验

### 4. 群消息没有翻页机制

**端点**: `POST /recv-group-msg`

只有 `count` 参数，没有 `before_id`。首次拉取后 `last_read_id` 被设到最新值，之后再也拉不到历史消息。前端被迫自己实现消息缓存——这是后端的职责。

**期望**: 参照 `post-fetch` 接口，增加 `before_id` 游标。

### 5. 标记已读的时机错误

**端点**: `POST /recv-group-msg`

在**拉取消息的同时**就更新了 `last_read_id`：

```python
if messages:
    db_execute("UPDATE user_in_group SET last_read_id = ? ...", (messages[-1]["id"], ...))
```

这导致用户**只要点了群组，消息就全部"已读"了**，不管有没有真正滚动到那条消息。应该由前端显式调用标记已读的接口。

**期望**: 拆分接口——`recv-group-msg` 只拉取不标记，新增 `mark-group-read` 接口由前端在用户滚动到底部时调用。

### 6. 私信会话列表缺失 `is_read` 状态

**端点**: `POST /get-conversations`

返回的是所有聊过天的用户列表，但每条会话的 `unread_count` 计算依赖 `is_read` 字段。`/recv-msg` 虽然会标记已读，但 `/get-conversations` 本身不会。

**期望**: 确保 `unread_count` 准确，并测试如下场景：A 给 B 发消息 → B 调用 `get-conversations` → `unread_count` 应该 > 0。

---

## 🟢 P2 — 设计改进建议

### 7. 单文件 2400 行 Python 代码

`main.py` 把所有路由、数据库操作、表定义、工具函数全部塞在一个文件里。对一个生产项目来说，维护成本极高：
- FastAPI 路由定义散落在 2300 行中
- 没有数据模型层（pydantic models 和 db 操作混在一起）
- 没有 service 层

**建议**: 拆分为：
```
src/backend/
├── main.py          # FastAPI app + 路由注册
├── models.py        # Pydantic 请求/响应模型
├── database.py      # 数据库连接、表初始化
├── services/        # 业务逻辑
│   ├── auth.py
│   ├── posts.py
│   ├── messages.py
│   └── groups.py
└── tests/
```

### 8. Cookie 永不过期

```python
db_execute("INSERT INTO cookies (...) VALUES (?, ?, '2099-12-31 13:59:59')")
```

所有 cookie 过期时间都是 2099 年，且 `/check-cookie` 注释掉了过期检查。没有 token 刷新、没有短期 token + 长期 refresh token 的机制。

### 9. 没有 WebSocket

群聊和私信全部依赖 HTTP 轮询。前端需要每隔 N 秒调一次 `recv-group-msg` 才能收到新消息。对于聊天应用来说这是反模式的——应该用 WebSocket 推送。

### 10. `post-fetch` 的 `random.shuffle` 是反模式

```python
if body.before_id == 0:
    random.shuffle(combined)
```

首次拉取帖子时随机打乱顺序，导致每次刷新看到的内容都不一样。用户体验极差——刚看到的帖子一刷新就找不到了。如果要实现"推荐流"，应该在排序算法上做，而非暴力 shuffle。

---

## 📊 接口对照表

| 后端端点 | 前端 C++ ApiClient 方法 | 状态 |
|---|---|---|
| `/register-request` | `registerUser` | ✅ |
| `/login-request` | `login` | ✅ |
| `/check-cookie` | `checkCookie` | ✅ |
| `/logout` | — | ❌ 未接入 |
| `/follow` `/unfollow` | `follow` `unfollow` | ✅ |
| `/get-follow-list` | `fetchFollowList` | ⚠️ 缺 avatar |
| `/pub-post` | `publishPost` | ✅ |
| `/post-fetch` | `fetchTimeline` | ⚠️ shuffle 问题 |
| `/get-post` | `getPost` | ✅ |
| `/delete-post` | — | ❌ 未接入 |
| `/edit-post` | — | ❌ 未接入 |
| `/like` `/unlike` | `likePost` `unlikePost` | ✅ |
| `/comment` `/get-comments` | `comment` `fetchComments` | ✅ |
| `/delete-comment` | — | ❌ 未接入 |
| `/send-msg` `/recv-msg` | `sendMessage` `receiveMessages` | ⚠️ 格式不一致 |
| `/get-conversations` | — | ❌ 未接入 |
| `/create-group` | `createGroup` | ✅ |
| `/join-group` `/leave-group` | `joinGroup` `leaveGroup` | ✅ |
| `/send-group-msg` `/recv-group-msg` | `sendGroupMessage` `receiveGroupMessages` | 🔴 last_read_id bug |
| `/get-group-members` | `fetchGroupMembers` | ⚠️ 缺 avatar |
| `/get-my-groups` | `fetchMyGroups` | ✅ |
| `/get-group-info` | `fetchGroupInfo` | ✅ |
| `/kick-group-member` | — | ❌ 未接入 |
| `/disband-group` | — | ❌ 未接入 |
| `/patch-avatar` `GET /avatar` | `patchAvatar` `fetchAvatar` | ✅ |
| `/search` | — | ❌ 未接入 |
| `/get-notifications` | — | ❌ 未接入 |
| `/bookmark` `/unbookmark` `/get-bookmarks` | — | ❌ 未接入 |
| `/repost` | — | ❌ 未接入 |
| `/block` `/unblock` | — | ❌ 未接入 |

---

## 🎯 修复优先级

1. **立即修**: `last_read_id` 问题（#1）— 加上 `before_id` 游标
2. **本周修**: 头像字段补充（#3）、`recv-msg` 格式统一（#2）
3. **下迭代**: 标记已读拆分（#5）、代码拆分（#7）、WebSocket（#9）
