# TinyBlog P2 功能文档

> 版本: 2026-07-07 | 覆盖 #25–#38 所有改进项

---

## 目录

1. [新增 API 端点](#1-新增-api-端点)
2. [现有端点修复](#2-现有端点修复)
3. [数据库变更](#3-数据库变更)
4. [基础设施改进](#4-基础设施改进)
5. [API 速查表](#5-api-速查表)

---

## 1. 新增 API 端点

### #25 修改密码 — `POST /change-password`

| 项目 | 内容 |
|------|------|
| **方法** | POST |
| **路径** | `/change-password` |
| **认证** | cookie |

**请求体:**
```json
{
    "cookie": "string",
    "old_password": "string",
    "new_password": "string"
}
```

**校验规则:**
- 旧密码必须正确
- 新密码至少 6 个字符
- 新旧密码不能为空

**成功响应:**
```json
{"status": "success"}
```

**错误响应:**
```json
{"error": "Incorrect old password."}
{"error": "Password must be at least 6 characters."}
```

---

### #26 注销账号 — `POST /delete-account`

| 项目 | 内容 |
|------|------|
| **方法** | POST |
| **路径** | `/delete-account` |
| **认证** | cookie |

**请求体:**
```json
{
    "cookie": "string",
    "password": "string"
}
```

**级联清理范围:**
cookies, following, liking_users, comments, offline_messages, read_posts, bookmarks, notifications, blocks, reports, user_in_group, group_messages, posts（及关联的 liking_users/comments/post_media/read_posts/bookmarks/post_hashtags/notifications），拥有的群组自动解散

**成功响应:**
```json
{"status": "success"}
```

---

### #27 屏蔽系统

#### `POST /block` — 拉黑用户

| 项目 | 内容 |
|------|------|
| **请求体** | `{"cookie":"str","user_id":int}` |
| **副作用** | 自动取消双方关注关系 |
| **幂等** | INSERT OR IGNORE |

#### `POST /unblock` — 取消拉黑

| 项目 | 内容 |
|------|------|
| **请求体** | `{"cookie":"str","user_id":int}` |
| **说明** | 目标未被拉黑也不报错 |

#### `POST /get-blocked-users` — 已拉黑列表

| 项目 | 内容 |
|------|------|
| **请求体** | `{"cookie":"str"}` |
| **返回** | `{"blocked_users":[{id,username,nickname,avatar,created_at}]}` |

---

### #28 群组管理

#### `POST /kick-group-member` — 踢出成员

| 项目 | 内容 |
|------|------|
| **请求体** | `{"cookie":"str","group_id":int,"user_id":int}` |
| **权限** | 仅群主 |
| **限制** | 不能踢自己 |

#### `POST /change-group-name` — 修改群名

| 项目 | 内容 |
|------|------|
| **请求体** | `{"cookie":"str","group_id":int,"name":"str"}` |
| **权限** | 仅群主 |
| **校验** | 群名不能为空 |

#### `POST /transfer-group` — 转让群主

| 项目 | 内容 |
|------|------|
| **请求体** | `{"cookie":"str","group_id":int,"new_owner_id":int}` |
| **权限** | 仅群主 |
| **限制** | 目标必须在群内，不能转给自己 |
| **副作用** | 原群主降为 member，新群主升为 owner |

#### `POST /disband-group` — 解散群组

| 项目 | 内容 |
|------|------|
| **请求体** | `{"cookie":"str","group_id":int}` |
| **权限** | 仅群主 |
| **级联** | 删除所有群消息和成员关系 |

---

### #29 转发通知

已集成到现有 `POST /repost` 端点：
- 转发成功后向原帖作者发送 `type: "repost"` 通知
- 通知的 `post_id` 指向新创建的转发帖

---

### #30 帖子可见性

已集成到 `POST /pub-post`：

| 字段 | 类型 | 默认值 | 可选值 |
|------|------|--------|--------|
| `visibility` | string | `"public"` | `public`, `followers_only`, `private` |

**行为:**
| 可见性 | 谁能看到 |
|--------|----------|
| `public` | 所有人 |
| `followers_only` | 关注发布者的人 + 发布者本人 |
| `private` | 仅发布者本人 |

`POST /post-fetch` 的推荐流已自动按可见性过滤。

---

### #31 举报系统 — `POST /report`

| 项目 | 内容 |
|------|------|
| **请求体** | `{"cookie":"str","target_type":"user|post|comment","target_id":int,"reason":"str"}` |
| **校验** | 验证目标存在 |
| **状态** | 默认 `pending` |

---

### #32 标签系统

#### `POST /get-hashtag-posts` — 按标签获取帖子

| 项目 | 内容 |
|------|------|
| **请求体** | `{"cookie":"str","hashtag":"str","before_id":0,"count":20}` |
| **分页** | 游标分页 (before_id) |
| **说明** | hashtag 参数可带或不带 `#` 前缀 |
| **返回** | `{"posts":[{完整帖子含media}],"count":int,"next_cursor":int}` |

#### `POST /trending-hashtags` — 热门标签

| 项目 | 内容 |
|------|------|
| **请求体** | `{"count":20}` |
| **返回** | `{"hashtags":[{"name":"str","post_count":int}]}` |
| **排序** | 按使用频次降序 |

#### 发帖时自动提取

在 `POST /pub-post` 中，系统自动从 `text` 中提取 `#标签名` 格式的标签（支持中文字符），存入 `hashtags` 和 `post_hashtags` 表。响应中返回提取到的标签列表：
```json
{"status":"success","post_id":1,"hashtags":["TinyBlog","test"]}
```

---

## 2. 现有端点修复

### #34 delete-post 级联清理

`POST /delete-post` 新增清理以下表：
- `bookmarks` — 收藏记录
- `post_hashtags` — 标签关联
- `notifications` — 引用该帖子的通知

### #35 同上（合并实现）

### #36 leave-group 群主保护

`POST /leave-group` 现在禁止群主直接退出，返回：
```json
{"error":"Owner cannot leave. Transfer ownership or disband the group first."}
```
群主必须先转让群主或解散群组。

---

## 3. 数据库变更

### 新增表

| 表名 | 用途 | 关键列 |
|------|------|--------|
| `blocks` | 拉黑关系 | blocker_id, blocked_id, created_at |
| `reports` | 举报记录 | reporter_id, target_type, target_id, reason, status |
| `hashtags` | 标签字典 | id, name (UNIQUE) |
| `post_hashtags` | 帖子-标签关联 | post_id, hashtag_id |

### 新增列

| 表 | 列名 | 类型 | 默认值 |
|----|------|------|--------|
| `posts` | `visibility` | TEXT | `'public'` |

所有新增均向后兼容，已有数据库通过 `ALTER TABLE ... ADD COLUMN` 自动升级。

---

## 4. 基础设施改进

### #33 `_last_cursor` 线程安全修复

**问题:** `db_execute()` 和 `db_lastrowid()`/`db_rowcount()` 之间跨线程串扰

**方案:** 使用 `threading.local()` 替代全局 `_last_cursor`

- `db_execute()` 在锁内同时捕获 `lastrowid` 和 `rowcount` 到线程本地存储
- `db_lastrowid()` / `db_rowcount()` 从线程本地存储读取
- 完全消除跨线程竞态条件

### #38 `.gitignore`

已存在且完整，覆盖：数据库文件、Python 缓存、虚拟环境、IDE 配置、构建产物。

---

## 5. API 速查表

| # | 端点 | 方法 | 类型 | 说明 |
|----|------|------|------|------|
| 25 | `/change-password` | POST | 新增 | 修改密码 |
| 26 | `/delete-account` | POST | 新增 | 注销账号 |
| 27a | `/block` | POST | 新增 | 拉黑用户 |
| 27b | `/unblock` | POST | 新增 | 取消拉黑 |
| 27c | `/get-blocked-users` | POST | 新增 | 已拉黑列表 |
| 28a | `/kick-group-member` | POST | 新增 | 踢出群成员 |
| 28b | `/change-group-name` | POST | 新增 | 修改群名 |
| 28c | `/transfer-group` | POST | 新增 | 转让群主 |
| 28d | `/disband-group` | POST | 新增 | 解散群组 |
| 29 | `/repost` | POST | 修复 | 转发时发送通知 |
| 30 | `/pub-post` | POST | 增强 | 支持 visibility 参数 |
| 31 | `/report` | POST | 新增 | 举报用户/帖子/评论 |
| 32a | `/get-hashtag-posts` | POST | 新增 | 按标签获取帖子 |
| 32b | `/trending-hashtags` | POST | 新增 | 热门标签排行 |
| 34 | `/delete-post` | POST | 修复 | 级联清理 bookmarks/hashtags/notifications |
| 36 | `/leave-group` | POST | 修复 | 禁止群主直接退群 |

---

**总计:** 新增 12 个端点 + 修复 6 处现有端点 + 1 处线程安全修复 + 4 张新表 + 1 个新列
