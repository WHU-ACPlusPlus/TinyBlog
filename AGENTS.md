# TinyBlog — AI Agent Guide

## Project Overview

TinyBlog (微微博) is a social networking app with a **Qt 6 / QML + C++ frontend** and a **Python/FastAPI + SQLite backend**.

| Layer | Tech | Directory |
|-------|------|-----------|
| Frontend | Qt 6 QML + C++ | `src/frontend/` |
| Backend | Python 3, FastAPI, SQLite, bcrypt | `src/backend/` |
| Design | 11 style guides | `style/` |

## Build & Run

### Frontend

```powershell
cmake -B build -S src/frontend
cmake --build build --config Release
./build/appfrontend
```

Requires: Qt 6.5+, CMake 3.16+, C++17 compiler.

### Backend

```powershell
cd src/backend
uv run python main.py
# Server starts at http://localhost:18999
# Test: curl http://localhost:18999/ping
```

Requires: Python 3.10+, `uv` package manager. Dependencies in `src/backend/pyproject.toml`.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  QML Layer (Main.qml → LoginFlow / MainPage)    │
│       ↓ context property "api"                  │
│  C++ ApiClient (api_client.h/.cpp)              │
│       ↓ HTTP/REST :18999                        │
│  Python Backend (src/backend/main.py)           │
│       ↓ db_execute / db_fetchone / db_fetchall  │
│  SQLite (main.db)                               │
└─────────────────────────────────────────────────┘
```

## Backend Conventions

### Database Access Pattern

All DB operations go through four helpers with a global `db_lock` (critical for SQLite thread safety — **never remove or bypass it**):

```python
db_execute(sql, params)   # INSERT/UPDATE/DELETE — returns cursor
db_fetchone(sql, params)  # Single row query — returns sqlite3.Row or None
db_fetchall(sql, params)  # Multi-row query — returns list[sqlite3.Row]
db_commit()               # Commit after writes
```

- `sqlite3.Row` objects support both index (`row[0]`) and key (`row["column"]`) access.
- Use `dict(row)` to convert to plain dict for JSON responses.

### Auth Pattern

Every endpoint (except `/ping`, `/register-request`, `/login-request`) validates cookie from request body:

```python
row = db_fetchone("SELECT user_id FROM cookies WHERE token = ?", (body.cookie,))
if not row:
    return {"error": "Bad cookie."}
