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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            owner_id INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
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
    # 为旧数据库补加 repost_id 列（SQLite 不支持 IF NOT EXISTS for ALTER，用 try 兼容）
    try:
        cursor.execute("ALTER TABLE posts ADD COLUMN repost_id INTEGER DEFAULT NULL")
    except:
        pass
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            bookmarked_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)
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
    return {"status": "success"}

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
        "repost_id": post["repost_id"],
        "media": [dict(m) for m in media]
    }

class Create_Group_Req(BaseModel):
    cookie: str
    name: str

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
    cursor.execute(
            "INSERT INTO groups (name, owner_id) VALUES (?, ?)",
            (body.name, user_id)
            )
    group_id = cursor.lastrowid
    cursor.execute(
            "INSERT INTO user_in_group (group_id, user_id, role) VALUES (?, ?, ?)",
            (group_id, user_id, "owner")
            )
    conn.commit()
    return {"group_id": group_id}

class Join_Group_Req(BaseModel):
    cookie: str
    group_id: int

@app.post("/join-group")
def join_group(body: Join_Group_Req):
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
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

class Leave_Group_Req(BaseModel):
    cookie: str
    group_id: int

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

class Send_Group_Msg_Req(BaseModel):
    cookie: str
    group_id: int
    content: str

@app.post("/send-group-msg")
def send_group_msg(body: Send_Group_Msg_Req):
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
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

class Recv_Group_Msg_Req(BaseModel):
    cookie: str
    group_id: int
    count: int = 20

@app.post("/recv-group-msg")
def recv_group_msg(body: Recv_Group_Msg_Req):
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    membership = cursor.execute(
            "SELECT last_read_id FROM user_in_group WHERE group_id = ? AND user_id = ?",
            (body.group_id, user_id)
            ).fetchone()
    if not membership:
        return {"error": "You are not in this group."}
    messages = cursor.execute("""
            SELECT gm.id, gm.sender_id, u.username, u.nickname, gm.content, gm.sent_at
            FROM group_messages gm
            JOIN users u ON u.id = gm.sender_id
            WHERE gm.group_id = ? AND gm.id > ?
            ORDER BY gm.id ASC
            LIMIT ?
    """, (body.group_id, membership["last_read_id"], body.count)).fetchall()
    if messages:
        cursor.execute(
                "UPDATE user_in_group SET last_read_id = ? WHERE group_id = ? AND user_id = ?",
                (messages[-1]["id"], body.group_id, user_id)
                )
        conn.commit()
    return {"messages": [dict(m) for m in messages]}

class Get_Group_Members_Req(BaseModel):
    cookie: str
    group_id: int

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

class Get_My_Groups_Req(BaseModel):
    cookie: str

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

# =============================================================================
# 用户系统：登出
# POST /logout — 删除当前token使其立即失效
# =============================================================================
class Logout_Req(BaseModel):
    cookie: str

@app.post("/logout")
def logout(body: Logout_Req):
    cursor.execute(
            "DELETE FROM cookies WHERE token = ?",
            (body.cookie,)
            )
    conn.commit()
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
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    post = cursor.execute(
            "SELECT publisher_id FROM posts WHERE id = ?",
            (body.post_id,)
            ).fetchone()
    if not post:
        return {"error": "Post not exist."}
    if post["publisher_id"] != user_id:
        return {"error": "Not your post."}
    # 级联清理所有关联数据
    cursor.execute("DELETE FROM liking_users WHERE post_id = ?", (body.post_id,))
    cursor.execute("DELETE FROM comments WHERE post_id = ?", (body.post_id,))
    cursor.execute("DELETE FROM post_media WHERE post_id = ?", (body.post_id,))
    cursor.execute("DELETE FROM read_posts WHERE post_id = ?", (body.post_id,))
    cursor.execute("DELETE FROM posts WHERE id = ?", (body.post_id,))
    conn.commit()
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
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    comment = cursor.execute(
            "SELECT commenter_id FROM comments WHERE id = ?",
            (body.comment_id,)
            ).fetchone()
    if not comment:
        return {"error": "Comment not exist."}
    if comment["commenter_id"] != user_id:
        return {"error": "Not your comment."}
    cursor.execute(
            "DELETE FROM comments WHERE id = ?",
            (body.comment_id,)
            )
    conn.commit()
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
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
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
# 收藏系统：收藏帖子
# POST /bookmark — 使用 INSERT OR IGNORE 保证幂等
# =============================================================================
class Bookmark_Req(BaseModel):
    cookie: str
    post_id: int

@app.post("/bookmark")
def bookmark(body: Bookmark_Req):
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
            "INSERT OR IGNORE INTO bookmarks (user_id, post_id) VALUES (?, ?)",
            (user_id, body.post_id)
            )
    conn.commit()
    return {"status": "success"}

# =============================================================================
# 收藏系统：取消收藏
# POST /unbookmark — 直接删除，不存在也不报错
# =============================================================================
@app.post("/unbookmark")
def unbookmark(body: Bookmark_Req):
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    cursor.execute(
            "DELETE FROM bookmarks WHERE user_id = ? AND post_id = ?",
            (user_id, body.post_id)
            )
    conn.commit()
    return {"status": "success"}

# =============================================================================
# 收藏系统：获取收藏列表
# POST /get-bookmarks — 返回完整帖子信息（含发布者和媒体），按收藏时间倒序
# =============================================================================
class Get_Bookmarks_Req(BaseModel):
    cookie: str

@app.post("/get-bookmarks")
def get_bookmarks(body: Get_Bookmarks_Req):
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    posts = cursor.execute("""
            SELECT p.*, u.username, u.nickname, b.bookmarked_at
            FROM bookmarks b
            JOIN posts p ON p.id = b.post_id
            JOIN users u ON u.id = p.publisher_id
            WHERE b.user_id = ?
            ORDER BY b.bookmarked_at DESC
    """, (user_id,)).fetchall()
    result = []
    for p in posts:
        media = cursor.execute(
                "SELECT offset, content FROM post_media WHERE post_id = ? ORDER BY offset",
                (p["id"],)
                ).fetchall()
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
    row = cursor.execute(
            "SELECT user_id FROM cookies WHERE token = ?",
            (body.cookie,)
            ).fetchone()
    if not row:
        return {"error": "Bad cookie."}
    user_id = row["user_id"]
    original = cursor.execute(
            "SELECT id, publisher_id FROM posts WHERE id = ?",
            (body.post_id,)
            ).fetchone()
    if not original:
        return {"error": "Post not exist."}
    if original["publisher_id"] == user_id:
        return {"error": "Cannot repost your own post."}
    cursor.execute(
            "INSERT INTO posts (publisher_id, content, repost_id) VALUES (?, ?, ?)",
            (user_id, body.text, body.post_id)
            )
    conn.commit()
    return {"status": "success", "new_post_id": cursor.lastrowid}

if __name__ == "__main__":
    uvicorn.run(app, port = 18999)
    uvicorn.run(app, port = 18999)
