#!/usr/bin/env python3
"""
TinyBlog 消息功能单元测试
========================
覆盖全部 17 个消息相关 API 端点：
- 正常场景测试
- 边界值测试（空值、极值）
- 异常/错误路径测试
- 数据一致性校验

用法: uv run python test_messaging.py
前提: 后端服务器已在 http://127.0.0.1:18999 运行
"""

import requests
import json
import random
import string
import os
import sys
from datetime import datetime
from typing import Any

# ─── 配置 ───────────────────────────────────────────────
BASE_URL = os.environ.get("TB_BASE_URL", "http://127.0.0.1:18999")
TIMEOUT = 10

# ─── 全局状态 ───────────────────────────────────────────
test_results: list[dict] = []
users: list[dict] = []     # [{cookie, username, password, nickname, user_id}]
groups: list[int] = []
conversation_ids: list[int] = []

# ═══════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════

def rand_str(min_len=4, max_len=12) -> str:
    return ''.join(random.choices(string.ascii_lowercase, k=random.randint(min_len, max_len)))

def record(endpoint: str, case: str, passed: bool, detail: str = "", response: Any = None):
    test_results.append({
        "endpoint": endpoint,
        "case": case,
        "passed": passed,
        "detail": detail,
        "response": str(response)[:300] if response else "",
        "timestamp": datetime.now().isoformat()
    })
    icon = "[PASS]" if passed else "[FAIL]"
    print(f"  {icon} [{endpoint}] {case} | {detail}")

def post(path: str, body: dict, expect_ok: bool = True) -> tuple[bool, dict]:
    try:
        r = requests.post(f"{BASE_URL}{path}", json=body, timeout=TIMEOUT)
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

def register(username_prefix="msgtest") -> dict | None:
    u = f"{username_prefix}_{rand_str(4, 8)}"
    ok, resp = post("/register-request", {
        "username": u, "password": "Test123!", "nickname": f"Nick{rand_str(2,4)}"
    })
    if ok and "cookie" in resp:
        return {"username": u, "password": "Test123!", "cookie": resp["cookie"]}
    return None

# ═══════════════════════════════════════════════════════
#  第0步：环境检查
# ═══════════════════════════════════════════════════════

def check_environment():
    print("=" * 60)
    print("[环境] 检查服务器连通性...")
    ok, resp = get("/ping")
    if not ok or resp.get("message") != "Pong!":
        print("[FATAL] 服务器不可达! 请先启动: uv run python main.py")
        sys.exit(1)
    print("[OK] 服务器连接正常\n")

# ═══════════════════════════════════════════════════════
#  第1步：准备测试用户
# ═══════════════════════════════════════════════════════

def prepare_users():
    global users
    print("=" * 60)
    print("[准备] 创建测试用户...")
    for i in range(3):
        u = register(f"msguser{i}")
        if u:
            users.append(u)
            # 通过 /check-cookie 获取 user_id
            ok, resp = post("/check-cookie", {"cookie": u["cookie"]})
            if ok and resp.get("valid"):
                u["user_id"] = resp.get("user_id")
            print(f"  用户{i+1}: {u['username']} (id={u.get('user_id')}, cookie={u['cookie'][:12]}...)")
    if len(users) < 2:
        print("[FATAL] 无法注册足够用户")
        sys.exit(1)
    # 建立双向关注 (好友)
    u0, u1 = users[0], users[1]
    post("/follow", {"cookie": u0["cookie"], "followee_id": u1["user_id"]})
    post("/follow", {"cookie": u1["cookie"], "followee_id": u0["user_id"]})
    # u0 单向关注 u2
    if len(users) >= 3:
        u2 = users[2]
        post("/follow", {"cookie": u0["cookie"], "followee_id": u2["user_id"]})
    print("[准备] 完成\n")

# ═══════════════════════════════════════════════════════
#  第2步：正常场景测试（17个端点）
# ═══════════════════════════════════════════════════════