user_id = row["user_id"]
```

### API Conventions

| Convention | Details |
|-----------|---------|
| Method | Almost all `POST` (only `/avatar` uses `GET`) |
| Request body | JSON with Pydantic `BaseModel` |
| Auth | `"cookie"` field in JSON body |
| Error format | HTTP 200 + `{"error": "描述"}` |
| Success format | `{"status": "success"}` or data object |
| Monolith | All routes in single `main.py` — **keep it that way unless explicitly asked** |

### Adding a New Endpoint

1. Define a Pydantic `BaseModel` for the request body
2. Write the endpoint function with `@app.post("/endpoint-name")`
3. Validate cookie → query DB → return result
4. Follow existing naming: kebab-case paths, snake_case Python functions

### Database Schema

Tables: `users`, `cookies`, `following`, `posts`, `liking_users`, `comments`, `offline_messages`, `post_media`, `read_posts`, `groups`, `user_in_group`, `group_messages`, `bookmarks`

Schema is auto-created on startup via `CREATE TABLE IF NOT EXISTS`. Backward-compatible ALTER TABLE for new columns uses try/except pattern (see existing code for `users.avatar`, `posts.repost_id`).

## Messaging Feature (消息功能)

The messaging system is the current development focus. Full specifications are in the requirements document on the desktop.

**Key design decisions:**
- **Conversation model**: Unified `conversations` table for both private chats and group chats
- **No more burn-after-reading**: Messages persist with `is_read` flag instead of auto-delete
- **Cursor pagination**: Message history uses `before_id` for efficient loading
- **Soft delete**: Conversations are hidden (`is_hidden=1`) not deleted

**Implementation order** (from requirements doc):
1. Database migration — add `is_read` to `offline_messages`, `avatar` to `groups`, create `conversations` table
2. New API endpoints — 7 new endpoints for conversations, search, contacts, user/group detail
3. Modify existing endpoints — session sync in `/send-msg`, `/send-group-msg`, `/create-group`, `/leave-group`
4. ApiClient C++ layer — new methods + signals
5. QML UI — three-column layout with `ConversationListPanel`, `ChatPanel`, `MessageBubble`

**Existing messaging endpoints** (for reference):

| Endpoint | Purpose | Status |
|----------|---------|--------|
| `POST /send-msg` | Send private message | Will be enhanced with conversation sync |
| `POST /recv-msg` | Receive private messages (burn-after-read) | Deprecated — replaced by `/get-private-messages` |
| `POST /send-group-msg` | Send group message | Will be enhanced with conversation sync |
| `POST /recv-group-msg` | Receive group messages (with `last_read_id`) | Keep as-is |
| `POST /create-group` | Create group + add owner | Will auto-create conversation record |
| `POST /join-group` | Join existing group | Keep as-is |
| `POST /leave-group` | Leave group | Will hide conversation record |

## Frontend Conventions

### Key QML Files

| File | Role |
|---|---|
| `Main.qml` | `ApplicationWindow` root, switches LoginFlow ↔ MainPage via `api.isLoggedIn` binding |
| `LoginFlow.qml` | 3-step auth: welcome → register → login |
| `MainPage.qml` | Responsive shell: sidebar (≥700px) / bottom bar (<700px) + `StackLayout` for pages |
| `SquarePage.qml` | Feed: post publishing, media attachments, timeline, likes, comments |
| `MessagesPage.qml` | Placeholder — being rebuilt for messaging feature |
| `ProfilePage.qml` | User profile card + logout |

### QML Rules

- **Always use `QtQuick.Controls.Basic`** — never import Material or Fusion styles.
- **Responsive breakpoint**: 700px width. Follow the pattern in `MainPage.qml`.
- **API binding**: `Connections { target: api; function onXxx(...) { ... } }` for async signals. Never `Timer`-based polling.
- **Spacing**: Multiples of 4px or 8px. No random magic numbers.
- **Animation**: `Behavior` / `Transition`, durations 150–300ms, eased curves.
- **New QML files**: Must be registered in `CMakeLists.txt` under `qt_add_qml_module → QML_FILES`.

### Frontend-Backend Contract

When adding a new endpoint, mirror it in the C++ layer:
1. Add method declaration in `api_client.h`
2. Add implementation in `api_client.cpp` (POST to endpoint, parse JSON response, emit signal)
3. Add data struct in `api_types.h` if needed, with `fromJson()` + `Q_DECLARE_METATYPE`

## Style System

`style/` contains 11 design guides. Before visual changes, **read the relevant guide** for design tokens.

| Style Guide | Keywords |
|---|---|
| `极简主义.md` | Black/white/gray, grid-based, minimal — **used for messaging UI** |
| `玻璃态.md` | Frosted glass, backdrop-blur, translucent |
| `极光玻璃.md` | Aurora gradients + glass cards, neon |
| `Fluent Design 2.0.md` | Acrylic, Windows 11 feel |
| `Soft UI 柔和界面.md` | Neumorphism, inset/outset shadows |
| `全息箔效果.md` / `全息渐变.md` | Holographic iridescent, foil |
| `Material Design 系统.md` | Material 3, elevation |
| `深色模式.md` | Dark theme, low-light |
| `平面设计系统.md` | Flat, no shadows, bold |
| `Gradients渐变.md` | Multi-stop gradients |

## File Boundaries

| Role | Modify | Don't Modify |
|------|--------|-------------|
| Backend dev | `src/backend/main.py`, `src/backend/*.py` | `src/frontend/*` (unless coordinating with frontend) |
| Frontend dev | `src/frontend/*.qml`, `src/frontend/*.h`, `src/frontend/*.cpp`, `src/frontend/CMakeLists.txt` | `src/backend/main.py` |
| Design | `style/*.md` | — |

## Key Documentation

| Document | Content |
|----------|---------|
| `src/backend/P2_FEATURES.md` | P2 backend features: password change, account deletion, block system, bookmarks, repost |
| `src/backend/test_runner.py` | Backend test suite |
| `style/极简主义.md` | Design tokens for messaging UI |
