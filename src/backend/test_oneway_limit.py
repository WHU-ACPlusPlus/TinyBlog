#!/usr/bin/env python3
"""单向关注限发1条消息 —— 功能测试"""
import requests, os

BASE = os.environ.get("TB_BASE_URL", "http://127.0.0.1:18999")

def post(path, body):
    r = requests.post(f"{BASE}{path}", json=body, timeout=10)
    return r.json()

# ── 准备用户 ──
print("=" * 55)
print("  单向关注限发1条消息测试")
print("=" * 55)

# 注册3个用户 (使用随机后缀避免冲突)
import random, string
suffix = ''.join(random.choices(string.ascii_lowercase, k=5))
A = post("/register-request", {"username":f"lma_{suffix}","password":"t","nickname":"LA"})
B = post("/register-request", {"username":f"lmb_{suffix}","password":"t","nickname":"LB"})
C = post("/register-request", {"username":f"lmc_{suffix}","password":"t","nickname":"LC"})
cA, cB, cC = A["cookie"], B["cookie"], C["cookie"]
idA = post("/check-cookie", {"cookie":cA})["user_id"]
idB = post("/check-cookie", {"cookie":cB})["user_id"]
idC = post("/check-cookie", {"cookie":cC})["user_id"]
print(f"  A={idA}, B={idB}, C={idC}\n")

passed = 0
failed = 0

def check(name, expected_ok, resp):
    global passed, failed
    has_error = "error" in resp
    ok = not has_error
    if expected_ok and ok:
        print(f"  [PASS] {name}: success")
        passed += 1
    elif not expected_ok and has_error:
        print(f"  [PASS] {name}: blocked -> {resp['error'][:50]}")
        passed += 1
    else:
        print(f"  [FAIL] {name}: expected_ok={expected_ok}, got={resp}")
        failed += 1

# ── 场景1: A单向关注B, A发第1条(应成功) ──
print("── 场景1: A→B 第1条(单向, 应允许) ──")
r = post("/send-msg", {"cookie":cA, "to_whom_id":idB, "content":"First msg from A to B"})
check("A->B msg1", True, r)

# ── 场景2: A发第2条(应被拦截) ──
print("── 场景2: A→B 第2条(单向, 应拦截) ──")
r = post("/send-msg", {"cookie":cA, "to_whom_id":idB, "content":"Second msg from A"})
check("A->B msg2", False, r)

# ── 场景3: A发第3条(也应拦截) ──
print("── 场景3: A→B 第3条(单向, 仍应拦截) ──")
r = post("/send-msg", {"cookie":cA, "to_whom_id":idB, "content":"Third msg from A"})
check("A->B msg3", False, r)

# ── 场景4: B回复A后, A可继续发 ──
print("── 场景4: B回复后, A→B 恢复 ──")
post("/send-msg", {"cookie":cB, "to_whom_id":idA, "content":"Reply from B"})
r = post("/send-msg", {"cookie":cA, "to_whom_id":idB, "content":"A msg after B replied"})
check("A->B after B replied", True, r)

# ── 场景5: 双向关注好友无限制 ──
print("── 场景5: A↔C 双向好友, 无限制 ──")
post("/follow", {"cookie":cA, "followee_id":idC})
post("/follow", {"cookie":cC, "followee_id":idA})
for i in range(1, 4):
    r = post("/send-msg", {"cookie":cA, "to_whom_id":idC, "content":f"Friend msg {i}"})
    check(f"A->C friend msg {i}", True, r)

# ── 场景6: 自我消息无限制 ──
print("── 场景6: 给自己发消息, 无限制 ──")
for i in range(1, 3):
    r = post("/send-msg", {"cookie":cA, "to_whom_id":idA, "content":f"Self msg {i}"})
    check(f"Self msg {i}", True, r)

# ── 结果 ──
print(f"\n{'='*55}")
print(f"  结果: {passed} 通过, {failed} 失败")
if failed == 0:
    print("  全部通过! ")
else:
    print(f"  {failed} 项失败! ")
print(f"{'='*55}")

# ── 日志验证 ──
print("\n── 日志验证 ──")
try:
    with open("api.log", "r", encoding="utf-8") as f:
        lines = [l for l in f if "one_way" in l]
    print(f"  日志中包含 'one_way' 的行数: {len(lines)}")
    for l in lines:
        print(f"    {l.strip()}")
except FileNotFoundError:
    print("  api.log 未找到")