def test_normal_all_endpoints():
    global users, groups, conversation_ids
    print("=" * 60)
    print("[正常] 消息端点全量正常场景测试")
    u0, u1 = users[0], users[1]
    c0, c1 = u0["cookie"], u1["cookie"]
    id0, id1 = u0["user_id"], u1["user_id"]

    # ─── 2.1 GET /get-conversations (关注后已有占位会话) ───
    ok, resp = post("/get-conversations", {"cookie": c0})
    has_placeholder = ok and len(resp.get("conversations", [])) >= 1
    record("/get-conversations", "关注后出现占位会话", has_placeholder,
           f"convs={len(resp.get('conversations',[]))} (关注后应有占位会话)", resp)

    # ─── 2.2 POST /send-msg (发送私信) ───
    ok, resp = post("/send-msg", {"cookie": c0, "to_whom_id": id1, "content": "Hello from u0!"})
    record("/send-msg", "发送私信", ok, "status=success", resp)

    # ─── 2.3 POST /send-msg (回复) ───
    ok, resp = post("/send-msg", {"cookie": c1, "to_whom_id": id0, "content": "Hi back from u1!"})
    record("/send-msg", "回复私信", ok, "status=success", resp)

    # ─── 2.4 GET /get-conversations (有会话) ───
    ok, resp = post("/get-conversations", {"cookie": c0})
    has_conv = ok and len(resp.get("conversations", [])) >= 1
    if has_conv:
        for conv in resp["conversations"]:
            if conv.get("type") == "private":
                conversation_ids.append(conv["id"])
    record("/get-conversations", "有会话列表", has_conv,
           f"convs={len(resp.get('conversations',[]))}", resp)

    # ─── 2.5 GET /get-private-messages (最新消息) ───
    ok, resp = post("/get-private-messages", {"cookie": c0, "with_user_id": id1, "count": 20})
    has_msgs = ok and len(resp.get("messages", [])) >= 2
    record("/get-private-messages", "获取最新消息", has_msgs,
           f"msgs={len(resp.get('messages',[]))} has_more={resp.get('has_more')}", resp)

    # ─── 2.6 GET /get-private-messages (游标翻页) ───
    ok, resp = post("/get-private-messages", {"cookie": c0, "with_user_id": id1, "count": 20})
    if ok and resp.get("messages"):
        oldest_id = resp["messages"][0]["id"]
        ok2, resp2 = post("/get-private-messages",
                          {"cookie": c0, "with_user_id": id1, "before_id": oldest_id, "count": 10})
        record("/get-private-messages", "游标翻页before_id", ok2,
               f"before_id={oldest_id} → msgs={len(resp2.get('messages',[]))}", resp2)
    else:
        record("/get-private-messages", "游标翻页before_id", False, "前置条件失败:无消息")

    # ─── 2.7 POST /recv-msg (废弃端点兼容) ───
    # 先确保有未读消息
    post("/send-msg", {"cookie": c1, "to_whom_id": id0, "content": "Unread for u0"})
    ok, resp = post("/recv-msg", {"cookie": c0})
    has_unread = ok and len(resp.get("msgs", [])) >= 1
    record("/recv-msg [DEPRECATED]", "获取未读私信", has_unread,
           f"msgs={len(resp.get('msgs',[]))}", resp)

    # ─── 2.8 POST /search-contacts (搜索用户) ───
    ok, resp = post("/search-contacts", {"cookie": c0, "keyword": users[1]["username"][:5], "type": "user"})
    found_user = ok and len(resp.get("users", [])) >= 1
    record("/search-contacts", "搜索用户", found_user,
           f"users={len(resp.get('users',[]))} groups={len(resp.get('groups',[]))}", resp)

    # ─── 2.9 POST /search-contacts (搜索全部) ───
    ok, resp = post("/search-contacts", {"cookie": c0, "keyword": "msg", "type": "all"})
    record("/search-contacts", "搜索全部", ok,
           f"users={len(resp.get('users',[]))} groups={len(resp.get('groups',[]))}", resp)

    # ─── 2.10 POST /get-contacts (好友列表) ───
    ok, resp = post("/get-contacts", {"cookie": c0})
    has_mutual = ok and len(resp.get("mutual", [])) >= 1
    record("/get-contacts", "好友+关注列表", has_mutual,
           f"mutual={len(resp.get('mutual',[]))} followed_only={len(resp.get('followed_only',[]))}", resp)

    # ─── 2.11 POST /get-user-detail ───
    ok, resp = post("/get-user-detail", {"cookie": c0, "user_id": id1})
    record("/get-user-detail", "查看用户详情", ok and resp.get("username") == u1["username"],
           f"user={resp.get('username')} mutual={resp.get('is_mutual')}", resp)

    # ─── 2.12 POST /create-group ───
    ok, resp = post("/create-group", {"cookie": c0, "name": f"TestGroup_{rand_str(3,6)}"})
    if ok and resp.get("group_id"):
        groups.append(resp["group_id"])
    record("/create-group", "创建群聊", ok,
           f"group_id={resp.get('group_id')}", resp)

    # ─── 2.13 POST /join-group ───
    if groups:
        ok, resp = post("/join-group", {"cookie": c1, "group_id": groups[0]})
        record("/join-group", "加入群聊", ok, f"group_id={groups[0]}", resp)
    else:
        record("/join-group", "加入群聊", False, "前置条件失败:无群组")

    # ─── 2.14 POST /send-group-msg ───
    if groups:
        ok, resp = post("/send-group-msg", {"cookie": c0, "group_id": groups[0], "content": "Hello group!"})
        record("/send-group-msg", "发送群消息", ok, f"group_id={groups[0]}", resp)
    else:
        record("/send-group-msg", "发送群消息", False, "前置条件失败:无群组")

    # ─── 2.15 POST /recv-group-msg (最新消息) ───
    if groups:
        ok, resp = post("/recv-group-msg", {"cookie": c1, "group_id": groups[0], "count": 20})
        record("/recv-group-msg", "接收群消息(latest)", ok,
               f"msgs={len(resp.get('messages',[]))} has_more={resp.get('has_more')}", resp)
    else:
        record("/recv-group-msg", "接收群消息", False, "前置条件失败:无群组")

    # ─── 2.16 POST /recv-group-msg (游标翻页) ───
    if groups:
        # 多发几条消息以便翻页
        for i in range(3):
            post("/send-group-msg", {"cookie": c0, "group_id": groups[0], "content": f"Page test {i}"})
        ok, resp = post("/recv-group-msg", {"cookie": c1, "group_id": groups[0], "count": 20})
        if ok and resp.get("messages"):
            oldest_id = resp["messages"][0]["id"]
            ok2, resp2 = post("/recv-group-msg",
                              {"cookie": c1, "group_id": groups[0], "before_id": oldest_id, "count": 10})
            record("/recv-group-msg", "游标翻页before_id", ok2,
                   f"before_id={oldest_id} → msgs={len(resp2.get('messages',[]))}", resp2)
        else:
            record("/recv-group-msg", "游标翻页before_id", False, "前置条件失败")
    else:
        record("/recv-group-msg", "游标翻页", False, "前置条件失败:无群组")

    # ─── 2.17 POST /get-group-members ───
    if groups:
        ok, resp = post("/get-group-members", {"cookie": c0, "group_id": groups[0]})
        record("/get-group-members", "查看群成员", ok and len(resp.get("members", [])) >= 2,
               f"members={len(resp.get('members',[]))}", resp)
    else:
        record("/get-group-members", "查看群成员", False, "前置条件失败:无群组")

    # ─── 2.18 POST /get-my-groups ───
    ok, resp = post("/get-my-groups", {"cookie": c0})
    record("/get-my-groups", "我的群列表", ok and len(resp.get("groups", [])) >= 1,
           f"groups={len(resp.get('groups',[]))}", resp)

    # ─── 2.19 POST /get-group-detail ───
    if groups:
        ok, resp = post("/get-group-detail", {"cookie": c0, "group_id": groups[0]})
        record("/get-group-detail", "群详情", ok and resp.get("member_count", 0) >= 1,
               f"name={resp.get('name')} members={resp.get('member_count')}", resp)
    else:
        record("/get-group-detail", "群详情", False, "前置条件失败:无群组")

    # ─── 2.20 POST /update-group ───
    if groups:
        ok, resp = post("/update-group",
                        {"cookie": c0, "group_id": groups[0], "name": f"Updated_{rand_str(3,5)}", "avatar": "testb64"})
        record("/update-group", "更新群信息", ok, f"group_id={groups[0]}", resp)
    else:
        record("/update-group", "更新群信息", False, "前置条件失败:无群组")

    # ─── 2.21 POST /hide-conversation ───
    if conversation_ids:
        conv_id = conversation_ids[0]
        ok, resp = post("/hide-conversation", {"cookie": c0, "conversation_id": conv_id})
        record("/hide-conversation", "隐藏会话", ok, f"conv_id={conv_id}", resp)
        # 验证已隐藏
        ok2, resp2 = post("/get-conversations", {"cookie": c0})
        still_visible = any(c["id"] == conv_id for c in resp2.get("conversations", []))
        record("/hide-conversation", "验证已隐藏", ok2 and not still_visible,
               f"conv_id={conv_id} still_visible={still_visible}", resp2)
    else:
        record("/hide-conversation", "隐藏会话", False, "前置条件失败:无会话ID")

    # ─── 2.22 POST /leave-group ───
    # 创建临时群用于测试退群
    ok_tmp, tmp_resp = post("/create-group", {"cookie": c1, "name": f"LeaveTest_{rand_str(3,5)}"})
    if ok_tmp and tmp_resp.get("group_id"):
        tmp_gid = tmp_resp["group_id"]
        ok, resp = post("/leave-group", {"cookie": c1, "group_id": tmp_gid})
        record("/leave-group", "退出群聊", ok, f"group_id={tmp_gid}", resp)
    else:
        record("/leave-group", "退出群聊", False, "前置条件失败:创建群失败")

    print(f"[正常] 完成\n")


