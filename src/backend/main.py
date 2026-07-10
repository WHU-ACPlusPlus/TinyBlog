#!/usr/bin/env -S uv run python3
# Tiny Blog - 微微博最小可用后端主文件
# Copyright (c) 2026 Becharm Kon. All Rights Reserved.

# Databases

import os, re, base64, io, random, sqlite3, bcrypt, secrets, threading, logging, sys
from datetime import datetime, timezone, timedelta

# ── Social 模块 ──
import social.social as social_mod
import social.search as social_search
import social.notification as social_notify

# ── 日志系统配置 ──
# 北京时间 (UTC+8)
TZ_BEIJING = timezone(timedelta(hours=8))

def _beijing_time():
    """返回北京时间字符串，格式: 2026-07-07 14:30:05"""
    return datetime.now(TZ_BEIJING).strftime("%Y-%m-%d %H:%M:%S")

# 同时输出到控制台和文件
_log_format = logging.Formatter(
    "[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

_logger = logging.getLogger("tinyblog")
_logger.setLevel(logging.DEBUG)

# 控制台 handler
_ch = logging.StreamHandler(sys.stdout)
_ch.setFormatter(_log_format)
_ch.setLevel(logging.DEBUG)
_logger.addHandler(_ch)

# 文件 handler（写入 api.log）
_fh = logging.FileHandler("api.log", encoding="utf-8")
_fh.setFormatter(_log_format)
_fh.setLevel(logging.DEBUG)
_logger.addHandler(_fh)

def log_api(endpoint: str, user_id, req_detail: str = "", resp_summary: str = ""):
    """统一API日志记录。
    
    Args:
        endpoint: 如 "POST /send-msg"
        user_id: 调用者user_id，None表示未认证
        req_detail: 请求关键参数简述
        resp_summary: 响应结果简述
    """
    uid = f"user={user_id}" if user_id else "user=?"
    parts = [endpoint, uid]
    if req_detail:
        parts.append(req_detail)
    if resp_summary:
        parts.append(f"→ {resp_summary}")
    else:
        parts.append("→ (no summary)")
    _logger.info(" | ".join(parts))

def resolve_user(cookie: str):
    """通过cookie解析user_id，失败返回None。"""
    if not cookie:
        return None
    row = db_fetchone(
        "SELECT user_id FROM cookies WHERE token = ?",
        (cookie,)
    )
    return row["user_id"] if row else None

# ── 屏蔽词库加载 ──
_BLOCKED_WORDS = []
_blocked_words_path = os.path.join(os.path.dirname(__file__), "blocked_words.txt")
if os.path.exists(_blocked_words_path):
    with open(_blocked_words_path, encoding="utf-8") as _f:
        _BLOCKED_WORDS = [
            _l.strip() for _l in _f
            if _l.strip() and not _l.startswith("#")
        ]
    log_api("SYSTEM", None, f"loaded {len(_BLOCKED_WORDS)} blocked words", "ok")
else:
    log_api("SYSTEM", None, f"blocked_words.txt not found at {_blocked_words_path}", "empty")

def contains_blocked(text: str) -> bool:
    """检查文本是否包含屏蔽词，命中返回 True。"""
    if not text or not _BLOCKED_WORDS:
        return False
    text_lower = text.lower()
    for w in _BLOCKED_WORDS:
        if w.lower() in text_lower:
            return True
    return False

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
    # ── 消息功能：数据库迁移 ──
    # 私信增加 is_read 标记（替代"阅后即焚"模式）
    try:
        db_execute("ALTER TABLE offline_messages ADD COLUMN is_read INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    # 群组增加头像字段
    try:
        db_execute("ALTER TABLE groups ADD COLUMN avatar TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    # 统一会话表（私聊 + 群聊统一存储）
    db_execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL DEFAULT 'private',
            target_id INTEGER NOT NULL,
            last_message TEXT DEFAULT '',
            last_message_time TEXT DEFAULT '',
            unread_count INTEGER DEFAULT 0,
            is_hidden INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, type, target_id)
        )
    """)
    # 好友申请表
    db_execute("""
        CREATE TABLE IF NOT EXISTS friend_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER NOT NULL,
            to_user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (from_user_id) REFERENCES users(id),
            FOREIGN KEY (to_user_id) REFERENCES users(id),
            UNIQUE(from_user_id, to_user_id)
        )
    """)
    db_commit()

    # ── 初始化 Social 模块表结构 ──
    print("[social] Initializing social tables...")
    social_mod._ensure_social_tables()
    print("[social] Social tables ready.")

# =============================================================================
# 头像生成：新用户注册时自动生成彩色首字母头像
# =============================================================================
import io, math
from PIL import Image, ImageDraw, ImageFont

# 尝试多个常见的 CJK 字体路径（按优先级排序）
_CJK_FONT_PATHS = [
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",         # Arch Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",   # Debian/Ubuntu
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",   # 其他发行版
    "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc",            # 其他发行版
    "/usr/share/fonts/noto-sans-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/wenquanyi/wqy-zenhei.ttc",               # 文泉驿
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
]

def _load_cjk_font(size):
    """加载 CJK 字体，返回 ImageFont 对象。优先尝试已知的 CJK 字体路径。"""
    # 先尝试已知的 CJK 字体路径（更可靠）
    for path in _CJK_FONT_PATHS:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # fallback：用 fontconfig 尝试找一个支持中文的字体
    try:
        import subprocess
        result = subprocess.run(
            ["fc-match", "-f", "%{file}", "sans:lang=zh"],
            capture_output=True, text=True, timeout=3
        )
        fc_path = result.stdout.strip()
        if fc_path and os.path.isfile(fc_path):
            # 确认该字体真的能渲染 CJK（避免 fontconfig 匹配到 DejaVu 等非 CJK 字体）
            try:
                test_font = ImageFont.truetype(fc_path, size)
                # 测试渲染一个中文字符，检查是否有非空白像素
                from PIL import Image, ImageDraw
                test_img = Image.new("L", (size, size), 0)
                test_draw = ImageDraw.Draw(test_img)
                test_draw.text((0, 0), "中", font=test_font, fill=255)
                bbox = test_img.getbbox()
                if bbox and bbox[2] > 2 and bbox[3] > 2:
                    return test_font
            except Exception:
                pass
    except Exception:
        pass
    # 全都不行，fallback
    print("[avatar] 警告：未找到 CJK 字体，头像中文可能显示为方框")
    return ImageFont.load_default()

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
        font = _load_cjk_font(72)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), char, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) / 2 - bbox[0]
    ty = (size - th) / 2 - bbox[1]
    draw.text((tx, ty), char, fill=text_color, font=font)

    # 背景色铺满整张图片（不做圆形裁切，前端显示时无圆角裁剪）
    # 直接返回全幅方块头像

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
        font = _load_cjk_font(36)
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
<div style="font-size:22px;font-weight:700;color:#333;margin-bottom:8px">Tiny Blog</div>
<div style="font-size:14px;color:#888;margin-bottom:28px">邮箱地址验证</div>
<div style="font-size:13px;color:#555;margin-bottom:20px">您的验证码为：</div>
<div style="font-size:36px;font-weight:700;letter-spacing:8px;color:#4a90d9;background:#f0f7ff;border-radius:8px;padding:16px 24px;display:inline-block">{code}</div>
<div style="font-size:12px;color:#aaa;margin-top:28px;line-height:1.6">验证码有效期为 10 分钟。<br>如非本人操作，请忽略此邮件。</div>
</td></tr>
<tr><td style="background:#fafafa;padding:16px 24px;text-align:center;font-size:11px;color:#bbb">Tiny Blog — 自动发送，请勿回复</td></tr>
</table>
</td></tr></table>
</body>
</html>"""

    # 注意：%% 是 Python format 中转义为单个 % 的方式，
    # 模板中不用再关心这个细节。
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = "Tiny Blog 邮箱验证"
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
    msg["From"] = formataddr(("Tiny Blog", from_addr))

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

