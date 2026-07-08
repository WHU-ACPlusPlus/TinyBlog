#!/usr/bin/env -S uv run python3
# Tiny Blog - 微微博最小可用后端主文件
# Copyright (c) 2026 Becharm Kon. All Rights Reserved.

# Databases

import re, sqlite3, bcrypt, secrets, threading

conn = sqlite3.connect("main.db", check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")

# 线程锁：保护所有数据库操作，防止并发读同一连接导致段错误
db_lock = threading.RLock()

# 用 conn.execute() 替代全局 cursor，每次获取新游标，线程安全
_last_cursor = None

def db_execute(sql, params=()):
    global _last_cursor
    with db_lock:
        _last_cursor = conn.execute(sql, params)
        return _last_cursor

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
    with db_lock:
        return _last_cursor.lastrowid if _last_cursor is not None else -1

def db_rowcount():
    with db_lock:
        if _last_cursor is not None:
            return _last_cursor.rowcount
        return 0

# =============================================================================
# 数据库初始化
# =============================================================================

def init_db():
    """建表 & 向后兼容列补丁，模块加载时自动执行。"""
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
            repost_id INTEGER DEFAULT NULL,
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
    db_execute("""
        CREATE TABLE IF NOT EXISTS read_posts (
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            read_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)
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
    # 标签系统：帖子 ↔ 标签 多对多关联
    db_execute("""
        CREATE TABLE IF NOT EXISTS post_tags (
            post_id INTEGER NOT NULL,
            tag TEXT NOT NULL COLLATE NOCASE,
            PRIMARY KEY (post_id, tag),
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        )
    """)
    db_execute("CREATE INDEX IF NOT EXISTS idx_post_tags_tag ON post_tags(tag)")

    # --- LYC 社交模块：关注/屏蔽/静音 ---
    db_execute("""
        CREATE TABLE IF NOT EXISTS follows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id INTEGER NOT NULL,
            following_id INTEGER NOT NULL,
            show_reblogs INTEGER DEFAULT 1,
            notify INTEGER DEFAULT 0,
            languages TEXT DEFAULT '[]',
            created_at TEXT NOT NULL,
            UNIQUE(follower_id, following_id)
        )
    """)
    db_execute("""
        CREATE TABLE IF NOT EXISTS follow_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    db_execute("""
        CREATE TABLE IF NOT EXISTS blocks (
            user_id INTEGER NOT NULL,
            blocked_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_id, blocked_id)
        )
    """)
    db_execute("""
        CREATE TABLE IF NOT EXISTS mutes (
            user_id INTEGER NOT NULL,
            muted_id INTEGER NOT NULL,
            mute_notifications INTEGER DEFAULT 1,
            expire_at TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_id, muted_id)
        )
    """)
    db_execute("""
        CREATE TABLE IF NOT EXISTS domain_blocks (
            user_id INTEGER NOT NULL,
            domain TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_id, domain)
        )
    """)
    # --- LYC 社交模块：通知 ---
    db_execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            notification_type TEXT NOT NULL,
            from_user_id INTEGER,
            post_id INTEGER,
            is_read INTEGER DEFAULT 0,
            report_data TEXT,
            relationship_severance TEXT,
            moderation_warning TEXT,
            annual_report TEXT,
            created_at TEXT NOT NULL
        )
    """)
    # --- LYC 社交模块：推送订阅 ---
    db_execute("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            endpoint TEXT NOT NULL,
            p256dh_key TEXT NOT NULL,
            auth_key TEXT NOT NULL,
            alerts TEXT DEFAULT '{}'
        )
    """)
    # --- LYC 社交模块：帖子 @提及 ---
    db_execute("""
        CREATE TABLE IF NOT EXISTS post_mentions (
            post_id INTEGER NOT NULL,
            mentioned_user_id INTEGER NOT NULL,
            PRIMARY KEY (post_id, mentioned_user_id)
        )
    """)

    # 向后兼容 & LYC 社交模块兼容列
    # --- users 表补列 ---
    for col in ["avatar", "signature", "display_name", "note", "acct"]:
        try:
            db_execute(f"ALTER TABLE users ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
    for col in ["locked", "bot", "limited"]:
        try:
            db_execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
    for col in ["followers_count", "following_count", "statuses_count"]:
        try:
            db_execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
    # users.url — 可能已通过旧版添加，用 try 包裹
    try:
        db_execute("ALTER TABLE users ADD COLUMN url TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        db_execute("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    # users.role — LYC 社交模块所需
    try:
        db_execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'normal'")
    except sqlite3.OperationalError:
        pass

    # --- posts 表补列 ---
    for col in ["spoiler_text"]:
        try:
            db_execute(f"ALTER TABLE posts ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
    for col in ["sensitive"]:
        try:
            db_execute(f"ALTER TABLE posts ADD COLUMN {col} INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
    for col in ["visibility"]:
        try:
            db_execute(f"ALTER TABLE posts ADD COLUMN {col} TEXT DEFAULT 'public'")
        except sqlite3.OperationalError:
            pass
    for col in ["author_id"]:
        try:
            db_execute(f"ALTER TABLE posts ADD COLUMN {col} INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
    for col in ["favourites_count", "reblogs_count", "replies_count", "in_reply_to_id"]:
        try:
            db_execute(f"ALTER TABLE posts ADD COLUMN {col} INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
    for col in ["edited_at", "url"]:
        try:
            db_execute(f"ALTER TABLE posts ADD COLUMN {col} TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
    # 同步 author_id = publisher_id（已有数据 + 新数据通过 trigger）
    db_execute("UPDATE posts SET author_id = publisher_id WHERE author_id = 0")
    # 同步 display_name = nickname、acct = username
    db_execute("UPDATE users SET display_name = nickname WHERE display_name = ''")
    db_execute("UPDATE users SET acct = username WHERE acct = ''")
    # 标签搜索所需的 tags 表（与 post_tags 共存，用于 FTS）
    db_execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL COLLATE NOCASE,
            total_uses INTEGER DEFAULT 1,
            total_accounts INTEGER DEFAULT 1
        )
    """)
    # 从已有 post_tags 回填 tags 表（幂等）
    db_execute("""
        INSERT OR IGNORE INTO tags (name) SELECT DISTINCT tag FROM post_tags
    """)
    # tags 表兼容列（LYC search_tags 需要 url / created_at）
    for col in ["url"]:
        try:
            db_execute(f"ALTER TABLE tags ADD COLUMN {col} TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
    try:
        db_execute("ALTER TABLE tags ADD COLUMN created_at TEXT DEFAULT (datetime('now'))")
    except sqlite3.OperationalError:
        pass
    # 新帖子自动同步 author_id = publisher_id
    db_execute("""
        CREATE TRIGGER IF NOT EXISTS trg_posts_author_id
        AFTER INSERT ON posts
        FOR EACH ROW
        WHEN NEW.author_id = 0 OR NEW.author_id IS NULL
        BEGIN
            UPDATE posts SET author_id = NEW.publisher_id WHERE id = NEW.id;
        END
    """)
    db_commit()

init_db()

# 将 social 数据库层绑定到 master 的连接和锁
from social import db as social_db
social_db.bind(conn, db_lock)

# 初始化 FTS5 全文搜索索引
from social import search as social_search
try:
    social_search.init_fts()
    print("[social] FTS5 索引初始化完成")
except Exception as e:
    print(f"[social] FTS5 索引初始化警告: {e}")

# Server Functions

import fastapi, uvicorn, random

app = fastapi.FastAPI(title = "Tiny Blog")

# 挂载社交功能路由
from routes_social import router as social_router
app.include_router(social_router)

@app.get("/ping") # For testing only
def ping():
    return {"message": "Pong!"}

# ── 标签工具函数 ──

def extract_tags(text: str) -> list[str]:
    """从文本中提取所有 #标签（去重、小写、限制长度）。"""
    if not text:
        return []
    tags = re.findall(r'#([^\s#,，。、！？;；：:""''【】（）()]+)', text)
    seen = set()
    result = []
    for t in tags:
        t = t.strip().lower()[:32]  # 统一小写，最长 32 字符
        if t and t not in seen:
            seen.add(t)
            result.append(t)
    return result

def write_post_tags(post_id: int, tags: list[str]):
    """将标签列表写入 post_tags 表，并同步到 tags 表（FTS 搜索用）。"""
    for tag in tags:
        db_execute(
            "INSERT OR IGNORE INTO post_tags (post_id, tag) VALUES (?, ?)",
            (post_id, tag)
        )
        db_execute(
            "INSERT OR IGNORE INTO tags (name) VALUES (?)",
            (tag,)
        )
    if tags:
        db_commit()

def get_post_with_media(post_row) -> dict:
    """将一行帖子 row 组装为标准返回格式（含媒体）。"""
    media = db_fetchall(
        "SELECT offset, content FROM post_media WHERE post_id = ? ORDER BY offset",
        (post_row["id"],)
    )
    tags = db_fetchall(
        "SELECT tag FROM post_tags WHERE post_id = ?", (post_row["id"],)
    )
    return {
        "id": post_row["id"],
        "publisher_id": post_row["publisher_id"],
        "username": post_row["username"],
        "nickname": post_row["nickname"],
        "content": post_row["content"],
        "like_num": post_row["like_num"],
        "favourites_count": post_row["favourites_count"],
        "reblogs_count": post_row["reblogs_count"],
        "replies_count": post_row["replies_count"],
        "created_at": post_row["created_at"],
        "repost_id": post_row["repost_id"],
        "media": [dict(m) for m in media],
        "tags": [r["tag"] for r in tags],
    }

# ── 请求/响应模型 ──
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

# ── 前端登录确认步骤 ──
class Login_Finish_Req(BaseModel):
    cookie: str

@app.post("/login-finish")
def login_finish(body: Login_Finish_Req):
    """前端双步登录的第二步：确认 cookie 有效并返回。"""
    row = db_fetchone(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    )
    if not row:
        return {"error": "Bad cookie."}
    return {"cookie": body.cookie}

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
            SELECT u.id, u.username, u.nickname
            FROM following f
            JOIN users u ON u.id == f.follower
            WHERE f.followee == ?
            """,
            (user_id,)
            )]
    followees = [dict(now) for now in db_fetchall(
            """
            SELECT u.id, u.username, u.nickname
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
    # 双写：TinyBlog 的 following 表和 LYC 的 follows 表
    db_execute("INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)",
            (user_id, body.followee_id)
            )
    from datetime import datetime
    db_execute(
        "INSERT OR IGNORE INTO follows (follower_id, following_id, created_at) VALUES (?, ?, ?)",
        (user_id, body.followee_id, datetime.utcnow().isoformat())
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
    db_execute("DELETE FROM follows WHERE follower_id = ? AND following_id = ?",
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
                "UPDATE posts SET like_num = like_num + 1, favourites_count = favourites_count + 1 WHERE id = ?",
                (body.post_id,)
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
                "UPDATE posts SET like_num = MAX(0, like_num - 1), favourites_count = MAX(0, favourites_count - 1) WHERE id = ?",
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
    db_execute(
            "UPDATE posts SET replies_count = replies_count + 1 WHERE id = ?",
            (body.post_id,)
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

def _ensure_private_messages_table():
    """确保 private_messages 表存在（幂等）。"""
    try:
        db_execute("SELECT 1 FROM private_messages LIMIT 1")
    except sqlite3.OperationalError:
        db_execute("""
            CREATE TABLE IF NOT EXISTS private_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                sent_at TEXT NOT NULL DEFAULT (datetime('now')),
                is_read INTEGER DEFAULT 0
            )
        """)
        db_commit()

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
    existence = db_fetchone(
            "SELECT id FROM users WHERE id = ?",
            (body.to_whom_id,)
            )
    if not existence:
        return {"error": "Bad `to_whom_id`"}
    # 双写：offline_messages（旧 TinyBlog）+ private_messages（LYC 会话系统）
    db_execute("INSERT INTO offline_messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
            (user_id, body.to_whom_id, body.content,)
            )
    _ensure_private_messages_table()
    from datetime import datetime
    db_execute(
        "INSERT INTO private_messages (sender_id, receiver_id, content, sent_at) VALUES (?, ?, ?, ?)",
        (user_id, body.to_whom_id, body.content, datetime.utcnow().isoformat())
    )
    db_commit()
    return {"status": "success"}

class Recv_Msg(BaseModel):
    cookie: str

@app.post("/recv-msg")
def recv_msg(body: Recv_Msg):
    user_id = db_fetchone(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    if not user_id:
        return {"error": "Bad cookie."}
    user_id = user_id["user_id"]
    msgs = [dict(row) for row in db_fetchall(
            "SELECT sender_id, sent_at, content FROM offline_messages WHERE receiver_id = ?",
            (user_id,)
            )]
    db_execute(
            "DELETE FROM offline_messages WHERE receiver_id = ?",
            (user_id,)
            )
    db_commit()
    return {"msgs": msgs}

class Pub_Post(BaseModel):
    cookie: str
    text: str
    media: list[str] = []

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
    for medium in body.media:
        if len(medium) > (1 << 24):
            return {"error": "Media cannot be larger than 16MiB."}
    db_execute("INSERT INTO posts (publisher_id, content) VALUES (?, ?)",
            (user_id, body.text)
            )
    post_id = db_lastrowid()
    for i in range(len(body.media)):
        db_execute(
                "INSERT INTO post_media (post_id, offset, content) VALUES (?, ?, ?)",
                (post_id, i, body.media[i],)
                )
    # 提取并写入 #标签
    tags = extract_tags(body.text)
    write_post_tags(post_id, tags)
    db_commit()
    return {"status": "success", "post_id": post_id, "tags": tags}

class Post_Fetch(BaseModel):
    cookie: str
    count: int = 20

@app.post("/post-fetch")
def post_fetch(body: Post_Fetch):
    print(f"DEBUG post_fetch: cookie={repr(body.cookie)}, count={body.count}", flush=True)
    row = db_fetchone(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 1. 关注的人发的帖子
    followed = db_fetchall("""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        WHERE p.publisher_id IN (
            SELECT followee FROM following WHERE follower = ?
        )
    """, (user_id,))

    # 2. 最火的帖子
    hot = db_fetchall("""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        WHERE p.like_num > 0
        ORDER BY p.like_num DESC LIMIT 50
    """)

    # 3. 最新的帖子
    recent = db_fetchall("""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        ORDER BY p.created_at DESC LIMIT 50
    """)

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

    random.shuffle(combined)

    # 截断到 count 条（计为最大数，不足则全返），返回 ID 列表
    result = combined[:body.count]
    for post in result:
        db_execute(
            "INSERT OR IGNORE INTO read_posts (user_id, post_id) VALUES (?, ?)",
            (user_id, post["id"])
        )
    db_commit()
    return {"posts": [p["id"] for p in result], "count": len(result)}

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

    post = db_fetchone(
        "SELECT p.*, u.username, u.nickname FROM posts p JOIN users u ON u.id = p.publisher_id WHERE p.id = ?",
        (body.post_id,)
    )
    if not post:
        return {"error": "Post not found."}

    media = db_fetchall(
        "SELECT offset, content FROM post_media WHERE post_id = ? ORDER BY offset",
        (body.post_id,)
    )

    return {
        "id": post["id"],
        "publisher_id": post["publisher_id"],
        "username": post["username"],
        "nickname": post["nickname"],
        "content": post["content"],
        "like_num": post["like_num"],
        "favourites_count": post["favourites_count"],
        "reblogs_count": post["reblogs_count"],
        "replies_count": post["replies_count"],
        "created_at": post["created_at"],
        "repost_id": post["repost_id"],
        "media": [dict(m) for m in media],
        "tags": [r["tag"] for r in db_fetchall("SELECT tag FROM post_tags WHERE post_id = ?", (body.post_id,))]
    }

# =============================================================================
# 标签系统
# =============================================================================

class Posts_By_Tag_Req(BaseModel):
    cookie: str
    tag: str
    count: int = 20
    offset: int = 0

@app.post("/get-posts-by-tag")
def get_posts_by_tag(body: Posts_By_Tag_Req):
    """按标签获取帖子，按发布时间倒序。"""
    row = db_fetchone(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    posts = db_fetchall("""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN post_tags pt ON pt.post_id = p.id
        JOIN users u ON u.id = p.publisher_id
        WHERE pt.tag = ?
        ORDER BY p.created_at DESC
        LIMIT ? OFFSET ?
    """, (body.tag.strip().lower()[:32], body.count, body.offset))

    result = []
    for p in posts:
        result.append(get_post_with_media(p))
        db_execute(
            "INSERT OR IGNORE INTO read_posts (user_id, post_id) VALUES (?, ?)",
            (user_id, p["id"])
        )
    db_commit()
    return {"posts": result, "count": len(result)}

class Interest_Tags_Req(BaseModel):
    cookie: str

@app.post("/get-user-interest-tags")
def get_user_interest_tags(body: Interest_Tags_Req):
    """分析用户的兴趣标签：根据点赞/评论/发帖中的标签聚合。"""
    row = db_fetchone(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 加权聚合：自己发帖 ×3，点赞 ×2，评论 ×1
    tags_score = {}

    # 自己发帖中的标签（权重 3）
    for r in db_fetchall("""
            SELECT pt.tag, COUNT(*) AS cnt
            FROM post_tags pt
            JOIN posts p ON p.id = pt.post_id
            WHERE p.publisher_id = ?
            GROUP BY pt.tag
    """, (user_id,)):
        tags_score[r["tag"]] = tags_score.get(r["tag"], 0) + r["cnt"] * 3

    # 点赞帖子的标签（权重 2）
    for r in db_fetchall("""
            SELECT pt.tag, COUNT(*) AS cnt
            FROM post_tags pt
            JOIN liking_users lu ON lu.post_id = pt.post_id
            WHERE lu.liker_id = ?
            GROUP BY pt.tag
    """, (user_id,)):
        tags_score[r["tag"]] = tags_score.get(r["tag"], 0) + r["cnt"] * 2

    # 评论帖子的标签（权重 1）
    for r in db_fetchall("""
            SELECT pt.tag, COUNT(*) AS cnt
            FROM post_tags pt
            JOIN comments c ON c.post_id = pt.post_id
            WHERE c.commenter_id = ?
            GROUP BY pt.tag
    """, (user_id,)):
        tags_score[r["tag"]] = tags_score.get(r["tag"], 0) + r["cnt"]

    sorted_tags = sorted(tags_score.items(), key=lambda x: -x[1])
    return {"tags": [{"tag": t, "score": s} for t, s in sorted_tags[:20]]}

class Recommend_Posts_Req(BaseModel):
    cookie: str
    count: int = 20

@app.post("/recommend-posts")
def recommend_posts(body: Recommend_Posts_Req):
    """根据用户兴趣标签推荐未读帖子。"""
    row = db_fetchone(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    )
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]

    # 1. 获取用户的兴趣标签（取前 10 个）
    tags_score = {}
    for r in db_fetchall("""
            SELECT pt.tag, COUNT(*) * 3 AS cnt
            FROM post_tags pt JOIN posts p ON p.id = pt.post_id
            WHERE p.publisher_id = ? GROUP BY pt.tag
    """, (user_id,)):
        tags_score[r["tag"]] = tags_score.get(r["tag"], 0) + r["cnt"]
    for r in db_fetchall("""
            SELECT pt.tag, COUNT(*) * 2 AS cnt
            FROM post_tags pt JOIN liking_users lu ON lu.post_id = pt.post_id
            WHERE lu.liker_id = ? GROUP BY pt.tag
    """, (user_id,)):
        tags_score[r["tag"]] = tags_score.get(r["tag"], 0) + r["cnt"]

    if not tags_score:
        return {"posts": [], "count": 0}

    top_tags = [t for t, _ in sorted(tags_score.items(), key=lambda x: -x[1])[:10]]

    # 2. 查找匹配这些标签的未读帖子，按匹配标签数排序
    placeholders = ",".join("?" for _ in top_tags)
    posts = db_fetchall(f"""
        SELECT p.*, u.username, u.nickname, COUNT(pt.tag) AS match_count
        FROM posts p
        JOIN post_tags pt ON pt.post_id = p.id
        JOIN users u ON u.id = p.publisher_id
        WHERE pt.tag IN ({placeholders})
          AND p.id NOT IN (SELECT post_id FROM read_posts WHERE user_id = ?)
          AND p.publisher_id != ?
        GROUP BY p.id
        ORDER BY match_count DESC, p.created_at DESC
        LIMIT ?
    """, top_tags + [user_id, user_id, body.count])

    result = []
    for p in posts:
        result.append(get_post_with_media(p))
        db_execute(
            "INSERT OR IGNORE INTO read_posts (user_id, post_id) VALUES (?, ?)",
            (user_id, p["id"])
        )
    db_commit()
    return {"posts": result, "count": len(result)}

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
            "SELECT last_read_id FROM user_in_group WHERE group_id = ? AND user_id = ?",
            (body.group_id, user_id)
            )
    if not membership:
        return {"error": "You are not in this group."}
    messages = db_fetchall("""
            SELECT gm.id, gm.sender_id, u.username, u.nickname, gm.content, gm.sent_at
            FROM group_messages gm
            JOIN users u ON u.id = gm.sender_id
            WHERE gm.group_id = ? AND gm.id > ?
            ORDER BY gm.id ASC
            LIMIT ?
    """, (body.group_id, membership["last_read_id"], body.count))
    if messages:
        db_execute(
                "UPDATE user_in_group SET last_read_id = ? WHERE group_id = ? AND user_id = ?",
                (messages[-1]["id"], body.group_id, user_id)
                )
        db_commit()
    return {"messages": [dict(m) for m in messages]}

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
            SELECT u.id, u.username, u.nickname, ug.role, ug.joined_at
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
            SELECT g.id, g.name, g.owner_id, ug.role, ug.joined_at
            FROM user_in_group ug
            JOIN groups g ON g.id = ug.group_id
            WHERE ug.user_id = ?
            ORDER BY ug.joined_at DESC
    """, (user_id,))
    return {"groups": [dict(g) for g in groups]}

# =============================================================================
# 用户系统：登出
# POST /logout — 删除当前token使其立即失效
# =============================================================================
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
            "favourites_count": p["favourites_count"],
            "reblogs_count": p["reblogs_count"],
            "replies_count": p["replies_count"],
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
    db_execute(
            "UPDATE posts SET reblogs_count = reblogs_count + 1 WHERE id = ?",
            (body.post_id,)
            )
    db_commit()
    return {"status": "success", "new_post_id": db_lastrowid()}

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
# 缺失的前端 API 端点
# =============================================================================

# ── Cookie 验证 / 获取用户资料 ──
@app.post("/check-cookie")
def check_cookie(body: dict = {}):
    cookie = body.get("cookie", "")
    if not cookie:
        return {"valid": False, "user_id": 0}
    row = db_fetchone("SELECT user_id FROM cookies WHERE token = ?", (cookie,))
    if not row:
        return {"valid": False, "user_id": 0}
    uid = row["user_id"]
    u = db_fetchone("SELECT id, username, nickname, avatar, signature, role FROM users WHERE id = ?", (uid,))
    if not u:
        return {"valid": False, "user_id": 0}
    return {
        "valid": True,
        "user_id": uid,
        "id": u["id"],
        "username": u["username"],
        "nickname": u["nickname"],
        "avatar": u["avatar"] or "",
        "signature": u["signature"] or "",
        "role": u["role"] or "normal",
    }

# ── 注册流程（简化：跳过邮箱验证）──
class RegisterVerifyReq(BaseModel):
    cookie: str
    captcha: str = ""
    email: str = ""

@app.post("/register-verify")
def register_verify(body: RegisterVerifyReq):
    # 验证 cookie 有效
    row = db_fetchone("SELECT user_id FROM cookies WHERE token = ?", (body.cookie,))
    if not row:
        return {"error": "Bad cookie."}
    return {"status": "ok"}

class RegisterFinishReq(BaseModel):
    cookie: str
    email_code: str = ""

@app.post("/register-finish")
def register_finish(body: RegisterFinishReq):
    row = db_fetchone("SELECT user_id FROM cookies WHERE token = ?", (body.cookie,))
    if not row:
        return {"error": "Bad cookie."}
    return {"cookie": body.cookie}

# ── 登录流程（简化：跳过验证码/邮箱）──
class LoginVerifyCaptchaReq(BaseModel):
    cookie: str
    captcha: str = ""

@app.post("/login-verify-captcha")
def login_verify_captcha(body: LoginVerifyCaptchaReq):
    return {"status": "ok"}

class LoginSendEmailReq(BaseModel):
    cookie: str

@app.post("/login-send-email-code")
def login_send_email_code(body: LoginSendEmailReq):
    return {"status": "ok"}

class LoginVerifyEmailReq(BaseModel):
    cookie: str
    email_code: str = ""

@app.post("/login-verify-email")
def login_verify_email(body: LoginVerifyEmailReq):
    return {"status": "ok"}

# ── 用户帖子列表 ──
class UserPostsReq(BaseModel):
    cookie: str
    publisher_id: int

@app.post("/get-user-posts")
def get_user_posts(body: UserPostsReq):
    row = db_fetchone("SELECT user_id FROM cookies WHERE token = ?", (body.cookie,))
    if not row:
        return {"error": "Bad cookie."}
    posts = db_fetchall(
        "SELECT id FROM posts WHERE publisher_id = ? ORDER BY id DESC",
        (body.publisher_id,)
    )
    return {"post_ids": [p["id"] for p in posts]}

@app.post("/get-user-posts-detail")
def get_user_posts_detail(body: UserPostsReq):
    row = db_fetchone("SELECT user_id FROM cookies WHERE token = ?", (body.cookie,))
    if not row:
        return {"error": "Bad cookie."}
    post_rows = db_fetchall(
        "SELECT p.*, u.username, u.nickname FROM posts p JOIN users u ON u.id = p.publisher_id WHERE p.publisher_id = ? ORDER BY p.id DESC",
        (body.publisher_id,)
    )
    posts = []
    for p in post_rows:
        media = db_fetchall("SELECT content FROM post_media WHERE post_id = ?", (p["id"],))
        tags = db_fetchall("SELECT tag FROM post_tags WHERE post_id = ?", (p["id"],))
        posts.append({
            "id": p["id"],
            "publisher_id": p["publisher_id"],
            "username": p["username"],
            "nickname": p["nickname"],
            "content": p["content"],
            "like_num": p["like_num"],
            "favourites_count": p["favourites_count"],
            "reblogs_count": p["reblogs_count"],
            "replies_count": p["replies_count"],
            "created_at": p["created_at"],
            "repost_id": p["repost_id"],
            "media": [dict(m) for m in media],
            "tags": [r["tag"] for r in tags],
        })
    return {"posts": posts}

# ── 用户详情（ChatPanel 用）──
class UserDetailReq(BaseModel):
    cookie: str
    user_id: int

@app.post("/get-user-detail")
def get_user_detail(body: UserDetailReq):
    row = db_fetchone("SELECT user_id FROM cookies WHERE token = ?", (body.cookie,))
    if not row:
        return {"error": "Bad cookie."}
    me_id = row["user_id"]
    u = db_fetchone("SELECT id, username, nickname, avatar, signature FROM users WHERE id = ?", (body.user_id,))
    if not u:
        return {"error": "User not found."}
    # 检查关注状态
    is_following = db_fetchone(
        "SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?",
        (me_id, body.user_id)
    ) is not None
    is_followed_by = db_fetchone(
        "SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?",
        (body.user_id, me_id)
    ) is not None
    return {
        "id": u["id"],
        "username": u["username"],
        "nickname": u["nickname"],
        "avatar": u["avatar"] or "",
        "signature": u["signature"] or "",
        "is_following": is_following,
        "is_mutual": is_following and is_followed_by,
    }

# ── 会话列表 ──
class GetConversationsReq(BaseModel):
    cookie: str

@app.post("/get-conversations")
def get_conversations(body: GetConversationsReq):
    cookie = body.cookie
    row = db_fetchone("SELECT user_id FROM cookies WHERE token = ?", (cookie,))
    if not row:
        return {"error": "Bad cookie."}
    me_id = row["user_id"]
    _ensure_private_messages_table()
    # 从私信表中聚合出会话
    rows = db_fetchall(
        """SELECT DISTINCT
               CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END AS target_id,
               MAX(id) as last_msg_id,
               MAX(sent_at) as last_time
           FROM private_messages
           WHERE sender_id = ? OR receiver_id = ?
           GROUP BY target_id
           ORDER BY last_time DESC""",
        (me_id, me_id, me_id)
    )
    conversations = []
    for r in rows:
        target = db_fetchone("SELECT id, username, nickname, avatar FROM users WHERE id = ?", (r["target_id"],))
        if not target:
            continue
        last_msg = db_fetchone(
            "SELECT content FROM private_messages WHERE id = ?",
            (r["last_msg_id"],)
        )
        cnv = {
            "id": r["target_id"],
            "type": "private",
            "target_id": r["target_id"],
            "target_name": target["nickname"] or target["username"],
            "target_avatar": target["avatar"] or "",
            "last_message": last_msg["content"] if last_msg else "",
            "last_message_time": r["last_time"] or "",
            "unread_count": 0,
        }
        conversations.append(cnv)
    return {"conversations": conversations}

# ── 隐藏会话 ──
class HideConversationReq(BaseModel):
    cookie: str
    conversation_id: int

@app.post("/hide-conversation")
def hide_conversation(body: HideConversationReq):
    row = db_fetchone("SELECT user_id FROM cookies WHERE token = ?", (body.cookie,))
    if not row:
        return {"error": "Bad cookie."}
    return {"status": "ok"}

# ── 私信历史 ──
class PrivateMessagesReq(BaseModel):
    cookie: str
    with_user_id: int
    before_id: int = 0
    count: int = 50

@app.post("/get-private-messages")
def get_private_messages(body: PrivateMessagesReq):
    row = db_fetchone("SELECT user_id FROM cookies WHERE token = ?", (body.cookie,))
    if not row:
        return {"error": "Bad cookie."}
    me_id = row["user_id"]
    _ensure_private_messages_table()
    if body.before_id > 0:
        msgs = db_fetchall(
            """SELECT pm.*, u.username, u.nickname, u.avatar
               FROM private_messages pm
               JOIN users u ON u.id = pm.sender_id
               WHERE ((pm.sender_id = ? AND pm.receiver_id = ?) OR (pm.sender_id = ? AND pm.receiver_id = ?))
                 AND pm.id < ?
               ORDER BY pm.id DESC LIMIT ?""",
            (me_id, body.with_user_id, body.with_user_id, me_id, body.before_id, body.count)
        )
    else:
        msgs = db_fetchall(
            """SELECT pm.*, u.username, u.nickname, u.avatar
               FROM private_messages pm
               JOIN users u ON u.id = pm.sender_id
               WHERE (pm.sender_id = ? AND pm.receiver_id = ?) OR (pm.sender_id = ? AND pm.receiver_id = ?)
               ORDER BY pm.id DESC LIMIT ?""",
            (me_id, body.with_user_id, body.with_user_id, me_id, body.count)
        )
    messages = []
    for m in reversed(msgs):
        messages.append({
            "id": m["id"],
            "sender_id": m["sender_id"],
            "sender_name": m["nickname"] or m["username"],
            "sender_avatar": m["avatar"] or "",
            "content": m["content"],
            "sent_at": m["sent_at"],
            "is_read": True,
        })
    has_more = len(messages) >= body.count
    return {"messages": messages, "has_more": has_more}

# ── 搜索联系人 ──
class SearchContactsReq(BaseModel):
    cookie: str
    keyword: str
    type: str = "all"

@app.post("/search-contacts")
def search_contacts(body: SearchContactsReq):
    row = db_fetchone("SELECT user_id FROM cookies WHERE token = ?", (body.cookie,))
    if not row:
        return {"error": "Bad cookie."}
    me_id = row["user_id"]
    kw = f"%{body.keyword}%"
    users = []
    if body.type in ("all", "user"):
        for u in db_fetchall(
            "SELECT id, username, nickname, avatar FROM users WHERE username LIKE ? OR nickname LIKE ? LIMIT 20",
            (kw, kw)
        ):
            if u["id"] == me_id:
                continue
            is_following = db_fetchone(
                "SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?",
                (me_id, u["id"])
            ) is not None
            is_followed_by = db_fetchone(
                "SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?",
                (u["id"], me_id)
            ) is not None
            users.append({
                "id": u["id"],
                "username": u["username"],
                "nickname": u["nickname"],
                "avatar": u["avatar"] or "",
                "is_following": is_following,
                "is_mutual": is_following and is_followed_by,
            })
    groups = []
    if body.type in ("all", "group"):
        for g in db_fetchall(
            "SELECT id, name FROM friend_groups WHERE name LIKE ? LIMIT 20",
            (kw,)
        ):
            groups.append({
                "id": g["id"],
                "name": g["name"],
                "is_member": db_fetchone(
                    "SELECT 1 FROM friend_group_members WHERE group_id = ? AND user_id = ?",
                    (g["id"], me_id)
                ) is not None,
            })
    return {"users": users, "groups": groups}

# ── 联系人列表 ──
class GetContactsReq(BaseModel):
    cookie: str

@app.post("/get-contacts")
def get_contacts(body: GetContactsReq):
    cookie = body.cookie
    row = db_fetchone("SELECT user_id FROM cookies WHERE token = ?", (cookie,))
    if not row:
        return {"error": "Bad cookie."}
    me_id = row["user_id"]
    # 相互关注 = 好友
    mutual_ids = db_fetchall(
        """SELECT f1.following_id AS uid FROM follows f1
           JOIN follows f2 ON f1.following_id = f2.follower_id AND f1.follower_id = f2.following_id
           WHERE f1.follower_id = ?""",
        (me_id,)
    )
    mutual_set = {r["uid"] for r in mutual_ids}
    contacts = []
    for uid in mutual_set:
        u = db_fetchone("SELECT id, username, nickname, avatar FROM users WHERE id = ?", (uid,))
        if u:
            contacts.append({
                "id": u["id"], "username": u["username"],
                "nickname": u["nickname"], "avatar": u["avatar"] or "",
            })
    # 仅我关注（单向）
    followed_ids = db_fetchall(
        "SELECT following_id AS uid FROM follows WHERE follower_id = ? AND following_id NOT IN (SELECT follower_id FROM follows WHERE following_id = ?)",
        (me_id, me_id)
    )
    followed_only = []
    for r in followed_ids:
        u = db_fetchone("SELECT id, username, nickname, avatar FROM users WHERE id = ?", (r["uid"],))
        if u:
            followed_only.append({
                "id": u["id"], "username": u["username"],
                "nickname": u["nickname"], "avatar": u["avatar"] or "",
            })
    return {"contacts": contacts, "followed_only": followed_only}

# ── 群组详情 ──
class GroupDetailReq(BaseModel):
    cookie: str
    group_id: int

@app.post("/get-group-detail")
def get_group_detail(body: GroupDetailReq):
    row = db_fetchone("SELECT user_id FROM cookies WHERE token = ?", (body.cookie,))
    if not row:
        return {"error": "Bad cookie."}
    g = db_fetchone("SELECT * FROM friend_groups WHERE id = ?", (body.group_id,))
    if not g:
        return {"error": "Group not found."}
    members = db_fetchall(
        """SELECT u.id, u.username, u.nickname, u.avatar, fgm.role, fgm.joined_at
           FROM friend_group_members fgm
           JOIN users u ON u.id = fgm.user_id
           WHERE fgm.group_id = ?""",
        (body.group_id,)
    )
    member_list = []
    for m in members:
        member_list.append({
            "id": m["id"],
            "username": m["username"],
            "nickname": m["nickname"],
            "avatar": m["avatar"] or "",
            "role": m["role"] or "member",
            "joined_at": m["joined_at"] or "",
        })
    return {
        "name": g["name"],
        "members": member_list,
    }

if __name__ == "__main__":
    uvicorn.run(app, port = 18999)