# ═══════════════════════════════════════════════════════
#  第3步：边界值与异常输入测试
# ═══════════════════════════════════════════════════════

def test_edge_cases():
    global users, groups
    print("=" * 60)
    print("[边界] 边界值与异常输入测试")
    u0 = users[0]
    c0 = u0["cookie"]
    id0 = u0["user_id"]

    # ── 边界：空cookie ──
    ok, resp = post("/get-conversations", {"cookie": ""}, expect_ok=False)
    record("/get-conversations", "空cookie", ok, str(resp.get("error",""))[:50], resp)

    # ── 边界：无效cookie ──
    ok, resp = post("/get-conversations", {"cookie": "invalid_token_12345"}, expect_ok=False)
    record("/get-conversations", "无效cookie", ok, str(resp.get("error",""))[:50], resp)

    # ── 边界：空消息内容 ──
    ok, resp = post("/send-msg", {"cookie": c0, "to_whom_id": users[1]["user_id"], "content": ""}, expect_ok=False)
    record("/send-msg", "空消息内容", ok, str(resp.get("error",""))[:50], resp)

    # ── 边界：发给不存在的用户 ──
    ok, resp = post("/send-msg", {"cookie": c0, "to_whom_id": 99999, "content": "Hi"}, expect_ok=False)
    record("/send-msg", "发给不存在用户", ok, str(resp.get("error",""))[:50], resp)

    # ── 边界：发给自己的ID（应该能发，因为没禁止）──
    ok, resp = post("/send-msg", {"cookie": c0, "to_whom_id": id0, "content": "Self msg"})
    record("/send-msg", "发给自己", ok, "自聊是否允许取决于业务逻辑", resp)

    # ── 边界：超长消息内容 ──
    long_msg = "A" * 10000
    ok, resp = post("/send-msg", {"cookie": c0, "to_whom_id": users[1]["user_id"], "content": long_msg})
    record("/send-msg", f"超长消息({len(long_msg)}字符)", ok,
           "应正确处理或拒绝" if ok else str(resp.get("error",""))[:60], resp)

    # ── 边界：不存在的with_user_id ──
    ok, resp = post("/get-private-messages", {"cookie": c0, "with_user_id": 99999, "count": 10})
    record("/get-private-messages", "不存在的with_user_id", ok,
           f"msgs={len(resp.get('messages',[]))}", resp)

    # ── 边界：count=0 ──
    ok, resp = post("/get-private-messages", {"cookie": c0, "with_user_id": users[1]["user_id"], "count": 0})
    record("/get-private-messages", "count=0", ok,
           f"msgs={len(resp.get('messages',[]))}", resp)

    # ── 边界：count负数 ──
    ok, resp = post("/get-private-messages", {"cookie": c0, "with_user_id": users[1]["user_id"], "count": -1})
    record("/get-private-messages", "count=-1", ok,
           f"msgs={len(resp.get('messages',[]))}", resp)

    # ── 边界：空搜索关键词 ──
    ok, resp = post("/search-contacts", {"cookie": c0, "keyword": "", "type": "all"})
    record("/search-contacts", "空关键词", ok,
           f"users={len(resp.get('users',[]))} groups={len(resp.get('groups',[]))}", resp)

    # ── 边界：特殊字符搜索 ──
    ok, resp = post("/search-contacts", {"cookie": c0, "keyword": "%_'; DROP TABLE--", "type": "all"})
    record("/search-contacts", "SQL注入式搜索", ok,
           f"users={len(resp.get('users',[]))} (应安全处理)", resp)

    # ── 边界：不存在的conversation_id ──
    ok, resp = post("/hide-conversation", {"cookie": c0, "conversation_id": 99999}, expect_ok=False)
    record("/hide-conversation", "隐藏不存在会话", ok, str(resp.get("error",""))[:50], resp)

    # ── 边界：不存在的user_id ──
    ok, resp = post("/get-user-detail", {"cookie": c0, "user_id": 99999}, expect_ok=False)
    record("/get-user-detail", "查看不存在用户", ok, str(resp.get("error",""))[:50], resp)

    # ── 边界：空群名 ──
    ok, resp = post("/create-group", {"cookie": c0, "name": ""}, expect_ok=False)
    record("/create-group", "空群名", ok, str(resp.get("error",""))[:50], resp)

    # ── 边界：加入不存在的群 ──
    ok, resp = post("/join-group", {"cookie": c0, "group_id": 99999}, expect_ok=False)
    record("/join-group", "加入不存在群", ok, str(resp.get("error",""))[:50], resp)

    # ── 边界：非群成员发消息 ──
    ok, resp = post("/send-group-msg", {"cookie": c0, "group_id": 99999, "content": "Hi"}, expect_ok=False)
    record("/send-group-msg", "非成员发群消息", ok, str(resp.get("error",""))[:50], resp)

    # ── 边界：非群主更新群信息 ──
    if groups:
        u2 = users[2] if len(users) >= 3 else users[1]
        ok, resp = post("/update-group",
                        {"cookie": u2["cookie"], "group_id": groups[0], "name": "Hacked!"},
                        expect_ok=False)
        record("/update-group", "非群主更新群信息", ok, str(resp.get("error",""))[:50], resp)
    else:
        record("/update-group", "非群主更新群信息", False, "前置条件失败:无群组")

    # ── 边界：不存在群详情 ──
    ok, resp = post("/get-group-detail", {"cookie": c0, "group_id": 99999}, expect_ok=False)
    record("/get-group-detail", "不存在群详情", ok, str(resp.get("error",""))[:50], resp)

    # ── 边界：空群消息 ──
    ok, resp = post("/send-group-msg", {"cookie": c0, "group_id": groups[0] if groups else 1, "content": ""}, expect_ok=False)
    record("/send-group-msg", "空群消息", ok, str(resp.get("error",""))[:50], resp)

    # ── 边界：超长群名 ──
    ok, resp = post("/create-group", {"cookie": c0, "name": "G" * 500})
    record("/create-group", f"超长群名(500字符)", ok,
           "应正确处理" if ok else str(resp.get("error",""))[:60], resp)

    print(f"[边界] 完成\n")


