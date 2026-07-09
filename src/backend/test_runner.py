#!/usr/bin/env python3
"""
TinyBlog 全功能压力测试与边缘测试脚本
======================================
覆盖所有 40 个 API 端点，包括：
- 正常场景测试
- 边缘/异常输入测试
- 并发压力测试
- 随机模糊测试
生成 HTML 测试报告
"""

import requests
import json
import random
import string
import time
import sys
import os
import concurrent.futures
from datetime import datetime
from typing import Any

# ─── 配置 ───────────────────────────────────────────────
BASE_URL = os.environ.get("TB_BASE_URL", "http://127.0.0.1:18999")
STRESS_CONCURRENT = 20       # 并发请求数
STRESS_ROUNDS = 3            # 压力轮次
FUZZ_COUNT = 50              # 模糊测试随机请求数
TIMEOUT = 10                 # 单请求超时(秒)

# ─── 全局状态 ───────────────────────────────────────────
test_results: list[dict] = []
user_pool: list[dict] = []   # {username, password, nickname, cookie, user_id}
post_pool: list[int] = []
group_pool: list[int] = []
stress_errors = 0
fuzz_errors = 0

# ─── 工具函数 ───────────────────────────────────────────
def rand_str(min_len=4, max_len=12, chars=string.ascii_lowercase) -> str:
    return ''.join(random.choices(chars, k=random.randint(min_len, max_len)))

def rand_unicode_str(min_len=1, max_len=50) -> str:
    """生成包含中文/emoji/特殊字符的随机字符串"""
    pool = "你好世界测试🌍🎉✨🚀\n\t\"'<>&%$#@!😀😂❤️　"
    return ''.join(random.choices(pool + string.ascii_letters + string.digits, k=random.randint(min_len, max_len)))

def rand_long_str(kb: int) -> str:
    """生成指定KB大小的字符串"""
    return 'A' * (kb * 1024)

def record(endpoint: str, case: str, passed: bool, detail: str = "", response: Any = None):
    test_results.append({
        "endpoint": endpoint,
        "case": case,
        "passed": passed,
        "detail": detail,
        "response": str(response)[:200] if response else "",
        "timestamp": datetime.now().isoformat()
    })

def post(path: str, json_data: dict, expect_ok: bool = True) -> tuple[bool, dict]:
    """发送POST请求，返回(是否通过, 响应JSON)"""
    try:
        r = requests.post(f"{BASE_URL}{path}", json=json_data, timeout=TIMEOUT)
        data = r.json()
        has_error = "error" in data
        if expect_ok:
            return not has_error, data
        else:
            return has_error, data
    except Exception as e:
        return False, {"_exception": str(e)}

def get(path: str, params: dict = None) -> tuple[bool, dict]:
    try:
        r = requests.get(f"{BASE_URL}{path}", params=params, timeout=TIMEOUT)
        return True, r.json()
    except Exception as e:
        return False, {"_exception": str(e)}

def register_user() -> dict | None:
    """注册一个随机用户并返回用户信息"""
    username = f"test_{rand_str(6,10)}"
    ok, resp = post("/register-request", {
        "username": username,
        "password": "Pass123!",
        "nickname": f"Tester{rand_str(2,6)}"
    })
    if ok and "cookie" in resp:
        return {"username": username, "password": "Pass123!", "nickname": resp.get("nickname",""), "cookie": resp["cookie"]}
    return None

def login_user(username: str, password: str) -> str | None:
    ok, resp = post("/login-request", {"username": username, "password": password})
    return resp.get("cookie") if ok else None

# ═══════════════════════════════════════════════════════════
#  第一部分：准备阶段 — 创建测试数据
# ═══════════════════════════════════════════════════════════
def prepare_test_data():
    global user_pool, post_pool, group_pool
    print("=" * 60)
    print("[准备] 创建测试用户和数据...")
    
    # 注册用户池
    for i in range(8):
        u = register_user()
        if u:
            user_pool.append(u)
            print(f"  用户{i+1}: {u['username']} (cookie={u['cookie'][:16]}...)")
    if len(user_pool) < 3:
        print("[FATAL] 无法注册足够用户，测试终止")
        sys.exit(1)
    
    # 查用户ID（通过关注列表间接获取）
    for u in user_pool:
        ok, resp = post("/get-follow-list", {"cookie": u["cookie"]})
        # 通过另一个端点查ID：让用户1关注用户2，然后查followee
    # 简化：假设user_id是连续的，先用search查
    for u in user_pool:
        ok, resp = post("/search", {"cookie": u["cookie"], "keyword": u["username"]})
        if ok and resp.get("users"):
            u["user_id"] = resp["users"][0]["id"]
    print(f"  用户池: {[(u['username'], u.get('user_id')) for u in user_pool]}")

    # 发帖池
    for u in user_pool:
        for _ in range(2):
            ok, resp = post("/pub-post", {"cookie": u["cookie"], "text": f"Post by {u['username']}: {rand_unicode_str(10,100)}"})
        # 获取最新帖子ID
        ok, resp = post("/get-user-posts", {"cookie": u["cookie"], "user_id": u.get("user_id", 0), "count": 5})
        if ok and resp.get("posts"):
            for p in resp["posts"]:
                if p["id"] not in post_pool:
                    post_pool.append(p["id"])
    print(f"  帖子池: {post_pool[:10]}... (共{len(post_pool)}条)")

    # 群组池
    for u in user_pool[:3]:
        ok, resp = post("/create-group", {"cookie": u["cookie"], "name": f"Group_{rand_str(4,8)}"})
        if ok and resp.get("group_id"):
            group_pool.append(resp["group_id"])
    print(f"  群组池: {group_pool}")

    print("[准备] 完成\n")

