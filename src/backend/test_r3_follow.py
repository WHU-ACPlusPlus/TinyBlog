#!/usr/bin/env python3
"""R3 修复: /follow 创建占位conversation + join/create-group 验证"""
import requests, os, random, string

BASE = os.environ.get("TB_BASE_URL", "http://127.0.0.1:18999")

def post(path, body):
    r = requests.post(f"{BASE}{path}", json=body, timeout=10)
    return r.json()

suffix = ''.join(random.choices(string.ascii_lowercase, k=5))
print("=" * 55)
print("  R3: /follow 创建占位会话测试")
print("=" * 55)

# 注册两个用户
A = post("/register-request", {"username":f"r3a_{suffix}","password":"t","nickname":"R3A"})
B = post("/register-request", {"username":f"r3b_{suffix}","password":"t","nickname":"R3B"})
cA, cB = A["cookie"], B["cookie"]
idA = post("/check-cookie", {"cookie":cA})["user_id"]
idB = post("/check-cookie", {"cookie":cB})["user_id"]
print(f"  A={idA}, B={idB}\n")

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

# ── 场景1: A关注B前, 会话列表为空 ──
print("── 场景1: 关注前, 会话列表为空 ──")
conv_before = post("/get-conversations", {"cookie":cA})
check("A的会话列表为空", len(conv_before.get("conversations",[])) == 0,
      f"convs={len(conv_before.get('conversations',[]))}")

# ── 场景2: A关注B ──
print("── 场景2: A关注B ──")
r = post("/follow", {"cookie":cA, "followee_id":idB})
check("关注成功", "status" in r and r["status"] == "success")

# ── 场景3: 关注后, B出现在A的会话列表中 ──
print("── 场景3: B出现在A的会话列表 ──")
conv_after = post("/get-conversations", {"cookie":cA})
hasB = any(c.get("target_id") == idB and c.get("type") == "private"
           for c in conv_after.get("conversations", []))
check("B出现在A的会话列表", hasB,
      f"convs={len(conv_after.get('conversations',[]))}")

# ── 场景4: 重复关注不重复创建 ──
print("── 场景4: 重复关注不重复创建 ──")
post("/follow", {"cookie":cA, "followee_id":idB})
conv_after2 = post("/get-conversations", {"cookie":cA})
countB = sum(1 for c in conv_after2.get("conversations",[])
             if c.get("target_id") == idB and c.get("type") == "private")
check("重复关注不重复创建会话", countB == 1, f"B出现{countB}次")

# ── 场景5: create-group已创建conversation ──
print("── 场景5: 创建群聊后群聊出现在会话列表 ──")
grp = post("/create-group", {"cookie":cA, "name":f"R3Group_{suffix}"})
gid = grp["group_id"]
conv_grp = post("/get-conversations", {"cookie":cA})
hasGrp = any(c.get("target_id") == gid and c.get("type") == "group"
             for c in conv_grp.get("conversations", []))
check("群聊出现在会话列表", hasGrp)

# ── 场景6: join-group已创建conversation ──
print("── 场景6: 加入群聊后出现在会话列表 ──")
post("/join-group", {"cookie":cB, "group_id":gid})
conv_B = post("/get-conversations", {"cookie":cB})
hasGrpB = any(c.get("target_id") == gid and c.get("type") == "group"
              for c in conv_B.get("conversations", []))
check("B加入群聊后群聊出现", hasGrpB)

# ── 结果 ──
print(f"\n{'='*55}")
print(f"  结果: {passed} 通过, {failed} 失败")
if failed == 0:
    print("  全部通过!")
else:
    print(f"  {failed} 项失败!")
print(f"{'='*55}")

# ── 日志验证 ──
print("\n── /follow 日志验证 ──")
try:
    with open("api.log", "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if "/follow" in l and "conversation" in l]
    for l in lines[-5:]:
        print(f"  {l}")
    print(f"  含'conversation created'的日志: {len(lines)} 条")
except FileNotFoundError:
    print("  api.log not found")
