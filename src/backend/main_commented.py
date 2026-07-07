#!/usr/bin/env -S uv run python3
# =============================================================================
# Tiny Blog（微微博）— 最小可用社交平台后端
# Copyright (c) 2026 Becharm Kon. All Rights Reserved.
#
# 本文件是一个单文件全栈后端，使用 FastAPI + SQLite 实现。
# 运行方式：
#   ./main.py              （利用 shebang 自动调用 uv）
#   uv run main.py
#   python main.py         （需要先激活虚拟环境）
# =============================================================================

# =============================================================================
# 第一部分：数据库初始化
# =============================================================================

import sqlite3, bcrypt, secrets

# --- 连接 SQLite 数据库 ---
# check_same_thread=False：允许多线程访问（FastAPI 默认多线程处理请求）
conn = sqlite3.connect("main.db", check_same_thread=False)
# 设置 row_factory 为 sqlite3.Row，这样查询结果可以用列名（如 row["id"]）访问
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# --- 建表（仅在直接运行此文件时执行，导入时不执行）---
if __name__ == "__main__":
    # 用户表：存储注册用户信息
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,   -- 用户唯一ID
            username TEXT UNIQUE NOT NULL,           -- 登录用户名（唯一）
            nickname TEXT NOT NULL,                  -- 显示昵称
            password_hash TEXT NOT NULL,             -- bcrypt加密后的密码哈希
            email_address TEXT NOT NULL DEFAULT ''   -- 邮箱地址（预留字段）
        )
    """)

    # Cookie/令牌表：管理登录会话
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cookies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,                -- 关联的用户ID
            token TEXT UNIQUE NOT NULL,              -- 64位十六进制随机令牌
            expires_at TEXT NOT NULL,                -- 过期时间
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # 关注关系表：多对多关系
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS following (
            follower INTEGER NOT NULL,               -- 关注者（粉丝）
            followee INTEGER NOT NULL,              -- 被关注者
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (follower, followee),        -- 联合主键，防止重复关注
            FOREIGN KEY (follower) REFERENCES users(id),
            FOREIGN KEY (followee) REFERENCES users(id)
        )
    """)

    # 帖子表：用户发布的内容
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            publisher_id INTEGER NOT NULL,           -- 发布者ID
            content TEXT,                            -- 文字内容
            like_num INTEGER NOT NULL DEFAULT 0,    -- 点赞数（冗余计数，避免JOIN查询）
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (publisher_id) REFERENCES users(id)
        )
    """)

    # 点赞记录表：记录谁给哪个帖子点了赞
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS liking_users (
            post_id INTEGER NOT NULL,
            liker_id INTEGER NOT NULL,              -- 点赞者ID
            liked_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (liker_id) REFERENCES users(id),
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)

    # 评论表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,                -- 被评论的帖子ID
            commenter_id INTEGER NOT NULL,           -- 评论者ID
            content TEXT NOT NULL,                   -- 评论内容
            commented_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (commenter_id) REFERENCES users(id)
        )
    """)

    # 离线私信表：阅后即焚的私信系统
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS offline_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,              -- 发送者ID
            receiver_id INTEGER NOT NULL,            -- 接收者ID
            sent_at TEXT NOT NULL DEFAULT (datetime('now')),
            content TEXT NOT NULL,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    """)

    # 帖子媒体附件表：一个帖子可以有多个媒体（图片等）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS post_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            offset INTEGER NOT NULL,                 -- 排序序号（0, 1, 2...）
            content TEXT NOT NULL,                   -- Base64编码的媒体数据
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)

    # 已读帖子记录表：用于推荐流去重
    # 用户拉取过的帖子会记录在此，下次推荐时排除
    cursor.execute(
"""
    CREATE TABLE IF NOT EXISTS read_posts (
        user_id INTEGER NOT NULL,
        post_id INTEGER NOT NULL,
        read_at TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (user_id, post_id),             -- 联合主键，保证唯一
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (post_id) REFERENCES posts(id)
    );