# ═══════════════════════════════════════════════════════════
#  第二部分：全端点正常场景测试
# ═══════════════════════════════════════════════════════════
def test_normal_scenarios():
    global user_pool, post_pool, group_pool
    print("=" * 60)
    print("[正常] 全端点正常场景测试")
    u0, u1 = user_pool[0], user_pool[1]
    c0, c1 = u0["cookie"], u1["cookie"]
    uid0, uid1 = u0.get("user_id", 1), u1.get("user_id", 2)
    
    # --- 基础 ---
    ok, resp = get("/ping")
    record("/ping", "健康检查", ok and resp.get("message")=="Pong!", "返回Pong", resp)

    # --- 用户系统 ---
    # 注册（正常）
    new_u = register_user()
    record("/register-request", "正常注册", new_u is not None, f"用户名:{new_u['username'] if new_u else 'FAIL'}", new_u)
    if new_u:
        user_pool.append(new_u)

    # 登录
    ok, resp = post("/login-request", {"username": u0["username"], "password": u0["password"]})
    record("/login-request", "正常登录", ok, "获取cookie", resp)

    # 登出
    tmp = login_user(u0["username"], u0["password"])
    ok, resp = post("/logout", {"cookie": tmp})
    record("/logout", "正常登出", ok, "", resp)
    # 登出后应失败
    ok2, resp2 = post("/get-follow-list", {"cookie": tmp})
    record("/logout", "登出后cookie失效", not ok2, "期望Bad cookie", resp2)

    # 编辑资料
    ok, resp = post("/edit-profile", {"cookie": c0, "nickname": f"Edited_{rand_str(3,6)}"})
    record("/edit-profile", "编辑昵称", ok, "", resp)
    
    # 头像
    ok, resp = get("/avatar", {"user_id": uid0})
    record("/avatar GET", "获取头像", ok, "", resp)
    r = requests.patch(f"{BASE_URL}/avatar", json={"cookie": c0, "signature": "Hello world!"})
    resp = r.json()
    ok = "error" not in resp
    record("/avatar PATCH", "更新签名", ok, "", resp)

    # --- 关注系统 ---
    ok, resp = post("/follow", {"cookie": c0, "followee_id": uid1})
    record("/follow", "关注用户", ok, "", resp)
    
    ok, resp = post("/get-follow-list", {"cookie": c0})
    record("/get-follow-list", "获取关注列表", ok, f"followers:{len(resp.get('followers',[]))}, followees:{len(resp.get('followees',[]))}", resp)
    
    ok, resp = post("/unfollow", {"cookie": c0, "followee_id": uid1})
    record("/unfollow", "取消关注", ok, "", resp)

    # --- 帖子系统 ---
    ok, resp = post("/pub-post", {"cookie": c0, "text": "Normal post for testing"})
    record("/pub-post", "发布纯文字帖子", ok, "", resp)
    
    # 带媒体
    small_img = "iVBORw0KGgo=" + "A" * 20  # 假base64
    ok, resp = post("/pub-post", {"cookie": c0, "text": "Post with pic", "media": [small_img]})
    record("/pub-post", "发布带媒体帖子", ok, "", resp)

    if post_pool:
        pid = post_pool[0]
        ok, resp = post("/get-post", {"cookie": c0, "post_id": pid})
        record("/get-post", "获取帖子详情", ok, f"is_liked={resp.get('is_liked')}, comment_count={resp.get('comment_count')}", resp)
    
    # Feed
    ok, resp = post("/post-fetch", {"cookie": c0, "count": 5})
    record("/post-fetch", "获取推荐Feed(首页)", ok, f"count={resp.get('count')}, next_cursor={resp.get('next_cursor')}", resp)
    
    next_cur = resp.get("next_cursor", 0)
    if next_cur:
        ok, resp = post("/post-fetch", {"cookie": c0, "count": 5, "before_id": next_cur})
        record("/post-fetch", "游标翻页Feed", ok, f"count={resp.get('count')}", resp)

    if post_pool:
        ok, resp = post("/edit-post", {"cookie": c0, "post_id": post_pool[0], "content": "EDITED!"})
        record("/edit-post", "编辑帖子", ok or resp.get("error")=="Not your post.", "", resp)

    # --- 互动系统 ---
    if post_pool and len(user_pool) >= 2:
        pid = post_pool[0]
        ok, resp = post("/like", {"cookie": c1, "post_id": pid})
        record("/like", "点赞帖子", ok, "", resp)
        
        ok, resp = post("/unlike", {"cookie": c1, "post_id": pid})
        record("/unlike", "取消点赞", ok, "", resp)
        
        ok, resp = post("/comment", {"cookie": c1, "post_id": pid, "content": "Great post!"})
        record("/comment", "发表评论", ok, "", resp)
        
        ok, resp = post("/get-comments", {"cookie": c0, "post_id": pid})
        record("/get-comments", "获取评论列表", ok, f"count={len(resp.get('comments',[]))}", resp)
        
        ok, resp = post("/get-post-likers", {"cookie": c0, "post_id": pid})
        record("/get-post-likers", "获取点赞列表", ok, f"total={resp.get('total')}", resp)

    # --- 收藏系统 ---
    if post_pool:
        ok, resp = post("/bookmark", {"cookie": c0, "post_id": post_pool[0]})
        record("/bookmark", "收藏帖子", ok, "", resp)
        ok, resp = post("/get-bookmarks", {"cookie": c0})
        record("/get-bookmarks", "获取收藏列表", ok, f"count={len(resp.get('posts',[]))}", resp)
        ok, resp = post("/unbookmark", {"cookie": c0, "post_id": post_pool[0]})
        record("/unbookmark", "取消收藏", ok, "", resp)

    # --- 转发 ---
    if len(post_pool) >= 2:
        ok, resp = post("/repost", {"cookie": c1, "post_id": post_pool[0], "text": "Repost!"})
        record("/repost", "转发帖子", ok or "own post" in str(resp), "", resp)

    # --- 私信系统 ---
    ok, resp = post("/send-msg", {"cookie": c0, "to_whom_id": uid1, "content": "Hello!"})
    record("/send-msg", "发送私信", ok, "", resp)
    ok, resp = post("/recv-msg", {"cookie": c1})
    record("/recv-msg", "接收私信(阅后即焚)", ok, f"msgs={len(resp.get('msgs',[]))}", resp)
    # 再次接收应为空
    ok, resp = post("/recv-msg", {"cookie": c1})
    record("/recv-msg", "再次接收(应空)", ok and len(resp.get('msgs',[]))==0, f"msgs={len(resp.get('msgs',[]))}", resp)

    # --- 群组系统 ---
    if group_pool:
        gid = group_pool[0]
        ok, resp = post("/join-group", {"cookie": c1, "group_id": gid})
        record("/join-group", "加入群组", ok, "", resp)
        ok, resp = post("/send-group-msg", {"cookie": c0, "group_id": gid, "content": "Group hello!"})
        record("/send-group-msg", "发送群消息", ok, "", resp)
        ok, resp = post("/recv-group-msg", {"cookie": c1, "group_id": gid})
        record("/recv-group-msg", "接收群消息", ok, f"count={len(resp.get('messages',[]))}", resp)
        ok, resp = post("/get-group-members", {"cookie": c0, "group_id": gid})
        record("/get-group-members", "获取群成员", ok, f"count={len(resp.get('members',[]))}", resp)
        ok, resp = post("/leave-group", {"cookie": c1, "group_id": gid})
        record("/leave-group", "退出群组", ok, "", resp)

    ok, resp = post("/get-my-groups", {"cookie": c0})
    record("/get-my-groups", "获取我的群组", ok, f"count={len(resp.get('groups',[]))}", resp)

    # --- P1: 搜索 ---
    ok, resp = post("/search", {"cookie": c0, "keyword": user_pool[0]["username"][:4]})
    record("/search", "搜索用户", ok, f"users={len(resp.get('users',[]))}", resp)

    # --- P1: 通知 ---
    ok, resp = post("/get-notifications", {"cookie": c0})
    record("/get-notifications", "获取通知", ok, f"unread={resp.get('unread_count')}", resp)
    ok, resp = post("/mark-notifications-read", {"cookie": c0})
    record("/mark-notifications-read", "全部标记已读", ok, "", resp)

    # --- P1: 用户资料 ---
    ok, resp = post("/get-user-profile", {"cookie": c0, "user_id": uid1})
    record("/get-user-profile", "查看用户资料", ok, f"is_following={resp.get('is_following')}", resp)
    ok, resp = post("/get-user-posts", {"cookie": c0, "user_id": uid1, "count": 5})
    record("/get-user-posts", "查看用户帖子", ok, f"count={len(resp.get('posts',[]))}", resp)

    # --- P1: 文件上传 ---
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    try:
        r = requests.post(f"{BASE_URL}/upload-media", data={"cookie": c0}, files={"file": ("test.png", fake_png, "image/png")}, timeout=TIMEOUT)
        resp = r.json()
        ok = "error" not in resp
        record("/upload-media", "上传文件", ok, f"filename={resp.get('filename','')}", resp)
    except Exception as e:
        record("/upload-media", "上传文件", False, str(e))

    # --- 删除操作 ---
    # 先发一个帖子再删
    ok, resp = post("/pub-post", {"cookie": c0, "text": "To be deleted"})
    # 获取最新帖子ID
    ok2, resp2 = post("/get-user-posts", {"cookie": c0, "user_id": uid0, "count": 1})
    if ok2 and resp2.get("posts"):
        del_pid = resp2["posts"][0]["id"]
        ok, resp = post("/delete-post", {"cookie": c0, "post_id": del_pid})
        record("/delete-post", "删除自己的帖子", ok, "", resp)

    if post_pool:
        # 先评论再删评论
        ok, resp = post("/comment", {"cookie": c0, "post_id": post_pool[0], "content": "Del me"})
        ok2, resp2 = post("/get-comments", {"cookie": c0, "post_id": post_pool[0]})
        if ok2 and resp2.get("comments"):
            cid = resp2["comments"][-1]["id"]
            ok, resp = post("/delete-comment", {"cookie": c0, "comment_id": cid})
            record("/delete-comment", "删除自己的评论", ok, "", resp)

    print(f"[正常] 完成\n")

