"""Database abstraction layer — MySQL primary, SQLite fallback.

If MySQL is available the app uses it exactly as before.  When MySQL is
unreachable the module transparently falls back to an SQLite file in the
project root so the whole application still works for demos and previews.
"""
import os, sqlite3, datetime
from config import Config

# ── Determine which backend to use ──────────────────────────
_SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'voter_portal.db')
_backend = None  # 'mysql' | 'sqlite' | None (not yet probed)

# Map MySQL-style placeholders (%s) to SQLite style (?)
def _adapt_query(q):
    """Convert MySQL-style query to SQLite-compatible query."""
    q = q.replace('%s', '?')
    # Strip MySQL-specific clauses that SQLite doesn't support
    q = q.replace('ON UPDATE CURRENT_TIMESTAMP', '')
    # Replace DATE_FORMAT with strftime
    import re
    q = re.sub(r"DATE_FORMAT\((\w+),\s*'([^']+)'\)", r"strftime('\2', \1)", q)
    return q

# Map a dict row returned by sqlite3.Row to a plain dict
def _row_to_dict(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)

def _rows_to_dicts(rows):
    if rows is None:
        return []
    return [dict(r) if not isinstance(r, dict) else r for r in rows]


# ── MySQL helpers (original behaviour) ──────────────────────
def _mysql_connect():
    import pymysql
    return pymysql.connect(
        host=Config.DATABASE_HOST,
        user=Config.DATABASE_USER,
        password=Config.DATABASE_PASSWORD,
        database=Config.DATABASE_NAME,
        port=Config.DATABASE_PORT,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def _try_mysql():
    """Return True if MySQL is reachable."""
    try:
        conn = _mysql_connect()
        conn.close()
        return True
    except Exception:
        return False


# ── SQLite helpers ──────────────────────────────────────────
_sqlite_conn = None

def _sqlite_connect():
    global _sqlite_conn
    if _sqlite_conn is None:
        _sqlite_conn = sqlite3.connect(_SQLITE_PATH, check_same_thread=False)
        _sqlite_conn.row_factory = sqlite3.Row
        _sqlite_conn.execute("PRAGMA journal_mode=WAL")
        _sqlite_conn.execute("PRAGMA foreign_keys=ON")
    return _sqlite_conn

# Map MySQL NOW() / CURRENT_TIMESTAMP → SQLite equivalents at connect time
def _sqlite_now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# ── Public API (backend-agnostic) ───────────────────────────
def get_backend():
    global _backend
    if _backend is None:
        _backend = 'mysql' if _try_mysql() else 'sqlite'
        print(f"[database] Using backend: {_backend.upper()}")
    return _backend


def query_db(query, args=None, one=False):
    backend = get_backend()
    if backend == 'mysql':
        return _query_mysql(query, args, one)
    return _query_sqlite(query, args, one)


def execute_db(query, args=None):
    backend = get_backend()
    if backend == 'mysql':
        return _execute_mysql(query, args)
    return _execute_sqlite(query, args)


def execute_transaction(operations):
    backend = get_backend()
    if backend == 'mysql':
        return _transaction_mysql(operations)
    return _transaction_sqlite(operations)


# ── MySQL implementations (unchanged logic) ─────────────────
def _query_mysql(query, args, one):
    try:
        conn = _mysql_connect()
        cur = conn.cursor()
        cur.execute(query, args)
        result = cur.fetchone() if one else cur.fetchall()
        cur.close()
        conn.close()
        return result
    except Exception as e:
        print(f"MySQL query error: {e}")
        return None


def _execute_mysql(query, args):
    try:
        conn = _mysql_connect()
        cur = conn.cursor()
        cur.execute(query, args)
        lastrowid = cur.lastrowid
        cur.close()
        conn.close()
        return lastrowid
    except Exception as e:
        print(f"MySQL execute error: {e}")
        return None


def _transaction_mysql(operations):
    try:
        conn = _mysql_connect()
        conn.autocommit(False)
        cur = conn.cursor()
        for q, a in operations:
            cur.execute(q, a)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"MySQL transaction error: {e}")
        return False


# ── SQLite implementations ──────────────────────────────────
def _query_sqlite(query, args, one):
    try:
        conn = _sqlite_connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        q = _adapt_query(query)
        # Replace NOW() with the literal timestamp value (not a ? placeholder,
        # because NOW() can appear at any position and insert(0,...) would
        # shift all subsequent arguments)
        q = q.replace('NOW()', f"'{_sqlite_now()}'").replace('ON UPDATE CURRENT_TIMESTAMP', '')
        # Handle DATE_FORMAT → strftime
        q = q.replace("DATE_FORMAT(created_at, '%Y-%m')", "strftime('%Y-%m', created_at)")
        a = list(args) if args else []
        cur.execute(q, a)
        if one:
            row = cur.fetchone()
            result = dict(row) if row else None
        else:
            result = [dict(r) for r in cur.fetchall()]
        cur.close()
        return result
    except Exception as e:
        print(f"SQLite query error: {e}\n  Query: {query[:120]}")
        return None


def _execute_sqlite(query, args):
    try:
        conn = _sqlite_connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        q = _adapt_query(query)
        q = q.replace('NOW()', f"'{_sqlite_now()}'").replace('ON UPDATE CURRENT_TIMESTAMP', '')
        a = list(args) if args else []
        cur.execute(q, a)
        conn.commit()
        lastrowid = cur.lastrowid
        cur.close()
        return lastrowid
    except Exception as e:
        print(f"SQLite execute error: {e}\n  Query: {query[:120]}")
        return None


def _transaction_sqlite(operations):
    try:
        conn = _sqlite_connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        for q, a in operations:
            q2 = _adapt_query(q).replace('NOW()', f"'{_sqlite_now()}'")
            a2 = list(a) if a else []
            cur.execute(q2, a2)
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"SQLite transaction error: {e}")
        conn.rollback()
        return False
