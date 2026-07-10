#!/usr/bin/env python3
"""R5: 群消息切换会话不消失 — 单元测试"""
import requests, os, random, string

BASE = os.environ.get("TB_BASE_URL", "http://127.0.0.1:18999")

# 封装POST请求，发送JSON并返回解析后的响应
def post(path, body):
    r = requests.post(f"{BASE}{path}", json=body, timeout=10)
    return r.json()

suffix = ''.join(random.choices(string.ascii_lowercase, k=5))
print("=" * 55)
print("  R5: recv-group-msg before_id=0 返回最新消息")
print("=" * 55)

# 注册用户 + 创建群
A = post("/register-request", {"username":f"r5a_{suffix}","password":"t","nickname":"R5A"})
B = post("/register-request", {"username":f"r5b_{suffix}","password":"t","nickname":"R5B"})
cA, cB = A["cookie"], B["cookie"]
idA = post("/check-cookie", {"cookie":cA})["user_id"]
idB = post("/check-cookie", {"cookie":cB})["user_id"]
grp = post("/create-group", {"cookie":cA, "name":f"R5Group_{suffix}"})
gid = grp["group_id"]
post("/join-group", {"cookie":cB, "group_id":gid})
print(f"  A={idA}, B={idB}, group={gid}\n")

passed = 0
failed = 0

# 记录测试结果并输出（通过/失败）
def check(name, cond, detail=""):
    global passed, failed
    if cond:
        print(f"  [PASS] {name} {detail}")
        passed += 1
    else:
        print(f"  [FAIL] {name} {detail}")
        failed += 1

# ── 场景1: 发送5条群消息 ──
print("── 场景1: 发送5条群消息 ──")
for i in range(5):
    post("/send-group-msg", {"cookie":cA, "group_id":gid, "content":f"Group msg {i+1}"})
print("  已发送5条")

# ── 场景2: 第1次获取群消息(应获取全部5条) ──
print("── 场景2: 第1次获取(before_id=0) ──")
msgs1 = post("/recv-group-msg", {"cookie":cB, "group_id":gid, "count":20})
cnt1 = len(msgs1.get("messages", []))
check("第1次获取最新消息", cnt1 == 5, f"msgs={cnt1} (期望5)")

# ── 场景3: 第2次获取(模拟切换会话后再进入) ──
print("── 场景3: 第2次获取(模拟切回) ──")
msgs2 = post("/recv-group-msg", {"cookie":cB, "group_id":gid, "count":20})
cnt2 = len(msgs2.get("messages", []))
check("第2次仍返回5条(不消失)", cnt2 == 5,
      f"msgs={cnt2} (期望5, BUG: last_read_id过滤导致消失)")

# ── 场景4: 第3次获取 ──
print("── 场景4: 第3次获取 ──")
msgs3 = post("/recv-group-msg", {"cookie":cB, "group_id":gid, "count":20})
cnt3 = len(msgs3.get("messages", []))
check("第3次仍返回5条", cnt3 == 5, f"msgs={cnt3}")

# ── 场景5: before_id翻页正常 ──
print("── 场景5: before_id翻页 ──")
oldest_id = msgs1["messages"][0]["id"]
page = post("/recv-group-msg", {"cookie":cB, "group_id":gid, "before_id":oldest_id, "count":10})
check("before_id翻页正常", "messages" in page,
      f"msgs={len(page.get('messages',[]))} has_more={page.get('has_more')}")

# ── 场景6: 新消息发送后立即获取 ──
print("── 场景6: 发送第6条后获取 ──")
post("/send-group-msg", {"cookie":cA, "group_id":gid, "content":"New msg 6"})
msgs6 = post("/recv-group-msg", {"cookie":cB, "group_id":gid, "count":20})
cnt6 = len(msgs6.get("messages", []))
check("新消息可获取", cnt6 >= 6, f"msgs={cnt6} (期望>=6)")

# ── 场景7: 边界 - 空群获取 ──
print("── 场景7: 空群边界测试 ──")
grp2 = post("/create-group", {"cookie":cA, "name":f"R5Empty_{suffix}"})
gid2 = grp2["group_id"]
empty = post("/recv-group-msg", {"cookie":cA, "group_id":gid2, "count":20})
check("空群返回0条消息", len(empty.get("messages", [])) == 0 and "messages" in empty,
      f"msgs={len(empty.get('messages',[]))}")

# ── 场景8: 异常 - 非成员获取 ──
print("── 场景8: 非成员获取(异常路径) ──")
C = post("/register-request", {"username":f"r5c_{suffix}","password":"t","nickname":"R5C"})
cC = C["cookie"]
err = post("/recv-group-msg", {"cookie":cC, "group_id":gid, "count":20})
check("非成员被拒绝", "error" in err, f"error={err.get('error','')[:50]}")

# ── 结果 ──
print(f"\n{'='*55}")
print(f"  结果: {passed} 通过, {failed} 失败")
if failed == 0:
    print("  全部通过!")
else:
    print(f"  {failed} 项失败!")
print(f"{'='*55}")