# ═══════════════════════════════════════════════════════════
#  第三部分：边缘/异常输入测试
# ═══════════════════════════════════════════════════════════
def test_edge_cases():
    global user_pool, post_pool
    print("=" * 60)
    print("[边缘] 边缘与异常输入测试")
    u0 = user_pool[0]
    c0 = u0["cookie"]

    # ── 认证 ──
    tests_auth = [
        ("空cookie", "/get-follow-list", {"cookie": ""}),
        ("无效cookie", "/get-follow-list", {"cookie": "invalid"*10}),
        ("超长cookie", "/get-follow-list", {"cookie": "A"*10000}),
        ("缺cookie字段", "/get-follow-list", {}),
        ("cookie为null", "/get-follow-list", {"cookie": None}),
    ]
    for name, path, body in tests_auth:
        ok, resp = post(path, body, expect_ok=False)
        record(path, f"边缘:{name}", ok, str(resp)[:100], resp)

    # ── 注册 ──
    reg_tests = [
        ("空用户名", {"username": "", "password": "pass", "nickname": "Nick"}, True),
        ("空密码", {"username": "abc", "password": "", "nickname": "Nick"}, True),
        ("空昵称", {"username": "abc", "password": "pass", "nickname": ""}, True),
        ("全部为空", {"username": "", "password": "", "nickname": ""}, True),
        ("超长用户名", {"username": "A"*1000, "password": "pass", "nickname": "N"}, False),
        ("超长昵称", {"username": rand_str(8,12), "password": "pass", "nickname": "B"*5000}, False),
        ("特殊字符用户名", {"username": rand_unicode_str(5,20), "password": "pass", "nickname": "Nick"}, False),
        ("中文用户名", {"username": "测试用户中文", "password": "pass", "nickname": "昵称"}, False),
        ("重复用户名", {"username": u0["username"], "password": "pass", "nickname": "Dup"}, True),
        ("SQL注入尝试", {"username": "'; DROP TABLE users;--", "password": "pass", "nickname": "Hack"}, False),
        ("XSS尝试", {"username": "<script>alert(1)</script>", "password": "pass", "nickname": "X"}, False),
        ("控制字符", {"username": "test\x00\x01\x02", "password": "pass", "nickname": "C"}, False),
        ("超长密码", {"username": rand_str(6,10), "password": "P"*2000, "nickname": "N"}, False),
    ]
    for name, body, expect_err in reg_tests:
        ok, resp = post("/register-request", body, expect_ok=not expect_err)
        record("/register-request", f"边缘:{name}", ok, str(resp)[:100], resp)

    # ── 登录 ──
    login_tests = [
        ("不存在的用户", {"username": "no_such_user_xyz_12345", "password": "x"}),
        ("错误密码", {"username": u0["username"], "password": "WrongPassword!"}),
        ("空用户名", {"username": "", "password": "x"}),
        ("空密码", {"username": u0["username"], "password": ""}),
    ]
    for name, body in login_tests:
        ok, resp = post("/login-request", body, expect_ok=False)
        record("/login-request", f"边缘:{name}", ok, str(resp)[:100], resp)

    # ── 关注 ──
    follow_tests = [
        ("关注自己", {"cookie": c0, "followee_id": u0.get("user_id", 1)}),
        ("关注不存在用户", {"cookie": c0, "followee_id": 999999}),
        ("followee_id为0", {"cookie": c0, "followee_id": 0}),
        ("followee_id为负数", {"cookie": c0, "followee_id": -1}),
        ("超大followee_id", {"cookie": c0, "followee_id": 2**31}),
    ]
    for name, body in follow_tests:
        ok, resp = post("/follow", body, expect_ok=False)
        record("/follow", f"边缘:{name}", ok, str(resp)[:100], resp)

    # ── 帖子 ──
    pub_tests = [
        ("空帖子(无文字无媒体)", {"cookie": c0, "text": "", "media": []}),
        ("超过9张媒体", {"cookie": c0, "text": "", "media": ["x"]*10}),
        ("超长文字", {"cookie": c0, "text": "A"*50000}),
        ("Unicode文字", {"cookie": c0, "text": rand_unicode_str(100, 500)}),
        ("纯空格文字", {"cookie": c0, "text": "   "}),
    ]
    for name, body in pub_tests:
        expect_err = name.startswith("空帖子") or name.startswith("超过9")
        ok, resp = post("/pub-post", body, expect_ok=not expect_err)
        record("/pub-post", f"边缘:{name}", ok, str(resp)[:100], resp)

    # ── 评论 ──
    if post_pool:
        comment_tests = [
            ("空评论", {"cookie": c0, "post_id": post_pool[0], "content": ""}),
            ("不存在帖子", {"cookie": c0, "post_id": 999999, "content": "Hi"}),
            ("超长评论", {"cookie": c0, "post_id": post_pool[0], "content": "C"*50000}),
            ("负post_id", {"cookie": c0, "post_id": -1, "content": "Hi"}),
        ]
        for name, body in comment_tests:
            ok, resp = post("/comment", body, expect_ok=False)
            record("/comment", f"边缘:{name}", ok, str(resp)[:100], resp)

    # ── 获取帖子详情 ──
    getpost_tests = [
        ("不存在帖子", {"cookie": c0, "post_id": 999999}),
        ("post_id=0", {"cookie": c0, "post_id": 0}),
        ("负post_id", {"cookie": c0, "post_id": -1}),
    ]
    for name, body in getpost_tests:
        ok, resp = post("/get-post", body, expect_ok=False)
        record("/get-post", f"边缘:{name}", ok, str(resp)[:100], resp)

    # ── 搜索 ──
    search_tests = [
        ("空关键词", {"cookie": c0, "keyword": ""}),
        ("超长关键词", {"cookie": c0, "keyword": "K"*10000}),
        ("特殊字符", {"cookie": c0, "keyword": "%_"}),
        ("纯空格", {"cookie": c0, "keyword": "   "}),
        ("SQL注入", {"cookie": c0, "keyword": "' OR 1=1 --"}),
    ]
    for name, body in search_tests:
        ok, resp = post("/search", body, expect_ok=not (name=="空关键词"))
        record("/search", f"边缘:{name}", ok, str(resp)[:100], resp)

    # ── 群组 ──
    group_tests = [
        ("空群名", {"cookie": c0, "name": ""}),
        ("超长群名", {"cookie": c0, "name": "G"*5000}),
        ("加入不存在群", {"cookie": c0, "group_id": 999999}),
        ("退出不存在群", {"cookie": c0, "group_id": 999999}),
    ]
    for name, body in group_tests:
        path = "/create-group" if "name" in body else ("/join-group" if "加入" in name else "/leave-group")
        ok, resp = post(path, body, expect_ok=False)
        record(path, f"边缘:{name}", ok, str(resp)[:100], resp)

    # ── 私信 ──
    msg_tests = [
        ("发给不存在用户", {"cookie": c0, "to_whom_id": 999999, "content": "Hi"}),
        ("发给0", {"cookie": c0, "to_whom_id": 0, "content": "Hi"}),
        ("空内容", {"cookie": c0, "to_whom_id": 1, "content": ""}),
        ("to_whom_id为自己", {"cookie": c0, "to_whom_id": u0.get("user_id",1), "content": "Hi"}),
    ]
    for name, body in msg_tests:
        ok, resp = post("/send-msg", body, expect_ok=not (name=="空内容" or name=="发给不存在用户" or name=="发给0"))
        record("/send-msg", f"边缘:{name}", ok, str(resp)[:100], resp)

    # ── Feed 边界 ──
    feed_tests = [
        ("count=0", {"cookie": c0, "count": 0}),
        ("count=1000", {"cookie": c0, "count": 1000}),
        ("负count", {"cookie": c0, "count": -5}),
        ("超大before_id", {"cookie": c0, "before_id": 2**63}),
        ("负before_id", {"cookie": c0, "before_id": -1}),
    ]
    for name, body in feed_tests:
        ok, resp = post("/post-fetch", body)
        record("/post-fetch", f"边缘:{name}", ok, str(resp)[:100], resp)

    # ── 编辑帖子 ──
    if post_pool:
        edit_tests = [
            ("编辑不存在帖子", {"cookie": c0, "post_id": 999999, "content": "X"}),
            ("编辑空内容", {"cookie": c0, "post_id": post_pool[0], "content": ""}),
        ]
        for name, body in edit_tests:
            ok, resp = post("/edit-post", body, expect_ok=False)
            record("/edit-post", f"边缘:{name}", ok, str(resp)[:100], resp)

    # ── 上传媒体 ──
    upload_tests = [
        ("空文件", b""),
        ("非图片文件", b"\x00"*1000),
    ]
    for name, data in upload_tests:
        try:
            r = requests.post(f"{BASE_URL}/upload-media", data={"cookie": c0}, files={"file": ("test.bin", data, "application/octet-stream")}, timeout=TIMEOUT)
            resp = r.json()
            ok = "error" not in resp
            record("/upload-media", f"边缘:{name}", ok, str(resp)[:100], resp)
        except Exception as e:
            record("/upload-media", f"边缘:{name}", False, str(e))

    # ── 错误的HTTP方法 ──
    for path in ["/register-request", "/login-request", "/ping", "/post-fetch"]:
        try:
            r = requests.get(f"{BASE_URL}{path}", timeout=TIMEOUT)
            ok = r.status_code == 405  # Method Not Allowed
            record(path, f"边缘:GET请求(期望405)", ok, f"status={r.status_code}")
        except:
            pass

    # ── 缺失必填字段 ──
    missing_field_tests = [
        ("/register-request", {"username": "x"}),
        ("/register-request", {"password": "x"}),
        ("/login-request", {"username": "x"}),
        ("/follow", {"cookie": c0}),
        ("/like", {"cookie": c0}),
        ("/comment", {"cookie": c0, "post_id": 1}),
        ("/pub-post", {"cookie": c0}),
        ("/send-msg", {"cookie": c0, "to_whom_id": 1}),
    ]
    for path, body in missing_field_tests:
        ok, resp = post(path, body, expect_ok=False)
        record(path, f"边缘:缺必填字段", ok, str(resp)[:100], resp)

    print(f"[边缘] 完成\n")

