#!/usr/bin/env -S uv run python3
"""
种子数据脚本 — 为 TinyBlog 后端生成测试数据。
用法: uv run python3 seed_data.py
"""

import os, sys, base64, re, random, sqlite3, bcrypt, io, logging
from datetime import datetime, timezone, timedelta
from PIL import Image

# ── 配置 ──
DB_PATH = os.path.join(os.path.dirname(__file__), "main.db")
BACKEND_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.dirname(os.path.dirname(BACKEND_DIR))  # software-engineering/

# 北京时区
TZ_BJ = timezone(timedelta(hours=8))

# ── 日志 ──
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
log = logging.getLogger("seed")

# =============================================================================
# 数据库连接
# =============================================================================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=5000")


def db_execute(sql, params=()):
    return conn.execute(sql, params)


def db_fetchone(sql, params=()):
    return conn.execute(sql, params).fetchone()


def db_fetchall(sql, params=()):
    return conn.execute(sql, params).fetchall()


def db_commit():
    conn.commit()


def db_lastrowid():
    return conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]


# =============================================================================
# 创建所有表（复用 main.py 的建表逻辑）
# =============================================================================
def create_tables():
    """建表逻辑复用后端 main.init_db()，避免 seed 脚本与后端各写一份 schema 造成漂移。"""
    os.chdir(BACKEND_DIR)          # main.py 用相对路径连 main.db
    if BACKEND_DIR not in sys.path:
        sys.path.insert(0, BACKEND_DIR)
    import main as backend_main
    backend_main.init_db()

def bj_now():
    """返回北京时间字符串"""
    return datetime.now(TZ_BJ).strftime("%Y-%m-%d %H:%M:%S")


