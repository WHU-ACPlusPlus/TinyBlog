#!/usr/bin/env -S uv run python3
# Tiny Blog - 微微博最小可用后端主文件
# Copyright (c) 2026 Becharm Kon. All Rights Reserved.

# Databases

import sqlite3, bcrypt, secrets, threading, base64, random

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

def get_user_id(cookie):
    """Check cookie validity and auto-extend (+1 hour), return user_id or None."""
    if not cookie:
        return None
    row = db_fetchone(
        "SELECT user_id FROM cookies WHERE token = ? AND expires_at > datetime('now')",
        (cookie,)
    )
    if not row:
        return None
    db_execute(
        "UPDATE cookies SET expires_at = datetime('now', '+1 hour') WHERE token = ?",
        (cookie,)
    )
    db_commit()
    return row['user_id']

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
    # email 列（可为 NULL，UNIQUE 通过独立索引实现，NULL 不参与唯一性检查）
    try:
        db_execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass
    try:
        db_execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
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
        CREATE TABLE IF NOT EXISTS reg_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cookie TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            nickname TEXT NOT NULL,
            captcha_answer TEXT NOT NULL,
            email TEXT,
            email_code TEXT,
            stage TEXT NOT NULL DEFAULT 'captcha',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    # 登录安全：last_active_at（可为 NULL，已有用户不受影响）
    try:
        db_execute("ALTER TABLE users ADD COLUMN last_active_at TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass
    db_execute("""
        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            attempted_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    db_execute("""
        CREATE TABLE IF NOT EXISTS login_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cookie TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            captcha_answer TEXT,
            captcha_verified INTEGER NOT NULL DEFAULT 0,
            email_verified INTEGER NOT NULL DEFAULT 0,
            email_code TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    db_commit()

# =============================================================================
# 头像生成：新用户注册时自动生成彩色首字母头像
# =============================================================================
import io, math
from PIL import Image, ImageDraw, ImageFont

_FONT_PATH = "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"

def _luminance(r, g, b):
    """计算 sRGB 相对亮度 (WCAG)"""
    def linearize(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)

def generate_avatar(nickname):
    """根据昵称首字符生成 128x128 PNG 头像，返回 base64 字符串"""
    char = nickname[0] if nickname else "?"
    size = 128

    # 随机色相(0-360)，中等饱和度(55-80%)，中等明度(40-55%)
    h = random.uniform(0, 360)
    s = random.uniform(55, 80) / 100.0
    l = random.uniform(40, 55) / 100.0

    # HSL → RGB
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    bg = (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))

    # 根据背景亮度选择黑/白文字
    text_color = (255, 255, 255) if _luminance(*bg) < 0.5 else (0, 0, 0)

    img = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(img)

    # 先画文字（！必须在 compositing 之前，否则 draw 绑定到旧对象）
    try:
        font = ImageFont.truetype(_FONT_PATH, 72)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), char, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) / 2 - bbox[0]
    ty = (size - th) / 2 - bbox[1]
    draw.text((tx, ty), char, fill=text_color, font=font)

    # 圆形裁剪：画圆遮罩后叠加
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([4, 4, size - 4, size - 4], fill=255)
    del mask_draw

    # 在背景上画正圆
    circle = Image.new("RGB", (size, size), (0, 0, 0))
    circle_draw = ImageDraw.Draw(circle)
    circle_draw.ellipse([4, 4, size - 4, size - 4], fill=bg)
    img = Image.composite(img, circle, mask)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# =============================================================================
# 图形验证码生成
# =============================================================================