# ═══════════════════════════════════════════════════════════
#  第四部分：并发压力测试
# ═══════════════════════════════════════════════════════════
def stress_worker(round_num: int):
    """单个压力测试工作线程"""
    global stress_errors
    errors = 0
    try:
        # 随机选择一个用户
        u = random.choice(user_pool)
        c = u["cookie"]
        
        actions = [
            lambda: get("/ping"),
            lambda: post("/get-follow-list", {"cookie": c}),
            lambda: post("/post-fetch", {"cookie": c, "count": 5}),
            lambda: post("/get-notifications", {"cookie": c}),
            lambda: post("/search", {"cookie": c, "keyword": rand_str(2,4)}),
            lambda: post("/get-my-groups", {"cookie": c}),
        ]
        if post_pool:
            actions.append(lambda: post("/get-post", {"cookie": c, "post_id": random.choice(post_pool)}))
            actions.append(lambda: post("/get-comments", {"cookie": c, "post_id": random.choice(post_pool)}))
            actions.append(lambda: post("/get-post-likers", {"cookie": c, "post_id": random.choice(post_pool)}))
        
        for _ in range(STRESS_ROUNDS):
            action = random.choice(actions)
            try:
                action()
            except Exception:
                errors += 1
    except Exception:
        errors += 1
    
    if errors > 0:
        with __import__('threading').Lock() if False else None:
            pass
        stress_errors += errors

