#!/usr/bin/env python3
"""R4: 头像字段透传 — 单元测试"""
import requests, os, random, string

BASE = os.environ.get("TB_BASE_URL", "http://127.0.0.1:18999")

def post(path, body):
    r = requests.post(f"{BASE}{path}", json=body, timeout=10)
    return r.json()

suffix = ''.join(random.choices(string.ascii_lowercase, k=5))
print("=" * 55)
print("  R4: 头像字段透传测试")
print("=" * 55)

# 注册用户
A = post("/register-request", {"username":f"r4a_{suffix}","password":"t","nickname":"R4A"})
B = post("/register-request", {"username":f"r4b_{suffix}","password":"t","nickname":"R4B"})
cA, cB = A["cookie"], B["cookie"]
idA = post("/check-cookie", {"cookie":cA})["user_id"]
idB = post("/check-cookie", {"cookie":cB})["user_id"]

# 上传头像 (给A设置头像)
post("/avatar", {"cookie":cA, "signature":"Test sig", "avatar":"TEST_BASE64_AVATAR_DATA_A"})
post("/avatar", {"cookie":cB, "signature":"Test sig", "avatar":"TEST_BASE64_AVATAR_DATA_B"})

print(f"  A={idA}, B={idB}")
print(f"  A avatar set, B avatar set\n")

passed = 0
failed = 0

def check(name, cond, detail=""):
    global passed, failed
    if cond:
        print(f"  [PASS] {name} {detail}")
        passed += 1
    else:
        print(f"  [FAIL] {name} {detail}")
        failed += 1

# ── 场景1: get-private-messages 返回 sender_avatar ──
print("── 场景1: 私信消息包含sender_avatar ──")
post("/send-msg", {"cookie":cA, "to_whom_id":idB, "content":"Test private msg"})
msgs = post("/get-private-messages", {"cookie":cB, "with_user_id":idA, "count":10})
has_avatar = "sender_avatar" in msgs.get("messages", [{}])[0]
check("私信含sender_avatar字段", has_avatar,
      f"value={msgs.get('messages',[{}])[0].get('sender_avatar','MISSING')[:30]}")

# ── 场景2: 创建群聊, 发群消息, 获取群消息含avatar ──
print("── 场景2: 群消息包含avatar ──")
grp = post("/create-group", {"cookie":cA, "name":f"R4Group_{suffix}"})
gid = grp["group_id"]
post("/join-group", {"cookie":cB, "group_id":gid})
post("/send-group-msg", {"cookie":cA, "group_id":gid, "content":"Group test msg"})
gmsgs = post("/recv-group-msg", {"cookie":cB, "group_id":gid, "count":10})
has_gavatar = "avatar" in gmsgs.get("messages", [{}])[0]
check("群消息含avatar字段", has_gavatar,
      f"value={gmsgs.get('messages',[{}])[0].get('avatar','MISSING')[:30]}")

# ── 场景3: 边界 - 无头像用户的消息 ──
print("── 场景3: 无头像用户消息返回空avatar ──")
C = post("/register-request", {"username":f"r4c_{suffix}","password":"t","nickname":"R4C"})
cC = C["cookie"]
idC = post("/check-cookie", {"cookie":cC})["user_id"]
post("/send-msg", {"cookie":cC, "to_whom_id":idA, "content":"From no-avatar user"})
msgs3 = post("/get-private-messages", {"cookie":cA, "with_user_id":idC, "count":10})
av3 = msgs3.get("messages", [{}])[0].get("sender_avatar", "MISSING")
check("无头像用户avatar为空字符串", av3 == "",
      f"avatar='{av3}'")

# ── 场景4: recv-group-msg before_id分页含avatar ──
print("── 场景4: 游标翻页群消息含avatar ──")
for i in range(3):
    post("/send-group-msg", {"cookie":cA, "group_id":gid, "content":f"Page {i}"})
all_msgs = post("/recv-group-msg", {"cookie":cB, "group_id":gid, "count":20})
if all_msgs.get("messages"):
    oldest = all_msgs["messages"][0]
    page = post("/recv-group-msg", {"cookie":cB, "group_id":gid, "before_id":oldest["id"], "count":10})
    has_page_av = len(page.get("messages",[])) > 0 and "avatar" in page["messages"][0]
    check("翻页消息含avatar", has_page_av,
          f"msgs={len(page.get('messages',[]))}")
else:
    check("翻页消息含avatar", False, "前置条件失败")

# ── 结果 ──
print(f"\n{'='*55}")
print(f"  结果: {passed} 通过, {failed} 失败")
if failed == 0:
    print("  全部通过!")
else:
    print(f"  {failed} 项失败!")
print(f"{'='*55}")