def generate_captcha(length=4):
    """
    生成图形验证码，返回 (text, base64_png)
    text: 验证码原文（供后续比对）
    base64_png: 图片的 base64 字符串
    """
    # 排除容易混淆的字符：0/O、1/l/I、2/Z、5/S、8/B
    chars = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    code = "".join(random.choices(chars, k=length))

    width = 28 * length + 20
    height = 48
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 加载字体
    try:
        font = ImageFont.truetype(_FONT_PATH, 36)
    except Exception:
        font = ImageFont.load_default()

    # 逐个写字符，每个带随机偏移和颜色
    for i, ch in enumerate(code):
        # 随机颜色（避开白色/太浅的）
        fg = (random.randint(30, 180), random.randint(30, 180), random.randint(30, 180))
        x = 10 + i * 28 + random.randint(-3, 3)
        y = random.randint(2, 10)
        draw.text((x, y), ch, fill=fg, font=font)

    # 随机干扰线（3~5 条）
    for _ in range(random.randint(3, 5)):
        line_color = (random.randint(100, 200), random.randint(100, 200), random.randint(100, 200))
        x1 = random.randint(0, width // 3)
        y1 = random.randint(0, height)
        x2 = random.randint(width * 2 // 3, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=line_color, width=random.randint(1, 2))

    # 随机噪点（约 80~150 个）
    for _ in range(random.randint(80, 150)):
        dot_color = (random.randint(0, 150), random.randint(0, 150), random.randint(0, 150))
        draw.point(
            (random.randint(0, width - 1), random.randint(0, height - 1)),
            fill=dot_color,
        )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return code, base64.b64encode(buf.getvalue()).decode()

# =============================================================================
# 邮箱验证码
# =============================================================================
import os, smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

def build_verification_email(code, to_email):
    """
    根据验证码生成 HTML 邮件内容。
    返回 MIMEText 对象（含 HTML body）。
    """
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif">
<table width="100%%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:40px 16px">
<table width="400" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08)">
<tr><td style="padding:32px 24px 24px;text-align:center">
<div style="font-size:22px;font-weight:700;color:#333;margin-bottom:8px">Tiny Chat</div>
<div style="font-size:14px;color:#888;margin-bottom:28px">邮箱地址验证</div>
<div style="font-size:13px;color:#555;margin-bottom:20px">您的验证码为：</div>
<div style="font-size:36px;font-weight:700;letter-spacing:8px;color:#4a90d9;background:#f0f7ff;border-radius:8px;padding:16px 24px;display:inline-block">{code}</div>
<div style="font-size:12px;color:#aaa;margin-top:28px;line-height:1.6">验证码有效期为 10 分钟。<br>如非本人操作，请忽略此邮件。</div>
</td></tr>
<tr><td style="background:#fafafa;padding:16px 24px;text-align:center;font-size:11px;color:#bbb">Tiny Chat — 自动发送，请勿回复</td></tr>
</table>
</td></tr></table>
</body>
</html>"""

    # 注意：%% 是 Python format 中转义为单个 % 的方式，
    # 模板中不用再关心这个细节。
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = "Tiny Chat 邮箱验证"
    msg["To"] = to_email
    return msg


def send_verification_email(to_email, code):
    """
    向指定邮箱发送验证码。
    从环境变量读取 SMTP 配置：
      SMTP_HOST     — SMTP 服务器地址，默认 smtp.qq.com
      SMTP_PORT     — SMTP 端口，默认 465 (SSL)
      SMTP_USER     — 发件邮箱地址
      SMTP_PASS     — 发件邮箱密码/授权码
      SMTP_FROM     — 发件人显示名称（可选），默认使用 SMTP_USER
    """
    host = os.environ.get("SMTP_HOST", "smtp.qq.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    from_addr = os.environ.get("SMTP_FROM", user)

    msg = build_verification_email(code, to_email)
    msg["From"] = formataddr(("Tiny Chat", from_addr))

    with smtplib.SMTP_SSL(host, port) as server:
        server.login(user, password)
        server.sendmail(from_addr, [to_email], msg.as_string())


# Server Functions

import fastapi, uvicorn

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
    cookie = secrets.token_hex(32)
    captcha_text, captcha_b64 = generate_captcha()
    db_execute(
        """INSERT INTO reg_sessions (cookie, username, password_hash, nickname, captcha_answer)
           VALUES (?, ?, ?, ?, ?)""",
        (cookie, body.username, password_hash, body.nickname, captcha_text)
    )
    db_commit()
    return {"cookie": cookie, "captcha": captcha_b64}

# =============================================================================
# 注册第二步：校验图形验证码 + 邮箱，发送邮箱验证码
# POST /register-verify
# 输入: cookie, captcha, email
# =============================================================================
class Reg_Verify_Req(BaseModel):
    cookie: str
    captcha: str
    email: str

@app.post("/register-verify")
def reg_verify(body: Reg_Verify_Req):
    session = db_fetchone(
        "SELECT * FROM reg_sessions WHERE cookie = ? AND stage = 'captcha'",
        (body.cookie,)
    )
    if not session:
        return {"error": "Bad cookie."}
    if not body.captcha:
        return {"error": "Captcha required."}
    if session["captcha_answer"] != body.captcha:
        return {"error": "Captcha incorrect."}
    if not body.email:
        return {"error": "Email required."}
    # 检查邮箱是否已被占用
    existing = db_fetchone(
        "SELECT id FROM users WHERE email = ?",
        (body.email,)
    )
    if existing:
        return {"error": "Email occupied."}
    # 生成并发送邮箱验证码
    email_code = "".join(random.choices("0123456789", k=6))
    try:
        send_verification_email(body.email, email_code)
    except Exception as e:
        return {"error": f"Failed to send email: {e}"}
    db_execute(
        "UPDATE reg_sessions SET email = ?, email_code = ?, stage = 'email' WHERE cookie = ?",
        (body.email, email_code, body.cookie)
    )
    db_commit()
    return {"status": "success"}

# =============================================================================
# 注册第三步：校验邮箱验证码，创建用户
# POST /register-finish
# 输入: cookie, email_code
# =============================================================================
class Reg_Finish_Req(BaseModel):
    cookie: str
    email_code: str

@app.post("/register-finish")
def reg_finish(body: Reg_Finish_Req):
    session = db_fetchone(
        "SELECT * FROM reg_sessions WHERE cookie = ? AND stage = 'email'",
        (body.cookie,)
    )
    if not session:
        return {"error": "Bad cookie."}
    if not body.email_code:
        return {"error": "Email code required."}
    if session["email_code"] != body.email_code:
        return {"error": "Email code incorrect."}
    if not session["email"]:
        return {"error": "No email in session."}
    # 再次检查邮箱是否被占用（防止并发注册）
    existing = db_fetchone(
        "SELECT id FROM users WHERE email = ?",
        (session["email"],)
    )
    if existing:
        return {"error": "Email occupied."}
    # 创建用户
    avatar_b64 = generate_avatar(session["nickname"])
    db_execute(
        "INSERT INTO users (username, nickname, password_hash, avatar, email) VALUES (?, ?, ?, ?, ?)",
        (session["username"], session["nickname"],
         session["password_hash"], avatar_b64, session["email"])
    )
    user_id = db_lastrowid()
    auth_cookie = secrets.token_hex(32)
    db_execute(
        "INSERT INTO cookies (user_id, token, expires_at) VALUES (?, ?, datetime('now', '+1 hour'))",
        (user_id, auth_cookie)
    )
    # 清理注册会话
    db_execute("DELETE FROM reg_sessions WHERE id = ?", (session["id"],))
    db_commit()
    return {"cookie": auth_cookie}

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
        # 记录失败尝试
        db_execute("INSERT INTO login_attempts (user_id) VALUES (?)", (log["id"],))
        db_commit()
        return {"error": "Incorrect password."}

    # 记录登录尝试（成功也算一次，防止高频重登）
    db_execute("INSERT INTO login_attempts (user_id) VALUES (?)", (log["id"],))
    db_commit()

    # 检查：半小时内失败次数 > 3 → 需要图形验证码
    recent_fails = db_fetchone(
        """SELECT COUNT(*) as cnt FROM login_attempts
           WHERE user_id = ? AND attempted_at > datetime('now', '-30 minutes')""",
        (log["id"],)
    )
    need_captcha = (recent_fails["cnt"] if recent_fails else 0) > 3

    # 检查：距上次活跃 > 72 小时 → 需要邮箱验证码
    need_email = False
    if log["last_active_at"]:
        inactive = db_fetchone(
            "SELECT (julianday('now') - julianday(?)) * 24 > 72 as expired",
            (log["last_active_at"],)
        )
        if inactive and inactive["expired"]:
            need_email = True

    # 创建登录会话
    cookie = secrets.token_hex(32)
    captcha_text, captcha_b64 = generate_captcha() if need_captcha else (None, None)
    db_execute(
        "INSERT INTO login_sessions (cookie, user_id, captcha_answer, captcha_verified, email_verified) VALUES (?, ?, ?, ?, ?)",
        (cookie, log["id"], captcha_text, 1 if not need_captcha else 0, 1 if not need_email else 0)
    )
    db_commit()

    result = {"cookie": cookie, "need_captcha": need_captcha, "need_email": need_email}
    if need_captcha:
        result["captcha"] = captcha_b64
    if need_email:
        result["email"] = log["email"] or ""
    return result

# =============================================================================
# 登录验证：图形验证码
# POST /login-verify-captcha
# =============================================================================
class Login_Verify_Captcha_Req(BaseModel):
    cookie: str
    captcha: str

@app.post("/login-verify-captcha")
def login_verify_captcha(body: Login_Verify_Captcha_Req):
    session = db_fetchone(
        "SELECT * FROM login_sessions WHERE cookie = ?",
        (body.cookie,)
    )
    if not session:
        return {"error": "Bad cookie."}
    if not session["captcha_answer"]:
        return {"error": "No captcha required."}
    if session["captcha_answer"] != body.captcha:
        return {"error": "Captcha incorrect."}
    db_execute(
        "UPDATE login_sessions SET captcha_verified = 1 WHERE cookie = ?",
        (body.cookie,)
    )
    db_commit()
    return {"status": "success"}

# =============================================================================
# 登录验证：发送邮箱验证码
# POST /login-send-email-code
# =============================================================================
class Login_Send_Email_Req(BaseModel):
    cookie: str

@app.post("/login-send-email-code")
def login_send_email_code(body: Login_Send_Email_Req):
    session = db_fetchone(
        "SELECT * FROM login_sessions WHERE cookie = ?",
        (body.cookie,)
    )
    if not session:
        return {"error": "Bad cookie."}

    user = db_fetchone("SELECT email FROM users WHERE id = ?", (session["user_id"],))
    if not user or not user["email"]:
        return {"error": "No email on file."}

    email_code = "".join(random.choices("0123456789", k=6))
    try:
        send_verification_email(user["email"], email_code)
    except Exception as e:
        return {"error": f"Failed to send email: {e}"}

    db_execute(
        "UPDATE login_sessions SET email_code = ? WHERE cookie = ?",
        (email_code, body.cookie)
    )
    db_commit()
    return {"status": "sent", "email": user["email"]}

# =============================================================================
# 登录验证：校验邮箱验证码
# POST /login-verify-email
# =============================================================================
class Login_Verify_Email_Req(BaseModel):
    cookie: str
    email_code: str

@app.post("/login-verify-email")
def login_verify_email(body: Login_Verify_Email_Req):
    session = db_fetchone(
        "SELECT * FROM login_sessions WHERE cookie = ?",
        (body.cookie,)
    )
    if not session:
        return {"error": "Bad cookie."}
    if not session["email_code"]:
        return {"error": "No email code sent."}
    if session["email_code"] != body.email_code:
        return {"error": "Email code incorrect."}

    db_execute(
        "UPDATE login_sessions SET email_verified = 1 WHERE cookie = ?",
        (body.cookie,)
    )
    db_commit()
    return {"status": "success"}

# =============================================================================
# 登录完成：获得真正的 auth cookie
# POST /login-finish
# =============================================================================
class Login_Finish_Req(BaseModel):
    cookie: str

@app.post("/login-finish")
def login_finish(body: Login_Finish_Req):
    session = db_fetchone(
        "SELECT * FROM login_sessions WHERE cookie = ?",
        (body.cookie,)
    )
    if not session:
        return {"error": "Bad cookie."}
    if not session["captcha_verified"]:
        return {"error": "Captcha not verified."}
    if not session["email_verified"]:
        return {"error": "Email not verified."}

    # 创建 auth cookie
    auth_cookie = secrets.token_hex(32)
    db_execute(
        "INSERT INTO cookies (user_id, token, expires_at) VALUES (?, ?, datetime('now', '+1 hour'))",
        (session["user_id"], auth_cookie)
    )
    # 更新最后活跃时间
    db_execute(
        "UPDATE users SET last_active_at = datetime('now') WHERE id = ?",
        (session["user_id"],)
    )
    # 清理登录会话
    db_execute("DELETE FROM login_sessions WHERE id = ?", (session["id"],))
    db_commit()
    return {"cookie": auth_cookie}

class Get_Follower(BaseModel):
    cookie: str

@app.post("/get-follow-list")
def get_follow_list(body: Get_Follower):
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    db_commit()
    return {"status": "success"}

@app.post("/unfollow")
def unfollow(body: Follow_Req):
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    db_commit()
    return {"status": "success"}

@app.post("/unlike")
def unlike(body: Like_Req):
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    db_commit()
    return {"status": "success"}

class Get_Comments_Req(BaseModel):
    cookie: str
    post_id: int

@app.post("/get-comments")
def get_comments(body: Get_Comments_Req):
    user_id = get_user_id(body.cookie)
    if not user_id:
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    existence = db_fetchone(
            "SELECT id FROM users WHERE id = ?",
            (body.to_whom_id,)
            )
    if not existence:
        return {"error": "Bad `to_whom_id`"}
    db_execute("INSERT INTO offline_messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
            (user_id, body.to_whom_id, body.content,)
            )
    db_commit()
    return {"status": "success"}

class Recv_Msg(BaseModel):
    cookie: str

@app.post("/recv-msg")
def recv_msg(body: Recv_Msg):
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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

@app.post("/post-fetch")
def post_fetch(body: Post_Fetch):
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}

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
    user_id = get_user_id(body.cookie)
    if not user_id:
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

    liked = db_fetchone(
        "SELECT 1 FROM liking_users WHERE post_id = ? AND liker_id = ?",
        (body.post_id, user_id)
    )

    return {
        "id": post["id"],
        "publisher_id": post["publisher_id"],
        "username": post["username"],
        "nickname": post["nickname"],
        "content": post["content"],
        "like_num": post["like_num"],
        "liked": liked is not None,
        "created_at": post["created_at"],
        "repost_id": post["repost_id"],
        "media": [dict(m) for m in media]
    }

class Create_Group_Req(BaseModel):
    cookie: str
    name: str

@app.post("/create-group")
def create_group(body: Create_Group_Req):
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    if not body.name:
        return {"error": "Group name cannot be empty."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
# =============================================================================
# 用户系统：检查 Cookie 有效性（返回完整个人资料）
# POST /check-cookie
# =============================================================================
class Check_Cookie_Req(BaseModel):
    cookie: str

@app.post("/check-cookie")
def check_cookie(body: Check_Cookie_Req):
    if not body.cookie:
        return {"error": "Empty cookie."}
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"valid": False}
    user = db_fetchone(
            "SELECT id, username, nickname, avatar, signature, email FROM users WHERE id = ?",
            (user_id,)
            )
    if not user:
        return {"valid": False}
    return {
        "valid": True,
        "user_id": user["id"],
        "username": user["username"],
        "nickname": user["nickname"],
        "avatar": user["avatar"],
        "signature": user["signature"],
        "email": user["email"],
    }

# =============================================================================
# 用户系统：查询自己的邮箱
# POST /get-email — 输入 cookie，返回 email
# =============================================================================
class Get_Email_Req(BaseModel):
    cookie: str

@app.post("/get-email")
def get_email(body: Get_Email_Req):
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    user = db_fetchone(
        "SELECT email FROM users WHERE id = ?",
        (user_id,)
    )
    if not user:
        return {"error": "User not exist."}
    return {"email": user["email"] or ""}

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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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

@app.post("/avatar")
def patch_avatar(body: Patch_Avatar_Req):
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
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

if __name__ == "__main__":
    uvicorn.run(app, port = 18999)