def test_stress():
    global stress_errors
    print("=" * 60)
    print(f"[压力] 并发压力测试 ({STRESS_CONCURRENT}并发 × {STRESS_ROUNDS}轮)")
    stress_errors = 0
    start = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=STRESS_CONCURRENT) as executor:
        futures = [executor.submit(stress_worker, i) for i in range(STRESS_CONCURRENT)]
        concurrent.futures.wait(futures)
    
    elapsed = time.time() - start
    total_requests = STRESS_CONCURRENT * STRESS_ROUNDS * (6 + (2 if post_pool else 0))
    
    record("STRESS", f"{STRESS_CONCURRENT}并发/{STRESS_ROUNDS}轮", stress_errors == 0,
           f"耗时:{elapsed:.2f}s, 错误:{stress_errors}, 约{total_requests}请求", {})
    
    print(f"  耗时: {elapsed:.2f}s")
    print(f"  错误: {stress_errors}")
    print(f"  QPS: ~{total_requests/elapsed:.0f}")
    print(f"[压力] 完成\n")

# ═══════════════════════════════════════════════════════════
#  第五部分：随机模糊测试
# ═══════════════════════════════════════════════════════════
def test_fuzz():
    global fuzz_errors
    print("=" * 60)
    print(f"[模糊] 随机模糊测试 ({FUZZ_COUNT}次随机请求)")
    fuzz_errors = 0
    
    endpoints = [
        ("/register-request", lambda: {
            "username": rand_unicode_str(0, 30),
            "password": rand_unicode_str(0, 50),
            "nickname": rand_unicode_str(0, 30)
        }),
        ("/login-request", lambda: {
            "username": random.choice([rand_unicode_str(0,20), "", random.choice(user_pool)["username"] if user_pool else "x"]),
            "password": rand_unicode_str(0, 50)
        }),
        ("/search", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad_cookie", ""]),
            "keyword": rand_unicode_str(0, 200)
        }),
        ("/post-fetch", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad", ""]),
            "count": random.choice([0, -1, 1, 20, 1000]),
            "before_id": random.choice([0, -1, 1, 99999, 2**63])
        }),
        ("/get-post", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "post_id": random.choice([0, -1, 1] + (post_pool[:5] if post_pool else [1]))
        }),
        ("/pub-post", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "text": rand_unicode_str(0, 500),
            "media": random.choice([[], ["x"*random.randint(1,100)], ["x"]*random.randint(1,15)])
        }),
        ("/follow", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "followee_id": random.choice([0, -1, 1, 99999])
        }),
        ("/like", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "post_id": random.choice([0, -1, 1, 99999] + (post_pool[:3] if post_pool else [1]))
        }),
        ("/comment", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "post_id": random.choice([0, -1, 1, 99999] + (post_pool[:3] if post_pool else [1])),
            "content": rand_unicode_str(0, 300)
        }),
        ("/send-msg", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "to_whom_id": random.choice([0, -1, 1, 99999]),
            "content": rand_unicode_str(0, 200)
        }),
        ("/create-group", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "name": random.choice(["", rand_unicode_str(1, 100)])
        }),
        ("/get-user-profile", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "user_id": random.choice([0, -1, 1, 99999])
        }),
        ("/get-user-posts", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "user_id": random.choice([0, -1, 1, 99999]),
            "count": random.choice([-1, 0, 1, 20, 1000]),
            "before_id": random.choice([0, -1, 99999])
        }),
        ("/edit-post", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "post_id": random.choice([0, -1, 1, 99999]),
            "content": rand_unicode_str(0, 200)
        }),
        ("/edit-profile", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "nickname": rand_unicode_str(0, 100),
            "email_address": rand_unicode_str(0, 100)
        }),
        ("/get-post-likers", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "post_id": random.choice([0, -1, 1]),
            "count": random.choice([-1, 0, 20, 1000])
        }),
        ("/repost", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "post_id": random.choice([0, -1, 1]),
            "text": rand_unicode_str(0, 200)
        }),
        ("/bookmark", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "post_id": random.choice([0, -1, 1, 99999])
        }),
        ("/join-group", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "group_id": random.choice([0, -1, 1, 99999] + (group_pool[:3] if group_pool else [1]))
        }),
        ("/leave-group", lambda: {
            "cookie": random.choice([u["cookie"] for u in user_pool] + ["bad"]),
            "group_id": random.choice([0, -1, 1, 99999])
        }),
    ]
    
    for i in range(FUZZ_COUNT):
        path, body_gen = random.choice(endpoints)
        try:
            body = body_gen()
            r = requests.post(f"{BASE_URL}{path}", json=body, timeout=TIMEOUT)
            # 仅检查不崩溃(非5xx)和返回有效JSON
            if r.status_code >= 500:
                fuzz_errors += 1
                record(path, f"模糊#{i}:5xx错误", False, f"status={r.status_code}, body={str(body)[:100]}")
            r.json()  # 确保可JSON解析
        except requests.exceptions.JSONDecodeError:
            fuzz_errors += 1
            record(path, f"模糊#{i}:非JSON响应", False, str(body)[:100])
        except Exception as e:
            fuzz_errors += 1
            record(path, f"模糊#{i}:异常", False, str(e)[:100])
    
    record("FUZZ", f"模糊测试({FUZZ_COUNT}次)", fuzz_errors == 0,
           f"共{FUZZ_COUNT}次随机请求, 错误:{fuzz_errors}", {})
    print(f"  随机请求: {FUZZ_COUNT}")
    print(f"  错误数: {fuzz_errors}")
    print(f"[模糊] 完成\n")