# ── LaTeX 渲染（本地 matplotlib.mathtext）──
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import urllib.parse
import subprocess
from fastapi.responses import Response

# ── 检测系统 LaTeX ──
_HAS_LATEX = False
try:
    subprocess.run(["pdflatex", "--version"], capture_output=True, timeout=5, check=True)
    matplotlib.rcParams['text.usetex'] = True
    matplotlib.rcParams['text.latex.preamble'] = r'\usepackage{amsmath}\usepackage{amssymb}'
    _HAS_LATEX = True
    print("[latex] 系统 LaTeX 已启用（完整渲染）")
except:
    print("[latex] 系统 LaTeX 未安装，使用 matplotlib mathtext 回退")

_IMG_FMT = 'svg'  # SVG 矢量格式
_IMG_MIME = 'image/svg+xml'

def _render_single(latex: str):
    """渲染单个 LaTeX 公式为 SVG bytes"""
    fig, ax = plt.subplots(figsize=(0.01, 0.01))
    rendered = ax.text(0.5, 0.5, f"${latex}$", fontsize=10,
                      transform=ax.transAxes, va='center', ha='center')
    ax.axis('off')
    fig.canvas.draw()
    bbox = rendered.get_window_extent(renderer=fig.canvas.get_renderer())
    bbox = bbox.transformed(fig.dpi_scale_trans.inverted())
    plt.close(fig)

    pad = 0.04
    w, h = max(bbox.width + pad, 1), max(bbox.height + pad, 1)
    fig2, ax2 = plt.subplots(figsize=(w, h))
    ax2.text(0.5, 0.5, f"${latex}$", fontsize=10,
           transform=ax2.transAxes, va='center', ha='center', color='black')
    ax2.axis('off')
    fig2.patch.set_alpha(0)
    ax2.patch.set_alpha(0)

    buf = BytesIO()
    fig2.savefig(buf, format=_IMG_FMT, transparent=True,
                bbox_inches='tight', pad_inches=0.02)
    plt.close(fig2)
    buf.seek(0)
    return buf.getvalue()

@app.get("/latex-image")
def latex_image(tex: str = ""):
    """GET 端点：返回 LaTeX 渲染的 SVG 图片"""
    latex = urllib.parse.unquote(tex).strip()
    if not latex:
        return Response(content=b"", media_type=_IMG_MIME)
    log_api("GET /latex-image", None, f"len={len(latex)}")

    try:
        # 有完整 LaTeX 时直接渲染（支持所有环境）
        if _HAS_LATEX:
            img_bytes = _render_single(latex)
            log_api("GET /latex-image", None, "", f"OK tex {len(img_bytes)} bytes")
            return Response(content=img_bytes, media_type=_IMG_MIME)

        # mathtext 回退：拆解 \begin{aligned}
        if "\\begin{aligned}" in latex:
            inner = latex.replace("\\begin{aligned}", "").replace("\\end{aligned}", "")
            lines = [L.strip() for L in inner.split("\\\\") if L.strip()]
            if lines:
                from PIL import Image as PILImage
                imgs = []
                for line in lines:
                    try:
                        imgs.append(_render_single(line))
                    except:
                        imgs.append(None)
                if any(imgs):
                    # SVG 垂直拼接
                    svg_parts = []
                    for img_bytes in imgs:
                        if img_bytes:
                            svg_parts.append(img_bytes.decode('utf-8'))
                    merged = '\n'.join(svg_parts)
                    log_api("GET /latex-image", None, "", f"OK aligned {len(lines)} lines")
                    return Response(content=merged.encode(), media_type=_IMG_MIME)

        # 默认渲染
        img_bytes = _render_single(latex)
        log_api("GET /latex-image", None, "", f"OK {len(img_bytes)} bytes")
        return Response(content=img_bytes, media_type=_IMG_MIME)
    except Exception as e:
        log_api("GET /latex-image", None, "", f"ERROR: {str(e)[:80]}")
        return Response(content=b"", media_type=_IMG_MIME)

