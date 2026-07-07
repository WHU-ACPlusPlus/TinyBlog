#!/usr/bin/env python3
"""消息API高并发压力测试"""
import requests, time, threading, sys, os

BASE = os.environ.get("TB_BASE_URL", "http://127.0.0.1:18999")
TIMEOUT = 15

# 准备测试用户
def setup():
    r1 = requests.post(f"{BASE}/register-request", json={"username":"pstress1","password":"t","nickname":"PS1"}, timeout=TIMEOUT).json()
    r2 = requests.post(f"{BASE}/register-request", json={"username":"pstress2","password":"t","nickname":"PS2"}, timeout=TIMEOUT).json()
    c0, c1 = r1["cookie"], r2["cookie"]
    id0 = requests.post(f"{BASE}/check-cookie", json={"cookie":c0}, timeout=TIMEOUT).json()["user_id"]
    id1 = requests.post(f"{BASE}/check-cookie", json={"cookie":c1}, timeout=TIMEOUT).json()["user_id"]
    grp = requests.post(f"{BASE}/create-group", json={"cookie":c0,"name":"StressG"}, timeout=TIMEOUT).json()
    gid = grp["group_id"]
    requests.post(f"{BASE}/join-group", json={"cookie":c1,"group_id":gid}, timeout=TIMEOUT)
    return c0, c1, id0, id1, gid

results = {"ok": 0, "fail": 0, "lock": threading.Lock()}

def do_send_msg(c0, id1, idx):
    try:
        r = requests.post(f"{BASE}/send-msg", json={"cookie":c0,"to_whom_id":id1,"content":f"Stress{idx}"}, timeout=TIMEOUT)
        ok = r.json().get("status") == "success"
    except:
        ok = False
    with results["lock"]:
        if ok: results["ok"] += 1
        else: results["fail"] += 1

def do_get_conv(c):
    try:
        r = requests.post(f"{BASE}/get-conversations", json={"cookie":c}, timeout=TIMEOUT)
        ok = "conversations" in r.json()
    except:
        ok = False
    with results["lock"]:
        if ok: results["ok"] += 1
        else: results["fail"] += 1

def do_send_group(c0, gid, idx):
    try:
        r = requests.post(f"{BASE}/send-group-msg", json={"cookie":c0,"group_id":gid,"content":f"GS{idx}"}, timeout=TIMEOUT)
        ok = r.json().get("status") == "success"
    except:
        ok = False
    with results["lock"]:
        if ok: results["ok"] += 1
        else: results["fail"] += 1

def do_mixed(c0, id1, idx):
    eps = ["send-msg", "get-conversations", "search-contacts", "get-private-messages"]
    ep = eps[idx % 4]
    try:
        if ep == "send-msg":
            r = requests.post(f"{BASE}/{ep}", json={"cookie":c0,"to_whom_id":id1,"content":f"Mix{idx}"}, timeout=TIMEOUT)
        elif ep == "get-conversations":
            r = requests.post(f"{BASE}/{ep}", json={"cookie":c0}, timeout=TIMEOUT)
        elif ep == "search-contacts":
            r = requests.post(f"{BASE}/{ep}", json={"cookie":c0,"keyword":"stress","type":"all"}, timeout=TIMEOUT)
        else:
            r = requests.post(f"{BASE}/{ep}", json={"cookie":c0,"with_user_id":id1,"count":5}, timeout=TIMEOUT)
        ok = "error" not in r.json()
    except:
        ok = False
    with results["lock"]:
        if ok: results["ok"] += 1
        else: results["fail"] += 1

def run_test(name, func, args_iter, concurrent, total):
    results["ok"] = results["fail"] = 0
    print(f"\n[{name}] {total}请求, {concurrent}并发...")
    args_list = list(args_iter)
    t0 = time.time()
    threads = []
    for i in range(total):
        t = threading.Thread(target=func, args=args_list[i])
        threads.append(t)
        t.start()
        if len(threads) >= concurrent:
            for t in threads:
                t.join()
            threads = []
    for t in threads:
        t.join()
    elapsed = (time.time() - t0) * 1000
    print(f"  成功:{results['ok']}  失败:{results['fail']}  耗时:{elapsed:.0f}ms  QPS:{total/(elapsed/1000):.1f}")

def main():
    print("=" * 60)
    print("  TinyBlog 消息API 高并发压力测试")
    print("=" * 60)
    
    try:
        r = requests.get(f"{BASE}/ping", timeout=5)
        print(f"  服务器: {r.json()['message']}")
    except:
        print("[FATAL] 服务器不可达"); sys.exit(1)
    
    c0, c1, id0, id1, gid = setup()
    print(f"  u0={id0}, u1={id1}, group={gid}")
    
    # 测试1: 并发发送私信
    run_test("并发send-msg", do_send_msg,
             ((c0, id1, i) for i in range(50)), concurrent=20, total=50)
    
    # 测试2: 并发查询会话
    run_test("并发get-conversations", do_get_conv,
             ((c0,) for _ in range(30)), concurrent=15, total=30)
    
    # 测试3: 并发群消息
    run_test("并发send-group-msg", do_send_group,
             ((c0, gid, i) for i in range(30)), concurrent=15, total=30)
    
    # 测试4: 混合并发
    run_test("混合压测(send/recv/search)", do_mixed,
             ((c0, id1, i) for i in range(50)), concurrent=20, total=50)
    
    # 测试5: 极限并发(100请求)
    run_test("极限并发 send-msg", do_send_msg,
             ((c0, id1, i) for i in range(100)), concurrent=50, total=100)
    
    # 验证数据一致性
    conv = requests.post(f"{BASE}/get-conversations", json={"cookie":c1}, timeout=TIMEOUT).json()
    total_unread = sum(c.get("unread_count",0) for c in conv.get("conversations",[]))
    print(f"\n[一致性] 接收方会话数:{len(conv.get('conversations',[]))}, 总未读:{total_unread}")
    
    print("\n" + "=" * 60)
    print("  压力测试完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