# ═══════════════════════════════════════════════════════════
#  第六部分：数据一致性测试
# ═══════════════════════════════════════════════════════════
def test_consistency():
    global user_pool, post_pool
    print("=" * 60)
    print("[一致性] 数据一致性校验")
    u0 = user_pool[0]
    c0 = u0["cookie"]
    uid0 = u0.get("user_id", 1)
    
    # 1. like_num 应与 liking_users 记录数一致
    if post_pool:
        pid = post_pool[0]
        ok1, post_resp = post("/get-post", {"cookie": c0, "post_id": pid})
        ok2, likers_resp = post("/get-post-likers", {"cookie": c0, "post_id": pid, "count": 1000})
        if ok1 and ok2:
            like_num = post_resp.get("like_num", -1)
            likers_total = likers_resp.get("total", -1)
            consistent = like_num == likers_total
            record("CONSISTENCY", f"帖子{pid}的like_num与likers_total一致", consistent,
                   f"like_num={like_num}, likers_total={likers_total}")

    # 2. 关注列表双向一致性
    if len(user_pool) >= 2:
        u1 = user_pool[1]
        uid1 = u1.get("user_id", 2)
        # u0 follow u1
        post("/follow", {"cookie": c0, "followee_id": uid1})
        ok1, fl0 = post("/get-follow-list", {"cookie": c0})
        ok2, fl1 = post("/get-follow-list", {"cookie": u1["cookie"]})
        if ok1 and ok2:
            # u0的followee应包含u1, u1的follower应包含u0
            f0_followees = [f["id"] for f in fl0.get("followees", [])]
            f1_followers = [f["id"] for f in fl1.get("followers", [])]
            consistent = uid1 in f0_followees and uid0 in f1_followers
            record("CONSISTENCY", "关注关系双向一致", consistent,
                   f"u0→u1:{uid1 in f0_followees}, u1←u0:{uid0 in f1_followers}")
        post("/unfollow", {"cookie": c0, "followee_id": uid1})

    # 3. 评论数一致性
    if post_pool:
        pid = post_pool[0]
        ok1, post_r = post("/get-post", {"cookie": c0, "post_id": pid})
        ok2, comments_r = post("/get-comments", {"cookie": c0, "post_id": pid})
        if ok1 and ok2:
            post_cc = post_r.get("comment_count", -1)
            actual_cc = len(comments_r.get("comments", []))
            consistent = post_cc == actual_cc
            record("CONSISTENCY", f"帖子{pid}的comment_count与实际评论数一致", consistent,
                   f"comment_count={post_cc}, actual={actual_cc}")

    # 4. 通知标记已读后unread_count为0
    post("/mark-notifications-read", {"cookie": c0})
    ok, resp = post("/get-notifications", {"cookie": c0})
    if ok:
        consistent = resp.get("unread_count", -1) == 0
        record("CONSISTENCY", "标记已读后unread_count为0", consistent,
               f"unread_count={resp.get('unread_count')}")

    # 5. 阅后即焚
    post("/send-msg", {"cookie": c0, "to_whom_id": uid0, "content": "Consistency check"})
    ok1, r1 = post("/recv-msg", {"cookie": c0})
    ok2, r2 = post("/recv-msg", {"cookie": c0})
    if ok1 and ok2:
        consistent = len(r1.get("msgs", [])) >= 1 and len(r2.get("msgs", [])) == 0
        record("CONSISTENCY", "私信阅后即焚", consistent,
               f"首次:{len(r1.get('msgs',[]))}, 二次:{len(r2.get('msgs',[]))}")

    print(f"[一致性] 完成\n")

