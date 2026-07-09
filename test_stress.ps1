# TinyBlog 后端压力+边缘测试
$base = "http://127.0.0.1:18999"
$pass = 0; $fail = 0

function test($name, $method, $endpoint, $body, $expectError) {
    try {
        $json = if ($body) { $body | ConvertTo-Json -Compress } else { "{}" }
        if ($method -eq "GET") {
            $r = Invoke-RestMethod "$base$endpoint" -TimeoutSec 5
        } else {
            $r = Invoke-RestMethod "$base$endpoint" -Method Post -Body $json -ContentType "application/json" -TimeoutSec 5
        }
        if ($expectError) {
            if ($r.error -eq $expectError) {
                Write-Host "  PASS: $name" -ForegroundColor Green; $global:pass++
            } else {
                Write-Host "  FAIL: $name (expected '$expectError', got '$($r.error)')" -ForegroundColor Red; $global:fail++
            }
        } else {
            Write-Host "  PASS: $name" -ForegroundColor Green; $global:pass++
        }
        return $r
    } catch {
        if ($expectError) {
            Write-Host "  PASS: $name (caught: $_)" -ForegroundColor Green; $global:pass++
        } else {
            Write-Host "  FAIL: $name -> $_" -ForegroundColor Red; $global:fail++
        }
        return $null
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  TinyBlog 后端边缘+压力测试" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# ── 1. 基础连通性 ──
Write-Host "[1] 连通性测试" -ForegroundColor Yellow
test "Ping" "GET" "/ping" $null $null

# ── 2. 注册边界测试 ──
Write-Host "`n[2] 注册边界测试" -ForegroundColor Yellow
test "空用户名" "POST" "/register-request" @{username="";password="p";nickname="n"} "Bad username."
test "空密码" "POST" "/register-request" @{username="u";password="";nickname="n"} "Bad password."
test "空昵称" "POST" "/register-request" @{username="u";password="p";nickname=""} "Bad nickname."

$ts = [DateTimeOffset]::Now.ToUnixTimeMilliseconds()
$u1 = "test_$ts"
$r = test "正常注册" "POST" "/register-request" @{username=$u1;password="pass";nickname="Tester"} $null
$cookie1 = $r.cookie

test "重复注册" "POST" "/register-request" @{username=$u1;password="p";nickname="n"} "Username occupied."

# ── 3. 登录边界测试 ──
Write-Host "`n[3] 登录边界测试" -ForegroundColor Yellow
test "错误密码" "POST" "/login-request" @{username=$u1;password="wrong"} "Incorrect password."
test "不存在用户" "POST" "/login-request" @{username="no_user_999";password="p"} "User not exist."
$r = test "正常登录" "POST" "/login-request" @{username=$u1;password="pass"} $null
$cookie1 = $r.cookie

# ── 4. Cookie 验证 ──
Write-Host "`n[4] Cookie验证" -ForegroundColor Yellow
test "无效cookie" "POST" "/get-conversations" @{cookie="bad_cookie"} "Bad cookie."
test "空会话列表" "POST" "/get-conversations" @{cookie=$cookie1} $null

# ── 5. 消息边界测试 ──
Write-Host "`n[5] 消息边界测试" -ForegroundColor Yellow
$u2name = "edge_$([DateTimeOffset]::Now.ToUnixTimeMilliseconds())"
$r2 = test "创建用户B" "POST" "/register-request" @{username=$u2name;password="p";nickname="EdgeUser"} $null
$cookie2 = $r2.cookie

test "空消息" "POST" "/send-msg" @{cookie=$cookie1;to_whom_id=99999;content=""} "Empty message not allowed."
test "不存在接收者" "POST" "/send-msg" @{cookie=$cookie1;to_whom_id=99999;content="hi"} "Bad `to_whom_id`"

# 获取用户B的ID（通过登录时已知信息，实际应该查profile）
# 这里我们假设cookie2有效，用它来获取用户ID
$r = Invoke-RestMethod "$base/check-cookie" -Method Post -Body (ConvertTo-Json @{cookie=$cookie2} -Compress) -ContentType "application/json"
$uid2 = $r.user_id
Write-Host "  用户B ID = $uid2" -ForegroundColor Gray

test "正常发送消息" "POST" "/send-msg" @{cookie=$cookie1;to_whom_id=$uid2;content="Hello!"} $null
test "发送Emoji" "POST" "/send-msg" @{cookie=$cookie1;to_whom_id=$uid2;content="😀🎉你好世界🌍"} $null
test "发送Unicode" "POST" "/send-msg" @{cookie=$cookie1;to_whom_id=$uid2;content="日本語 한국어 العربية"} $null

# 极长消息
$longMsg = "A" * 5000
test "发送5000字符" "POST" "/send-msg" @{cookie=$cookie1;to_whom_id=$uid2;content=$longMsg} $null

# ── 6. 会话列表验证 ──
Write-Host "`n[6] 会话列表" -ForegroundColor Yellow
$r = Invoke-RestMethod "$base/get-conversations" -Method Post -Body (ConvertTo-Json @{cookie=$cookie1} -Compress) -ContentType "application/json"
Write-Host "  用户A会话数: $($r.conversations.Count)" -ForegroundColor Gray
$r2c = Invoke-RestMethod "$base/get-conversations" -Method Post -Body (ConvertTo-Json @{cookie=$cookie2} -Compress) -ContentType "application/json"
Write-Host "  用户B会话数: $($r2c.conversations.Count)" -ForegroundColor Gray

# ── 7. 群组测试 ──
Write-Host "`n[7] 群组测试" -ForegroundColor Yellow
test "空群名" "POST" "/create-group" @{cookie=$cookie1;name=""} "Group name cannot be empty."
$r = test "创建群组" "POST" "/create-group" @{cookie=$cookie1;name="TestGroup"} $null
$gid = $r.group_id
Write-Host "  群ID = $gid" -ForegroundColor Gray

test "发送群消息" "POST" "/send-group-msg" @{cookie=$cookie1;group_id=$gid;content="群消息测试"} $null
test "空群消息" "POST" "/send-group-msg" @{cookie=$cookie1;group_id=$gid;content=""} "Empty message not allowed."

# ── 8. 搜索测试 ──
Write-Host "`n[8] 搜索测试" -ForegroundColor Yellow
test "空搜索" "POST" "/search-contacts" @{cookie=$cookie1;keyword="";type="all"} @{error="Bad keyword."}
$r = Invoke-RestMethod "$base/search-contacts" -Method Post -Body (ConvertTo-Json @{cookie=$cookie1;keyword=$u1;type="all"} -Compress) -ContentType "application/json"
Write-Host "  搜索'$u1': users=$($r.users.Count) groups=$($r.groups.Count)" -ForegroundColor Gray

# ── 9. 压力：连续快速请求 ──
Write-Host "`n[9] 压力: 连续5次fetchConversations" -ForegroundColor Yellow
1..5 | ForEach-Object {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $null = Invoke-RestMethod "$base/get-conversations" -Method Post -Body (ConvertTo-Json @{cookie=$cookie1} -Compress) -ContentType "application/json" -TimeoutSec 5
    $sw.Stop()
    Write-Host "  请求#$_ : $($sw.ElapsedMilliseconds)ms" -ForegroundColor Gray
}

# ── 结果 ──
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  结果: PASS=$pass FAIL=$fail" -ForegroundColor $(if($fail -eq 0){'Green'}else{'Red'})
Write-Host "========================================" -ForegroundColor Cyan
