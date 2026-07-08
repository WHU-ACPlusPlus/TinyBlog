"""
数据库连接 - 注入式包装器。
不自己创建连接，而是等待 main.py 通过 bind(conn, lock) 注入 master 的全局连接和锁。
"""
import sqlite3

_conn = None
_lock = None


def bind(conn: sqlite3.Connection, lock):
    """注入 master 的全局连接和锁。main.py 在创建 conn/db_lock 后调用一次。"""
    global _conn, _lock
    _conn = conn
    _lock = lock


def get_conn() -> sqlite3.Connection:
    return _conn


def close_conn():
    pass  # master 管理连接生命周期


def transactional(fn):
    """装饰器：持锁执行，自动提交/回滚。依赖 RLock 支持嵌套。"""

    def wrapper(*args, **kwargs):
        conn = get_conn()
        with _lock:
            try:
                result = fn(*args, **kwargs)
                conn.commit()
                return result
            except Exception:
                conn.rollback()
                raise

    return wrapper
