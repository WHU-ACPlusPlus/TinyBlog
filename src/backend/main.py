#!/usr/bin/env -S uv run python3
# Tiny Blog - 微微博最小可用后端主文件
# Copyright (c) 2026 Becharm Kon. All Rights Reserved.

# Databases

import sqlite3, bcrypt, secrets

conn = sqlite3.connect("main.db", check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

if __name__ == "__main__":
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    nickname TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    email_address TEXT NOT NULL DEFAULT ''
                   )
                   """)
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS cookies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                   )
                   """)
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS following (
                    follower INTEGER NOT NULL,
                    followee INTEGER NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    PRIMARY KEY (follower, followee),
                    FOREIGN KEY (follower) REFERENCES users(id),
                    FOREIGN KEY (followee) REFERENCES users(id)
                   )
                   """)
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    publisher_id INTEGER NOT NULL,
                    content TEXT,
                    like_num INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (publisher_id) REFERENCES users(id)
                   )
                   """)
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS liking_users (
                    post_id INTEGER NOT NULL,
                    liker_id INTEGER NOT NULL,
                    liked_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (liker_id) REFERENCES users(id),
                    FOREIGN KEY (post_id) REFERENCES posts(id)
                   )
                   """)
    cursor.execute("""
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
    cursor.execute("""
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
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS post_media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    offset INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    FOREIGN KEY (post_id) REFERENCES posts(id)
                   )
                   """)
    cursor.execute(
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
    conn.commit()

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
    existing = cursor.execute(
            "SELECT id FROM users WHERE username = ?",
            (body.username,)
            ).fetchone()
    if existing:
        return {"error": "Username occupied."}
    password_hash = bcrypt.hashpw(
            body.password.encode(), bcrypt.gensalt()
            ).decode()
    cursor.execute(
            "INSERT INTO users (username, nickname, password_hash) VALUES (?, ?, ?)",
            (body.username, body.nickname, password_hash)
            )
    user_id = cursor.lastrowid
    cookie = secrets.token_hex(32)
    cursor.execute(
            "INSERT INTO cookies (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user_id, cookie, "2099-12-31 13:59:59")
            )
    conn.commit()
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
    log = cursor.execute(
            "SELECT * FROM users WHERE username = ?",
            (body.username,)
            ).fetchone()
    if not log:
        return {"error": "User not exist."}
    if not bcrypt.checkpw(
            body.password.encode(), log["password_hash"].encode()
            ):
        return {"error": "Incorrect password."}
    cookie = secrets.token_hex(32)
    cursor.execute(
            "INSERT INTO cookies (user_id, token, expires_at) VALUES (?, ?, ?)",
            (log["id"], cookie, "2099-12-31 13:59:59")
            )
    conn.commit()
    return {"cookie": cookie}

class Get_Follower(BaseModel):
    cookie: str

@app.post("/get-follow-list")
def get_follow_list(body: Get_Follower):
    log = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not log:
        return {"error": "Bad cookie."}
    user_id = log["user_id"]
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

class Follow_Req(BaseModel):
    cookie: str
    followee_id: int

@app.post("/follow")
def follow(body: Follow_Req):
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    if user_id == body.followee_id:
        return {"error": "Cannot follow yourself."}
    target = cursor.execute(
            "SELECT id FROM users WHERE id = ?",
            (body.followee_id,)
            ).fetchone()
    if not target:
        return {"error": "User not exist."}
    cursor.execute(
            "INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)",
            (user_id, body.followee_id)
            )
    conn.commit()
    return {"status": "success"}

@app.post("/unfollow")
def unfollow(body: Follow_Req):
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    cursor.execute(
            "DELETE FROM following WHERE follower = ? AND followee = ?",
            (user_id, body.followee_id)
            )
    conn.commit()
    return {"status": "success"}

class Like_Req(BaseModel):
    cookie: str
    post_id: int

@app.post("/like")
def like(body: Like_Req):
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    post = cursor.execute(
            "SELECT id FROM posts WHERE id = ?",
            (body.post_id,)
            ).fetchone()
    if not post:
        return {"error": "Post not exist."}
    cursor.execute(
            "INSERT OR IGNORE INTO liking_users (post_id, liker_id) VALUES (?, ?)",
            (body.post_id, user_id)
            )
    if cursor.rowcount > 0:
        cursor.execute(
                "UPDATE posts SET like_num = like_num + 1 WHERE id = ?",
                (body.post_id,)
                )
    conn.commit()
    return {"status": "success"}

@app.post("/unlike")
def unlike(body: Like_Req):
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    cursor.execute(
            "DELETE FROM liking_users WHERE post_id = ? AND liker_id = ?",
            (body.post_id, user_id)
            )
    if cursor.rowcount > 0:
        cursor.execute(
                "UPDATE posts SET like_num = like_num - 1 WHERE id = ?",
                (body.post_id,)
                )
    conn.commit()
    return {"status": "success"}

class Comment_Req(BaseModel):
    cookie: str
    post_id: int
    content: str

@app.post("/comment")
def comment(body: Comment_Req):
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    if not body.content:
        return {"error": "Empty comment not allowed."}
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

class Get_Comments_Req(BaseModel):
    cookie: str
    post_id: int

@app.post("/get-comments")
def get_comments(body: Get_Comments_Req):
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
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

class Send_Msg(BaseModel):
    cookie: str
    to_whom_id: int
    content: str

@app.post("/send-msg")
def send_msg(body: Send_Msg):
    user_id = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not user_id:
        return {"error": "Bad cookie."}
    user_id = user_id["user_id"]
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
    return {"stauts": "success"}

class Recv_Msg(BaseModel):
    cookie: str

@app.post("/recv-msg")
def recv_msg(body: Recv_Msg):
    user_id = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not user_id:
        return {"error": "Bad cookie."}
    user_id = user_id["user_id"]
    cursor.execute(
            "SELECT sender_id, sent_at, content FROM offline_messages WHERE receiver_id = ?",
            (user_id,)
            )
    msgs = [dict(row) for row in cursor.fetchall()]
    cursor.execute(
            "DELETE FROM offline_messages WHERE receiver_id = ?",
            (user_id,)
            )
    conn.commit()
    return {"msgs": msgs}

class Pub_Post(BaseModel):
    cookie: str
    text: str
    media: list[str] = []

@app.post("/pub-post")
def pub_post(body: Pub_Post):
    user_id = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
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
    cursor.execute(
            "INSERT INTO posts (publisher_id, content) VALUES (?, ?)",
            (user_id, body.text)
            )
    conn.commit()
    post_id = cursor.lastrowid
    for i in range(len(body.media)):
        cursor.execute(
                "INSERT INTO post_media (post_id, offset, content) VALUES (?, ?, ?)",
                (post_id, i, body.media[i],)
                )
    conn.commit()
    return {"status": "success"}

class Post_Fetch(BaseModel):
    cookie: str
    count: int = 20

@app.post("/post-fetch")
def post_fetch(body: Post_Fetch):
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

    # 2. 最火的帖子
    hot = cursor.execute("""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        WHERE p.like_num > 0
        ORDER BY p.like_num DESC LIMIT 50
    """).fetchall()

    # 3. 最新的帖子
    recent = cursor.execute("""
        SELECT p.*, u.username, u.nickname
        FROM posts p
        JOIN users u ON u.id = p.publisher_id
        ORDER BY p.created_at DESC LIMIT 50
    """).fetchall()

    # 排除已读
    seen = set()
    for r in cursor.execute(
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
        cursor.execute(
            "INSERT OR IGNORE INTO read_posts (user_id, post_id) VALUES (?, ?)",
            (user_id, post["id"])
        )
    conn.commit()
    return {"posts": [p["id"] for p in result], "count": len(result)}

class Get_Post(BaseModel):
    cookie: str
    post_id: int

@app.post("/get-post")
def get_post(body: Get_Post):
    row = cursor.execute(
        "SELECT user_id FROM cookies WHERE token = ?",
        (body.cookie,)
    ).fetchone()
    if not row:
        return {"error": "Bad cookie."}

    post = cursor.execute(
        "SELECT p.*, u.username, u.nickname FROM posts p JOIN users u ON u.id = p.publisher_id WHERE p.id = ?",
        (body.post_id,)
    ).fetchone()
    if not post:
        return {"error": "Post not found."}

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

if __name__ == "__main__":
    uvicorn.run(app, port = 18999)