def bj_ago(days=0, hours=0, minutes=0):
    """返回北京时间过去某时刻字符串"""
    dt = datetime.now(TZ_BJ) - timedelta(days=days, hours=hours, minutes=minutes)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def compress_image_to_base64(img_path, max_width=640, max_height=640, quality=75):
    """压缩图片并返回 base64 (不含 mime prefix)"""
    try:
        img = Image.open(img_path)
        orig_format = img.format or "JPEG"
        # 转换为 RGB（RGBA → RGB）
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGBA")
            # 透明背景铺白色
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        if w > max_width or h > max_height:
            ratio = min(max_width / w, max_height / h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        log.warning(f"图片压缩失败 {img_path}: {e}")
        return None


def compress_video_to_base64(video_path, max_size=500*1024):
    """压缩视频为小尺寸 webm，返回 base64。如达不成 max_size 则返回 None。"""
    import subprocess, tempfile, shutil
    if not shutil.which("ffmpeg"):
        log.warning("ffmpeg 未安装，无法压缩视频")
        return None

    tmp = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        # 尝试极低码率 360p 15fps
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", "scale=480:-2:flags=lanczos",
            "-r", "10",
            "-c:v", "libvpx-vp9",
            "-b:v", "150k",
            "-maxrate", "200k",
            "-bufsize", "300k",
            "-an",
            "-loglevel", "error",
            tmp_path
        ]
        subprocess.run(cmd, check=True, timeout=30)
        compressed_size = os.path.getsize(tmp_path)

        if compressed_size > max_size:
            log.info(f"  视频仍过大 ({compressed_size/1024:.0f}KB)，进一步压缩...")
            # 再压一次：更小分辨率 + 更低码率
            cmd[5] = "scale=320:-2:flags=lanczos"
            cmd[10] = "80k"
            cmd[11] = "120k"
            cmd[12] = "200k"
            subprocess.run(cmd, check=True, timeout=30)
            compressed_size = os.path.getsize(tmp_path)

        if compressed_size > max_size:
            log.warning(f"  视频压缩后仍 {compressed_size/1024:.0f}KB，超过 {max_size/1024:.0f}KB，跳过")
            os.unlink(tmp_path)
            return None

        with open(tmp_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        os.unlink(tmp_path)
        return b64
    except Exception as e:
        log.warning(f"视频压缩失败 {video_path}: {e}")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return None


def random_color_avatar(nickname, size=128):
    """生成随机彩色头像（同 main.py 逻辑），返回 base64"""
    char = nickname[0] if nickname else "?"
    h = random.uniform(0, 360)
    s = random.uniform(55, 80) / 100.0
    l_val = random.uniform(40, 55) / 100.0

    c = (1 - abs(2 * l_val - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l_val - c / 2
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

    def luminance(r2, g2, b2):
        def linearize(cv):
            cv = cv / 255.0
            return cv / 12.92 if cv <= 0.04045 else ((cv + 0.055) / 1.055) ** 2.4
        return 0.2126 * linearize(r2) + 0.7152 * linearize(g2) + 0.0722 * linearize(b2)

    text_color = (255, 255, 255) if luminance(*bg) < 0.5 else (0, 0, 0)

    img = Image.new("RGB", (size, size), bg)
    from PIL import ImageDraw

    # 尝试找字体
    font_paths = [
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc",
    ]
    font = None
    for fp in font_paths:
        if os.path.isfile(fp):
            try:
                from PIL import ImageFont
                font = ImageFont.truetype(fp, 72)
                break
            except:
                pass
    if font is None:
        from PIL import ImageFont
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), char, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) / 2 - bbox[0]
    ty = (size - th) / 2 - bbox[1]
    draw.text((tx, ty), char, fill=text_color, font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def add_avatar_from_file(filepath, max_size=100*1024):
    """从文件读取头像并压缩到不超过 max_size，返回 base64"""
    try:
        img = Image.open(filepath)
        # 统一处理为正方形
        w, h = img.size
        size = min(w, h, 128)
        # 居中裁剪
        left = (w - size) / 2
        top = (h - size) / 2
        img = img.crop((left, top, left + size, top + size))
        img = img.resize((128, 128), Image.LANCZOS)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        buf = io.BytesIO()
        quality = 85
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        while buf.tell() > max_size and quality > 20:
            quality -= 10
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        log.warning(f"头像处理失败 {filepath}: {e}")
        return None


# =============================================================================
# 主要种子数据生成
# =============================================================================

def seed():
    """生成所有种子数据"""
    log.info("=" * 60)
    log.info("开始写入种子数据...")
    log.info("=" * 60)

    # ── 1. 创建用户 ──
    log.info("\n--- 创建用户 ---")
    usernames = [
        ("beichen", "北辰", "主用户，喜欢编程与写作"),
        ("lingyue", "凌月", "前端爱好者，喜欢扁平化设计"),
        ("hangyu", "航宇", "大数据专业，热衷于数据分析"),
        ("moli", "墨离", "插画师，擅长数字绘画"),
        ("yunfei", "云飞", "摄影师，喜欢户外旅行"),
        ("shuiyan", "水烟", "文学少女，热爱古典诗词"),
        ("fengzhi", "风之", "音乐制作人，混音达人"),
        ("qiucao", "秋草", "美食博主，探店达人"),
    ]

    password_hash = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode()
    user_ids = {}

    # 为某些用户准备自定义头像
    avatar_sources = {
        "beichen": None,  # 用生成的彩色头像
        "lingyue": None,
        "moli": None,
        "yunfei": os.path.expanduser("~/Pictures/头像.jpg"),
    }

    for idx, (uname, nick, sig) in enumerate(usernames):
        email = f"{uname}@tinyblog.test"
        avatar_b64 = avatar_sources.get(uname)
        if avatar_b64 == os.path.expanduser("~/Pictures/头像.jpg"):
            # 尝试从文件读取
            file_avatar = add_avatar_from_file(avatar_b64)
            if file_avatar:
                avatar_b64 = file_avatar
                log.info(f"  {uname}: 使用自定义头像")
            else:
                avatar_b64 = random_color_avatar(nick)
                log.info(f"  {uname}: 头像文件读取失败，使用生成的彩色头像")
        else:
            avatar_b64 = random_color_avatar(nick)

        db_execute(
            "INSERT INTO users (username, nickname, password_hash, avatar, signature, email) VALUES (?, ?, ?, ?, ?, ?)",
            (uname, nick, password_hash, avatar_b64, sig, email)
        )
        uid = db_lastrowid()
        user_ids[uname] = uid
        log.info(f"  [{uid}] {uname} / {nick}")

    db_commit()
    main_uid = user_ids["beichen"]
    log.info(f"\n主用户 ID: {main_uid} (beichen)")

    # ── 2. 创建 cookies（让这些用户直接可登录） ──
    log.info("\n--- 创建 Cookie（可直接登录） ---")
    for uname, uid in user_ids.items():
        token = f"seed_token_{uname}_{uid}"
        db_execute(
            "INSERT INTO cookies (user_id, token, expires_at) VALUES (?, ?, datetime('now', '+30 days'))",
            (uid, token)
        )
    db_commit()

    # ── 3. 关注关系 ──
    log.info("\n--- 建立关注关系 ---")
    # 主用户关注所有人
    other_ids = [uid for un, uid in user_ids.items() if un != "beichen"]
    for oid in other_ids:
        db_execute("INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)", (main_uid, oid))
    # 所有人都关注主用户
    for oid in other_ids:
        db_execute("INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)", (oid, main_uid))
    # 凌月 关注 航宇、墨离
    db_execute("INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)", (user_ids["lingyue"], user_ids["hangyu"]))
    db_execute("INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)", (user_ids["lingyue"], user_ids["moli"]))
    # 墨离 关注 风之、秋草
    db_execute("INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)", (user_ids["moli"], user_ids["fengzhi"]))
    db_execute("INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)", (user_ids["moli"], user_ids["qiucao"]))
    # 云飞 关注 水烟
    db_execute("INSERT OR IGNORE INTO following (follower, followee) VALUES (?, ?)", (user_ids["yunfei"], user_ids["shuiyan"]))
    db_commit()
    log.info("  关注关系建立完成")

    # ── 4. 帖子 ──
    log.info("\n--- 创建帖子 ---")

    # 准备好示例媒体
    post_media_map = {}  # post_id -> [base64_strings]

    # 先检查哪些图片文件可用
    available_images = []
    # 可用的较小图片文件
    img_candidates = [
        os.path.expanduser("~/Pictures/wallpaper/武汉大学.jpg"),
        os.path.expanduser("~/Pictures/wallpaper/仙桃市简版分区设色.jpg"),
        os.path.expanduser("~/Pictures/wallpaper/Vladimirka.jpg"),
        os.path.expanduser("~/Pictures/wallpaper/ICSLAB.png"),
        os.path.expanduser("~/Pictures/证件照/4比3.jpg"),
    ]
    # 一些小尺寸截图
    for fname in os.listdir(os.path.expanduser("~/Pictures/屏幕截图")):
        fpath = os.path.join(os.path.expanduser("~/Pictures/屏幕截图"), fname)
        if os.path.getsize(fpath) < 500 * 1024:
            img_candidates.append(fpath)

    # 压缩可用图片
    for img_path in img_candidates:
        if os.path.exists(img_path):
            b64 = compress_image_to_base64(img_path, max_width=480, max_height=480, quality=65)
            if b64:
                available_images.append((os.path.basename(img_path), b64))
                log.info(f"  可用图片: {os.path.basename(img_path)} ({len(b64)//1024}KB base64)")

    # 尝试压缩一个视频
    video_b64 = None
    video_candidates = [
        os.path.expanduser("~/2026-07-11 00-32-16.mp4"),
        os.path.expanduser("~/2026-04-28 11-41-47.mp4"),
    ]
    for vp in video_candidates:
        if os.path.exists(vp) and os.path.getsize(vp) < 10 * 1024 * 1024:
            log.info(f"  尝试压缩视频: {os.path.basename(vp)}...")
            video_b64 = compress_video_to_base64(vp)
            if video_b64:
                log.info(f"    压缩成功 ({len(video_b64)//1024}KB base64)")
                break
            else:
                log.info("    压缩失败或仍过大")

    # ── 主用户的帖子 ──
    posts = [
        (main_uid, "今天终于把 TinyBlog 的消息功能写得差不多了，支持 Markdown 和 LaTeX！\n\n公式测试：$E = mc^2$", 12),
        (main_uid, "分享一篇关于 Python 元编程的文章，非常实用。\n\n#编程 #Python", 8),
        (main_uid, "晚安。\n\n梦里不知身是客，一晌贪欢。", 23),
        (main_uid, "珞珈山上的晚霞美得令人窒息。\n\n#武汉大学 #摄影", 45),
        (user_ids["lingyue"], "今天试了下 QML 的动画系统，配合 Behavior 和 Transition 真的太优雅了。\n\n前端开发真的越来越有意思了。", 15),
        (user_ids["lingyue"], "重构 UI 中，极简风格才是王道。\n\n少即是多。\n\n#设计 #极简主义", 7),
        (user_ids["hangyu"], "用 Pandas 处理了一个 10GB 的数据集，优化后从 40 分钟降到了 2 分钟。\n\n关键点：分块读取 + 向量化操作。\n\n#数据科学 #Pandas", 31),
        (user_ids["hangyu"], "最近在学习 Rust 的数据结构和算法，性能真不是盖的。\n\n#Rust #算法", 9),
        (user_ids["moli"], "新画了一张插画，大家看看怎么样？\n\n#插画 #数字绘画", 56),
        (user_ids["moli"], "色彩搭配是插画的灵魂。\n\n推荐大家看《色彩与光线》这本书。\n\n#艺术 #学习", 11),
        (user_ids["yunfei"], "今天去东湖骑行，拍了几张照片。\n\n#摄影 #东湖 #骑行", 34),
        (user_ids["yunfei"], "分享一个摄影技巧：黄金时刻后半小时的柔光最适合拍人像。\n\n#摄影技巧", 19),
        (user_ids["shuiyan"], "昨夜雨疏风骤，浓睡不消残酒。\n\n试问卷帘人，却道海棠依旧。\n\n#诗词", 42),
        (user_ids["shuiyan"], "今天读完了《百年孤独》，马尔克斯的叙事结构令人叹为观止。\n\n推荐指数：⭐⭐⭐⭐⭐\n\n#读书 #文学", 28),
        (user_ids["fengzhi"], "新 remix 完成了！这次用了一些实验性的合成器音色。\n\n#音乐制作 #电子音乐", 17),
        (user_ids["fengzhi"], "分享我的音乐制作工作台设置。\n\n#音乐 #设备", 13),
        (user_ids["qiucao"], "今天打卡了一家藏在巷子里的小店，招牌红烧肉绝了！\n\n#美食 #探店", 38),
        (user_ids["qiucao"], "分享一个简单的抹茶提拉米苏食谱。\n\n#烘焙 #甜品", 22),
        (main_uid, "做了一个自动生成 LaTeX 笔记的小工具，从 Markdown 一键生成。\n\n```python\ndef md_to_latex(text):\n    # converting...\n    pass\n```\n\n开源地址：https://github.com/tinyblog/notes", 6),
        (main_uid, "测试视频上传功能。", 0),
    ]

    # 为某些帖子分配媒体
    posts_with_images = [8, 10, 16]  # 0-indexed: 墨离的插画, 云飞的东湖, 风之的工作台
    posts_with_video = [19]  # 测试视频帖

    for idx, (uid, content, likes) in enumerate(posts):
        # 错开发布时间
        created = bj_ago(days=random.randint(0, 14), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        db_execute(
            "INSERT INTO posts (publisher_id, content, like_num, created_at) VALUES (?, ?, ?, ?)",
            (uid, content, likes, created)
        )
        pid = db_lastrowid()
        post_media_map[pid] = []

        # 为某些帖子附加媒体
        if idx in posts_with_images and available_images:
            img_count = min(1 if idx != 16 else 2, len(available_images))
            for i in range(img_count):
                fname, b64 = available_images[i % len(available_images)]
                db_execute(
                    "INSERT INTO post_media (post_id, offset, content) VALUES (?, ?, ?)",
                    (pid, i, b64)
                )
                post_media_map[pid].append(("image", fname))

        if idx in posts_with_video and video_b64:
            db_execute(
                "INSERT INTO post_media (post_id, offset, content) VALUES (?, ?, ?)",
                (pid, 0, video_b64)
            )
            post_media_map[pid].append(("video", "sample.webm"))

        log.info(f"  帖子 [{pid}] {content[:40]}...")

    db_commit()
    all_post_ids = list(post_media_map.keys())
    log.info(f"\n  共创建 {len(all_post_ids)} 条帖子")

    # ── 5. 点赞数据 ──
    log.info("\n--- 创建点赞 ---")
    like_count = 0
    for pid in all_post_ids:
        # 让随机用户点赞
        likers = random.sample(other_ids, min(random.randint(1, 4), len(other_ids)))
        for liker_id in likers:
            db_execute("INSERT OR IGNORE INTO liking_users (post_id, liker_id) VALUES (?, ?)", (pid, liker_id))
            like_count += 1
    db_commit()
    log.info(f"  共创建 {like_count} 条点赞")

    # ── 6. 评论 ──
    log.info("\n--- 创建评论 ---")
    comments_data = [
        (all_post_ids[0], user_ids["lingyue"], "太棒了！支持公式渲染正是我需要的功能 👍"),
        (all_post_ids[0], user_ids["hangyu"], "期待上线。$\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}$"),
        (all_post_ids[3], user_ids["yunfei"], "珞珈山的晚霞确实很美，我也拍过！"),
        (all_post_ids[3], user_ids["shuiyan"], "落霞与孤鹜齐飞，秋水共长天一色。"),
        (all_post_ids[4], user_ids["beichen"], "QML 的动画确实不错，配合 C++ 后端更流畅。"),
        (all_post_ids[4], user_ids["moli"], "有没有示例代码分享？"),
        (all_post_ids[6], user_ids["beichen"], "10GB 做到 2 分钟，优化效果显著！"),
        (all_post_ids[6], user_ids["fengzhi"], "学习了，数据科学真有意思。"),
        (all_post_ids[8], user_ids["beichen"], "画得好漂亮！什么软件画的？"),
        (all_post_ids[8], user_ids["shuiyan"], "色彩搭配太棒了，有教学视频吗？"),
        (all_post_ids[8], user_ids["lingyue"], "可以约稿吗？😊"),
        (all_post_ids[12], user_ids["beichen"], "李清照的词，总有一种说不出的忧伤。"),
        (all_post_ids[14], user_ids["moli"], "什么时候发布？想听！"),
        (all_post_ids[16], user_ids["yunfei"], "看起来好好吃，求地址！"),
        (all_post_ids[18], user_ids["hangyu"], "这个工具好，先 star 了！"),
    ]

    for pid, commenter_id, content in comments_data:
        created = bj_ago(days=random.randint(0, 7), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        db_execute(
            "INSERT INTO comments (post_id, commenter_id, content, commented_at) VALUES (?, ?, ?, ?)",
            (pid, commenter_id, content, created)
        )
    db_commit()
    log.info(f"  共创建 {len(comments_data)} 条评论")

    # ── 7. 私信聊天（主用户与几位用户的聊天，含 Markdown 和 LaTeX） ──
    log.info("\n--- 创建私信聊天 ---")

    chat_users = [
        ("lingyue", "凌月"),
        ("moli", "墨离"),
        ("hangyu", "航宇"),
        ("shuiyan", "水烟"),
    ]

    chat_messages = {
        "lingyue": [
            ("beichen", f"凌月，前端那个 Markdown 渲染组件你试了吗？"),
            ("lingyue", "试了！`remarkable` 库渲染效果不错，不过表格支持有点问题。"),
            ("beichen", "表格问题我也遇到了，可以看看这个方案：\n\n```markdown\n| 特性 | 状态 |\n|------|------|\n| 粗体 | ✅ |\n| 斜体 | ✅ |\n| 表格 | ⚠️ WIP |\n| 公式 | 🚧 |\n```"),
            ("lingyue", "公式渲染用 KaTeX 怎么样？感觉比 MathJax 轻量。"),
            ("beichen", "好主意，KaTeX 确实快很多。公式示例：$\\int_{0}^{\\infty} e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$"),
            ("lingyue", "漂亮！这个渲染速度可以接受。"),
            ("lingyue", "对了，消息列表的 UI 我按极简主义风格重写了，你看看合并请求。"),
            ("beichen", "好的，我 review 一下。"),
        ],
        "moli": [
            ("beichen", "墨离，你那幅新插画的色彩太惊艳了！"),
            ("moli", "谢谢！用了新的配色方案，暖色调为主。"),
            ("beichen", "有没有考虑过做一套 TinyBlog 的主题插画？"),
            ("moli", "可以啊！我正好有灵感。给你看个草图。"),
            ("moli", "**主题方向**：\n> 以星空和极光为灵感\n> 配合玻璃态 UI 设计"),
            ("beichen", "这个方向很棒！$\\mathcal{L}(\\theta) = \\prod_{i=1}^{n} P(y_i | x_i; \\theta)$ 我们的视觉风格会跟这个公式一样优美。"),
            ("moli", "哈哈，你这公式打得我猝不及防 😂"),
        ],
        "hangyu": [
            ("beichen", "航宇，你那个 10GB 数据处理方案能写篇博客分享吗？"),
            ("hangyu", "可以啊，我整理一下代码。主要思路是分块 + 向量化。"),
            ("beichen", "好的，我帮你 review。公式展示方面，后端支持 KaTeX。"),
            ("hangyu", "那太好了。我正好有个公式想展示：$\\hat{\\theta} = \\arg\\min_{\\theta} \\sum_{i=1}^{n} (y_i - f_\\theta(x_i))^2$"),
            ("beichen", "最小二乘法！经典。发布的时候可以配上数据可视化图表。"),
            ("hangyu", "嗯，我用 Matplotlib 画了几张图，到时候一起放上去。"),
        ],
        "shuiyan": [
            ("beichen", "水烟，看你最近在读《百年孤独》，感觉怎么样？"),
            ("shuiyan", "很震撼。马尔克斯的叙事像一条河，把时间揉碎了又重新编织。"),
            ("shuiyan", "最喜欢那句：「*多年以后，面对行刑队，奥雷里亚诺·布恩迪亚上校将会回想起父亲带他去见识冰块的那个遥远的下午。*」"),
            ("beichen", "经典的开头。我在想能不能把这种叙事风格转化成 UI 的转场动画……"),
            ("shuiyan", "哈？你这个想法有点抽象 😂 先写代码吧，别太魔怔。"),
            ("beichen", "也对。对了，你的诗词帖下面评论区里好多人引用你的句子。"),
            ("shuiyan", "嗯，有人喜欢总是一件好事。$\\text{知音少，弦断有谁听？}$"),
        ],
    }

    msg_id_counter = 1
    for target_uname, messages in chat_messages.items():
        target_uid = user_ids[target_uname]
        # 生成消息，每条间隔几分钟
        for i, (sender_uname, msg_content) in enumerate(messages):
            sender_uid = user_ids[sender_uname]
            receiver_uid = target_uid if sender_uname == "beichen" else main_uid
            sent_at = bj_ago(days=random.randint(0, 3), hours=random.randint(0, 12),
                             minutes=(len(messages) - i) * 5)

            db_execute(
                "INSERT INTO offline_messages (sender_id, receiver_id, content, sent_at, is_read) VALUES (?, ?, ?, ?, ?)",
                (sender_uid, receiver_uid, msg_content, sent_at, 0)
            )
            log.info(f"  私信 [{sender_uname}→{target_uname}]: {msg_content[:40]}...")
            msg_id_counter += 1

    db_commit()

    # ── 8. 会话记录（conversations 表） ──
    log.info("\n--- 创建会话记录 ---")
    # 为主用户和聊天对象建立会话
    for target_uname, messages in chat_messages.items():
        target_uid = user_ids[target_uname]
        last_msg = messages[-1][1]
        last_time = bj_ago(hours=random.randint(0, 6), minutes=random.randint(0, 59))

        # 主用户视角
        db_execute("""
            INSERT OR IGNORE INTO conversations (user_id, type, target_id, last_message, last_message_time, unread_count, is_hidden)
            VALUES (?, 'private', ?, ?, ?, 0, 0)
        """, (main_uid, target_uid, last_msg[:80], last_time))
        # 对方视角
        db_execute("""
            INSERT OR IGNORE INTO conversations (user_id, type, target_id, last_message, last_message_time, unread_count, is_hidden)
            VALUES (?, 'private', ?, ?, ?, 0, 0)
        """, (target_uid, main_uid, last_msg[:80], last_time))

    db_commit()
    log.info(f"  会话记录创建完成")

    # ── 9. 群组 ──
    log.info("\n--- 创建群组 ---")
    groups_data = [
        ("TinyBlog 开发组", main_uid, [user_ids["lingyue"], user_ids["hangyu"]]),
        ("文艺茶话会", user_ids["shuiyan"], [main_uid, user_ids["moli"], user_ids["yunfei"]]),
        ("美食小分队", user_ids["qiucao"], [main_uid, user_ids["yunfei"]]),
    ]

    for gname, owner_uid, members in groups_data:
        db_execute("INSERT INTO groups (name, owner_id, created_at) VALUES (?, ?, ?)",
                   (gname, owner_uid, bj_ago(days=random.randint(5, 30))))
        gid = db_lastrowid()
        # 添加群主
        db_execute("INSERT INTO user_in_group (group_id, user_id, role) VALUES (?, ?, 'owner')", (gid, owner_uid))
        # 添加其他成员
        for muid in members:
            db_execute("INSERT OR IGNORE INTO user_in_group (group_id, user_id, role) VALUES (?, ?, 'member')", (gid, muid))
        log.info(f"  群组 [{gid}] {gname}")

    db_commit()

    # ── 10. 群消息 ──
    log.info("\n--- 创建群消息 ---")
    group_msgs = [
        (1, main_uid, "大家看邮件，我更新了 API 文档。"),
        (1, user_ids["lingyue"], "收到，我 review 一下。"),
        (1, user_ids["hangyu"], "后端测试通过了，没有 regression。$\\checkmark$"),
        (1, main_uid, "好的，明天开会讨论消息功能的最终方案。"),
        (1, user_ids["lingyue"], "没问题。"),
        (2, user_ids["shuiyan"], "今天读到一首很好的诗，分享给大家。"),
        (2, user_ids["shuiyan"], "**《从前慢》** — 木心\n\n> 从前的日色变得慢\n> 车，马，邮件都慢\n> 一生只够爱一个人"),
        (2, main_uid, "好诗。"),
        (2, user_ids["moli"], "美。我画一幅配图吧。"),
        (2, user_ids["yunfei"], "我也来抛张照片，配这首诗的意境。"),
        (3, user_ids["qiucao"], "今天发现一家很棒的川菜馆，推荐！"),
        (3, main_uid, "求地址！"),
        (3, user_ids["yunfei"], "我也想去。"),
        (3, user_ids["qiucao"], "在珞狮路，叫「川味轩」，水煮鱼超级好吃。"),
    ]

    # 获取 group IDs
    group_rows = db_fetchall("SELECT id FROM groups ORDER BY id")
    gids = [r["id"] for r in group_rows]
    # 前面创建的群组 ID 就是按顺序的
    gid_map = {1: gids[0], 2: gids[1], 3: gids[2]}

    for gidx, sender, content in group_msgs:
        gid = gid_map[gidx]
        sent_at = bj_ago(days=random.randint(0, 5), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        db_execute(
            "INSERT INTO group_messages (group_id, sender_id, content, sent_at) VALUES (?, ?, ?, ?)",
            (gid, sender, content, sent_at)
        )
    db_commit()
    log.info(f"  群消息创建完成")

    # ── 11. 通知 ──
    log.info("\n--- 创建通知 ---")
    notifications = [
        (main_uid, user_ids["lingyue"], "follow", None),
        (main_uid, user_ids["moli"], "follow", None),
        (main_uid, user_ids["hangyu"], "follow", None),
        (main_uid, user_ids["shuiyan"], "follow", None),
        (main_uid, user_ids["moli"], "favourite", all_post_ids[0]),
        (main_uid, user_ids["lingyue"], "favourite", all_post_ids[0]),
        (main_uid, user_ids["hangyu"], "favourite", all_post_ids[3]),
    ]
    for uid, from_uid, ntype, tid in notifications:
        db_execute(
            "INSERT INTO notifications (user_id, from_user_id, notification_type, post_id, created_at) VALUES (?, ?, ?, ?, datetime('now')) ",
            (uid, from_uid, ntype, tid)
        )
    db_commit()
    log.info(f"  通知创建完成")

    # ── 12. 书签 ──
    log.info("\n--- 创建书签 ---")
    bookmarks = [
        (main_uid, all_post_ids[6]),   # 航宇的数据处理帖
        (main_uid, all_post_ids[12]),  # 水烟的诗词帖
        (main_uid, all_post_ids[14]),  # 风之的 remix 帖
        (user_ids["lingyue"], all_post_ids[0]),  # 主用户的 Markdown 帖
        (user_ids["moli"], all_post_ids[16]),    # 秋草的美食帖
    ]
    for uid, pid in bookmarks:
        db_execute("INSERT OR IGNORE INTO bookmarks (user_id, post_id) VALUES (?, ?)", (uid, pid))
    db_commit()
    log.info(f"  书签创建完成")

    # ── 13. 创建 Cookie 以供直接使用（方便测试） ──
    log.info("\n--- 登录 Token 清单 ---")
    log.info("所有用户密码均为: 123456")
    log.info("可以直接使用的 token（等同于 cookie 值）：")
    for uname, uid in user_ids.items():
        log.info(f"  {uname}: seed_token_{uname}_{uid}")

    log.info("\n" + "=" * 60)
    log.info("种子数据写入完成！")
    log.info("=" * 60)


if __name__ == "__main__":
    # 删除旧数据库
    if os.path.exists(DB_PATH):
        log.info(f"删除旧数据库: {DB_PATH}")
        conn.close()
        os.remove(DB_PATH)

    # 重新连接
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    create_tables()
    seed()
    conn.close()
    log.info("完成！")