@app.get("/video-play-url")
def video_play_url(bvid: str = "", cid: str = ""):
    """GET 端点：获取 B站/视频直链 URL（内嵌播放用）"""
    import urllib.request
    import json as _json
    if not bvid:
        return {"error": "bvid required"}
    if not cid:
        # 没有 cid 时，先通过 view API 获取
        view_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        try:
            vr = urllib.request.Request(view_url, headers={
                "Referer": "https://www.bilibili.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(vr, timeout=5) as resp:
                vdata = _json.loads(resp.read().decode())
            cid = str(vdata.get("data", {}).get("cid", 0))
        except Exception as e:
            log_api("GET /video-play-url", None, f"bvid={bvid}", f"view API ERROR: {str(e)[:60]}")
            return {"error": f"Failed to get cid: {e}"}

    play_url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=80&fnval=1&fourk=1"
    log_api("GET /video-play-url", None, f"bvid={bvid} cid={cid}", "")
    try:
        pr = urllib.request.Request(play_url, headers={
            "Referer": "https://www.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(pr, timeout=8) as resp:
            pdata = _json.loads(resp.read().decode())
        durl = pdata.get("data", {}).get("durl", [])
        if durl and len(durl) > 0:
            video_url = durl[0].get("url", "")
            # 提取标题
            log_api("GET /video-play-url", None, "", f"OK {len(video_url)} bytes url")
            return {"url": video_url, "format": "flv", "bvid": bvid, "cid": cid}
        dash = pdata.get("data", {}).get("dash", {})
        if dash:
            videos = dash.get("video", [])
            if videos:
                return {"url": videos[0].get("baseUrl", ""), "format": "mp4", "bvid": bvid, "cid": cid}
        log_api("GET /video-play-url", None, "", f"no playable url in response")
        return {"error": "No playable URL found"}
    except Exception as e:
        log_api("GET /video-play-url", None, "", f"ERROR: {str(e)[:80]}")
        return {"error": str(e)}

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
            SELECT u.id, u.username, u.nickname, u.avatar
            FROM following f
            JOIN users u ON u.id == f.follower
            WHERE f.followee == ?
            """,
            (user_id,)
            )]
    followees = [dict(now) for now in db_fetchall(
            """
            SELECT u.id, u.username, u.nickname, u.avatar
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
    # 委托给 social 模块（同步维护 follows + following 两表）
    try:
        result = social_mod.follow(user_id, body.followee_id)
    except ValueError as e:
        log_api("POST /follow", user_id, f"to={body.followee_id}", str(e))
        return {"error": str(e)}
    if result["status"] == "blocked":
        log_api("POST /follow", user_id, f"to={body.followee_id}", result.get("message", "blocked"))
        return {"error": result.get("message", "你已被该用户屏蔽，无法关注")}
    if result["status"] == "banned":
        return {"error": result.get("message", "你已被封禁")}
    # 关注成功后，为关注者创建占位会话（使对方出现在会话列表中）
    if result["status"] in ("followed", "requested", "already_following"):
        db_execute("""
            INSERT OR IGNORE INTO conversations (user_id, type, target_id, last_message, last_message_time, unread_count)
            VALUES (?, 'private', ?, '', datetime('now'), 0)
        """, (user_id, body.followee_id))
        db_commit()
    log_api("POST /follow", user_id, f"to={body.followee_id}", result["status"])
    return {"status": result["status"]}

@app.post("/unfollow")
def unfollow(body: Follow_Req):
    user_id = get_user_id(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    # social_mod.unfollow 已处理表删除
    result = social_mod.unfollow(user_id, body.followee_id)
    # 同时隐藏与该用户的会话（YFunction）
    db_execute(
        "UPDATE conversations SET is_hidden = 1 WHERE user_id = ? AND type = 'private' AND target_id = ?",
        (user_id, body.followee_id)
    )
    db_commit()
    return result

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
        log_api("POST /send-msg", None, f"to={body.to_whom_id}", "Bad cookie")
        return {"error": "Bad cookie."}
    existence = db_fetchone(
            "SELECT id FROM users WHERE id = ?",
            (body.to_whom_id,)
            )
    if not existence:
        log_api("POST /send-msg", user_id, f"to={body.to_whom_id}", "Bad to_whom_id")
        return {"error": "Bad `to_whom_id`"}
    # ── 空消息检查 ──
    if not body.content:
        log_api("POST /send-msg", user_id, f"to={body.to_whom_id}", "Empty message")
        return {"error": "Empty message not allowed."}
    # ── 敏感词检查 ──
    if contains_blocked(body.content):
        log_api("POST /send-msg", user_id, f"to={body.to_whom_id}", "blocked")
        return {"error": "消息包含不允许的内容"}
    # ── 单向关注限制：对方未关注我且未回复 → 只能发1条 ──
    mutual = db_fetchone("""
        SELECT 1 FROM following f1
        JOIN following f2 ON f1.followee = f2.follower AND f1.follower = f2.followee
        WHERE f1.follower = ? AND f1.followee = ?
    """, (user_id, body.to_whom_id))
    if not mutual:
        # 对方是否给我发过消息（即已回复）
        replied = db_fetchone(
            "SELECT 1 FROM offline_messages WHERE sender_id = ? AND receiver_id = ?",
            (body.to_whom_id, user_id)
        )
        if not replied:
            # 我是否已给对方发过消息
            sent_count = db_fetchone(
                "SELECT COUNT(*) AS cnt FROM offline_messages WHERE sender_id = ? AND receiver_id = ?",
                (user_id, body.to_whom_id)
            )
            already_sent = sent_count["cnt"] if sent_count else 0
            if already_sent >= 1:
                log_api("POST /send-msg", user_id,
                        f"to={body.to_whom_id} one_way_limit sent={already_sent}", "blocked: 单向限制")
                return {"error": "对方尚未回复，只能发送一条消息。请等待对方回复后再发送。"}
            log_api("POST /send-msg", user_id,
                    f"to={body.to_whom_id} one_way(1st msg)", "allowed")
        else:
            log_api("POST /send-msg", user_id,
                    f"to={body.to_whom_id} one_way(replied)", "allowed")
    # 双写：offline_messages（旧 TinyBlog）+ private_messages（LYC 会话系统）
    db_execute("INSERT INTO offline_messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
            (user_id, body.to_whom_id, body.content,)
            )
    # 2. 更新/创建发送方的会话记录（unread=0, is_hidden=0）
    db_execute("""
        INSERT INTO conversations (user_id, type, target_id, last_message, last_message_time, unread_count, is_hidden)
        VALUES (?, 'private', ?, ?, datetime('now'), 0, 0)
        ON CONFLICT(user_id, type, target_id) DO UPDATE SET
            last_message = excluded.last_message,
            last_message_time = excluded.last_message_time,
            is_hidden = 0
    """, (user_id, body.to_whom_id, body.content))
    # 3. 更新/创建接收方的会话记录（unread+1, 如果已隐藏则重新激活）
    db_execute("""
        INSERT INTO conversations (user_id, type, target_id, last_message, last_message_time, unread_count, is_hidden)
        VALUES (?, 'private', ?, ?, datetime('now'), 1, 0)
        ON CONFLICT(user_id, type, target_id) DO UPDATE SET
            last_message = excluded.last_message,
            last_message_time = excluded.last_message_time,
            unread_count = unread_count + 1,
            is_hidden = 0
    """, (body.to_whom_id, user_id, body.content))
    db_commit()
    log_api("POST /send-msg", user_id, f"to={body.to_whom_id} len={len(body.content)}", "success")
    return {"status": "success"}

class Recv_Msg(BaseModel):
    cookie: str

@app.post("/recv-msg")
def recv_msg(body: Recv_Msg):
    user_id = get_user_id(body.cookie)
    if not user_id:
        log_api("POST /recv-msg [DEPRECATED]", None, "", "Bad cookie")
        return {"error": "Bad cookie."}
    msgs = [dict(row) for row in db_fetchall(
            "SELECT sender_id, sent_at, content FROM offline_messages WHERE receiver_id = ? AND is_read = 0",
            (user_id,)
            )]
    # 标记为已读，不再删除
    db_execute(
            "UPDATE offline_messages SET is_read = 1 WHERE receiver_id = ? AND is_read = 0",
            (user_id,)
            )
    db_commit()
    log_api("POST /recv-msg [DEPRECATED]", user_id, "", f"{len(msgs)} msgs")
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
        log_api("POST /create-group", user_id, "", "Empty name")
        return {"error": "Group name cannot be empty."}
    db_execute("INSERT INTO groups (name, owner_id) VALUES (?, ?)",
            (body.name, user_id)
            )
    group_id = db_lastrowid()
    db_execute(
            "INSERT INTO user_in_group (group_id, user_id, role) VALUES (?, ?, ?)",
            (group_id, user_id, "owner")
            )
    # 为创建者初始化会话记录
    db_execute("""
        INSERT OR IGNORE INTO conversations (user_id, type, target_id, last_message, last_message_time, unread_count)
        VALUES (?, 'group', ?, '群聊已创建', datetime('now'), 0)
    """, (user_id, group_id))
    db_commit()
    log_api("POST /create-group", user_id, f"name={body.name}", f"group_id={group_id}")
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
        log_api("POST /join-group", user_id, f"group={body.group_id}", "Group not exist")
        return {"error": "Group not exist."}
    db_execute("INSERT OR IGNORE INTO user_in_group (group_id, user_id) VALUES (?, ?)",
            (body.group_id, user_id)
            )
    # 为新成员创建会话记录
    db_execute("""
        INSERT OR IGNORE INTO conversations (user_id, type, target_id, last_message, last_message_time, unread_count)
        VALUES (?, 'group', ?, '', datetime('now'), 0)
    """, (user_id, body.group_id))
    db_commit()
    log_api("POST /join-group", user_id, f"group={body.group_id}", "success")
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
    # 隐藏该用户的群聊会话
    db_execute("""
        UPDATE conversations SET is_hidden = 1
        WHERE user_id = ? AND type = 'group' AND target_id = ?
    """, (user_id, body.group_id))
    db_commit()
    log_api("POST /leave-group", user_id, f"group={body.group_id}", "success")
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
        log_api("POST /send-group-msg", user_id, f"group={body.group_id}", "Not in group")
        return {"error": "You are not in this group."}
    if not body.content:
        log_api("POST /send-group-msg", user_id, f"group={body.group_id}", "Empty message")
        return {"error": "Empty message not allowed."}
    if contains_blocked(body.content):
        log_api("POST /send-group-msg", user_id, f"group={body.group_id}", "blocked")
        return {"error": "消息包含不允许的内容"}
    # 1. 插入群消息
    db_execute("INSERT INTO group_messages (group_id, sender_id, content) VALUES (?, ?, ?)",
            (body.group_id, user_id, body.content)
            )
    # 2. 获取发送者昵称用于会话预览
    sender = db_fetchone("SELECT nickname FROM users WHERE id = ?", (user_id,))
    sender_name = sender["nickname"] if sender else "Unknown"
    # 3. 更新所有群成员的会话记录
    members = db_fetchall("SELECT user_id FROM user_in_group WHERE group_id = ?", (body.group_id,))
    for m in members:
        if m["user_id"] == user_id:
            db_execute("""
                INSERT INTO conversations (user_id, type, target_id, last_message, last_message_time, unread_count, is_hidden)
                VALUES (?, 'group', ?, ?, datetime('now'), 0, 0)
                ON CONFLICT(user_id, type, target_id) DO UPDATE SET
                    last_message = excluded.last_message,
                    last_message_time = excluded.last_message_time,
                    is_hidden = 0
            """, (user_id, body.group_id, f"我: {body.content}"))
        else:
            db_execute("""
                INSERT INTO conversations (user_id, type, target_id, last_message, last_message_time, unread_count, is_hidden)
                VALUES (?, 'group', ?, ?, datetime('now'), 1, 0)
                ON CONFLICT(user_id, type, target_id) DO UPDATE SET
                    last_message = excluded.last_message,
                    last_message_time = excluded.last_message_time,
                    unread_count = unread_count + 1,
                    is_hidden = 0
            """, (m["user_id"], body.group_id, f"{sender_name}: {body.content}"))
    db_commit()
    log_api("POST /send-group-msg", user_id, f"group={body.group_id} members={len(members)} len={len(body.content)}", "success")
    return {"status": "success"}

class Recv_Group_Msg_Req(BaseModel):
    cookie: str
    group_id: int
    count: int = 20
    before_id: int = 0       # 游标分页：获取id < before_id的消息，0=最新

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
        log_api("POST /recv-group-msg", user_id, f"group={body.group_id}", "Not in group")
        return {"error": "You are not in this group."}
    last_read = membership["last_read_id"]

    # 游标分页：before_id>0 时加载更早的消息
    if body.before_id > 0:
        messages = db_fetchall("""
                SELECT gm.id, gm.sender_id, u.username, u.nickname, u.avatar, gm.content, gm.sent_at
                FROM group_messages gm
                JOIN users u ON u.id = gm.sender_id
                WHERE gm.group_id = ? AND gm.id < ?
                ORDER BY gm.id DESC
                LIMIT ?
        """, (body.group_id, body.before_id, body.count))
        messages = list(reversed(messages))  # 反转为时间正序
        has_more = len(messages) == body.count
        page_mode = f"before_id={body.before_id}"
    else:
        # before_id=0: 返回最新 N 条消息（不受 last_read_id 影响，与私聊一致）
        messages = db_fetchall("""
                SELECT gm.id, gm.sender_id, u.username, u.nickname, u.avatar, gm.content, gm.sent_at
                FROM group_messages gm
                JOIN users u ON u.id = gm.sender_id
                WHERE gm.group_id = ?
                ORDER BY gm.id DESC
                LIMIT ?
        """, (body.group_id, body.count))
        messages = list(reversed(messages))  # 反转为时间正序
        has_more = len(messages) == body.count
        page_mode = "latest"

    # 更新 last_read_id（仅用于未读计数追踪，不影响消息返回）
    if messages:
        max_id = max(m["id"] for m in messages)
        if max_id > last_read:
            db_execute(
                    "UPDATE user_in_group SET last_read_id = ? WHERE group_id = ? AND user_id = ?",
                    (max_id, body.group_id, user_id)
                    )
    # 重置该群聊会话的未读计数
    db_execute("""
        UPDATE conversations SET unread_count = 0
        WHERE user_id = ? AND type = 'group' AND target_id = ?
    """, (user_id, body.group_id))
    db_commit()
    log_api("POST /recv-group-msg", user_id, f"group={body.group_id} {page_mode}", f"{len(messages)} msgs has_more={has_more}")
    return {"messages": [dict(m) for m in messages], "has_more": has_more}

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
    log_api("POST /get-group-members", user_id, f"group={body.group_id}", f"{len(members)} members")
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
    log_api("POST /get-my-groups", user_id, "", f"{len(groups)} groups")
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
    post_count = db_fetchone(
            "SELECT COUNT(*) AS cnt FROM posts WHERE publisher_id = ?",
            (user["id"],)
        )
    follower_count = db_fetchone(
            "SELECT COUNT(*) AS cnt FROM following WHERE followee = ?",
            (user["id"],)
        )
    followee_count = db_fetchone(
            "SELECT COUNT(*) AS cnt FROM following WHERE follower = ?",
            (user["id"],)
        )
    return {
        "valid": True,
        "user_id": user["id"],
        "username": user["username"],
        "nickname": user["nickname"],
        "avatar": user["avatar"],
        "signature": user["signature"],
        "email": user["email"],
        "post_count": post_count["cnt"] if post_count else 0,
        "follower_count": follower_count["cnt"] if follower_count else 0,
        "followee_count": followee_count["cnt"] if followee_count else 0,
    }

# ======================================================================
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

# =============================================================================
# 消息功能：新增 API 端点
# =============================================================================

# ── Pydantic 模型 ──

class Fetch_Conversations_Req(BaseModel):
    cookie: str

class Hide_Conversation_Req(BaseModel):
    cookie: str
    conversation_id: int

class Fetch_Private_Msgs_Req(BaseModel):
    cookie: str
    with_user_id: int
    before_id: int = 0      # 游标分页：获取id < before_id的消息，0=最新
    count: int = 20

class Search_Contacts_Req(BaseModel):
    cookie: str
    keyword: str
    type: str = "all"       # "all" | "user" | "group"

class Get_Contacts_Req(BaseModel):
    cookie: str

class Get_User_Detail_Req(BaseModel):
    cookie: str
    user_id: int

class Get_Group_Detail_Req(BaseModel):
    cookie: str
    group_id: int

class Update_Group_Req(BaseModel):
    cookie: str
    group_id: int
    name: str = ""          # 可选：新群名称
    avatar: str = ""        # 可选：新群头像(base64)

# ── 2.3.1 POST /get-conversations ──

@app.post("/get-conversations")
def get_conversations(body: Fetch_Conversations_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        log_api("POST /get-conversations", None, "", "Bad cookie")
        return {"error": "Bad cookie."}
    convs = db_fetchall("""
        SELECT id, type, target_id, last_message, last_message_time, unread_count
        FROM conversations
        WHERE user_id = ? AND is_hidden = 0
        ORDER BY last_message_time DESC
    """, (user_id,))
    result = []
    for c in convs:
        item = dict(c)
        if c["type"] == "private":
            target = db_fetchone(
                    "SELECT nickname, avatar FROM users WHERE id = ?",
                    (c["target_id"],)
                    )
            item["target_name"] = target["nickname"] if target else "Unknown"
            item["target_avatar"] = target["avatar"] if target else ""
        else:
            target = db_fetchone(
                    "SELECT name, avatar FROM groups WHERE id = ?",
                    (c["target_id"],)
                    )
            item["target_name"] = target["name"] if target else "Unknown"
            item["target_avatar"] = target["avatar"] if target else ""
        result.append(item)
    unread_total = sum(c.get("unread_count", 0) for c in result)
    log_api("POST /get-conversations", user_id, "", f"{len(result)} convs, unread_total={unread_total}")
    return {"conversations": result}

# ── 2.3.2 POST /get-private-messages ──

@app.post("/get-private-messages")
def get_private_messages(body: Fetch_Private_Msgs_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        log_api("POST /get-private-messages", None, f"with={body.with_user_id}", "Bad cookie")
        return {"error": "Bad cookie."}
    # 游标分页查询（双方的消息都查）
    if body.before_id > 0:
        msgs = db_fetchall("""
            SELECT m.id, m.sender_id, u.nickname AS sender_name, u.avatar AS sender_avatar, m.sent_at, m.content
            FROM offline_messages m
            JOIN users u ON u.id = m.sender_id
            WHERE ((m.sender_id = ? AND m.receiver_id = ?)
                OR (m.sender_id = ? AND m.receiver_id = ?))
              AND m.id < ?
            ORDER BY m.id DESC
            LIMIT ?
        """, (user_id, body.with_user_id, body.with_user_id, user_id,
              body.before_id, body.count))
        has_more = len(msgs) == body.count
        msgs_list = [dict(m) for m in reversed(msgs)]
        page_mode = f"before_id={body.before_id}"
    else:
        msgs = db_fetchall("""
            SELECT m.id, m.sender_id, u.nickname AS sender_name, u.avatar AS sender_avatar, m.sent_at, m.content
            FROM offline_messages m
            JOIN users u ON u.id = m.sender_id
            WHERE ((m.sender_id = ? AND m.receiver_id = ?)
                OR (m.sender_id = ? AND m.receiver_id = ?))
            ORDER BY m.id DESC
            LIMIT ?
        """, (user_id, body.with_user_id, body.with_user_id, user_id, body.count))
        has_more = len(msgs) == body.count
        msgs_list = [dict(m) for m in reversed(msgs)]
        page_mode = "latest"
    # 将对方发来的未读消息标记为已读
    db_execute("""
        UPDATE offline_messages SET is_read = 1
        WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
    """, (body.with_user_id, user_id))
    # 重置该私聊会话的未读计数
    db_execute("""
        UPDATE conversations SET unread_count = 0
        WHERE user_id = ? AND type = 'private' AND target_id = ?
    """, (user_id, body.with_user_id))
    db_commit()
    log_api("POST /get-private-messages", user_id, f"with={body.with_user_id} {page_mode}", f"{len(msgs_list)} msgs has_more={has_more}")
    return {"messages": msgs_list, "has_more": has_more}

# ── 2.3.3 POST /search-contacts ──

@app.post("/search-contacts")
def search_contacts(body: Search_Contacts_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        log_api("POST /search-contacts", None, f"kw={body.keyword} type={body.type}", "Bad cookie")
        return {"error": "Bad cookie."}
    keyword = f"%{body.keyword}%"
    users_result = []
    groups_result = []
    if body.type in ("all", "user"):
        users = db_fetchall("""
            SELECT u.id, u.username, u.nickname, u.avatar,
                   (SELECT 1 FROM following WHERE follower = ? AND followee = u.id) AS is_following,
                   (SELECT 1 FROM following WHERE follower = u.id AND followee = ?) AS is_followed_back,
                   (SELECT status FROM friend_requests WHERE from_user_id = ? AND to_user_id = u.id) AS sent_request_status,
                   (SELECT status FROM friend_requests WHERE from_user_id = u.id AND to_user_id = ?) AS received_request_status
            FROM users u
            WHERE u.id != ?
              AND (u.username LIKE ? OR u.nickname LIKE ?)
            LIMIT 30
        """, (user_id, user_id, user_id, user_id, user_id, keyword, keyword))
        for u in users:
            d = dict(u)
            d["is_following"] = d["is_following"] is not None
            d["is_mutual"] = d["is_following"] and (d["is_followed_back"] is not None)
            # 好友请求状态: None=无申请, "pending"=待处理, "accepted"=已接受, "rejected"=已拒绝
            d["friend_request_status"] = d["sent_request_status"] or d["received_request_status"]
            del d["is_followed_back"]
            del d["sent_request_status"]
            del d["received_request_status"]
            users_result.append(d)
    if body.type in ("all", "group"):
        groups = db_fetchall("""
            SELECT g.id, g.name, g.avatar, g.owner_id,
                   (SELECT 1 FROM user_in_group WHERE group_id = g.id AND user_id = ?) AS is_member
            FROM groups g
            WHERE g.name LIKE ?
            LIMIT 30
        """, (user_id, keyword))
        for g in groups:
            d = dict(g)
            d["is_member"] = d["is_member"] is not None
            groups_result.append(d)
    log_api("POST /search-contacts", user_id, f"kw={body.keyword} type={body.type}", f"{len(users_result)} users + {len(groups_result)} groups")
    return {"users": users_result, "groups": groups_result}

# ── 2.3.4 POST /get-contacts ──

@app.post("/get-contacts")
def get_contacts(body: Get_Contacts_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        log_api("POST /get-contacts", None, "", "Bad cookie")
        return {"error": "Bad cookie."}
    # 好友（双向关注）
    mutual = db_fetchall("""
        SELECT u.id, u.username, u.nickname, u.avatar, u.signature
        FROM users u
        WHERE u.id IN (
            SELECT f1.followee FROM following f1 WHERE f1.follower = ?
            INTERSECT
            SELECT f2.follower FROM following f2 WHERE f2.followee = ?
        )
    """, (user_id, user_id))
    # 仅关注的（单向）
    followed_only = db_fetchall("""
        SELECT u.id, u.username, u.nickname, u.avatar, u.signature
        FROM users u
        WHERE u.id IN (SELECT followee FROM following WHERE follower = ?)
          AND u.id NOT IN (SELECT follower FROM following WHERE followee = ?)
    """, (user_id, user_id))
    log_api("POST /get-contacts", user_id, "", f"mutual={len(mutual)} followed={len(followed_only)}")
    # 待处理的好友申请（别人发给我的）
    pending_requests = db_fetchall("""
        SELECT fr.id AS request_id, u.id, u.username, u.nickname, u.avatar,
               fr.status, fr.created_at AS requested_at
        FROM friend_requests fr
        JOIN users u ON u.id = fr.from_user_id
        WHERE fr.to_user_id = ? AND fr.status = 'pending'
        ORDER BY fr.created_at DESC
    """, (user_id,))
    return {
        "mutual": [dict(m) for m in mutual],
        "followed_only": [dict(f) for f in followed_only],
        "pending_requests": [dict(p) for p in pending_requests]
    }

# ── 2.3.5 POST /hide-conversation ──

@app.post("/hide-conversation")
def hide_conversation(body: Hide_Conversation_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        log_api("POST /hide-conversation", None, f"conv={body.conversation_id}", "Bad cookie")
        return {"error": "Bad cookie."}
    conv = db_fetchone(
            "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
            (body.conversation_id, user_id)
            )
    if not conv:
        log_api("POST /hide-conversation", user_id, f"conv={body.conversation_id}", "Not found")
        return {"error": "Conversation not found."}
    db_execute(
            "UPDATE conversations SET is_hidden = 1 WHERE id = ? AND user_id = ?",
            (body.conversation_id, user_id)
            )
    db_commit()
    log_api("POST /hide-conversation", user_id, f"conv={body.conversation_id}", "success")
    return {"status": "success"}

# ── 2.3.6 POST /get-user-detail ──

@app.post("/get-user-detail")
def get_user_detail(body: Get_User_Detail_Req):
    my_id = resolve_user(body.cookie)
    if not my_id:
        log_api("POST /get-user-detail", None, f"target={body.user_id}", "Bad cookie")
        return {"error": "Bad cookie."}
    target = db_fetchone(
            "SELECT id, username, nickname, avatar, signature FROM users WHERE id = ?",
            (body.user_id,)
            )
    if not target:
        log_api("POST /get-user-detail", my_id, f"target={body.user_id}", "User not exist")
        return {"error": "User not exist."}
    post_count = db_fetchone(
            "SELECT COUNT(*) AS cnt FROM posts WHERE publisher_id = ?",
            (body.user_id,)
            )
    follower_count = db_fetchone(
            "SELECT COUNT(*) AS cnt FROM following WHERE followee = ?",
            (body.user_id,)
            )
    followee_count = db_fetchone(
            "SELECT COUNT(*) AS cnt FROM following WHERE follower = ?",
            (body.user_id,)
            )
    # 关注关系
    i_follow = db_fetchone(
            "SELECT 1 FROM following WHERE follower = ? AND followee = ?",
            (my_id, body.user_id)
            )
    follows_me = db_fetchone(
            "SELECT 1 FROM following WHERE follower = ? AND followee = ?",
            (body.user_id, my_id)
            )
    log_api("POST /get-user-detail", my_id, f"target={body.user_id}", f"user={target['username']}")
    return {
        "id": target["id"],
        "username": target["username"],
        "nickname": target["nickname"],
        "avatar": target["avatar"],
        "signature": target["signature"],
        "post_count": post_count["cnt"] if post_count else 0,
        "follower_count": follower_count["cnt"] if follower_count else 0,
        "followee_count": followee_count["cnt"] if followee_count else 0,
        "is_following": i_follow is not None,
        "is_mutual": (i_follow is not None) and (follows_me is not None),
    }

# ── 2.3.7 POST /get-group-detail ──

@app.post("/get-group-detail")
def get_group_detail(body: Get_Group_Detail_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        log_api("POST /get-group-detail", None, f"group={body.group_id}", "Bad cookie")
        return {"error": "Bad cookie."}
    group = db_fetchone(
            "SELECT id, name, owner_id, avatar, created_at FROM groups WHERE id = ?",
            (body.group_id,)
            )
    if not group:
        log_api("POST /get-group-detail", user_id, f"group={body.group_id}", "Group not exist")
        return {"error": "Group not exist."}
    my_membership = db_fetchone(
            "SELECT role FROM user_in_group WHERE group_id = ? AND user_id = ?",
            (body.group_id, user_id)
            )
    members = db_fetchall("""
        SELECT u.id, u.username, u.nickname, u.avatar, ug.role, ug.joined_at
        FROM user_in_group ug
        JOIN users u ON u.id = ug.user_id
        WHERE ug.group_id = ?
        ORDER BY ug.joined_at ASC
    """, (body.group_id,))
    member_count = len(members)
    log_api("POST /get-group-detail", user_id, f"group={body.group_id}", f"name={group['name']} members={member_count}")
    return {
        "id": group["id"],
        "name": group["name"],
        "avatar": group["avatar"],
        "owner_id": group["owner_id"],
        "created_at": group["created_at"],
        "member_count": member_count,
        "members": [dict(m) for m in members],
        "my_role": my_membership["role"] if my_membership else None,
    }

# ── 补充：POST /update-group（更新群名称/头像，仅群主可操作）──

@app.post("/update-group")
def update_group(body: Update_Group_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        log_api("POST /update-group", None, f"group={body.group_id}", "Bad cookie")
        return {"error": "Bad cookie."}
    group = db_fetchone(
            "SELECT id, owner_id FROM groups WHERE id = ?",
            (body.group_id,)
            )
    if not group:
        log_api("POST /update-group", user_id, f"group={body.group_id}", "Group not exist")
        return {"error": "Group not exist."}
    if group["owner_id"] != user_id:
        log_api("POST /update-group", user_id, f"group={body.group_id}", "Not owner")
        return {"error": "Only group owner can update group info."}
    changes = []
    if body.name:
        db_execute(
                "UPDATE groups SET name = ? WHERE id = ?",
                (body.name, body.group_id)
                )
        changes.append("name")
    if body.avatar:
        db_execute(
                "UPDATE groups SET avatar = ? WHERE id = ?",
                (body.avatar, body.group_id)
                )
        changes.append("avatar")
    db_commit()
    log_api("POST /update-group", user_id, f"group={body.group_id}", f"updated: {','.join(changes) if changes else 'nothing'}")
    return {"status": "success"}

# =============================================================================
# 好友申请系统 (BUG 1 修复)
# =============================================================================

class Send_Friend_Req_Req(BaseModel):
    cookie: str
    to_user_id: int

@app.post("/send-friend-request")
def send_friend_request(body: Send_Friend_Req_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        log_api("POST /send-friend-request", None, f"to={body.to_user_id}", "Bad cookie")
        return {"error": "Bad cookie."}
    if user_id == body.to_user_id:
        log_api("POST /send-friend-request", user_id, "to=self", "Cannot friend yourself")
        return {"error": "Cannot send friend request to yourself."}
    target = db_fetchone("SELECT id FROM users WHERE id = ?", (body.to_user_id,))
    if not target:
        log_api("POST /send-friend-request", user_id, f"to={body.to_user_id}", "User not exist")
        return {"error": "User not exist."}
    # 检查是否已是好友（双向关注）
    mutual = db_fetchone("""
        SELECT 1 FROM following f1
        WHERE f1.follower = ? AND f1.followee = ?
        INTERSECT
        SELECT 1 FROM following f2
        WHERE f2.follower = ? AND f2.followee = ?
    """, (user_id, body.to_user_id, body.to_user_id, user_id))
    if mutual:
        log_api("POST /send-friend-request", user_id, f"to={body.to_user_id}", "Already friends")
        return {"error": "Already friends."}
    # 检查是否已有待处理申请
    existing = db_fetchone(
        "SELECT id, status FROM friend_requests WHERE from_user_id = ? AND to_user_id = ?",
        (user_id, body.to_user_id)
    )
    if existing:
        if existing["status"] == "pending":
            log_api("POST /send-friend-request", user_id, f"to={body.to_user_id}", "Request already pending")
            return {"error": "Friend request already sent."}
        # 之前被拒绝过，允许重新发送：更新状态
        db_execute(
            "UPDATE friend_requests SET status = 'pending', created_at = datetime('now') WHERE id = ?",
            (existing["id"],)
        )
        db_commit()
        log_api("POST /send-friend-request", user_id, f"to={body.to_user_id}", "request re-sent")
        return {"status": "success", "request_id": existing["id"]}
    db_execute(
        "INSERT INTO friend_requests (from_user_id, to_user_id) VALUES (?, ?)",
        (user_id, body.to_user_id)
    )
    db_commit()
    log_api("POST /send-friend-request", user_id, f"to={body.to_user_id}", f"request_id={db_lastrowid()}")
    return {"status": "success", "request_id": db_lastrowid()}

class Get_Friend_Reqs_Req(BaseModel):
    cookie: str

@app.post("/get-friend-requests")
def get_friend_requests(body: Get_Friend_Reqs_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        log_api("POST /get-friend-requests", None, "", "Bad cookie")
        return {"error": "Bad cookie."}
    # 收到的申请
    incoming = db_fetchall("""
        SELECT fr.id, fr.from_user_id, u.username, u.nickname, u.avatar, fr.status, fr.created_at
        FROM friend_requests fr
        JOIN users u ON u.id = fr.from_user_id
        WHERE fr.to_user_id = ? AND fr.status = 'pending'
        ORDER BY fr.created_at DESC
    """, (user_id,))
    # 发出的申请
    outgoing = db_fetchall("""
        SELECT fr.id, fr.to_user_id, u.username, u.nickname, u.avatar, fr.status, fr.created_at
        FROM friend_requests fr
        JOIN users u ON u.id = fr.to_user_id
        WHERE fr.from_user_id = ?
        ORDER BY fr.created_at DESC
    """, (user_id,))
    log_api("POST /get-friend-requests", user_id, "",
            f"incoming={len(incoming)} outgoing={len(outgoing)}")
    return {
        "incoming": [dict(r) for r in incoming],
        "outgoing": [dict(r) for r in outgoing]
    }

class Handle_Friend_Req_Req(BaseModel):
    cookie: str
    request_id: int
    action: str   # "accept" | "reject"

@app.post("/handle-friend-request")
def handle_friend_request(body: Handle_Friend_Req_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        log_api("POST /handle-friend-request", None, f"req={body.request_id}", "Bad cookie")
        return {"error": "Bad cookie."}
    if body.action not in ("accept", "reject"):
        log_api("POST /handle-friend-request", user_id, f"req={body.request_id}", f"Bad action: {body.action}")
        return {"error": "Action must be 'accept' or 'reject'."}
    req = db_fetchone(
        "SELECT id, from_user_id, to_user_id, status FROM friend_requests WHERE id = ?",
        (body.request_id,)
    )
    if not req:
        log_api("POST /handle-friend-request", user_id, f"req={body.request_id}", "Request not found")
        return {"error": "Friend request not found."}
    if req["to_user_id"] != user_id:
        log_api("POST /handle-friend-request", user_id, f"req={body.request_id}", "Not your request")
        return {"error": "This request is not for you."}
    if req["status"] != "pending":
        log_api("POST /handle-friend-request", user_id, f"req={body.request_id}", f"Already {req['status']}")
        return {"error": f"Request already {req['status']}."}
    if body.action == "accept":
        # 双向关注 → 成为好友
        db_execute("INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)",
                   (req["from_user_id"], req["to_user_id"]))
        db_execute("INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)",
                   (req["to_user_id"], req["from_user_id"]))
        db_execute("UPDATE friend_requests SET status = 'accepted' WHERE id = ?",
                   (body.request_id,))
        log_api("POST /handle-friend-request", user_id, f"req={body.request_id}", "accepted")
    else:
        db_execute("UPDATE friend_requests SET status = 'rejected' WHERE id = ?",
                   (body.request_id,))
        log_api("POST /handle-friend-request", user_id, f"req={body.request_id}", "rejected")
    db_commit()
    return {"status": "success", "result": body.action}

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
            "favourites_count": p.get("favourites_count", 0),
            "reblogs_count": p.get("reblogs_count", 0),
            "replies_count": p.get("replies_count", 0),
            "created_at": p["created_at"],
            "repost_id": p.get("repost_id"),
            "media": [dict(m) for m in media],
            "tags": [r["tag"] for r in tags],
        })
    return {"posts": posts}

# =============================================================================
# Social 模块路由 — 屏蔽、搜索、通知、推荐、审核
# =============================================================================

# ── 屏蔽 / 取消屏蔽 ──

class Block_User_Req(BaseModel):
    cookie: str
    blocked_id: int

@app.post("/block")
def block_user(body: Block_User_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    result = social_mod.block(user_id, body.blocked_id)
    log_api("POST /block", user_id, f"target={body.blocked_id}", result.get("status", "error"))
    return result

@app.post("/unblock")
def unblock_user(body: Block_User_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    result = social_mod.unblock(user_id, body.blocked_id)
    return result

@app.post("/get-blocked")
def get_blocked_list(body: Get_Follower):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return {"blocked": social_mod.get_blocked(user_id)}

# ── 静音 / 取消静音 ──

class Mute_Req(BaseModel):
    cookie: str
    muted_id: int

@app.post("/mute")
def mute_user(body: Mute_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    result = social_mod.mute(user_id, body.muted_id)
    return result

@app.post("/unmute")
def unmute_user(body: Mute_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    result = social_mod.unmute(user_id, body.muted_id)
    return result

@app.post("/get-muted")
def get_muted_list(body: Get_Follower):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return {"muted": social_mod.get_muted(user_id)}

# ── FTS5 全文搜索 ──

class Social_Search_Req(BaseModel):
    cookie: str
    query: str
    limit: int = 20

@app.post("/social/search")
def social_search_api(body: Social_Search_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    result = social_search.search_all(body.query, viewer_id=user_id, limit=body.limit)
    log_api("POST /social/search", user_id, f"query={body.query}", f"posts={len(result.get('posts',[]))} users={len(result.get('users',[]))} tags={len(result.get('tags',[]))}")
    return result

@app.post("/social/search-users")
def social_search_users(body: Social_Search_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return {"users": social_search.search_users(body.query, limit=body.limit)}

@app.post("/social/search-posts")
def social_search_posts(body: Social_Search_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return {"posts": social_search.search_posts(body.query, viewer_id=user_id, limit=body.limit)}

# ── 通知 ──

class Notification_Req(BaseModel):
    cookie: str
    limit: int = 40
    offset: int = 0

@app.post("/notifications")
def get_notifications(body: Notification_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return {"notifications": social_notify.get_notifications(user_id, limit=body.limit, offset=body.offset)}

@app.post("/notifications/unread-count")
def unread_count(body: Get_Follower):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return {"count": social_notify.get_unread_count(user_id)}

class Mark_Read_Req(BaseModel):
    cookie: str
    notification_ids: list[int]

@app.post("/notifications/mark-read")
def mark_notifications_read(body: Mark_Read_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    count = social_notify.mark_read(body.notification_ids, user_id)
    return {"marked": count}

@app.post("/notifications/mark-all-read")
def mark_all_read(body: Get_Follower):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    count = social_notify.mark_all_read(user_id)
    return {"marked": count}

# ── 推荐 ──

@app.post("/recommend/users")
def recommend_users(body: Notification_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return {"users": social_mod.recommend_users(user_id, limit=body.limit)}

@app.post("/recommend/posts")
def recommend_posts(body: Social_Search_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return {"posts": social_mod.recommend_posts(user_id, limit=body.limit)}

# ── 好友分组 ──

class Create_Friend_Group_Req(BaseModel):
    cookie: str
    name: str

@app.post("/friend-groups/create")
def create_friend_group(body: Create_Friend_Group_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    result = social_mod.create_friend_group(user_id, body.name)
    log_api("POST /friend-groups/create", user_id, f"name={body.name}", result.get("status", "error"))
    return result

class Delete_Friend_Group_Req(BaseModel):
    cookie: str
    group_id: int

@app.post("/friend-groups/delete")
def delete_friend_group(body: Delete_Friend_Group_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return social_mod.delete_friend_group(body.group_id, user_id)

@app.post("/friend-groups/list")
def list_friend_groups(body: Get_Follower):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return {"groups": social_mod.get_friend_groups(user_id)}

class Friend_Group_Member_Req(BaseModel):
    cookie: str
    group_id: int
    friend_id: int

@app.post("/friend-groups/add-member")
def add_to_friend_group(body: Friend_Group_Member_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return social_mod.add_to_friend_group(body.group_id, user_id, body.friend_id)

@app.post("/friend-groups/remove-member")
def remove_from_friend_group(body: Friend_Group_Member_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return social_mod.remove_from_friend_group(body.group_id, user_id, body.friend_id)

# ── 检查好友关系 ──

class Check_Friend_Req(BaseModel):
    cookie: str
    target_id: int

@app.post("/check-friend")
def check_friend(body: Check_Friend_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return {"are_friends": social_mod.are_friends(user_id, body.target_id)}

@app.post("/get-friends")
def get_friends(body: Get_Follower):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return {"friends": social_mod.get_friends(user_id)}

# ── 审核 / 举报 ──

class Report_Req(BaseModel):
    cookie: str
    post_id: int
    reason: str = ""

@app.post("/report")
def report_content(body: Report_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    result = social_mod.report_content(user_id, body.post_id, body.reason)
    log_api("POST /report", user_id, f"post={body.post_id}", result.get("status", "error"))
    return result

class Admin_Base_Req(BaseModel):
    cookie: str

class Admin_Review_Req(BaseModel):
    cookie: str
    report_id: int
    action: str = ""    # "dismiss" | "delete_post" | "ban_user"
    note: str = ""

@app.post("/admin/reports")
def get_reports(body: Admin_Base_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return {"reports": social_mod.get_reports(user_id)}

@app.post("/admin/review-report")
def review_report(body: Admin_Review_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return social_mod.review_report(body.report_id, user_id, body.action, body.note)

class Admin_Ban_Req(BaseModel):
    cookie: str
    target_id: int
    reason: str = ""

@app.post("/admin/ban")
def ban_user(body: Admin_Ban_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return social_mod.ban_user(user_id, body.target_id, body.reason)

@app.post("/admin/unban")
def unban_user(body: Admin_Ban_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        return {"error": "Bad cookie."}
    return social_mod.unban_user(user_id, body.target_id)

# ── 补充：POST /update-group（更新群名称/头像，仅群主可操作）──

@app.post("/update-group")
def update_group(body: Update_Group_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        log_api("POST /update-group", None, f"group={body.group_id}", "Bad cookie")
        return {"error": "Bad cookie."}
    group = db_fetchone(
            "SELECT id, owner_id FROM groups WHERE id = ?",
            (body.group_id,)
            )
    if not group:
        log_api("POST /update-group", user_id, f"group={body.group_id}", "Group not exist")
        return {"error": "Group not exist."}
    if group["owner_id"] != user_id:
        log_api("POST /update-group", user_id, f"group={body.group_id}", "Not owner")
        return {"error": "Only group owner can update group info."}
    changes = []
    if body.name:
        db_execute(
                "UPDATE groups SET name = ? WHERE id = ?",
                (body.name, body.group_id)
                )
        changes.append("name")
    if body.avatar:
        db_execute(
                "UPDATE groups SET avatar = ? WHERE id = ?",
                (body.avatar, body.group_id)
                )
        changes.append("avatar")
    db_commit()
    log_api("POST /update-group", user_id, f"group={body.group_id}", f"updated: {','.join(changes) if changes else 'nothing'}")
    return {"status": "success"}

# =============================================================================
# 好友申请系统 (BUG 1 修复)
# =============================================================================

class Send_Friend_Req_Req(BaseModel):
    cookie: str
    to_user_id: int

@app.post("/send-friend-request")
def send_friend_request(body: Send_Friend_Req_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        log_api("POST /send-friend-request", None, f"to={body.to_user_id}", "Bad cookie")
        return {"error": "Bad cookie."}
    if user_id == body.to_user_id:
        log_api("POST /send-friend-request", user_id, "to=self", "Cannot friend yourself")
        return {"error": "Cannot send friend request to yourself."}
    target = db_fetchone("SELECT id FROM users WHERE id = ?", (body.to_user_id,))
    if not target:
        log_api("POST /send-friend-request", user_id, f"to={body.to_user_id}", "User not exist")
        return {"error": "User not exist."}
    # 检查是否已是好友（双向关注）
    mutual = db_fetchone("""
        SELECT 1 FROM following f1
        WHERE f1.follower = ? AND f1.followee = ?
        INTERSECT
        SELECT 1 FROM following f2
        WHERE f2.follower = ? AND f2.followee = ?
    """, (user_id, body.to_user_id, body.to_user_id, user_id))
    if mutual:
        log_api("POST /send-friend-request", user_id, f"to={body.to_user_id}", "Already friends")
        return {"error": "Already friends."}
    # 检查是否已有待处理申请
    existing = db_fetchone(
        "SELECT id, status FROM friend_requests WHERE from_user_id = ? AND to_user_id = ?",
        (user_id, body.to_user_id)
    )
    if existing:
        if existing["status"] == "pending":
            log_api("POST /send-friend-request", user_id, f"to={body.to_user_id}", "Request already pending")
            return {"error": "Friend request already sent."}
        # 之前被拒绝过，允许重新发送：更新状态
        db_execute(
            "UPDATE friend_requests SET status = 'pending', created_at = datetime('now') WHERE id = ?",
            (existing["id"],)
        )
        db_commit()
        log_api("POST /send-friend-request", user_id, f"to={body.to_user_id}", "request re-sent")
        return {"status": "success", "request_id": existing["id"]}
    db_execute(
        "INSERT INTO friend_requests (from_user_id, to_user_id) VALUES (?, ?)",
        (user_id, body.to_user_id)
    )
    db_commit()
    log_api("POST /send-friend-request", user_id, f"to={body.to_user_id}", f"request_id={db_lastrowid()}")
    return {"status": "success", "request_id": db_lastrowid()}

class Get_Friend_Reqs_Req(BaseModel):
    cookie: str

@app.post("/get-friend-requests")
def get_friend_requests(body: Get_Friend_Reqs_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        log_api("POST /get-friend-requests", None, "", "Bad cookie")
        return {"error": "Bad cookie."}
    # 收到的申请
    incoming = db_fetchall("""
        SELECT fr.id, fr.from_user_id, u.username, u.nickname, u.avatar, fr.status, fr.created_at
        FROM friend_requests fr
        JOIN users u ON u.id = fr.from_user_id
        WHERE fr.to_user_id = ? AND fr.status = 'pending'
        ORDER BY fr.created_at DESC
    """, (user_id,))
    # 发出的申请
    outgoing = db_fetchall("""
        SELECT fr.id, fr.to_user_id, u.username, u.nickname, u.avatar, fr.status, fr.created_at
        FROM friend_requests fr
        JOIN users u ON u.id = fr.to_user_id
        WHERE fr.from_user_id = ?
        ORDER BY fr.created_at DESC
    """, (user_id,))
    log_api("POST /get-friend-requests", user_id, "",
            f"incoming={len(incoming)} outgoing={len(outgoing)}")
    return {
        "incoming": [dict(r) for r in incoming],
        "outgoing": [dict(r) for r in outgoing]
    }

class Handle_Friend_Req_Req(BaseModel):
    cookie: str
    request_id: int
    action: str   # "accept" | "reject"

@app.post("/handle-friend-request")
def handle_friend_request(body: Handle_Friend_Req_Req):
    user_id = resolve_user(body.cookie)
    if not user_id:
        log_api("POST /handle-friend-request", None, f"req={body.request_id}", "Bad cookie")
        return {"error": "Bad cookie."}
    if body.action not in ("accept", "reject"):
        log_api("POST /handle-friend-request", user_id, f"req={body.request_id}", f"Bad action: {body.action}")
        return {"error": "Action must be 'accept' or 'reject'."}
    req = db_fetchone(
        "SELECT id, from_user_id, to_user_id, status FROM friend_requests WHERE id = ?",
        (body.request_id,)
    )
    if not req:
        log_api("POST /handle-friend-request", user_id, f"req={body.request_id}", "Request not found")
        return {"error": "Friend request not found."}
    if req["to_user_id"] != user_id:
        log_api("POST /handle-friend-request", user_id, f"req={body.request_id}", "Not your request")
        return {"error": "This request is not for you."}
    if req["status"] != "pending":
        log_api("POST /handle-friend-request", user_id, f"req={body.request_id}", f"Already {req['status']}")
        return {"error": f"Request already {req['status']}."}
    if body.action == "accept":
        # 双向关注 → 成为好友
        db_execute("INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)",
                   (req["from_user_id"], req["to_user_id"]))
        db_execute("INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)",
                   (req["to_user_id"], req["from_user_id"]))
        db_execute("UPDATE friend_requests SET status = 'accepted' WHERE id = ?",
                   (body.request_id,))
        # 为双方创建会话记录
        now = _beijing_time()
        db_execute(
            "INSERT OR IGNORE INTO conversations (user_id, type, target_id, last_message, last_message_time, unread_count, is_hidden) VALUES (?, 'private', ?, '你们已成为好友', ?, 0, 0)",
            (req["from_user_id"], req["to_user_id"], now))
        db_execute(
            "INSERT OR IGNORE INTO conversations (user_id, type, target_id, last_message, last_message_time, unread_count, is_hidden) VALUES (?, 'private', ?, '你们已成为好友', ?, 0, 0)",
            (req["to_user_id"], req["from_user_id"], now))
        log_api("POST /handle-friend-request", user_id, f"req={body.request_id}", "accepted")
    else:
        db_execute("UPDATE friend_requests SET status = 'rejected' WHERE id = ?",
                   (body.request_id,))
        log_api("POST /handle-friend-request", user_id, f"req={body.request_id}", "rejected")
    db_commit()
    return {"status": "success", "result": body.action}
if __name__ == "__main__":
    uvicorn.run(app, port = 18999, access_log = False)
