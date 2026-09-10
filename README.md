# TinyBlog（微微博）

一个迷你社交网络应用：**Qt 6 / QML + C++ 客户端**（含 Android 构建预设）+ **Python / FastAPI + SQLite 后端**。

武汉大学计算机学院小学期实践项目。

## 功能

| 模块 | 说明 |
|------|------|
| 账号 | 三步注册（图形验证码 → 邮箱验证码 → 建立账号）、三步登录、登出、Cookie 过期与自动续期 |
| 动态 | 发布文字 / 图片 / 视频动态（媒体随 `POST /pub-post` 以 base64 提交，单条最多 9 个、单个最大 16 MiB），Markdown 与 LaTeX 公式渲染，删除、转帖 |
| 信息流 | 首页 Feed、推荐帖子、用户动态列表、分页游标 |
| 互动 | 点赞、评论、收藏、书签 |
| 关系 | 关注 / 取关、关注请求、好友、好友分组、屏蔽、静音、域名屏蔽 |
| 消息 | 私信会话、会话列表、未读数、软删除、群聊（建群 / 入群 / 退群 / 群成员 / 群消息） |
| 通知 | 关注 / 点赞 / 评论等通知的聚合、单条已读、全部已读、未读数 |
| 搜索 | 用户 / 帖子全文搜索（SQLite FTS5）、联系人搜索 |
| 管理 | 举报、管理员审核、封禁 / 解封、屏蔽词过滤 |
| 客户端 | 登录流、首页、消息页、个人主页、响应式布局（侧边栏 / 底栏断点 700px）、11 套设计风格、中英双语 |

## 技术栈

| 层 | 技术 | 目录 |
|----|------|------|
| 客户端 | Qt 6.5+ / QML / C++17 / CMake | `src/frontend/` |
| 服务端 | Python 3.11+、FastAPI、Uvicorn、SQLite、bcrypt、Pillow、Matplotlib（LaTeX 渲染） | `src/backend/` |
| 设计 | 11 套界面风格规范 | `style/` |
| 文档 | 架构 / 缺陷分析 / 修复计划 | `docs/` |
| 部署 | 单机部署脚本（systemd + uv） | `deploy/` |

客户端与服务端通过 HTTP REST 通信，服务端默认监听 `127.0.0.1:18999`。

## 目录结构

```
.
├── src/
│   ├── frontend/          # Qt 6 / QML 客户端
│   │   ├── Main.qml               # 应用入口，登录态切换
│   │   ├── LoginFlow.qml          # 注册 / 登录流程
│   │   ├── MainPage.qml           # 主框架（侧边栏 / 底栏 + StackLayout）
│   │   ├── SquarePage.qml         # 首页信息流
│   │   ├── MessagesPage.qml       # 私信 / 群聊
│   │   ├── ProfilePage.qml        # 个人主页
│   │   ├── api_client.{h,cpp}     # 与服务端通信的 C++ 层
│   │   └── CMakePresets.json      # Android 构建预设
│   └── backend/
│       ├── main.py                # 所有接口 + 建表（init_db）
│       ├── social/                # 社交关系、私信、群组、通知、搜索
│       ├── seed_data.py           # 演示数据生成脚本
│       └── test_runner.py         # 接口压力 / 边缘测试
├── style/                 # 设计风格指南
├── docs/                  # 架构与修复文档
├── deploy/                # 部署脚本
└── AGENTS.md              # 代码库约定（面向 AI Agent）
```

## 快速开始

### 服务端

```bash
cd src/backend
uv sync                 # 安装依赖（Python 3.11）
uv run python main.py   # 启动，监听 127.0.0.1:18999

curl http://127.0.0.1:18999/ping     # {"message":"Pong!"}
```

### 客户端

```bash
cmake -B build -S src/frontend
cmake --build build --config Release
./build/appfrontend
```

需要 Qt 6.5+（Quick / Network / QuickDialogs2 / Multimedia / LinguistTools）、CMake 3.16+、支持 C++17 的编译器。

Android 构建见 `src/frontend/CMakePresets.json` 中的 `android-debug` / `android-release` 预设（Qt 6.5.3 arm64-v8a + NDK 25.1.8937393）。

### 演示数据

```bash
cd src/backend
uv run python seed_data.py
```

会重建数据库并写入 8 个用户（密码均为 `123456`）、动态、评论、私信、群组、通知等数据。脚本同时写入 `seed_token_<用户名>_<id>` 形式的 Cookie，可直接作为登录态使用。

> ⚠️ 该脚本会**先删除现有的 `main.db`**，有需要保留的数据请先备份。

## 配置

服务端通过环境变量读取邮件服务配置，注册与登录的邮箱验证码依赖它：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SMTP_HOST` | SMTP 服务器 | `smtp.qq.com` |
| `SMTP_PORT` | SMTP 端口（SSL） | `465` |
| `SMTP_USER` | 发件邮箱地址 | 必填 |
| `SMTP_PASS` | 发件邮箱密码 / 授权码 | 必填 |
| `SMTP_FROM` | 发件人显示名 | 同 `SMTP_USER` |

未配置 `SMTP_USER` / `SMTP_PASS` 时服务端可以正常启动，但注册流程无法完成（邮箱验证码发不出去）。

## 接口约定

- 绝大多数接口为 `POST`，请求体是 JSON，鉴权用请求体里的 `"cookie"` 字段（仅 `/avatar` 用 `GET`）
- 出错时返回 HTTP 200 + `{"error": "描述"}`；成功返回 `{"status": "success"}` 或数据对象
- 路径用 kebab-case，Python 函数名用 snake_case
- 完整约定见 `AGENTS.md`

## 文档

| 文档 | 内容 |
|------|------|
| `AGENTS.md` | 代码库约定：目录职责、数据库访问模式、接口与 QML 规范、文件边界 |
| `docs/ARCHITECTURE_消息系统.md` | 消息系统架构设计 |
| `docs/BUG_ANALYSIS_*.md` | 消息功能缺陷分析 |
| `docs/FIX_PLAN_*.md` | 修复计划 |
| `src/backend/P2_FEATURES.md` | P2 功能设计与接口速查（#25–#38；部分条目为计划，尚未全部实现） |
| `style/*.md` | 11 套界面设计规范 |

## 部署

`deploy/bc1-setup.sh` 提供单机部署流程（`git pull` → `uv sync --no-dev` → 重启 `backend-18999.service`）。

## 许可证

[MIT](LICENSE)