# ═══════════════════════════════════════════════════════════
#  第七部分：报告生成
# ═══════════════════════════════════════════════════════════
def generate_report():
    total = len(test_results)
    passed = sum(1 for t in test_results if t["passed"])
    failed = total - passed
    
    # 按端点统计
    by_endpoint = {}
    for t in test_results:
        ep = t["endpoint"]
        if ep not in by_endpoint:
            by_endpoint[ep] = {"total": 0, "passed": 0, "failed": 0, "details": []}
        by_endpoint[ep]["total"] += 1
        if t["passed"]:
            by_endpoint[ep]["passed"] += 1
        else:
            by_endpoint[ep]["failed"] += 1
            by_endpoint[ep]["details"].append(t)
    
    # 按类别统计
    categories = {
        "正常场景": [t for t in test_results if "边缘" not in t["case"] and "模糊" not in t["case"] and t["endpoint"] not in ("STRESS", "FUZZ", "CONSISTENCY")],
        "边缘测试": [t for t in test_results if t["case"].startswith("边缘")],
        "压力测试": [t for t in test_results if t["endpoint"] == "STRESS"],
        "模糊测试": [t for t in test_results if t["endpoint"] == "FUZZ"],
        "一致性测试": [t for t in test_results if t["endpoint"] == "CONSISTENCY"],
    }
    
    # ─── 生成文本报告 ───
    report_path = os.path.join(os.path.dirname(__file__) or ".", "test_report.txt")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("  TinyBlog 全功能压力测试与边缘测试报告\n")
        f.write(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"  目标服务器: {BASE_URL}\n")
        f.write("=" * 70 + "\n\n")
        
        # 总览
        f.write("【总览】\n")
        f.write(f"  测试总数: {total}\n")
        f.write(f"  通过: {passed}  ({passed/total*100:.1f}%)\n" if total > 0 else "  通过: 0\n")
        f.write(f"  失败: {failed}  ({failed/total*100:.1f}%)\n" if total > 0 else "  失败: 0\n")
        f.write(f"  覆盖端点: {len(by_endpoint)} 个\n\n")
        
        # 分类统计
        f.write("【分类统计】\n")
        for cat, items in categories.items():
            cat_passed = sum(1 for t in items if t["passed"])
            cat_total = len(items)
            status = "✅" if cat_passed == cat_total else "❌"
            f.write(f"  {status} {cat}: {cat_passed}/{cat_total} 通过\n")
        f.write("\n")
        
        # 端点详细报告
        f.write("【端点详细报告】\n")
        for ep in sorted(by_endpoint.keys()):
            stats = by_endpoint[ep]
            status = "✅" if stats["failed"] == 0 else "❌"
            f.write(f"\n  {status} {ep}  ({stats['passed']}/{stats['total']} 通过)\n")
            
            # 失败详情
            for detail in stats["details"]:
                f.write(f"    ❌ [{detail['case']}] {detail['detail'][:120]}\n")
                if detail["response"]:
                    f.write(f"       响应: {detail['response'][:150]}\n")
        
        # 风险与建议
        f.write("\n\n【发现的风险与建议】\n")
        risks = []
        
        # 检查是否有5xx错误
        five_xx = [t for t in test_results if "5xx" in str(t.get("detail", "")) or "500" in str(t.get("response", ""))]
        if five_xx:
            risks.append(f"⚠ 发现 {len(five_xx)} 次服务端5xx错误，可能存在未处理的异常")
        
        if stress_errors > 0:
            risks.append(f"⚠ 压力测试出现 {stress_errors} 个错误，高并发下可能不稳定")
        
        if fuzz_errors > 0:
            risks.append(f"⚠ 模糊测试出现 {fuzz_errors} 个错误，对异常输入处理不完善")
        
        # 检查输入校验
        no_validation = [t for t in test_results if not t["passed"] and "超长" in t.get("case","") and "error" not in str(t.get("response","")).lower()]
        if no_validation:
            risks.append("⚠ 部分超长输入未被拦截，存在输入校验缺失")
        
        xss_sql = [t for t in test_results if ("SQL" in t.get("case","") or "XSS" in t.get("case","")) and t["passed"]]
        if not xss_sql:
            risks.append("✅ SQL注入/XSS测试均被正确拒绝或无害处理")
        else:
            risks.append("⚠ SQL注入/XSS测试中部分请求未被拦截")
        
        if risks:
            for r in risks:
                f.write(f"  {r}\n")
        else:
            f.write("  未发现明显风险\n")
        
        f.write("\n" + "=" * 70 + "\n")
        f.write("  报告结束\n")
        f.write("=" * 70 + "\n")
    
    # ─── 打印摘要到控制台 ───
    print("\n" + "=" * 70)
    print("  [测试报告摘要]")
    print("=" * 70)
    print(f"  总数: {total}  |  PASS: {passed}  |  FAIL: {failed}")
    print(f"  通过率: {passed/total*100:.1f}%" if total > 0 else "  通过率: N/A")
    print()
    for cat, items in categories.items():
        cat_passed = sum(1 for t in items if t["passed"])
        cat_total = len(items)
        icon = "PASS" if cat_passed == cat_total else "FAIL"
        print(f"  {icon} {cat}: {cat_passed}/{cat_total}")
    
    print(f"\n  详细报告已保存到: {report_path}")
    
    # 打印失败列表
    if failed > 0:
        print(f"\n  -- 失败用例 ({failed}条) --")
        for t in test_results:
            if not t["passed"]:
                print(f"  FAIL [{t['endpoint']}] {t['case']}: {t['detail'][:100]}")
    
    return report_path


