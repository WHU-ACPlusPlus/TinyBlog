"""
社交功能 API 路由（移植自 LYC social 模块）。
以 APIRouter 挂载到 main.py，与 master 原生端点并存。
"""
from fastapi import APIRouter
from pydantic import BaseModel

from social import social, models, notification, search
from social.db import get_conn

router = APIRouter()


# =============================================================================
# 通用辅助
# =============================================================================

def get_user_id(cookie: str) -> int | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT user_id FROM cookies WHERE token = ?", (cookie,)
    ).fetchone()
    return row["user_id"] if row else None


def check_admin(user_id: int) -> bool:
    try:
        return models.check_permission(user_id, "admin")
    except Exception:
        return False


# =============================================================================
# M3. 角色权限
# =============================================================================

class Role_Req(BaseModel):
    cookie: str

@router.post("/get-role")
def api_get_role(body: Role_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    role = models.get_user_role(uid)
    return {"role": role}


class Set_Role_Req(BaseModel):
    cookie: str
    target_id: int
    role: str  # normal | creator | admin

@router.post("/set-role")
def api_set_role(body: Set_Role_Req):
    uid = get_user_id(body.cookie)
    if not uid or not check_admin(uid):
        return {"error": "Forbidden."}
    result = models.set_user_role(body.target_id, body.role)
    return result or {"status": "success"}


# =============================================================================
# M3. 屏蔽 / 静音
# =============================================================================

class Block_Req(BaseModel):
    cookie: str
    target_id: int

@router.post("/block")
def api_block(body: Block_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    return social.block(uid, body.target_id)


@router.post("/unblock")
def api_unblock(body: Block_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    return social.unblock(uid, body.target_id)


@router.post("/get-blocked")
def api_get_blocked(body: Role_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    conn = get_conn()
    rows = conn.execute(
        "SELECT u.id, u.username, u.nickname FROM blocks b JOIN users u ON u.id = b.blocked_id WHERE b.user_id = ?",
        (uid,)
    ).fetchall()
    return {"users": [dict(r) for r in rows]}


@router.post("/mute")
def api_mute(body: Block_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    return social.mute(uid, body.target_id)


@router.post("/unmute")
def api_unmute(body: Block_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    return social.unmute(uid, body.target_id)


@router.post("/get-muted")
def api_get_muted(body: Role_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    conn = get_conn()
    rows = conn.execute(
        "SELECT u.id, u.username, u.nickname FROM mutes m JOIN users u ON u.id = m.muted_id WHERE m.user_id = ?",
        (uid,)
    ).fetchall()
    return {"users": [dict(r) for r in rows]}


# =============================================================================
# M4. 举报 / 审核 / 封禁 (admin)
# =============================================================================

class Report_Req(BaseModel):
    cookie: str
    post_id: int
    reason: str = ""

@router.post("/report")
def api_report(body: Report_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    return social.report_content(uid, body.post_id, body.reason)


class Review_Req(BaseModel):
    cookie: str
    report_id: int
    action: str  # resolve | delete | ban
    reason: str = ""

@router.post("/review-report")
def api_review_report(body: Review_Req):
    uid = get_user_id(body.cookie)
    if not uid or not check_admin(uid):
        return {"error": "Forbidden."}
    return social.review_report(body.report_id, uid, body.action, body.reason)


class Ban_Req(BaseModel):
    cookie: str
    target_id: int
    ban_type: str = "spam"

@router.post("/ban-user")
def api_ban_user(body: Ban_Req):
    uid = get_user_id(body.cookie)
    if not uid or not check_admin(uid):
        return {"error": "Forbidden."}
    return social.ban_user(uid, body.target_id, body.ban_type)


class ModLog_Req(BaseModel):
    cookie: str
    count: int = 50
    offset: int = 0

@router.post("/get-moderation-log")
def api_get_mod_log(body: ModLog_Req):
    uid = get_user_id(body.cookie)
    if not uid or not check_admin(uid):
        return {"error": "Forbidden."}
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM moderation_logs ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (body.count, body.offset)
    ).fetchall()
    return {"logs": [dict(r) for r in rows]}


@router.post("/get-reports")
def api_get_reports(body: ModLog_Req):
    uid = get_user_id(body.cookie)
    if not uid or not check_admin(uid):
        return {"error": "Forbidden."}
    conn = get_conn()
    rows = conn.execute(
        "SELECT r.*, u.username, u.nickname FROM reports r JOIN users u ON u.id = r.reporter_id ORDER BY r.created_at DESC LIMIT ? OFFSET ?",
        (body.count, body.offset)
    ).fetchall()
    return {"reports": [dict(r) for r in rows]}


# =============================================================================
# M5. 全文搜索 (FTS5)
# =============================================================================

class Search_Req(BaseModel):
    cookie: str
    query: str
    count: int = 20
    offset: int = 0

@router.post("/search")
def api_search(body: Search_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    result = search.search_all(body.query, uid, body.count, body.offset)
    return result


@router.post("/search-posts")
def api_search_posts(body: Search_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    result = search.search_posts(body.query, uid, body.count, body.offset)
    return {"posts": result, "count": len(result)}


@router.post("/search-users")
def api_search_users(body: Search_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    result = search.search_users(body.query, body.count, body.offset)
    return {"users": result, "count": len(result)}


@router.post("/search-tags")
def api_search_tags(body: Search_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    result = search.search_tags(body.query, body.count, body.offset)
    return {"tags": result, "count": len(result)}


class AdvSearch_Req(BaseModel):
    cookie: str
    keyword: str = ""
    tag: str = ""
    from_user: str = ""
    min_likes: int = 0
    count: int = 20
    offset: int = 0

@router.post("/advanced-search")
def api_advanced_search(body: AdvSearch_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    result = search.advanced_search(
        body.keyword, body.tag, body.from_user, body.min_likes,
        uid, body.count, body.offset
    )
    return {"posts": result, "count": len(result)}


class Suggest_Req(BaseModel):
    cookie: str
    query: str
    count: int = 5

@router.post("/search-suggest")
def api_search_suggest(body: Suggest_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    result = search.search_suggest(body.query, body.count)
    return {"suggestions": result}


# =============================================================================
# M5. 通知系统
# =============================================================================

class Notif_Req(BaseModel):
    cookie: str
    count: int = 40
    offset: int = 0

@router.post("/get-notifications")
def api_get_notifications(body: Notif_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    result = notification.get_notifications(uid, body.count, body.offset)
    return {"notifications": result, "count": len(result)}


class Unread_Req(BaseModel):
    cookie: str

@router.post("/get-unread-count")
def api_get_unread_count(body: Unread_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    count = notification.get_unread_count(uid)
    return {"unread_count": count}


class MarkRead_Req(BaseModel):
    cookie: str
    notification_ids: list[int] = []

@router.post("/mark-notification-read")
def api_mark_read(body: MarkRead_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    conn = get_conn()
    if body.notification_ids:
        conn.execute(
            "UPDATE notifications SET is_read = 1 WHERE id IN ({}) AND user_id = ?".format(
                ",".join("?" for _ in body.notification_ids)
            ), (*body.notification_ids, uid)
        )
    else:
        conn.execute(
            "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
            (uid,)
        )
    conn.commit()
    return {"status": "success"}


class MarkAllRead_Req(BaseModel):
    cookie: str

@router.post("/mark-all-read")
def api_mark_all_read(body: MarkAllRead_Req):
    uid = get_user_id(body.cookie)
    if not uid:
        return {"error": "Bad cookie."}
    conn = get_conn()
    conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
        (uid,)
    )
    conn.commit()
    return {"status": "success"}