"""
            )

    # 群组表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,                      -- 群名称
            owner_id INTEGER NOT NULL,               -- 群主ID
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
    """)

    # 群组成员表：记录用户和群的归属关系
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_in_group (
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',     -- 角色：'owner' 或 'member'
            joined_at TEXT DEFAULT (datetime('now')),
            last_read_id INTEGER DEFAULT 0,          -- 已读消息游标（用于增量拉取）
            PRIMARY KEY (group_id, user_id),
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # 群聊消息表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            content TEXT,
            sent_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (sender_id) REFERENCES users(id)
        )
    """)

    # 提交所有建表操作
    conn.commit()

# =============================================================================
# 第二部分：FastAPI 服务路由
# =============================================================================

import fastapi, uvicorn, random

# 创建 FastAPI 应用实例
app = fastapi.FastAPI(title="Tiny Blog")

# ---------------------------------------------------------------------------
# 健康检查接口
# ---------------------------------------------------------------------------

@app.get("/ping")  # 仅用于测试服务是否正常运行
def ping():
    return {"message": "Pong!"}

# ---------------------------------------------------------------------------
# 数据模型定义（Pydantic 请求体校验）
# ---------------------------------------------------------------------------

from pydantic import BaseModel

# --- 注册请求体 ---
class Reg_Req(BaseModel):
    username: str        # 用户名
    password: str        # 密码（明文传输，服务端加密存储）
    nickname: str        # 显示昵称

# =============================================================================
# 用户系统：注册
# POST /register-request
#
# 流程：
#   1. 校验用户名、昵称、密码非空
#   2. 检查用户名是否已被占用
#   3. 用 bcrypt 对密码加盐哈希
#   4. 插入用户记录
#   5. 生成 64 位随机 token 作为登录凭证
#   6. 返回 cookie
# =============================================================================

@app.post("/register-request")
def reg_req(body: Reg_Req):
    # 参数校验
    if not body.username:
        return {"error": "Bad username."}
    if not body.nickname:
        return {"error": "Bad nickname."}
    if not body.password:
        return {"error": "Bad password."}

    # 检查用户名是否已存在
    existing = cursor.execute(
        "SELECT id FROM users WHERE username = ?",
        (body.username,)
    ).fetchone()
    if existing:
        return {"error": "Username occupied."}

    # bcrypt 加密密码：hashpw(密码.encode(), gensalt())
    password_hash = bcrypt.hashpw(
        body.password.encode(), bcrypt.gensalt()
    ).decode()

    # 插入用户
    cursor.execute(
        "INSERT INTO users (username, nickname, password_hash) VALUES (?, ?, ?)",
        (body.username, body.nickname, password_hash)
    )
    user_id = cursor.lastrowid  # 获取自增生成的用户ID

    # 生成 64 位十六进制随机令牌（共 32 字节）
    cookie = secrets.token_hex(32)

    # 创建登录会话，过期时间设为 2099 年（实际永不过期）
    cursor.execute(
        "INSERT INTO cookies (user_id, token, expires_at) VALUES (?, ?, ?)",
        (user_id, cookie, "2099-12-31 13:59:59")
    )
    conn.commit()
    return {"cookie": cookie}


# --- 登录请求体 ---
class Log_Req(BaseModel):
    username: str
    password: str

# =============================================================================
# 用户系统：登录
# POST /login-request
#
# 流程：
#   1. 通过用户名查找用户
#   2. 用 bcrypt.checkpw 验证密码
#   3. 签发新 token，返回给客户端
# =============================================================================

@app.post("/login-request")
def log_req(body: Log_Req):
    if not body.username:
        return {"error": "Bad username."}
    if not body.password:
        return {"error": "Bad password."}

    # 查询用户
    log = cursor.execute(
        "SELECT * FROM users WHERE username = ?",
        (body.username,)
    ).fetchone()
    if not log:
        return {"error": "User not exist."}

    # bcrypt 密码验证：checkpw(输入密码.encode(), 存储的哈希.encode())
    if not bcrypt.checkpw(
        body.password.encode(), log["password_hash"].encode()
    ):
        return {"error": "Incorrect password."}

    # 签发新 token
    cookie = secrets.token_hex(32)
    cursor.execute(
        "INSERT INTO cookies (user_id, token, expires_at) VALUES (?, ?, ?)",
        (log["id"], cookie, "2099-12-31 13:59:59")
    )
    conn.commit()
    return {"cookie": cookie}


# --- 获取关注列表请求体 ---
class Get_Follower(BaseModel):
    cookie: str

# =============================================================================
# 社交系统：获取关注列表
# POST /get-follow-list
#
# 返回两类数据：
#   followers：谁关注了我（我的粉丝）
#   followees：我关注了谁
# =============================================================================

@app.post("/get-follow-list")
def get_follow_list(body: Get_Follower):
    # 验证 cookie，获取当前用户ID
    log = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not log:
        return {"error": "Bad cookie."}
    user_id = log["user_id"]

    # 查询粉丝列表（followee 是我，follower 是关注我的人）
    cursor.execute(
        """
        SELECT u.id, u.username, u.nickname
        FROM following f
        JOIN users u ON u.id == f.follower
        WHERE f.followee == ?
        """,
        (user_id,)
    )
    followers = [dict(row) for row in cursor.fetchall()]

    # 查询我关注的人（follower 是我，followee 是我关注的人）
    cursor.execute(
        """
        SELECT u.id, u.username, u.nickname
        FROM following f
        JOIN users u ON u.id == f.followee
        WHERE f.follower == ?
        """,
        (user_id,)
    )
    followees = [dict(now) for now in cursor.fetchall()]

    return {
        "followers": followers,
        "followees": followees
    }


# --- 关注/取关请求体 ---
class Follow_Req(BaseModel):
    cookie: str
    followee_id: int     # 要关注（或取关）的用户ID

# =============================================================================
# 社交系统：关注用户
# POST /follow
#
# 使用 INSERT OR IGNORE 保证幂等性（重复关注不会报错）
# =============================================================================

@app.post("/follow")
def follow(body: Follow_Req):
    # 验证身份
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 不允许关注自己
    if user_id == body.followee_id:
        return {"error": "Cannot follow yourself."}

    # 检查目标用户是否存在
    target = cursor.execute(
        "SELECT id FROM users WHERE id = ?",
        (body.followee_id,)
    ).fetchone()
    if not target:
        return {"error": "User not exist."}

    # INSERT OR IGNORE：如果已存在则忽略，保证幂等
    cursor.execute(
        "INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)",
        (user_id, body.followee_id)
    )
    conn.commit()
    return {"status": "success"}


# =============================================================================
# 社交系统：取关用户
# POST /unfollow
# =============================================================================

@app.post("/unfollow")
def unfollow(body: Follow_Req):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 直接删除关注关系，即使不存在也不会报错
    cursor.execute(
        "DELETE FROM following WHERE follower = ? AND followee = ?",
        (user_id, body.followee_id)
    )
    conn.commit()
    return {"status": "success"}


# --- 点赞请求体 ---
class Like_Req(BaseModel):
    cookie: str
    post_id: int

# =============================================================================
# 互动系统：点赞
# POST /like
#
# 使用 INSERT OR IGNORE 保证不重复点赞。
# 仅在确实新增了点赞记录时才更新 like_num（通过 cursor.rowcount 判断）
# =============================================================================

@app.post("/like")
def like(body: Like_Req):
    # 验证身份
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 检查帖子是否存在
    post = cursor.execute(
        "SELECT id FROM posts WHERE id = ?",
        (body.post_id,)
    ).fetchone()
    if not post:
        return {"error": "Post not exist."}

    # 尝试插入点赞记录
    cursor.execute(
        "INSERT OR IGNORE INTO liking_users (post_id, liker_id) VALUES (?, ?)",
        (body.post_id, user_id)
    )

    # rowcount > 0 表示真的新增了（之前没点过赞），才增加计数
    if cursor.rowcount > 0:
        cursor.execute(
            "UPDATE posts SET like_num = like_num + 1 WHERE id = ?",
            (body.post_id,)
        )
    conn.commit()
    return {"status": "success"}


# =============================================================================
# 互动系统：取消点赞
# POST /unlike
# =============================================================================

@app.post("/unlike")
def unlike(body: Like_Req):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 删除点赞记录
    cursor.execute(
        "DELETE FROM liking_users WHERE post_id = ? AND liker_id = ?",
        (body.post_id, user_id)
    )

    # 只有确实删除了记录才减少计数
    if cursor.rowcount > 0:
        cursor.execute(
            "UPDATE posts SET like_num = like_num - 1 WHERE id = ?",
            (body.post_id,)
        )
    conn.commit()
    return {"status": "success"}


# --- 评论请求体 ---
class Comment_Req(BaseModel):
    cookie: str
    post_id: int
    content: str

# =============================================================================
# 互动系统：发表评论
# POST /comment
# =============================================================================

@app.post("/comment")
def comment(body: Comment_Req):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 不允许空评论
    if not body.content:
        return {"error": "Empty comment not allowed."}

    # 检查帖子是否存在
    post = cursor.execute(
        "SELECT id FROM posts WHERE id = ?",
        (body.post_id,)
    ).fetchone()
    if not post:
        return {"error": "Post not exist."}

    cursor.execute(
        "INSERT INTO comments (post_id, commenter_id, content) VALUES (?, ?, ?)",
        (body.post_id, user_id, body.content)
    )
    conn.commit()
    return {"status": "success"}


# --- 获取评论请求体 ---
class Get_Comments_Req(BaseModel):
    cookie: str
    post_id: int

# =============================================================================
# 互动系统：获取帖子的评论列表
# POST /get-comments
#
# 按时间升序排列，带回评论者信息（用户名、昵称）
# =============================================================================

@app.post("/get-comments")
def get_comments(body: Get_Comments_Req):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}

    # 联表查询评论 + 用户信息，按时间从早到晚排列
    cursor.execute(
        """
        SELECT c.id, u.username, u.nickname, c.content, c.commented_at
        FROM comments c
        JOIN users u ON u.id = c.commenter_id
        WHERE c.post_id = ?
        ORDER BY c.commented_at ASC
        """,
        (body.post_id,)
    )
    return {"comments": [dict(r) for r in cursor.fetchall()]}


# --- 发送私信请求体 ---
class Send_Msg(BaseModel):
    cookie: str
    to_whom_id: int      # 接收者用户ID
    content: str

# =============================================================================
# 私信系统：发送离线消息
# POST /send-msg
#
# 消息写入数据库，等接收者主动拉取后删除（阅后即焚）
# =============================================================================

@app.post("/send-msg")
def send_msg(body: Send_Msg):
    user_id = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not user_id:
        return {"error": "Bad cookie."}
    user_id = user_id["user_id"]

    # 验证接收者存在
    existence = cursor.execute(
        "SELECT id FROM users WHERE id = ?",
        (body.to_whom_id,)
    ).fetchone()
    if not existence:
        return {"error": "Bad `to_whom_id`"}

    cursor.execute(
        "INSERT INTO offline_messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
        (user_id, body.to_whom_id, body.content,)
    )
    conn.commit()
    return {"status": "success"}


# --- 接收私信请求体 ---
class Recv_Msg(BaseModel):
    cookie: str

# =============================================================================
# 私信系统：接收离线消息
# POST /recv-msg
#
# 拉取所有发给当前用户的未读消息，然后立即删除（阅后即焚）
# =============================================================================

@app.post("/recv-msg")
def recv_msg(body: Recv_Msg):
    user_id = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not user_id:
        return {"error": "Bad cookie."}
    user_id = user_id["user_id"]

    # 查询所有未读私信（发送者、时间、内容）
    cursor.execute(
        "SELECT sender_id, sent_at, content FROM offline_messages WHERE receiver_id = ?",
        (user_id,)
    )
    msgs = [dict(row) for row in cursor.fetchall()]

    # 删除已读取的消息（阅后即焚）
    cursor.execute(
        "DELETE FROM offline_messages WHERE receiver_id = ?",
        (user_id,)
    )
    conn.commit()
    return {"msgs": msgs}


# --- 发帖请求体 ---
class Pub_Post(BaseModel):
    cookie: str
    text: str                        # 文字内容
    media: list[str] = []           # 媒体列表（默认空），每项是Base64编码的数据

# =============================================================================
# 帖子系统：发布帖子
# POST /pub-post
#
# 约束：
#   - 文字和媒体至少有一个非空
#   - 媒体最多 9 个
#   - 单个媒体最大 16MiB（1 << 24 = 16777216 字节）
# =============================================================================

@app.post("/pub-post")
def pub_post(body: Pub_Post):
    user_id = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not user_id:
        return {"error": "Bad cookie."}
    user_id = user_id["user_id"]

    # 文字和媒体不能同时为空
    if (not body.text) and (not body.media):
        return {"error": "Empty post not allowed."}

    # 媒体数量限制
    if len(body.media) > 9:
        return {"error": "Too many media."}

    # 单个媒体大小限制 16MiB
    for medium in body.media:
        if len(medium) > (1 << 24):  # 1 << 24 = 16,777,216
            return {"error": "Media cannot be larger than 16MiB."}

    # 插入帖子
    cursor.execute(
        "INSERT INTO posts (publisher_id, content) VALUES (?, ?)",
        (user_id, body.text)
    )
    conn.commit()
    post_id = cursor.lastrowid

    # 逐个插入媒体附件（offset 从 0 开始编号）
    for i in range(len(body.media)):
        cursor.execute(
            "INSERT INTO post_media (post_id, offset, content) VALUES (?, ?, ?)",
            (post_id, i, body.media[i],)
        )
    conn.commit()
    return {"status": "success"}


# --- 拉取帖子流请求体 ---
class Post_Fetch(BaseModel):
    cookie: str
    count: int = 20                 # 每次拉取的帖子数量，默认20条

# =============================================================================
# 帖子系统：推荐流（核心算法）
# POST /post-fetch
#
# 推荐策略（三路合并 + 去重 + 随机化）：
#   1. 关注流：我关注的人发的帖子
#   2. 热门流：点赞数 > 0 的帖子，按点赞降序取前50
#   3. 最新流：全部帖子按时间降序取前50
#   4. 排除已读（已读记录存在 read_posts 表）
#   5. 三路按顺序合并后 random.shuffle 随机打乱
#   6. 截取前 count 条，将这些帖子的 ID 返回
#   7. 将返回的帖子标记为已读
# =============================================================================

@app.post("/post-fetch")
def post_fetch(body: Post_Fetch):
    # 验证身份
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 1. 关注的人发的帖子
    followed = cursor.execute("""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        WHERE p.publisher_id IN (
            SELECT followee FROM following WHERE follower = ?
        )
    """, (user_id,)).fetchall()

    # 2. 最火的帖子（点赞数 > 0，按赞数降序，最多 50 条）
    hot = cursor.execute("""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        WHERE p.like_num > 0
        ORDER BY p.like_num DESC LIMIT 50
    """).fetchall()

    # 3. 最新的帖子（按时间降序，最多 50 条）
    recent = cursor.execute("""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        ORDER BY p.created_at DESC LIMIT 50
    """).fetchall()

    # 4. 获取已读帖子 ID 集合
    seen = set()
    for r in cursor.execute(
        "SELECT post_id FROM read_posts WHERE user_id = ?", (user_id,)
    ):
        seen.add(r["post_id"])

    # 5. 三路合并去重：按 关注 → 热门 → 最新 顺序，后出现的自动跳过
    combined = []
    for post in followed + hot + recent:
        if post["id"] not in seen:
            seen.add(post["id"])
            combined.append(dict(post))

    # 6. 随机打乱，增加信息流的多样性
    random.shuffle(combined)

    # 7. 截取前 count 条
    result = combined[:body.count]

    # 8. 标记为已读（下次不再出现）
    for post in result:
        cursor.execute(
            "INSERT OR IGNORE INTO read_posts (user_id, post_id) VALUES (?, ?)",
            (user_id, post["id"])
        )
    conn.commit()

    # 只返回帖子 ID 列表（客户端再按需调用 /get-post 获取详情）
    return {"posts": [p["id"] for p in result], "count": len(result)}


# --- 获取单个帖子请求体 ---
class Get_Post(BaseModel):
    cookie: str
    post_id: int

# =============================================================================
# 帖子系统：获取帖子详情
# POST /get-post
#
# 返回帖子正文、发布者信息、点赞数、发布时间以及媒体附件列表
# =============================================================================

@app.post("/get-post")
def get_post(body: Get_Post):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}

    # 联表查询帖子 + 发布者信息
    post = cursor.execute(
        """
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        WHERE p.id = ?
        """,
        (body.post_id,)
    ).fetchone()
    if not post:
        return {"error": "Post not found."}

    # 查询帖子的媒体附件（按 offset 排序）
    media = cursor.execute(
        "SELECT offset, content FROM post_media WHERE post_id = ? ORDER BY offset",
        (body.post_id,)
    ).fetchall()

    return {
        "id": post["id"],
        "publisher_id": post["publisher_id"],
        "username": post["username"],
        "nickname": post["nickname"],
        "content": post["content"],
        "like_num": post["like_num"],
        "created_at": post["created_at"],
        "media": [dict(m) for m in media]
    }


# --- 创建群组请求体 ---
class Create_Group_Req(BaseModel):
    cookie: str
    name: str

# =============================================================================
# 群组系统：创建群组
# POST /create-group
#
# 创建者自动成为群主（role = 'owner'）
# =============================================================================

@app.post("/create-group")
def create_group(body: Create_Group_Req):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    if not body.name:
        return {"error": "Group name cannot be empty."}
    user_id = row["user_id"]

    # 创建群组
    cursor.execute(
        "INSERT INTO groups (name, owner_id) VALUES (?, ?)",
        (body.name, user_id)
    )
    group_id = cursor.lastrowid

    # 创建者自动加入，角色为 owner
    cursor.execute(
        "INSERT INTO user_in_group (group_id, user_id, role) VALUES (?, ?, ?)",
        (group_id, user_id, "owner")
    )
    conn.commit()
    return {"group_id": group_id}


# --- 加入群组请求体 ---
class Join_Group_Req(BaseModel):
    cookie: str
    group_id: int

# =============================================================================
# 群组系统：加入群组
# POST /join-group
#
# 使用 INSERT OR IGNORE 保证幂等，不限制加入权限（开放群组）
# =============================================================================

@app.post("/join-group")
def join_group(body: Join_Group_Req):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 检查群是否存在
    group = cursor.execute(
        "SELECT id FROM groups WHERE id = ?",
        (body.group_id,)
    ).fetchone()
    if not group:
        return {"error": "Group not exist."}

    cursor.execute(
        "INSERT OR IGNORE INTO user_in_group (group_id, user_id) VALUES (?, ?)",
        (body.group_id, user_id)
    )
    conn.commit()
    return {"status": "success"}


# --- 退出群组请求体 ---
class Leave_Group_Req(BaseModel):
    cookie: str
    group_id: int

# =============================================================================
# 群组系统：退出群组
# POST /leave-group
#
# 直接删除成员记录，owner 也可以退出（会导致群无主）
# =============================================================================

@app.post("/leave-group")
def leave_group(body: Leave_Group_Req):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    cursor.execute(
        "DELETE FROM user_in_group WHERE group_id = ? AND user_id = ?",
        (body.group_id, user_id)
    )
    conn.commit()
    return {"status": "success"}


# --- 发送群消息请求体 ---
class Send_Group_Msg_Req(BaseModel):
    cookie: str
    group_id: int
    content: str

# =============================================================================
# 群组系统：发送群消息
# POST /send-group-msg
#
# 需要先验证用户确实在该群内
# =============================================================================

@app.post("/send-group-msg")
def send_group_msg(body: Send_Group_Msg_Req):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 验证群成员身份
    in_group = cursor.execute(
        "SELECT role FROM user_in_group WHERE group_id = ? AND user_id = ?",
        (body.group_id, user_id)
    ).fetchone()
    if not in_group:
        return {"error": "You are not in this group."}
    if not body.content:
        return {"error": "Empty message not allowed."}

    cursor.execute(
        "INSERT INTO group_messages (group_id, sender_id, content) VALUES (?, ?, ?)",
        (body.group_id, user_id, body.content)
    )
    conn.commit()
    return {"status": "success"}


# --- 接收群消息请求体 ---
class Recv_Group_Msg_Req(BaseModel):
    cookie: str
    group_id: int
    count: int = 20                  # 每次拉取的最大消息数

# =============================================================================
# 群组系统：接收群消息（增量拉取）
# POST /recv-group-msg
#
# 基于游标（last_read_id）实现增量拉取：
#   - 只拉取 id > last_read_id 的消息
#   - 拉取完成后更新 last_read_id 为最新消息的 id
#   - 这样每个用户可以独立跟踪自己的阅读进度
# =============================================================================

@app.post("/recv-group-msg")
def recv_group_msg(body: Recv_Group_Msg_Req):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 获取成员信息和 last_read_id 游标
    membership = cursor.execute(
        "SELECT last_read_id FROM user_in_group WHERE group_id = ? AND user_id = ?",
        (body.group_id, user_id)
    ).fetchone()
    if not membership:
        return {"error": "You are not in this group."}

    # 增量拉取：只取 id > last_read_id 的消息
    messages = cursor.execute("""
        SELECT gm.id, gm.sender_id, u.username, u.nickname, gm.content, gm.sent_at
        FROM group_messages gm
        JOIN users u ON u.id = gm.sender_id
        WHERE gm.group_id = ? AND gm.id > ?
        ORDER BY gm.id ASC
        LIMIT ?
    """, (body.group_id, membership["last_read_id"], body.count)).fetchall()

    # 更新阅读游标到最后一条已读消息的 id
    if messages:
        cursor.execute(
            "UPDATE user_in_group SET last_read_id = ? WHERE group_id = ? AND user_id = ?",
            (messages[-1]["id"], body.group_id, user_id)
        )
        conn.commit()

    return {"messages": [dict(m) for m in messages]}


# --- 获取群成员请求体 ---
class Get_Group_Members_Req(BaseModel):
    cookie: str
    group_id: int

# =============================================================================
# 群组系统：获取群成员列表
# POST /get-group-members
#
# 返回成员的用户名、昵称、角色、加入时间
# =============================================================================

@app.post("/get-group-members")
def get_group_members(body: Get_Group_Members_Req):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}

    members = cursor.execute("""
        SELECT u.id, u.username, u.nickname, ug.role, ug.joined_at
        FROM user_in_group ug
        JOIN users u ON u.id = ug.user_id
        WHERE ug.group_id = ?
        ORDER BY ug.joined_at ASC
    """, (body.group_id,)).fetchall()

    return {"members": [dict(m) for m in members]}


# --- 获取我的群组列表请求体 ---
class Get_My_Groups_Req(BaseModel):
    cookie: str

# =============================================================================
# 群组系统：获取我加入的群组列表
# POST /get-my-groups
#
# 返回群信息 + 我在该群的角色 + 加入时间
# =============================================================================

@app.post("/get-my-groups")
def get_my_groups(body: Get_My_Groups_Req):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    groups = cursor.execute("""
        SELECT g.id, g.name, g.owner_id, ug.role, ug.joined_at
        FROM user_in_group ug
        JOIN groups g ON g.id = ug.group_id
        WHERE ug.user_id = ?
        ORDER BY ug.joined_at DESC
    """, (user_id,)).fetchall()

    return {"groups": [dict(g) for g in groups]}


# --- 登出请求体 ---
class Logout_Req(BaseModel):
    cookie: str

# =============================================================================
# 用户系统：登出
# POST /logout
#
# 直接删除 cookies 表中对应的 token 记录，使其立即失效。
# 即使 token 不存在也不会报错（客户端可能重复调用）。
# =============================================================================

@app.post("/logout")
def logout(body: Logout_Req):
    cursor.execute(
        "DELETE FROM cookies WHERE token = ?",
        (body.cookie,)
    )
    conn.commit()
    return {"status": "success"}


# --- 删除帖子请求体 ---
class Del_Post_Req(BaseModel):
    cookie: str
    post_id: int      # 要删除的帖子ID

# =============================================================================
# 帖子系统：删除帖子
# POST /delete-post
#
# 权限校验：
#   - 仅帖子发布者本人可以删除
#
# 级联清理（手动删除所有关联数据）：
#   1. liking_users   — 该帖子的所有点赞记录
#   2. comments       — 该帖子的所有评论
#   3. post_media     — 该帖子的所有媒体附件
#   4. read_posts     — 该帖子的所有已读记录
#   5. posts          — 帖子本身
# =============================================================================

@app.post("/delete-post")
def delete_post(body: Del_Post_Req):
    # 验证身份
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 检查帖子是否存在，并获取发布者ID
    post = cursor.execute(
        "SELECT publisher_id FROM posts WHERE id = ?",
        (body.post_id,)
    ).fetchone()
    if not post:
        return {"error": "Post not exist."}

    # 仅允许发布者本人删除
    if post["publisher_id"] != user_id:
        return {"error": "Not your post."}

    # 级联清理关联数据（SQLite 默认不启用外键约束，需手动清理）
    cursor.execute("DELETE FROM liking_users WHERE post_id = ?", (body.post_id,))
    cursor.execute("DELETE FROM comments WHERE post_id = ?", (body.post_id,))
    cursor.execute("DELETE FROM post_media WHERE post_id = ?", (body.post_id,))
    cursor.execute("DELETE FROM read_posts WHERE post_id = ?", (body.post_id,))
    cursor.execute("DELETE FROM posts WHERE id = ?", (body.post_id,))
    conn.commit()
    return {"status": "success"}


# --- 删除评论请求体 ---
class Del_Comment_Req(BaseModel):
    cookie: str
    comment_id: int   # 要删除的评论ID

# =============================================================================
# 互动系统：删除评论
# POST /delete-comment
#
# 权限校验：
#   - 仅评论者本人可以删除自己的评论
# =============================================================================

@app.post("/delete-comment")
def delete_comment(body: Del_Comment_Req):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 检查评论是否存在，并获取评论者ID
    comment = cursor.execute(
        "SELECT commenter_id FROM comments WHERE id = ?",
        (body.comment_id,)
    ).fetchone()
    if not comment:
        return {"error": "Comment not exist."}

    # 仅允许评论者本人删除
    if comment["commenter_id"] != user_id:
        return {"error": "Not your comment."}

    cursor.execute(
        "DELETE FROM comments WHERE id = ?",
        (body.comment_id,)
    )
    conn.commit()
    return {"status": "success"}


# --- 编辑资料请求体 ---
class Edit_Profile_Req(BaseModel):
    cookie: str
    nickname: str = ""          # 新昵称（可选，不传则不修改）
    email_address: str = ""     # 新邮箱（可选，不传则不修改）

# =============================================================================
# 用户系统：编辑个人资料
# POST /edit-profile
#
# 设计说明：
#   - nickname 和 email_address 都是可选的，只更新传入的非空字段
#   - 不允许修改 username（用户名是唯一标识）
#   - 不支持修改密码（需要单独的安全流程，如旧密码验证）
# =============================================================================

@app.post("/edit-profile")
def edit_profile(body: Edit_Profile_Req):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 仅更新传入的非空字段
    if body.nickname:
        cursor.execute(
            "UPDATE users SET nickname = ? WHERE id = ?",
            (body.nickname, user_id)
        )
    if body.email_address:
        cursor.execute(
            "UPDATE users SET email_address = ? WHERE id = ?",
            (body.email_address, user_id)
        )
    conn.commit()
    return {"status": "success"}


# =============================================================================
# 第三部分：服务启动
# =============================================================================

if __name__ == "__main__":
    # 使用 uvicorn 启动 FastAPI 服务，监听 18999 端口
    # 注：原代码有两行重复的 uvicorn.run，第二行实际上不会执行
    uvicorn.run(app, port=18999)