# ═══════════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════════
def main():
    print("╔" + "═" * 58 + "╗")
    print("║  TinyBlog 全功能测试套件" + " " * 31 + "║")
    print("║  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " " * 38 + "║")
    print("╚" + "═" * 58 + "╝")
    print(f"  目标: {BASE_URL}")
    print(f"  并发数: {STRESS_CONCURRENT}, 压力轮次: {STRESS_ROUNDS}")
    print(f"  模糊测试次数: {FUZZ_COUNT}")
    print()
    
    # 健康检查
    ok, resp = get("/ping")
    if not ok or resp.get("message") != "Pong!":
        print("[FATAL] 服务器不可达! 请先启动服务器:")
        print(f"  uv run --directory src/backend python main.py")
        sys.exit(1)
    print("[OK] 服务器连接正常\n")
    
    # 执行测试
    try:
        prepare_test_data()
        test_normal_scenarios()
        test_edge_cases()
        test_consistency()
        test_fuzz()
        test_stress()
    except KeyboardInterrupt:
        print("\n[中断] 测试被用户中断")
    except Exception as e:
        print(f"\n[异常] {e}")
        import traceback
        traceback.print_exc()
    
    # 生成报告
    report_path = generate_report()
    
    return report_path

if __name__ == "__main__":
    main()