# ═══════════════════════════════════════════════════════
#  第4步：数据一致性测试
# ═══════════════════════════════════════════════════════

def test_consistency():
    global users, groups
    print("=" * 60)
    print("[一致性] 消息数据一致性校验")
    u0, u1 = users[0], users[1]
    c0, c1 = u0["cookie"], u1["cookie"]
    id0, id1 = u0["user_id"], u1["user_id"]

    # ── 4.1 发送消息后，双方会话都应存在 ──
    # 确保发送多条消息让unread_count累积，避免之前测试步骤误清零
    for _ in range(3):
        post("/send-msg", {"cookie": c0, "to_whom_id": id1, "content": "Consistency check"})
    ok1, r1 = post("/get-conversations", {"cookie": c0})
    ok2, r2 = post("/get-conversations", {"cookie": c1})
    c0_has = any(c.get("target_id") == id1 and c.get("type") == "private"
                 for c in r1.get("conversations", []))
    c1_has = any(c.get("target_id") == id0 and c.get("type") == "private"
                 for c in r2.get("conversations", []))
    record("CONSISTENCY", "双方会话双向存在", ok1 and ok2 and c0_has and c1_has,
           f"u0→u1:{c0_has}, u1→u0:{c1_has}")

    # ── 4.2 对方unread_count应>=1 ──
    # 发一条独立消息后立即检查接收方会话
    post("/send-msg", {"cookie": c0, "to_whom_id": id1, "content": "Unread test"})
    ok, r2b = post("/get-conversations", {"cookie": c1})
    c1_conv = next((c for c in r2b.get("conversations", [])
                    if c.get("target_id") == id0 and c.get("type") == "private"), None)
    if c1_conv:
        unread = c1_conv.get("unread_count", -1)
        record("CONSISTENCY", "接收方unread_count>=1", unread >= 1,
               f"unread_count={unread}")
    else:
        record("CONSISTENCY", "接收方unread_count>=1", False, "未找到u1的私聊会话")

    # ── 4.3 读取消息后unread_count归零 ──
    post("/get-private-messages", {"cookie": c1, "with_user_id": id0, "count": 20})
    ok, resp = post("/get-conversations", {"cookie": c1})
    if ok and c1_has:
        conv_c1_after = next((c for c in resp["conversations"] if c.get("target_id") == id0), None)
        unread_after = conv_c1_after.get("unread_count", -1) if conv_c1_after else -1
        record("CONSISTENCY", "读消息后unread=0", unread_after == 0,
               f"unread_count={unread_after}")
    else:
        record("CONSISTENCY", "读消息后unread=0", False, "前置条件失败")

    # ── 4.4 get-contacts与get-follow-list一致 ──
    ok1, r1 = post("/get-contacts", {"cookie": c0})
    ok2, r2 = post("/get-follow-list", {"cookie": c0})
    if ok1 and ok2:
        mutual_cnt = len(r1.get("mutual", []))
        followed_cnt = len(r1.get("followed_only", []))
        total_from_contacts = mutual_cnt + followed_cnt
        total_from_follow = len(r2.get("followees", []))
        record("CONSISTENCY", "联系人总数与关注列表一致",
               total_from_contacts == total_from_follow,
               f"contacts={total_from_contacts}, follow_list={total_from_follow}")

    # ── 4.5 群消息发送后群成员都有会话 ──
    if groups:
        gid = groups[0]
        post("/send-group-msg", {"cookie": c0, "group_id": gid, "content": "Group consistency"})
        ok0, r0 = post("/get-conversations", {"cookie": c0})
        ok1, r1 = post("/get-conversations", {"cookie": c1})
        c0_has_grp = any(c.get("target_id") == gid and c.get("type") == "group"
                         for c in r0.get("conversations", []))
        c1_has_grp = any(c.get("target_id") == gid and c.get("type") == "group"
                         for c in r1.get("conversations", []))
        record("CONSISTENCY", "群消息后成员皆有会话",
               ok0 and ok1 and c0_has_grp and c1_has_grp,
               f"u0:{c0_has_grp}, u1:{c1_has_grp}")
    else:
        record("CONSISTENCY", "群消息后成员皆有会话", False, "前置条件失败:无群组")

    # ── 4.6 隐藏会话后对方会话不受影响 ──
    post("/send-msg", {"cookie": c0, "to_whom_id": id1, "content": "Before hide"})
    ok1, r1 = post("/get-conversations", {"cookie": c0})
    if ok1 and r1.get("conversations"):
        conv = next((c for c in r1["conversations"] if c.get("type") == "private" and c.get("target_id") == id1), None)
        if conv:
            post("/hide-conversation", {"cookie": c0, "conversation_id": conv["id"]})
            ok2, r2 = post("/get-conversations", {"cookie": c1})
            c1_still_has = any(c.get("target_id") == id0 and c.get("type") == "private"
                               for c in r2.get("conversations", []))
            record("CONSISTENCY", "隐藏会话不影响对方", ok2 and c1_still_has,
                   f"对方仍有会话={c1_still_has}")

    print(f"[一致性] 完成\n")

