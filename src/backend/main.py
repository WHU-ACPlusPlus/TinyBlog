#!/usr/bin/env -S uv run python3
# Tiny Blog - 微微博最小可用后端主文件
# Copyright (c) 2026 Becharm Kon. All Rights Reserved.

# Databases

import sqlite3, bcrypt, secrets, threading, base64

conn = sqlite3.connect("main.db", check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")

# 线程锁：保护所有数据库操作，防止并发读同一连接导致段错误
db_lock = threading.Lock()

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
    existence = db_fetchone(
            "SELECT id FROM users WHERE id = ?",
            (body.to_whom_id,)
            )
    if not existence:
        return {"error": "Bad `to_whom_id`"}
    db_execute("INSERT INTO offline_messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
            (user_id, body.to_whom_id, body.content,)
            )
    db_execute(
            "INSERT INTO notifications (user_id, type, from_user_id, content) VALUES (?, 'message', ?, ?)",
            (body.to_whom_id, user_id, body.content[:50])
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
    db_commit()
    post_id = db_lastrowid()
    for i in range(len(body.media)):
        db_execute(
                "INSERT INTO post_media (post_id, offset, content) VALUES (?, ?, ?)",
                (post_id, i, body.media[i],)
                )
    db_commit()
    return {"status": "success"}

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

    # 1. 关注的人发的帖子
    followed = db_fetchall(f"""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        WHERE p.publisher_id IN (
            SELECT followee FROM following WHERE follower = ?
        ){before_clause}
    """, (user_id,) + before_param)

    # 2. 最火的帖子
    hot = db_fetchall(f"""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        WHERE p.like_num > 0{before_clause}
        ORDER BY p.like_num DESC LIMIT 50
    """, before_param)

    # 3. 最新的帖子
    recent = db_fetchall(f"""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        WHERE 1=1{before_clause}
        ORDER BY p.created_at DESC LIMIT 50
    """, before_param)

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

if __name__ == "__main__":
    uvicorn.run(app, port = 18999)
