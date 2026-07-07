#!/usr/bin/env -S uv run python3
# Tiny Blog - 微微博最小可用后端主文件
# Copyright (c) 2026 Becharm Kon. All Rights Reserved.

# Databases

import sqlite3, bcrypt, secrets, threading, base64, re

conn = sqlite3.connect("main.db", check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")

# 线程锁：保护所有数据库操作，防止并发读同一连接导致段错误
db_lock = threading.Lock()
_thread_local = threading.local()  # 线程本地存储，防止 lastrowid/rowcount 跨线程串扰

# 用 conn.execute() 替代全局 cursor，每次获取新游标，线程安全

def db_execute(sql, params=()):
    with db_lock:
        cur = conn.execute(sql, params)
        _thread_local.lastrowid = cur.lastrowid
        _thread_local.rowcount = cur.rowcount
        return cur

def db_fetchone(sql, params=()):
    with db_lock:
        return conn.execute(sql, params).fetchone()

def db_fetchall(sql, params=()):
    with db_lock:
        return conn.execute(sql, params).fetchall()

def db_commit():
    with db_lock:
        conn.commit()

def db_lastrowid():
    return getattr(_thread_local, 'lastrowid', -1)

def db_rowcount():
    return getattr(_thread_local, 'rowcount', 0)

# ─── 工具函数 ───────────────────────────────────────────

def extract_hashtags(text: str) -> list[str]:
    """从文本中提取去重的 #标签，支持中文标签"""
    if not text:
        return []
    tags = re.findall(r'#([\w\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+)', text)
    return list(dict.fromkeys(tags))  # 保持顺序去重

if __name__ == "__main__":
    db_execute("""
                   CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    nickname TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    email_address TEXT NOT NULL DEFAULT ''
                   )
                   """)
    db_execute("""
                   CREATE TABLE IF NOT EXISTS cookies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                   )
                   """)
    db_execute("""
                   CREATE TABLE IF NOT EXISTS following (
                    follower INTEGER NOT NULL,
                    followee INTEGER NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    PRIMARY KEY (follower, followee),
                    FOREIGN KEY (follower) REFERENCES users(id),
                    FOREIGN KEY (followee) REFERENCES users(id)
                   )
                   """)
    db_execute("""
                   CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    publisher_id INTEGER NOT NULL,
                    content TEXT,
                    like_num INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (publisher_id) REFERENCES users(id)
                   )
                   """)
    db_execute("""
                   CREATE TABLE IF NOT EXISTS liking_users (
                    post_id INTEGER NOT NULL,
                    liker_id INTEGER NOT NULL,
                    liked_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (liker_id) REFERENCES users(id),
                    FOREIGN KEY (post_id) REFERENCES posts(id)
                   )
                   """)
    db_execute("""
                   CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    commenter_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    commented_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (post_id) REFERENCES posts(id),
                    FOREIGN KEY (commenter_id) REFERENCES users(id)
                   )
                   """)
    db_execute("""
                   CREATE TABLE IF NOT EXISTS offline_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    sent_at TEXT NOT NULL DEFAULT (datetime('now')),
                    content TEXT NOT NULL,
                    FOREIGN KEY (sender_id) REFERENCES users(id),
                    FOREIGN KEY (receiver_id) REFERENCES users(id)
                   )
                   """)
    db_execute("""
                   CREATE TABLE IF NOT EXISTS post_media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    offset INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    FOREIGN KEY (post_id) REFERENCES posts(id)
                   )
                   """)
    db_execute(
"""
    CREATE TABLE IF NOT EXISTS read_posts (
        user_id INTEGER NOT NULL,
        post_id INTEGER NOT NULL,
        read_at TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (user_id, post_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (post_id) REFERENCES posts(id)
    );
"""
            )
    db_execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            owner_id INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
    """)
    db_execute("""
        CREATE TABLE IF NOT EXISTS user_in_group (
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            joined_at TEXT DEFAULT (datetime('now')),
            last_read_id INTEGER DEFAULT 0,
            PRIMARY KEY (group_id, user_id),
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    db_execute("""
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
    # 向后兼容：新增字段（已有数据库不会自动加列）
    for col in ["avatar", "signature"]:
        try:
            db_execute(f"ALTER TABLE users ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # 列已存在
    # 为旧数据库补加 repost_id 列
    try:
        db_execute("ALTER TABLE posts ADD COLUMN repost_id INTEGER DEFAULT NULL")
    except sqlite3.OperationalError:
        pass
    # 为旧数据库补加 offline_messages.is_read 列（持久化私信）
    try:
        db_execute("ALTER TABLE offline_messages ADD COLUMN is_read INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    db_execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            bookmarked_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)
    db_execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            from_user_id INTEGER NOT NULL,
            post_id INTEGER DEFAULT NULL,
            comment_id INTEGER DEFAULT NULL,
            content TEXT NOT NULL DEFAULT '',
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (from_user_id) REFERENCES users(id),
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (comment_id) REFERENCES comments(id)
        )
    """)
    # ─── P2 新增表 ────────────────────────────────────────
    db_execute("""
        CREATE TABLE IF NOT EXISTS blocks (
            blocker_id INTEGER NOT NULL,
            blocked_id INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (blocker_id, blocked_id),
            FOREIGN KEY (blocker_id) REFERENCES users(id),
            FOREIGN KEY (blocked_id) REFERENCES users(id)
        )
    """)
    db_execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER NOT NULL,
            target_type TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (reporter_id) REFERENCES users(id)
        )
    """)
    db_execute("""
        CREATE TABLE IF NOT EXISTS hashtags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    db_execute("""
        CREATE TABLE IF NOT EXISTS post_hashtags (
            post_id INTEGER NOT NULL,
            hashtag_id INTEGER NOT NULL,
            PRIMARY KEY (post_id, hashtag_id),
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (hashtag_id) REFERENCES hashtags(id)
        )
    """)
    # 为旧数据库补加 visibility 列
    try:
        db_execute("ALTER TABLE posts ADD COLUMN visibility TEXT NOT NULL DEFAULT 'public'")
    except sqlite3.OperationalError:
        pass
    db_commit()

# Server Functions

import fastapi, uvicorn, random

app = fastapi.FastAPI(title = "Tiny Blog")

@app.get("/ping") # For testing only
def ping():
    return {"message": "Pong!"}

from pydantic import BaseModel

class Reg_Req(BaseModel):
    username: str
    password: str
    nickname: str

@app.post("/register-request")
def reg_req(body: Reg_Req):
    if not body.username:
        return {"error": "Bad username."}
    if not body.nickname:
        return {"error": "Bad nickname."}
    if not body.password:
        return {"error": "Bad password."}
    existing = db_fetchone(
            "SELECT id FROM users WHERE username = ?",
            (body.username,)
            )
    if existing:
        return {"error": "Username occupied."}
    password_hash = bcrypt.hashpw(
            body.password.encode(), bcrypt.gensalt()
            ).decode()
    db_execute("INSERT INTO users (username, nickname, password_hash) VALUES (?, ?, ?)",
            (body.username, body.nickname, password_hash)
            )
    user_id = db_lastrowid()
    cookie = secrets.token_hex(32)
    db_execute(
            "INSERT INTO cookies (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user_id, cookie, "2099-12-31 13:59:59")
            )
    db_commit()
    return {"cookie": cookie}

class Log_Req(BaseModel):
    username: str
    password: str

@app.post("/login-request")
def log_req(body: Log_Req):
    if not body.username:
        return {"error": "Bad username."}
    if not body.password:
        return {"error": "Bad password."}
    log = db_fetchone(
            "SELECT * FROM users WHERE username = ?",
            (body.username,)
            )
    if not log:
        return {"error": "User not exist."}
    if not bcrypt.checkpw(
            body.password.encode(), log["password_hash"].encode()
            ):
        return {"error": "Incorrect password."}
    cookie = secrets.token_hex(32)
    db_execute("INSERT INTO cookies (user_id, token, expires_at) VALUES (?, ?, ?)",
            (log["id"], cookie, "2099-12-31 13:59:59")
            )
    db_commit()
    return {"cookie": cookie}

class Get_Follower(BaseModel):
    cookie: str

@app.post("/get-follow-list")
def get_follow_list(body: Get_Follower):
    log = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not log:
        return {"error": "Bad cookie."}
    user_id = log["user_id"]
    followers = [dict(row) for row in db_fetchall(
            """
            SELECT u.id, u.username, u.nickname, u.avatar, u.signature
            FROM following f
            JOIN users u ON u.id == f.follower
            WHERE f.followee == ?
            """,
            (user_id,)
            )]
    followees = [dict(now) for now in db_fetchall(
            """
            SELECT u.id, u.username, u.nickname, u.avatar, u.signature
            FROM following f
            JOIN users u ON u.id == f.followee
            WHERE f.follower == ?
            """,
            (user_id,)
            )]
    return {
            "followers": followers,
            "followees": followees
            }

class Follow_Req(BaseModel):
    cookie: str
    followee_id: int

@app.post("/follow")
def follow(body: Follow_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    if user_id == body.followee_id:
        return {"error": "Cannot follow yourself."}
    target = db_fetchone(
            "SELECT id FROM users WHERE id = ?",
            (body.followee_id,)
            )
    if not target:
        return {"error": "User not exist."}
    db_execute("INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)",
            (user_id, body.followee_id)
            )
    if db_rowcount() > 0:
        db_execute(
                "INSERT INTO notifications (user_id, type, from_user_id, content) VALUES (?, 'follow', ?, '')",
                (body.followee_id, user_id)
                )
    db_commit()
    return {"status": "success"}

@app.post("/unfollow")
def unfollow(body: Follow_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    db_execute("DELETE FROM following WHERE follower = ? AND followee = ?",
            (user_id, body.followee_id)
            )
    db_commit()
    return {"status": "success"}

class Like_Req(BaseModel):
    cookie: str
    post_id: int

@app.post("/like")
def like(body: Like_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    post = db_fetchone(
            "SELECT id FROM posts WHERE id = ?",
            (body.post_id,)
            )
    if not post:
        return {"error": "Post not exist."}
    db_execute("INSERT OR IGNORE INTO liking_users (post_id, liker_id) VALUES (?, ?)",
            (body.post_id, user_id)
            )
    if db_rowcount() > 0:
        db_execute(
                "UPDATE posts SET like_num = like_num + 1 WHERE id = ?",
                (body.post_id,)
                )
        post_owner = db_fetchone(
                "SELECT publisher_id FROM posts WHERE id = ?",
                (body.post_id,)
                )
        if post_owner and post_owner["publisher_id"] != user_id:
            db_execute(
                    "INSERT INTO notifications (user_id, type, from_user_id, post_id, content) VALUES (?, 'like', ?, ?, '')",
                    (post_owner["publisher_id"], user_id, body.post_id)
                    )
    db_commit()
    return {"status": "success"}

@app.post("/unlike")
def unlike(body: Like_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    db_execute("DELETE FROM liking_users WHERE post_id = ? AND liker_id = ?",
            (body.post_id, user_id)
            )
    if db_rowcount() > 0:
        db_execute(
                "UPDATE posts SET like_num = like_num - 1 WHERE id = ?",
                (body.post_id,)
                )
    db_commit()
    return {"status": "success"}

class Comment_Req(BaseModel):
    cookie: str
    post_id: int
    content: str

@app.post("/comment")
def comment(body: Comment_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    if not body.content:
        return {"error": "Empty comment not allowed."}
    post = db_fetchone(
            "SELECT id FROM posts WHERE id = ?",
            (body.post_id,)
            )
    if not post:
        return {"error": "Post not exist."}
    db_execute("INSERT INTO comments (post_id, commenter_id, content) VALUES (?, ?, ?)",
            (body.post_id, user_id, body.content)
            )
    comment_id = db_lastrowid()
    post_owner = db_fetchone(
            "SELECT publisher_id FROM posts WHERE id = ?",
            (body.post_id,)
            )
    if post_owner and post_owner["publisher_id"] != user_id:
        db_execute(
                "INSERT INTO notifications (user_id, type, from_user_id, post_id, comment_id, content) VALUES (?, 'comment', ?, ?, ?, ?)",
                (post_owner["publisher_id"], user_id, body.post_id, comment_id, body.content[:50])
                )
    db_commit()
    return {"status": "success"}

class Get_Comments_Req(BaseModel):
    cookie: str
    post_id: int

@app.post("/get-comments")
def get_comments(body: Get_Comments_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    return {"comments": [dict(r) for r in db_fetchall(
            """
            SELECT c.id, u.username, u.nickname, c.content, c.commented_at
            FROM comments c
            JOIN users u ON u.id = c.commenter_id
            WHERE c.post_id = ?
            ORDER BY c.commented_at ASC
            """,
            (body.post_id,)
            )]}

class Send_Msg(BaseModel):
    cookie: str
    to_whom_id: int
    content: str

@app.post("/send-msg")
def send_msg(body: Send_Msg):
    user_id = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not user_id:
        return {"error": "Bad cookie."}
    user_id = user_id["user_id"]
    if user_id == body.to_whom_id:
        return {"error": "Cannot send message to yourself."}
    existence = db_fetchone(
            "SELECT id FROM users WHERE id = ?",
            (body.to_whom_id,)
            )
    if not existence:
        return {"error": "Bad `to_whom_id`"}
    # 检查屏蔽关系
    blocked = db_fetchone(
            "SELECT 1 FROM blocks WHERE (blocker_id = ? AND blocked_id = ?) OR (blocker_id = ? AND blocked_id = ?)",
            (user_id, body.to_whom_id, body.to_whom_id, user_id)
            )
    if blocked:
        return {"error": "Cannot send message due to block relationship."}
    if not body.content:
        return {"error": "Empty message not allowed."}
    db_execute("INSERT INTO offline_messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
            (user_id, body.to_whom_id, body.content,)
            )
    db_execute(
            "INSERT INTO notifications (user_id, type, from_user_id, content) VALUES (?, 'message', ?, ?)",
            (body.to_whom_id, user_id, body.content[:50])
            )
    db_commit()
    return {"status": "success", "message_id": db_lastrowid()}

class Recv_Msg(BaseModel):
    cookie: str
    with_user_id: int = 0   # 0=获取所有未读消息摘要, >0=与该用户的聊天记录
    before_id: int = 0       # 游标分页
    count: int = 20

@app.post("/recv-msg")
def recv_msg(body: Recv_Msg):
    user_id = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not user_id:
        return {"error": "Bad cookie."}
    user_id = user_id["user_id"]

    if body.with_user_id > 0:
        # ── 与特定用户的聊天记录（游标分页，标记已读） ──
        if body.before_id > 0:
            msgs = db_fetchall("""
                SELECT m.id, m.sender_id, u.username, u.nickname, m.content, m.sent_at, m.is_read
                FROM offline_messages m
                JOIN users u ON u.id = m.sender_id
                WHERE ((m.sender_id = ? AND m.receiver_id = ?)
                    OR (m.sender_id = ? AND m.receiver_id = ?))
                  AND m.id < ?
                ORDER BY m.id DESC LIMIT ?
            """, (user_id, body.with_user_id, body.with_user_id, user_id, body.before_id, body.count))
        else:
            msgs = db_fetchall("""
                SELECT m.id, m.sender_id, u.username, u.nickname, m.content, m.sent_at, m.is_read
                FROM offline_messages m
                JOIN users u ON u.id = m.sender_id
                WHERE (m.sender_id = ? AND m.receiver_id = ?)
                   OR (m.sender_id = ? AND m.receiver_id = ?)
                ORDER BY m.id DESC LIMIT ?
            """, (user_id, body.with_user_id, body.with_user_id, user_id, body.count))
        # 标记对方发给我的消息为已读
        db_execute(
                "UPDATE offline_messages SET is_read = 1 WHERE receiver_id = ? AND sender_id = ? AND is_read = 0",
                (user_id, body.with_user_id)
                )
        db_commit()
        next_cursor = msgs[-1]["id"] if msgs else 0
        return {"messages": [dict(m) for m in msgs], "count": len(msgs), "next_cursor": next_cursor}
    else:
        # ── 无 with_user_id：拉取所有未读消息（用于通知角标） ──
        msgs = [dict(row) for row in db_fetchall("""
            SELECT m.id, m.sender_id, u.username, u.nickname, m.content, m.sent_at
            FROM offline_messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.receiver_id = ? AND m.is_read = 0
            ORDER BY m.id DESC
        """, (user_id,))]
        return {"messages": msgs, "count": len(msgs), "next_cursor": 0}

class Pub_Post(BaseModel):
    cookie: str
    text: str
    media: list[str] = []
    visibility: str = "public"  # public | followers_only | private

@app.post("/pub-post")
def pub_post(body: Pub_Post):
    user_id = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not user_id:
        return {"error": "Bad cookie."}
    user_id = user_id["user_id"]
    if (not body.text) and (not body.media):
        return {"error": "Empty post not allowed."}
    if len(body.media) > 9:
        return {"error": "Too many media."}
    if body.visibility not in ("public", "followers_only", "private"):
        return {"error": "Invalid visibility."}
    for medium in body.media:
        if len(medium) > (1 << 24):
            return {"error": "Media cannot be larger than 16MiB."}
    db_execute("INSERT INTO posts (publisher_id, content, visibility) VALUES (?, ?, ?)",
            (user_id, body.text, body.visibility)
            )
    db_commit()
    post_id = db_lastrowid()
    for i in range(len(body.media)):
        db_execute(
                "INSERT INTO post_media (post_id, offset, content) VALUES (?, ?, ?)",
                (post_id, i, body.media[i],)
                )
    # 提取并存储 #标签
    tags = extract_hashtags(body.text)
    for tag in tags:
        db_execute("INSERT OR IGNORE INTO hashtags (name) VALUES (?)", (tag,))
        db_commit()
        ht = db_fetchone("SELECT id FROM hashtags WHERE name = ?", (tag,))
        if ht:
            db_execute("INSERT OR IGNORE INTO post_hashtags (post_id, hashtag_id) VALUES (?, ?)",
                    (post_id, ht["id"]))
    db_commit()
    return {"status": "success", "post_id": post_id, "hashtags": tags}

class Post_Fetch(BaseModel):
    cookie: str
    count: int = 20
    before_id: int = 0

@app.post("/post-fetch")
def post_fetch(body: Post_Fetch):
    print(f"DEBUG post_fetch: cookie={repr(body.cookie)}, count={body.count}, before_id={body.before_id}", flush=True)
    row = db_fetchone(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    before_clause = ""
    before_param = ()
    if body.before_id > 0:
        before_clause = " AND p.id < ?"
        before_param = (body.before_id,)

    # 获取已屏蔽和被屏蔽的用户列表
    blocked_ids = set()
    for r in db_fetchall("SELECT blocked_id FROM blocks WHERE blocker_id = ?", (user_id,)):
        blocked_ids.add(r["blocked_id"])
    for r in db_fetchall("SELECT blocker_id FROM blocks WHERE blocked_id = ?", (user_id,)):
        blocked_ids.add(r["blocker_id"])

    block_filter = ""
    block_params = ()
    if blocked_ids:
        placeholders = ",".join("?" for _ in blocked_ids)
        block_filter = f" AND p.publisher_id NOT IN ({placeholders})"
        block_params = tuple(blocked_ids)

    # 可见性过滤：private 仅自己可见；followers_only 仅粉丝和本人可见
    vis_clause = """AND (
        p.visibility = 'public'
        OR p.publisher_id = ?
        OR (p.visibility = 'followers_only' AND p.publisher_id IN (
            SELECT followee FROM following WHERE follower = ?
        ))
    )"""

    # 1. 关注的人发的帖子
    followed = db_fetchall(f"""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        WHERE p.publisher_id IN (
            SELECT followee FROM following WHERE follower = ?
        ){before_clause}{block_filter}
        AND (p.visibility != 'private' OR p.publisher_id = ?)
    """, (user_id,) + before_param + block_params + (user_id,))

    # 2. 最火的帖子
    hot = db_fetchall(f"""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        WHERE p.like_num > 0{before_clause}{block_filter}
        {vis_clause}
        ORDER BY p.like_num DESC LIMIT 50
    """, before_param + block_params + (user_id, user_id))

    # 3. 最新的帖子
    recent = db_fetchall(f"""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        WHERE 1=1{before_clause}{block_filter}
        {vis_clause}
        ORDER BY p.created_at DESC LIMIT 50
    """, before_param + block_params + (user_id, user_id))

    # 排除已读
    seen = set()
    for r in db_fetchall(
        "SELECT post_id FROM read_posts WHERE user_id = ?", (user_id,)
    ):
        seen.add(r["post_id"])

    combined = []
    for post in followed + hot + recent:
        if post["id"] not in seen:
            seen.add(post["id"])
            combined.append(dict(post))

    if body.before_id == 0:
        random.shuffle(combined)

    # 截断到 count 条（计为最大数，不足则全返），返回 ID 列表
    result = combined[:body.count]
    for post in result:
        db_execute(
            "INSERT OR IGNORE INTO read_posts (user_id, post_id) VALUES (?, ?)",
            (user_id, post["id"])
        )
    db_commit()
    next_cursor = result[-1]["id"] if result else 0
    return {"posts": [p["id"] for p in result], "count": len(result), "next_cursor": next_cursor}

class Get_Post(BaseModel):
    cookie: str
    post_id: int

@app.post("/get-post")
def get_post(body: Get_Post):
    row = db_fetchone(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    post = db_fetchone(
        "SELECT p.*, u.username, u.nickname, u.avatar FROM posts p JOIN users u ON u.id = p.publisher_id WHERE p.id = ?",
        (body.post_id,)
    )
    if not post:
        return {"error": "Post not found."}

    media = db_fetchall(
        "SELECT offset, content FROM post_media WHERE post_id = ? ORDER BY offset",
        (body.post_id,)
    )

    liked = db_fetchone(
        "SELECT 1 FROM liking_users WHERE post_id = ? AND liker_id = ?",
        (body.post_id, user_id)
    ) is not None

    bookmarked = db_fetchone(
        "SELECT 1 FROM bookmarks WHERE post_id = ? AND user_id = ?",
        (body.post_id, user_id)
    ) is not None

    comment_count = db_fetchone(
        "SELECT COUNT(*) as cnt FROM comments WHERE post_id = ?",
        (body.post_id,)
    )

    return {
        "id": post["id"],
        "publisher_id": post["publisher_id"],
        "username": post["username"],
        "nickname": post["nickname"],
        "avatar": post["avatar"],
        "content": post["content"],
        "like_num": post["like_num"],
        "liked": liked is not None,
        "created_at": post["created_at"],
        "repost_id": post["repost_id"],
        "is_liked": liked,
        "is_bookmarked": bookmarked,
        "comment_count": comment_count["cnt"] if comment_count else 0,
        "media": [dict(m) for m in media]
    }

class Create_Group_Req(BaseModel):
    cookie: str
    name: str

@app.post("/create-group")
def create_group(body: Create_Group_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    if not body.name:
        return {"error": "Group name cannot be empty."}
    user_id = row["user_id"]
    db_execute("INSERT INTO groups (name, owner_id) VALUES (?, ?)",
            (body.name, user_id)
            )
    group_id = db_lastrowid()
    db_execute(
            "INSERT INTO user_in_group (group_id, user_id, role) VALUES (?, ?, ?)",
            (group_id, user_id, "owner")
            )
    db_commit()
    return {"group_id": group_id}

class Join_Group_Req(BaseModel):
    cookie: str
    group_id: int

@app.post("/join-group")
def join_group(body: Join_Group_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    group = db_fetchone(
            "SELECT id FROM groups WHERE id = ?",
            (body.group_id,)
            )
    if not group:
        return {"error": "Group not exist."}
    db_execute("INSERT OR IGNORE INTO user_in_group (group_id, user_id) VALUES (?, ?)",
            (body.group_id, user_id)
            )
    db_commit()
    return {"status": "success"}

class Leave_Group_Req(BaseModel):
    cookie: str
    group_id: int

@app.post("/leave-group")
def leave_group(body: Leave_Group_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    group = db_fetchone(
            "SELECT owner_id FROM groups WHERE id = ?",
            (body.group_id,)
            )
    if not group:
        return {"error": "Group not exist."}
    if group["owner_id"] == user_id:
        return {"error": "Owner cannot leave. Transfer ownership or disband the group first."}
    db_execute("DELETE FROM user_in_group WHERE group_id = ? AND user_id = ?",
            (body.group_id, user_id)
            )
    db_commit()
    return {"status": "success"}

class Send_Group_Msg_Req(BaseModel):
    cookie: str
    group_id: int
    content: str

@app.post("/send-group-msg")
def send_group_msg(body: Send_Group_Msg_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    in_group = db_fetchone(
            "SELECT role FROM user_in_group WHERE group_id = ? AND user_id = ?",
            (body.group_id, user_id)
            )
    if not in_group:
        return {"error": "You are not in this group."}
    if not body.content:
        return {"error": "Empty message not allowed."}
    db_execute("INSERT INTO group_messages (group_id, sender_id, content) VALUES (?, ?, ?)",
            (body.group_id, user_id, body.content)
            )
    db_commit()
    return {"status": "success"}

class Recv_Group_Msg_Req(BaseModel):
    cookie: str
    group_id: int
    before_id: int = 0     # 0=拉取最新消息, >0=拉取此ID之前的消息（游标翻页）
    count: int = 20

@app.post("/recv-group-msg")
def recv_group_msg(body: Recv_Group_Msg_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    membership = db_fetchone(
            "SELECT 1 FROM user_in_group WHERE group_id = ? AND user_id = ?",
            (body.group_id, user_id)
            )
    if not membership:
        return {"error": "You are not in this group."}
    if body.before_id > 0:
        messages = db_fetchall("""
                SELECT gm.id, gm.sender_id, u.username, u.nickname, gm.content, gm.sent_at
                FROM group_messages gm
                JOIN users u ON u.id = gm.sender_id
                WHERE gm.group_id = ? AND gm.id < ?
                ORDER BY gm.id DESC LIMIT ?
        """, (body.group_id, body.before_id, body.count))
    else:
        messages = db_fetchall("""
                SELECT gm.id, gm.sender_id, u.username, u.nickname, gm.content, gm.sent_at
                FROM group_messages gm
                JOIN users u ON u.id = gm.sender_id
                WHERE gm.group_id = ?
                ORDER BY gm.id DESC LIMIT ?
        """, (body.group_id, body.count))
    # 反转回 ASC 顺序显示
    messages = list(reversed([dict(m) for m in messages]))
    next_cursor = messages[0]["id"] if messages else 0
    return {"messages": messages, "count": len(messages), "next_cursor": next_cursor}

# =============================================================================
# P3: 群聊 — 标记群消息已读（由前端在用户滚动到底部时显式调用）
# POST /mark-group-read
# =============================================================================
class Mark_Group_Read_Req(BaseModel):
    cookie: str
    group_id: int

@app.post("/mark-group-read")
def mark_group_read(body: Mark_Group_Read_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    # 取该群最后一条消息ID
    last_msg = db_fetchone(
            "SELECT MAX(id) as max_id FROM group_messages WHERE group_id = ?",
            (body.group_id,)
            )
    if last_msg and last_msg["max_id"] is not None:
        db_execute(
                "UPDATE user_in_group SET last_read_id = ? WHERE group_id = ? AND user_id = ?",
                (last_msg["max_id"], body.group_id, user_id)
                )
        db_commit()
    return {"status": "success"}

class Get_Group_Members_Req(BaseModel):
    cookie: str
    group_id: int

@app.post("/get-group-members")
def get_group_members(body: Get_Group_Members_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    members = db_fetchall("""
            SELECT u.id, u.username, u.nickname, u.avatar, ug.role, ug.joined_at
            FROM user_in_group ug
            JOIN users u ON u.id = ug.user_id
            WHERE ug.group_id = ?
            ORDER BY ug.joined_at ASC
    """, (body.group_id,))
    return {"members": [dict(m) for m in members]}

class Get_My_Groups_Req(BaseModel):
    cookie: str

@app.post("/get-my-groups")
def get_my_groups(body: Get_My_Groups_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    groups = db_fetchall("""
            SELECT g.id, g.name, g.owner_id, ug.role, ug.joined_at,
                   (SELECT gm.content FROM group_messages gm
                    WHERE gm.group_id = g.id ORDER BY gm.id DESC LIMIT 1) as last_message,
                   (SELECT gm.sent_at FROM group_messages gm
                    WHERE gm.group_id = g.id ORDER BY gm.id DESC LIMIT 1) as last_message_time,
                   (SELECT COUNT(*) FROM group_messages gm
                    WHERE gm.group_id = g.id AND gm.id > ug.last_read_id) as unread_count,
                   (SELECT COUNT(*) FROM user_in_group uig
                    WHERE uig.group_id = g.id) as member_count
            FROM user_in_group ug
            JOIN groups g ON g.id = ug.group_id
            WHERE ug.user_id = ?
            ORDER BY COALESCE(
                (SELECT gm.sent_at FROM group_messages gm WHERE gm.group_id = g.id ORDER BY gm.id DESC LIMIT 1),
                ug.joined_at
            ) DESC
    """, (user_id,))
    return {"groups": [dict(g) for g in groups]}

# =============================================================================
# 用户系统：登出
# POST /logout — 删除当前token使其立即失效
# =============================================================================
# =============================================================================
# 用户系统：检查 Cookie 有效性
# POST /check-cookie
# =============================================================================
class Check_Cookie_Req(BaseModel):
    cookie: str

@app.post("/check-cookie")
def check_cookie(body: Check_Cookie_Req):
    if not body.cookie:
        return {"error": "Empty cookie."}
    row = db_fetchone(
            "SELECT user_id, expires_at FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"valid": False}
    # 可选：检查过期，但当前所有 cookie expires_at = '2099-12-31'
    # from datetime import datetime
    # if row["expires_at"] < datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
    #     return {"valid": False, "expired": True}
    return {"valid": True, "user_id": row["user_id"]}

class Logout_Req(BaseModel):
    cookie: str

@app.post("/logout")
def logout(body: Logout_Req):
    db_execute(
            "DELETE FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    db_commit()
    return {"status": "success"}

# =============================================================================
# 帖子系统：删除帖子
# POST /delete-post
# 仅发布者本人可删，级联清理 liking_users/comments/post_media/read_posts
# =============================================================================
class Del_Post_Req(BaseModel):
    cookie: str
    post_id: int

@app.post("/delete-post")
def delete_post(body: Del_Post_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    post = db_fetchone(
            "SELECT publisher_id FROM posts WHERE id = ?",
            (body.post_id,)
            )
    if not post:
        return {"error": "Post not exist."}
    if post["publisher_id"] != user_id:
        return {"error": "Not your post."}
    # 级联清理所有关联数据
    db_execute("DELETE FROM liking_users WHERE post_id = ?", (body.post_id,))
    db_execute("DELETE FROM comments WHERE post_id = ?", (body.post_id,))
    db_execute("DELETE FROM post_media WHERE post_id = ?", (body.post_id,))
    db_execute("DELETE FROM read_posts WHERE post_id = ?", (body.post_id,))
    db_execute("DELETE FROM bookmarks WHERE post_id = ?", (body.post_id,))
    db_execute("DELETE FROM post_hashtags WHERE post_id = ?", (body.post_id,))
    db_execute("DELETE FROM notifications WHERE post_id = ?", (body.post_id,))
    db_execute("DELETE FROM posts WHERE id = ?", (body.post_id,))
    db_commit()
    return {"status": "success"}

# =============================================================================
# 互动系统：删除评论
# POST /delete-comment — 仅评论者本人可删
# =============================================================================
class Del_Comment_Req(BaseModel):
    cookie: str
    comment_id: int

@app.post("/delete-comment")
def delete_comment(body: Del_Comment_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    comment = db_fetchone(
            "SELECT commenter_id FROM comments WHERE id = ?",
            (body.comment_id,)
            )
    if not comment:
        return {"error": "Comment not exist."}
    if comment["commenter_id"] != user_id:
        return {"error": "Not your comment."}
    db_execute(
            "DELETE FROM comments WHERE id = ?",
            (body.comment_id,)
            )
    db_commit()
    return {"status": "success"}

# =============================================================================
# 用户系统：编辑个人资料
# POST /edit-profile — nickname和email_address均为可选，只更新非空字段
# =============================================================================
class Edit_Profile_Req(BaseModel):
    cookie: str
    nickname: str = ""
    email_address: str = ""

@app.post("/edit-profile")
def edit_profile(body: Edit_Profile_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    if body.nickname:
        db_execute(
                "UPDATE users SET nickname = ? WHERE id = ?",
                (body.nickname, user_id)
                )
    if body.email_address:
        db_execute(
                "UPDATE users SET email_address = ? WHERE id = ?",
                (body.email_address, user_id)
                )
    db_commit()
    return {"status": "success"}

# =============================================================================
# 收藏系统：收藏帖子
# POST /bookmark — 使用 INSERT OR IGNORE 保证幂等
# =============================================================================
class Bookmark_Req(BaseModel):
    cookie: str
    post_id: int

@app.post("/bookmark")
def bookmark(body: Bookmark_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    post = db_fetchone(
            "SELECT id FROM posts WHERE id = ?",
            (body.post_id,)
            )
    if not post:
        return {"error": "Post not exist."}
    db_execute(
            "INSERT OR IGNORE INTO bookmarks (user_id, post_id) VALUES (?, ?)",
            (user_id, body.post_id)
            )
    db_commit()
    return {"status": "success"}

# =============================================================================
# 收藏系统：取消收藏
# POST /unbookmark — 直接删除，不存在也不报错
# =============================================================================
@app.post("/unbookmark")
def unbookmark(body: Bookmark_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    db_execute(
            "DELETE FROM bookmarks WHERE user_id = ? AND post_id = ?",
            (user_id, body.post_id)
            )
    db_commit()
    return {"status": "success"}

# =============================================================================
# 收藏系统：获取收藏列表
# POST /get-bookmarks — 返回完整帖子信息（含发布者和媒体），按收藏时间倒序
# =============================================================================
class Get_Bookmarks_Req(BaseModel):
    cookie: str

@app.post("/get-bookmarks")
def get_bookmarks(body: Get_Bookmarks_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    posts = db_fetchall("""
            SELECT p.*, u.username, u.nickname, b.bookmarked_at
            FROM bookmarks b
            JOIN posts p ON p.id = b.post_id
            JOIN users u ON u.id = p.publisher_id
            WHERE b.user_id = ?
            ORDER BY b.bookmarked_at DESC
    """, (user_id,))
    result = []
    for p in posts:
        media = db_fetchall(
                "SELECT offset, content FROM post_media WHERE post_id = ? ORDER BY offset",
                (p["id"],)
                )
        result.append({
            "id": p["id"],
            "publisher_id": p["publisher_id"],
            "username": p["username"],
            "nickname": p["nickname"],
            "content": p["content"],
            "like_num": p["like_num"],
            "created_at": p["created_at"],
            "bookmarked_at": p["bookmarked_at"],
            "repost_id": p["repost_id"],
            "media": [dict(m) for m in media]
        })
    return {"posts": result}

# =============================================================================
# 帖子系统：转发
# POST /repost — 用自己的账户将原帖重新发布，可选附加文字
# 原帖信息通过 repost_id 字段记录在 posts 表中
# =============================================================================
class Repost_Req(BaseModel):
    cookie: str
    post_id: int          # 要转发的原帖ID
    text: str = ""         # 转发时附加的文字（可选）

@app.post("/repost")
def repost(body: Repost_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    original = db_fetchone(
            "SELECT id, publisher_id FROM posts WHERE id = ?",
            (body.post_id,)
            )
    if not original:
        return {"error": "Post not exist."}
    if original["publisher_id"] == user_id:
        return {"error": "Cannot repost your own post."}
    db_execute(
            "INSERT INTO posts (publisher_id, content, repost_id) VALUES (?, ?, ?)",
            (user_id, body.text, body.post_id)
            )
    new_post_id = db_lastrowid()
    # 通知原帖作者被转发
    db_execute(
            "INSERT INTO notifications (user_id, type, from_user_id, post_id, content) VALUES (?, 'repost', ?, ?, '')",
            (original["publisher_id"], user_id, new_post_id)
            )
    db_commit()
    return {"status": "success", "new_post_id": new_post_id}

class Patch_Avatar_Req(BaseModel):
    cookie: str
    avatar: str = ""
    signature: str = ""

@app.patch("/avatar")
def patch_avatar(body: Patch_Avatar_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    if body.avatar:
        db_execute("UPDATE users SET avatar = ? WHERE id = ?",
                (body.avatar, user_id)
                )
    if body.signature:
        db_execute(
                "UPDATE users SET signature = ? WHERE id = ?",
                (body.signature, user_id)
                )
    db_commit()
    return {"status": "success"}

@app.get("/avatar")
def get_avatar(user_id: int = 0):
    if not user_id:
        return {"error": "Missing user_id."}
    row = db_fetchone(
            "SELECT avatar, signature FROM users WHERE id = ?",
            (user_id,)
            )
    if not row:
        return {"error": "User not found."}
    return {"user_id": user_id, "avatar": row["avatar"], "signature": row["signature"]}

# =============================================================================
# P1: 搜索系统 — 全局搜索用户/帖子/群组
# POST /search
# =============================================================================
class Search_Req(BaseModel):
    cookie: str
    keyword: str

@app.post("/search")
def search(body: Search_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    if not body.keyword:
        return {"error": "Keyword required."}
    kw = "%" + body.keyword + "%"
    users = [dict(u) for u in db_fetchall(
            "SELECT id, username, nickname, avatar, signature FROM users WHERE username LIKE ? OR nickname LIKE ? LIMIT 20",
            (kw, kw)
            )]
    posts = [dict(p) for p in db_fetchall(
            "SELECT p.id, p.content, p.created_at, u.username, u.nickname FROM posts p JOIN users u ON u.id = p.publisher_id WHERE p.content LIKE ? ORDER BY p.created_at DESC LIMIT 20",
            (kw,)
            )]
    groups = [dict(g) for g in db_fetchall(
            "SELECT id, name, owner_id, created_at FROM groups WHERE name LIKE ? LIMIT 20",
            (kw,)
            )]
    return {"users": users, "posts": posts, "groups": groups}

# =============================================================================
# P1: 通知系统 — 获取通知列表（游标分页）
# POST /get-notifications
# =============================================================================
class Get_Notifications_Req(BaseModel):
    cookie: str
    before_id: int = 0
    count: int = 20

@app.post("/get-notifications")
def get_notifications(body: Get_Notifications_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    if body.before_id > 0:
        notis = db_fetchall("""
                SELECT n.*, u.username, u.nickname
                FROM notifications n
                JOIN users u ON u.id = n.from_user_id
                WHERE n.user_id = ? AND n.id < ?
                ORDER BY n.id DESC LIMIT ?
        """, (user_id, body.before_id, body.count))
    else:
        notis = db_fetchall("""
                SELECT n.*, u.username, u.nickname
                FROM notifications n
                JOIN users u ON u.id = n.from_user_id
                WHERE n.user_id = ?
                ORDER BY n.id DESC LIMIT ?
        """, (user_id, body.count))
    unread = db_fetchone(
            "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,)
            )
    next_cursor = notis[-1]["id"] if notis else 0
    return {
            "notifications": [dict(n) for n in notis],
            "unread_count": unread["cnt"] if unread else 0,
            "next_cursor": next_cursor
            }

# =============================================================================
# P1: 通知系统 — 标记已读
# POST /mark-notifications-read
# =============================================================================
class Mark_Read_Req(BaseModel):
    cookie: str
    notification_id: int = 0

@app.post("/mark-notifications-read")
def mark_notifications_read(body: Mark_Read_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    if body.notification_id > 0:
        db_execute(
                "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
                (body.notification_id, user_id)
                )
    else:
        db_execute(
                "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
                (user_id,)
                )
    db_commit()
    return {"status": "success"}

# =============================================================================
# P1: 用户系统 — 查看用户主页（帖子时间线，游标分页）
# POST /get-user-posts
# =============================================================================
class Get_User_Posts_Req(BaseModel):
    cookie: str
    user_id: int
    before_id: int = 0
    count: int = 20

@app.post("/get-user-posts")
def get_user_posts(body: Get_User_Posts_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    target_user = db_fetchone(
            "SELECT id, username, nickname, avatar, signature FROM users WHERE id = ?",
            (body.user_id,)
            )
    if not target_user:
        return {"error": "User not exist."}
    if body.before_id > 0:
        posts = db_fetchall("""
                SELECT p.*, u.username, u.nickname
                FROM posts p
                JOIN users u ON u.id = p.publisher_id
                WHERE p.publisher_id = ? AND p.id < ?
                ORDER BY p.id DESC LIMIT ?
        """, (body.user_id, body.before_id, body.count))
    else:
        posts = db_fetchall("""
                SELECT p.*, u.username, u.nickname
                FROM posts p
                JOIN users u ON u.id = p.publisher_id
                WHERE p.publisher_id = ?
                ORDER BY p.id DESC LIMIT ?
        """, (body.user_id, body.count))
    next_cursor = posts[-1]["id"] if posts else 0
    result = []
    for p in posts:
        media = db_fetchall(
                "SELECT offset, content FROM post_media WHERE post_id = ? ORDER BY offset",
                (p["id"],)
                )
        result.append({
            "id": p["id"],
            "content": p["content"],
            "like_num": p["like_num"],
            "created_at": p["created_at"],
            "repost_id": p["repost_id"],
            "media": [dict(m) for m in media]
        })
    return {
            "user": {
                "id": target_user["id"],
                "username": target_user["username"],
                "nickname": target_user["nickname"],
                "avatar": target_user["avatar"],
                "signature": target_user["signature"]
                },
            "posts": result,
            "next_cursor": next_cursor
            }

# =============================================================================
# P1: 用户系统 — 查看用户详细资料（含关注状态和统计）
# POST /get-user-profile
# =============================================================================
class Get_User_Profile_Req(BaseModel):
    cookie: str
    user_id: int

@app.post("/get-user-profile")
def get_user_profile(body: Get_User_Profile_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    my_id = row["user_id"]
    target = db_fetchone(
            "SELECT id, username, nickname, avatar, signature, email_address FROM users WHERE id = ?",
            (body.user_id,)
            )
    if not target:
        return {"error": "User not exist."}
    is_following = db_fetchone(
            "SELECT 1 FROM following WHERE follower = ? AND followee = ?",
            (my_id, body.user_id)
            ) is not None
    is_followed = db_fetchone(
            "SELECT 1 FROM following WHERE follower = ? AND followee = ?",
            (body.user_id, my_id)
            ) is not None
    post_count = db_fetchone(
            "SELECT COUNT(*) as cnt FROM posts WHERE publisher_id = ?",
            (body.user_id,)
            )
    follower_count = db_fetchone(
            "SELECT COUNT(*) as cnt FROM following WHERE followee = ?",
            (body.user_id,)
            )
    followee_count = db_fetchone(
            "SELECT COUNT(*) as cnt FROM following WHERE follower = ?",
            (body.user_id,)
            )
    return {
            "id": target["id"],
            "username": target["username"],
            "nickname": target["nickname"],
            "avatar": target["avatar"],
            "signature": target["signature"],
            "email_address": target["email_address"],
            "is_following": is_following,
            "is_followed": is_followed,
            "post_count": post_count["cnt"] if post_count else 0,
            "follower_count": follower_count["cnt"] if follower_count else 0,
            "followee_count": followee_count["cnt"] if followee_count else 0
            }

# =============================================================================
# P1: 帖子系统 — 编辑帖子（仅发布者本人）
# POST /edit-post
# =============================================================================
class Edit_Post_Req(BaseModel):
    cookie: str
    post_id: int
    content: str

@app.post("/edit-post")
def edit_post(body: Edit_Post_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    post = db_fetchone(
            "SELECT publisher_id FROM posts WHERE id = ?",
            (body.post_id,)
            )
    if not post:
        return {"error": "Post not exist."}
    if post["publisher_id"] != user_id:
        return {"error": "Not your post."}
    db_execute(
            "UPDATE posts SET content = ? WHERE id = ?",
            (body.content, body.post_id)
            )
    db_commit()
    return {"status": "success"}

# =============================================================================
# P1: 互动系统 — 获取点赞用户列表（游标分页）
# POST /get-post-likers
# =============================================================================
class Get_Post_Likers_Req(BaseModel):
    cookie: str
    post_id: int
    before_liker_id: int = 0
    count: int = 20

@app.post("/get-post-likers")
def get_post_likers(body: Get_Post_Likers_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    if body.before_liker_id > 0:
        likers = db_fetchall("""
                SELECT u.id, u.username, u.nickname, u.avatar, lu.liked_at
                FROM liking_users lu
                JOIN users u ON u.id = lu.liker_id
                WHERE lu.post_id = ? AND lu.liker_id < ?
                ORDER BY lu.liked_at DESC LIMIT ?
        """, (body.post_id, body.before_liker_id, body.count))
    else:
        likers = db_fetchall("""
                SELECT u.id, u.username, u.nickname, u.avatar, lu.liked_at
                FROM liking_users lu
                JOIN users u ON u.id = lu.liker_id
                WHERE lu.post_id = ?
                ORDER BY lu.liked_at DESC LIMIT ?
        """, (body.post_id, body.count))
    total = db_fetchone(
            "SELECT like_num FROM posts WHERE id = ?",
            (body.post_id,)
            )
    next_cursor = likers[-1]["id"] if likers else 0
    return {
            "likers": [dict(l) for l in likers],
            "total": total["like_num"] if total else 0,
            "next_cursor": next_cursor
            }

# =============================================================================
# 用户系统：查找我的博文
# POST /get-my-posts — 通过cookie识别当前用户，返回自己发布的所有帖子（游标分页）
# =============================================================================
class Get_My_Posts_Req(BaseModel):
    cookie: str
    before_id: int = 0
    count: int = 20

@app.post("/get-my-posts")
def get_my_posts(body: Get_My_Posts_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    if body.before_id > 0:
        posts = db_fetchall("""
                SELECT p.*, u.username, u.nickname
                FROM posts p
                JOIN users u ON u.id = p.publisher_id
                WHERE p.publisher_id = ? AND p.id < ?
                ORDER BY p.id DESC LIMIT ?
        """, (user_id, body.before_id, body.count))
    else:
        posts = db_fetchall("""
                SELECT p.*, u.username, u.nickname
                FROM posts p
                JOIN users u ON u.id = p.publisher_id
                WHERE p.publisher_id = ?
                ORDER BY p.id DESC LIMIT ?
        """, (user_id, body.count))
    next_cursor = posts[-1]["id"] if posts else 0
    result = []
    for p in posts:
        media = db_fetchall(
                "SELECT offset, content FROM post_media WHERE post_id = ? ORDER BY offset",
                (p["id"],)
                )
        result.append({
            "id": p["id"],
            "content": p["content"],
            "like_num": p["like_num"],
            "created_at": p["created_at"],
            "repost_id": p["repost_id"],
            "media": [dict(m) for m in media]
        })
    return {
            "posts": result,
            "count": len(result),
            "next_cursor": next_cursor
            }

# =============================================================================
# 互动系统：查找我的评论
# POST /get-my-comments — 返回当前用户发表的所有评论，含所在博文信息和评论ID
# =============================================================================
class Get_My_Comments_Req(BaseModel):
    cookie: str
    before_id: int = 0
    count: int = 20

@app.post("/get-my-comments")
def get_my_comments(body: Get_My_Comments_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    if body.before_id > 0:
        comments = db_fetchall("""
                SELECT c.id AS comment_id, c.content AS comment_content,
                       c.commented_at,
                       p.id AS post_id, p.content AS post_content,
                       u.username AS post_username, u.nickname AS post_nickname
                FROM comments c
                JOIN posts p ON p.id = c.post_id
                JOIN users u ON u.id = p.publisher_id
                WHERE c.commenter_id = ? AND c.id < ?
                ORDER BY c.id DESC LIMIT ?
        """, (user_id, body.before_id, body.count))
    else:
        comments = db_fetchall("""
                SELECT c.id AS comment_id, c.content AS comment_content,
                       c.commented_at,
                       p.id AS post_id, p.content AS post_content,
                       u.username AS post_username, u.nickname AS post_nickname
                FROM comments c
                JOIN posts p ON p.id = c.post_id
                JOIN users u ON u.id = p.publisher_id
                WHERE c.commenter_id = ?
                ORDER BY c.id DESC LIMIT ?
        """, (user_id, body.count))
    next_cursor = comments[-1]["comment_id"] if comments else 0
    return {
            "comments": [dict(c) for c in comments],
            "count": len(comments),
            "next_cursor": next_cursor
            }

# =============================================================================
# P1: 文件上传 — multipart/form-data 上传，返回 Base64
# POST /upload-media
# =============================================================================
@app.post("/upload-media")
async def upload_media(
        cookie: str = fastapi.Form(...),
        file: fastapi.UploadFile = fastapi.File(...)
        ):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    data = await file.read()
    if len(data) > (1 << 24):
        return {"error": "Media cannot be larger than 16MiB."}
    encoded = base64.b64encode(data).decode()
    return {"filename": file.filename, "content_type": file.content_type, "data": encoded}

# =============================================================================
# P2: 用户系统 — 修改密码
# POST /change-password
# =============================================================================
class Change_Password_Req(BaseModel):
    cookie: str
    old_password: str
    new_password: str

@app.post("/change-password")
def change_password(body: Change_Password_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    if not body.old_password or not body.new_password:
        return {"error": "Password cannot be empty."}
    if len(body.new_password) < 6:
        return {"error": "Password must be at least 6 characters."}
    user = db_fetchone(
            "SELECT password_hash FROM users WHERE id = ?",
            (user_id,)
            )
    if not bcrypt.checkpw(body.old_password.encode(), user["password_hash"].encode()):
        return {"error": "Incorrect old password."}
    new_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
    db_execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
    db_commit()
    return {"status": "success"}

# =============================================================================
# P2: 用户系统 — 注销账号（级联清理所有用户数据）
# POST /delete-account
# =============================================================================
class Delete_Account_Req(BaseModel):
    cookie: str
    password: str

@app.post("/delete-account")
def delete_account(body: Delete_Account_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    user = db_fetchone(
            "SELECT password_hash FROM users WHERE id = ?",
            (user_id,)
            )
    if not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        return {"error": "Incorrect password."}
    # 级联清理所有关联数据
    db_execute("DELETE FROM cookies WHERE user_id = ?", (user_id,))
    db_execute("DELETE FROM following WHERE follower = ? OR followee = ?", (user_id, user_id))
    db_execute("DELETE FROM liking_users WHERE liker_id = ?", (user_id,))
    db_execute("DELETE FROM comments WHERE commenter_id = ?", (user_id,))
    db_execute("DELETE FROM offline_messages WHERE sender_id = ? OR receiver_id = ?", (user_id, user_id))
    db_execute("DELETE FROM read_posts WHERE user_id = ?", (user_id,))
    db_execute("DELETE FROM bookmarks WHERE user_id = ?", (user_id,))
    db_execute("DELETE FROM notifications WHERE user_id = ? OR from_user_id = ?", (user_id, user_id))
    db_execute("DELETE FROM blocks WHERE blocker_id = ? OR blocked_id = ?", (user_id, user_id))
    db_execute("DELETE FROM reports WHERE reporter_id = ?", (user_id,))
    db_execute("DELETE FROM user_in_group WHERE user_id = ?", (user_id,))
    db_execute("DELETE FROM group_messages WHERE sender_id = ?", (user_id,))
    # 删除用户发布的帖子和关联数据
    post_ids = [r["id"] for r in db_fetchall("SELECT id FROM posts WHERE publisher_id = ?", (user_id,))]
    for pid in post_ids:
        db_execute("DELETE FROM liking_users WHERE post_id = ?", (pid,))
        db_execute("DELETE FROM comments WHERE post_id = ?", (pid,))
        db_execute("DELETE FROM post_media WHERE post_id = ?", (pid,))
        db_execute("DELETE FROM read_posts WHERE post_id = ?", (pid,))
        db_execute("DELETE FROM bookmarks WHERE post_id = ?", (pid,))
        db_execute("DELETE FROM post_hashtags WHERE post_id = ?", (pid,))
        db_execute("DELETE FROM notifications WHERE post_id = ?", (pid,))
    db_execute("DELETE FROM posts WHERE publisher_id = ?", (user_id,))
    # 转移或解散拥有的群组
    owned = db_fetchall("SELECT id FROM groups WHERE owner_id = ?", (user_id,))
    for g in owned:
        db_execute("DELETE FROM group_messages WHERE group_id = ?", (g["id"],))
        db_execute("DELETE FROM user_in_group WHERE group_id = ?", (g["id"],))
        db_execute("DELETE FROM groups WHERE id = ?", (g["id"],))
    db_execute("DELETE FROM users WHERE id = ?", (user_id,))
    db_commit()
    return {"status": "success"}

# =============================================================================
# P2: 屏蔽系统 — 拉黑用户
# POST /block
# =============================================================================
class Block_Req(BaseModel):
    cookie: str
    user_id: int

@app.post("/block")
def block_user(body: Block_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    blocker_id = row["user_id"]
    if blocker_id == body.user_id:
        return {"error": "Cannot block yourself."}
    target = db_fetchone("SELECT id FROM users WHERE id = ?", (body.user_id,))
    if not target:
        return {"error": "User not exist."}
    db_execute("INSERT OR IGNORE INTO blocks (blocker_id, blocked_id) VALUES (?, ?)",
            (blocker_id, body.user_id))
    # 自动取消双方关注
    db_execute("DELETE FROM following WHERE (follower = ? AND followee = ?) OR (follower = ? AND followee = ?)",
            (blocker_id, body.user_id, body.user_id, blocker_id))
    db_commit()
    return {"status": "success"}

# =============================================================================
# P2: 屏蔽系统 — 取消拉黑
# POST /unblock
# =============================================================================
@app.post("/unblock")
def unblock_user(body: Block_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    blocker_id = row["user_id"]
    db_execute("DELETE FROM blocks WHERE blocker_id = ? AND blocked_id = ?",
            (blocker_id, body.user_id))
    db_commit()
    return {"status": "success"}

# =============================================================================
# P2: 屏蔽系统 — 获取已拉黑用户列表
# POST /get-blocked-users
# =============================================================================
class Get_Blocked_Req(BaseModel):
    cookie: str

@app.post("/get-blocked-users")
def get_blocked_users(body: Get_Blocked_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    blocked = db_fetchall("""
            SELECT u.id, u.username, u.nickname, u.avatar, b.created_at
            FROM blocks b
            JOIN users u ON u.id = b.blocked_id
            WHERE b.blocker_id = ?
            ORDER BY b.created_at DESC
    """, (user_id,))
    return {"blocked_users": [dict(u) for u in blocked]}

# =============================================================================
# P2: 群组管理 — 踢出成员（仅群主可用）
# POST /kick-group-member
# =============================================================================
class Kick_Member_Req(BaseModel):
    cookie: str
    group_id: int
    user_id: int

@app.post("/kick-group-member")
def kick_group_member(body: Kick_Member_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    operator_id = row["user_id"]
    group = db_fetchone("SELECT owner_id FROM groups WHERE id = ?", (body.group_id,))
    if not group:
        return {"error": "Group not exist."}
    if group["owner_id"] != operator_id:
        return {"error": "Only the group owner can kick members."}
    if body.user_id == operator_id:
        return {"error": "Cannot kick yourself. Use disband instead."}
    db_execute("DELETE FROM user_in_group WHERE group_id = ? AND user_id = ?",
            (body.group_id, body.user_id))
    db_commit()
    return {"status": "success"}

# =============================================================================
# P2: 群组管理 — 修改群名（仅群主可用）
# POST /change-group-name
# =============================================================================
class Change_Group_Name_Req(BaseModel):
    cookie: str
    group_id: int
    name: str

@app.post("/change-group-name")
def change_group_name(body: Change_Group_Name_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    operator_id = row["user_id"]
    if not body.name:
        return {"error": "Group name cannot be empty."}
    group = db_fetchone("SELECT owner_id FROM groups WHERE id = ?", (body.group_id,))
    if not group:
        return {"error": "Group not exist."}
    if group["owner_id"] != operator_id:
        return {"error": "Only the group owner can rename the group."}
    db_execute("UPDATE groups SET name = ? WHERE id = ?", (body.name, body.group_id))
    db_commit()
    return {"status": "success"}

# =============================================================================
# P2: 群组管理 — 转让群主（仅群主可用，目标必须在群内）
# POST /transfer-group
# =============================================================================
class Transfer_Group_Req(BaseModel):
    cookie: str
    group_id: int
    new_owner_id: int

@app.post("/transfer-group")
def transfer_group(body: Transfer_Group_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    operator_id = row["user_id"]
    group = db_fetchone("SELECT owner_id FROM groups WHERE id = ?", (body.group_id,))
    if not group:
        return {"error": "Group not exist."}
    if group["owner_id"] != operator_id:
        return {"error": "Only the group owner can transfer ownership."}
    if body.new_owner_id == operator_id:
        return {"error": "You are already the owner."}
    member = db_fetchone(
            "SELECT 1 FROM user_in_group WHERE group_id = ? AND user_id = ?",
            (body.group_id, body.new_owner_id))
    if not member:
        return {"error": "Target user is not in this group."}
    db_execute("UPDATE groups SET owner_id = ? WHERE id = ?",
            (body.new_owner_id, body.group_id))
    db_execute("UPDATE user_in_group SET role = 'owner' WHERE group_id = ? AND user_id = ?",
            (body.group_id, body.new_owner_id))
    db_execute("UPDATE user_in_group SET role = 'member' WHERE group_id = ? AND user_id = ?",
            (body.group_id, operator_id))
    db_commit()
    return {"status": "success"}

# =============================================================================
# P2: 群组管理 — 解散群组（仅群主可用）
# POST /disband-group
# =============================================================================
class Disband_Group_Req(BaseModel):
    cookie: str
    group_id: int

@app.post("/disband-group")
def disband_group(body: Disband_Group_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    operator_id = row["user_id"]
    group = db_fetchone("SELECT owner_id FROM groups WHERE id = ?", (body.group_id,))
    if not group:
        return {"error": "Group not exist."}
    if group["owner_id"] != operator_id:
        return {"error": "Only the group owner can disband the group."}
    db_execute("DELETE FROM group_messages WHERE group_id = ?", (body.group_id,))
    db_execute("DELETE FROM user_in_group WHERE group_id = ?", (body.group_id,))
    db_execute("DELETE FROM groups WHERE id = ?", (body.group_id,))
    db_commit()
    return {"status": "success"}

# =============================================================================
# P2: 举报系统 — 举报用户/帖子/评论
# POST /report
# =============================================================================
class Report_Req(BaseModel):
    cookie: str
    target_type: str    # "user" | "post" | "comment"
    target_id: int
    reason: str = ""

@app.post("/report")
def report(body: Report_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    reporter_id = row["user_id"]
    if body.target_type not in ("user", "post", "comment"):
        return {"error": "Invalid target_type. Must be user, post, or comment."}
    # 验证目标存在
    if body.target_type == "user":
        target = db_fetchone("SELECT id FROM users WHERE id = ?", (body.target_id,))
    elif body.target_type == "post":
        target = db_fetchone("SELECT id FROM posts WHERE id = ?", (body.target_id,))
    else:
        target = db_fetchone("SELECT id FROM comments WHERE id = ?", (body.target_id,))
    if not target:
        return {"error": f"{body.target_type.capitalize()} not exist."}
    db_execute(
            "INSERT INTO reports (reporter_id, target_type, target_id, reason) VALUES (?, ?, ?, ?)",
            (reporter_id, body.target_type, body.target_id, body.reason))
    db_commit()
    return {"status": "success", "report_id": db_lastrowid()}

# =============================================================================
# P2: 标签系统 — 按标签获取帖子（游标分页）
# POST /get-hashtag-posts
# =============================================================================
class Get_Hashtag_Posts_Req(BaseModel):
    cookie: str
    hashtag: str
    before_id: int = 0
    count: int = 20

@app.post("/get-hashtag-posts")
def get_hashtag_posts(body: Get_Hashtag_Posts_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    tag_name = body.hashtag.lstrip('#')
    ht = db_fetchone("SELECT id FROM hashtags WHERE name = ?", (tag_name,))
    if not ht:
        return {"posts": [], "count": 0, "next_cursor": 0}
    if body.before_id > 0:
        posts = db_fetchall("""
                SELECT p.*, u.username, u.nickname
                FROM post_hashtags ph
                JOIN posts p ON p.id = ph.post_id
                JOIN users u ON u.id = p.publisher_id
                WHERE ph.hashtag_id = ? AND p.id < ?
                ORDER BY p.id DESC LIMIT ?
        """, (ht["id"], body.before_id, body.count))
    else:
        posts = db_fetchall("""
                SELECT p.*, u.username, u.nickname
                FROM post_hashtags ph
                JOIN posts p ON p.id = ph.post_id
                JOIN users u ON u.id = p.publisher_id
                WHERE ph.hashtag_id = ?
                ORDER BY p.id DESC LIMIT ?
        """, (ht["id"], body.count))
    next_cursor = posts[-1]["id"] if posts else 0
    result = []
    for p in posts:
        media = db_fetchall(
                "SELECT offset, content FROM post_media WHERE post_id = ? ORDER BY offset",
                (p["id"],))
        result.append({
            "id": p["id"],
            "content": p["content"],
            "like_num": p["like_num"],
            "created_at": p["created_at"],
            "publisher_id": p["publisher_id"],
            "username": p["username"],
            "nickname": p["nickname"],
            "repost_id": p["repost_id"],
            "media": [dict(m) for m in media]
        })
    return {"posts": result, "count": len(result), "next_cursor": next_cursor}

# =============================================================================
# P2: 标签系统 — 获取热门标签（按使用频次降序）
# GET /trending-hashtags
# =============================================================================
class Trending_Hashtags_Req(BaseModel):
    count: int = 20

@app.post("/trending-hashtags")
def trending_hashtags(body: Trending_Hashtags_Req):
    tags = db_fetchall("""
            SELECT h.name, COUNT(ph.post_id) as post_count
            FROM hashtags h
            JOIN post_hashtags ph ON ph.hashtag_id = h.id
            GROUP BY h.id
            ORDER BY post_count DESC
            LIMIT ?
    """, (body.count,))
    return {"hashtags": [{"name": t["name"], "post_count": t["post_count"]} for t in tags]}

# =============================================================================
# P3: 私信增强 — 获取会话列表
# POST /get-conversations — 返回所有聊过天的用户及最后消息预览、未读数
# =============================================================================
class Get_Conversations_Req(BaseModel):
    cookie: str

@app.post("/get-conversations")
def get_conversations(body: Get_Conversations_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    # 获取所有与我交换过消息的唯一用户（含最后消息ID）
    conversations = db_fetchall("""
            SELECT
                CASE WHEN m.sender_id = ? THEN m.receiver_id ELSE m.sender_id END as other_id,
                u.username, u.nickname, u.avatar,
                MAX(m.id) as last_msg_id
            FROM offline_messages m
            JOIN users u ON u.id = CASE WHEN m.sender_id = ? THEN m.receiver_id ELSE m.sender_id END
            WHERE m.sender_id = ? OR m.receiver_id = ?
            GROUP BY other_id
            ORDER BY last_msg_id DESC
    """, (user_id, user_id, user_id, user_id))
    result = []
    for c in conversations:
        last_msg = db_fetchone(
                "SELECT content, sent_at, sender_id FROM offline_messages WHERE id = ?",
                (c["last_msg_id"],)
                )
        unread = db_fetchone(
                "SELECT COUNT(*) as cnt FROM offline_messages WHERE sender_id = ? AND receiver_id = ? AND is_read = 0",
                (c["other_id"], user_id)
                )
        result.append({
            "user_id": c["other_id"],
            "username": c["username"],
            "nickname": c["nickname"],
            "avatar": c["avatar"],
            "last_message": last_msg["content"] if last_msg else "",
            "last_time": last_msg["sent_at"] if last_msg else "",
            "last_is_mine": (last_msg["sender_id"] == user_id) if last_msg else False,
            "unread_count": unread["cnt"] if unread else 0
        })
    return {"conversations": result}

# =============================================================================
# P3: 群聊增强 — 获取单个群详情
# POST /get-group-info
# =============================================================================
class Get_Group_Info_Req(BaseModel):
    cookie: str
    group_id: int

@app.post("/get-group-info")
def get_group_info(body: Get_Group_Info_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    group = db_fetchone("""
            SELECT g.id, g.name, g.owner_id, g.created_at,
                   u.username as owner_username, u.nickname as owner_nickname,
                   (SELECT COUNT(*) FROM user_in_group WHERE group_id = g.id) as member_count
            FROM groups g
            JOIN users u ON u.id = g.owner_id
            WHERE g.id = ?
    """, (body.group_id,))
    if not group:
        return {"error": "Group not exist."}
    my_role = db_fetchone(
            "SELECT role FROM user_in_group WHERE group_id = ? AND user_id = ?",
            (body.group_id, user_id)
            )
    return {
        "id": group["id"],
        "name": group["name"],
        "owner_id": group["owner_id"],
        "owner_username": group["owner_username"],
        "owner_nickname": group["owner_nickname"],
        "created_at": group["created_at"],
        "member_count": group["member_count"],
        "my_role": my_role["role"] if my_role else None
    }

# =============================================================================
# P3: 群聊增强 — 删除群消息（发送者或群主可删）
# POST /delete-group-msg
# =============================================================================
class Delete_Group_Msg_Req(BaseModel):
    cookie: str
    group_id: int
    message_id: int

@app.post("/delete-group-msg")
def delete_group_msg(body: Delete_Group_Msg_Req):
    row = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    msg = db_fetchone(
            "SELECT sender_id, group_id FROM group_messages WHERE id = ?",
            (body.message_id,)
            )
    if not msg:
        return {"error": "Message not exist."}
    if msg["group_id"] != body.group_id:
        return {"error": "Message not in this group."}
    # 发送者或群主可删
    group = db_fetchone("SELECT owner_id FROM groups WHERE id = ?", (body.group_id,))
    if msg["sender_id"] != user_id and (not group or group["owner_id"] != user_id):
        return {"error": "Permission denied."}
    db_execute("DELETE FROM group_messages WHERE id = ?", (body.message_id,))
    db_commit()
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run(app, port = 18999)