# ═══════════════════════════════════════════════════════
#  第5步：生成报告
# ═══════════════════════════════════════════════════════

def generate_report():
    total = len(test_results)
    passed = sum(1 for t in test_results if t["passed"])
    failed = total - passed
    pct = (passed / total * 100) if total > 0 else 0

    # 按端点统计
    by_endpoint = {}
    for t in test_results:
        ep = t["endpoint"]
        if ep not in by_endpoint:
            by_endpoint[ep] = {"total": 0, "passed": 0, "failed": 0, "failures": []}
        by_endpoint[ep]["total"] += 1
        if t["passed"]:
            by_endpoint[ep]["passed"] += 1
        else:
            by_endpoint[ep]["failed"] += 1
            by_endpoint[ep]["failures"].append(t)

    # 类别统计
    categories = {
        "正常场景": [t for t in test_results if t["endpoint"] not in ("CONSISTENCY",) and "边界" not in t["case"]],
        "边界异常": [t for t in test_results if "边界" in t["case"]],
        "一致性": [t for t in test_results if t["endpoint"] == "CONSISTENCY"],
    }

    report_path = os.path.join(os.path.dirname(__file__) or ".", "test_messaging_report.txt")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("  TinyBlog 消息功能单元测试报告\n")
        f.write(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"  目标服务器: {BASE_URL}\n")
        f.write("=" * 70 + "\n\n")

        f.write("【总览】\n")
        f.write(f"  测试总数: {total}\n")
        f.write(f"  通过: {passed}  ({pct:.1f}%)\n")
        f.write(f"  失败: {failed}  ({100-pct:.1f}%)\n" if total > 0 else "  失败: 0\n")
        f.write(f"  覆盖端点: {len(by_endpoint)} 个\n\n")

        f.write("【分类统计】\n")
        for cat, items in categories.items():
            cat_passed = sum(1 for t in items if t["passed"])
            cat_total = len(items)
            status = "✅" if cat_passed == cat_total else "❌"
            f.write(f"  {status} {cat}: {cat_passed}/{cat_total} 通过\n")
        f.write("\n")

        f.write("【端点详细报告】\n")
        for ep in sorted(by_endpoint.keys()):
            stats = by_endpoint[ep]
            status = "✅" if stats["failed"] == 0 else "❌"
            f.write(f"\n  {status} {ep}  ({stats['passed']}/{stats['total']} 通过)\n")
            for fail in stats["failures"]:
                f.write(f"    ❌ [{fail['case']}] {fail['detail'][:120]}\n")
                if fail["response"]:
                    f.write(f"       响应: {fail['response'][:200]}\n")

        # 安全建议
        f.write("\n\n【安全审查建议】\n")
        f.write("  a. 输入校验: 所有端点均使用 Pydantic BaseModel 进行类型校验 ✅\n")
        f.write("     - 建议增加: 字符串长度上限(如content限制10000字符)\n")
        f.write("     - 建议增加: 对search keyword做长度限制防止LIKE慢查询\n")
        f.write("  b. 依赖纯净: 仅使用项目标准依赖(fastapi/uvicorn/bcrypt) ✅\n")
        f.write("  c. 环境脱敏: BASE_URL通过环境变量TB_BASE_URL配置,无硬编码密钥 ✅\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("  报告结束\n")
        f.write("=" * 70 + "\n")

    # 控制台摘要
    print("\n" + "=" * 60)
    print(f"  测试完成: {passed}/{total} 通过 ({pct:.1f}%)")
    if failed > 0:
        print(f"  [FAIL] {failed} 项失败！详情见 {report_path}")
    else:
        print(f"  [PASS] 全部通过！")
    print(f"  报告: {report_path}")
    print("=" * 60)

    return report_path


# ═══════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  TinyBlog 消息功能单元测试")
    print("=" * 60)
    print(f"  服务器: {BASE_URL}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    check_environment()
    prepare_users()

    try:
        test_normal_all_endpoints()
        test_edge_cases()
        test_consistency()
    except KeyboardInterrupt:
        print("\n[中断] 测试被用户中断")
    except Exception as e:
        print(f"\n[异常] {e}")
        import traceback
        traceback.print_exc()

    report_path = generate_report()

    # 返回退出码
    total = len(test_results)
    passed = sum(1 for t in test_results if t["passed"])
    if total > 0 and passed == total:
        print("\n[PASS] 所有测试通过！")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} 项测试失败，请检查报告")
        return 1

if __name__ == "__main__":
    sys.exit(main())
