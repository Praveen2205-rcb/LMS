from __future__ import annotations
import datetime
from decimal import Decimal
from backend.database import get_connection


def _row(cursor) -> dict | None:
    cols = [d[0] for d in cursor.description]
    row = cursor.fetchone()
    return dict(zip(cols, row)) if row else None


def _rows(cursor) -> list[dict]:
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in cursor.fetchall()]


def _fix(d: dict) -> dict:
    """Convert Decimal/date/datetime to JSON-safe types."""
    for k, v in d.items():
        if isinstance(v, Decimal):
            d[k] = float(v)
        elif isinstance(v, (datetime.date, datetime.datetime)):
            d[k] = v.isoformat()
    return d


# ─── BOOKS ───────────────────────────────────────────────────────────────────

def get_all_books(search: str = "", category_id: int | None = None) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    q = """SELECT b.*, c.name AS category_name
           FROM books b LEFT JOIN categories c ON b.category_id=c.id
           WHERE b.is_active=1"""
    params: list = []
    if search:
        q += " AND (b.title LIKE %s OR b.author LIKE %s OR b.isbn LIKE %s)"
        like = f"%{search}%"
        params += [like, like, like]
    if category_id:
        q += " AND b.category_id=%s"
        params.append(category_id)
    q += " ORDER BY b.title"
    cur.execute(q, params)
    result = [_fix(r) for r in _rows(cur)]
    cur.close(); conn.close()
    return result


def get_book(book_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""SELECT b.*, c.name AS category_name
                   FROM books b LEFT JOIN categories c ON b.category_id=c.id
                   WHERE b.id=%s""", (book_id,))
    r = _row(cur)
    cur.close(); conn.close()
    return _fix(r) if r else None


def add_book(data: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""INSERT INTO books (isbn,title,author,publisher,year_published,
                   category_id,total_copies,available_copies,location,description)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (data.get("isbn"), data["title"], data["author"],
                 data.get("publisher"), data.get("year_published"),
                 data.get("category_id"), data.get("total_copies", 1),
                 data.get("total_copies", 1), data.get("location"), data.get("description")))
    new_id = cur.lastrowid
    cur.close(); conn.close()
    return new_id


def update_book(book_id: int, data: dict) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""UPDATE books SET isbn=%s,title=%s,author=%s,publisher=%s,
                   year_published=%s,category_id=%s,total_copies=%s,location=%s,description=%s
                   WHERE id=%s""",
                (data.get("isbn"), data["title"], data["author"],
                 data.get("publisher"), data.get("year_published"),
                 data.get("category_id"), data.get("total_copies", 1),
                 data.get("location"), data.get("description"), book_id))
    ok = cur.rowcount > 0
    cur.close(); conn.close()
    return ok


def delete_book(book_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE books SET is_active=0 WHERE id=%s", (book_id,))
    ok = cur.rowcount > 0
    cur.close(); conn.close()
    return ok


# ─── MEMBERS ─────────────────────────────────────────────────────────────────

def get_all_members(search: str = "") -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    q = """SELECT u.*, 
           (SELECT COUNT(*) FROM transactions t WHERE t.user_id=u.id AND t.status='issued') AS active_borrows
           FROM users u WHERE u.role='member'"""
    params: list = []
    if search:
        q += " AND (u.full_name LIKE %s OR u.email LIKE %s OR u.member_id LIKE %s)"
        like = f"%{search}%"
        params += [like, like, like]
    q += " ORDER BY u.full_name"
    cur.execute(q, params)
    result = [_fix(r) for r in _rows(cur)]
    cur.close(); conn.close()
    return result


def get_user(user_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    r = _row(cur)
    cur.close(); conn.close()
    return _fix(r) if r else None


def get_user_by_username(username: str) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=%s AND is_active=1", (username,))
    r = _row(cur)
    cur.close(); conn.close()
    return _fix(r) if r else None


def add_member(data: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE role='member'")
    count = cur.fetchone()[0] + 1
    member_id = f"MEM{count:04d}"
    cur.execute("""INSERT INTO users (username,password_hash,role,full_name,email,phone,address,member_id)
                   VALUES (%s,%s,'member',%s,%s,%s,%s,%s)""",
                (data["username"], data["password_hash"], data["full_name"],
                 data.get("email"), data.get("phone"), data.get("address"), member_id))
    new_id = cur.lastrowid
    cur.close(); conn.close()
    return new_id


def update_member(user_id: int, data: dict) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""UPDATE users SET full_name=%s,email=%s,phone=%s,address=%s,is_active=%s
                   WHERE id=%s""",
                (data["full_name"], data.get("email"), data.get("phone"),
                 data.get("address"), data.get("is_active", 1), user_id))
    ok = cur.rowcount > 0
    cur.close(); conn.close()
    return ok


# ─── TRANSACTIONS ─────────────────────────────────────────────────────────────

def issue_book(book_id: int, user_id: int, issued_by: int, days: int = 14) -> int | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT available_copies FROM books WHERE id=%s", (book_id,))
    row = cur.fetchone()
    if not row or row[0] < 1:
        cur.close(); conn.close()
        return None
    today = datetime.date.today()
    due = today + datetime.timedelta(days=days)
    cur.execute("""INSERT INTO transactions (book_id,user_id,issued_by,issue_date,due_date,status)
                   VALUES (%s,%s,%s,%s,%s,'issued')""", (book_id, user_id, issued_by, today, due))
    txn_id = cur.lastrowid
    cur.execute("UPDATE books SET available_copies=available_copies-1 WHERE id=%s", (book_id,))
    cur.close(); conn.close()
    return txn_id


def return_book(transaction_id: int, returned_to: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions WHERE id=%s AND status='issued'", (transaction_id,))
    txn = _row(cur)
    if not txn:
        cur.close(); conn.close()
        return {"error": "Transaction not found or already returned"}
    today = datetime.date.today()
    due_date = txn["due_date"]
    if isinstance(due_date, str):
        due_date = datetime.date.fromisoformat(due_date)
    fine = 0.0
    if today > due_date:
        overdue_days = (today - due_date).days
        fine = round(overdue_days * 2.0, 2)  # ₹2 per day
    cur.execute("""UPDATE transactions SET return_date=%s,fine_amount=%s,
                   returned_to=%s,status='returned',updated_at=NOW()
                   WHERE id=%s""", (today, fine, returned_to, transaction_id))
    cur.execute("UPDATE books SET available_copies=available_copies+1 WHERE id=%s", (txn["book_id"],))
    cur.close(); conn.close()
    return {"fine": fine, "overdue_days": max(0, (today - due_date).days)}


def get_all_transactions(status: str = "", user_id: int | None = None) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    q = """SELECT t.*,
           b.title AS book_title, b.author AS book_author,
           u.full_name AS member_name, u.member_id AS member_code,
           ib.full_name AS issued_by_name
           FROM transactions t
           JOIN books b ON t.book_id=b.id
           JOIN users u ON t.user_id=u.id
           LEFT JOIN users ib ON t.issued_by=ib.id
           WHERE 1=1"""
    params: list = []
    if status:
        q += " AND t.status=%s"
        params.append(status)
    if user_id:
        q += " AND t.user_id=%s"
        params.append(user_id)
    q += " ORDER BY t.created_at DESC"
    cur.execute(q, params)
    result = [_fix(r) for r in _rows(cur)]
    cur.close(); conn.close()
    return result


def get_transaction(txn_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""SELECT t.*,
                   b.title AS book_title,b.author AS book_author,
                   u.full_name AS member_name,u.member_id AS member_code
                   FROM transactions t
                   JOIN books b ON t.book_id=b.id
                   JOIN users u ON t.user_id=u.id
                   WHERE t.id=%s""", (txn_id,))
    r = _row(cur)
    cur.close(); conn.close()
    return _fix(r) if r else None


def update_overdue_status():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""UPDATE transactions SET status='overdue'
                   WHERE status='issued' AND due_date < CURDATE()""")
    cur.close(); conn.close()


# ─── CATEGORIES ──────────────────────────────────────────────────────────────

def get_categories() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories ORDER BY name")
    result = _rows(cur)
    cur.close(); conn.close()
    return result


# ─── DASHBOARD STATS ─────────────────────────────────────────────────────────

def get_dashboard_stats() -> dict:
    conn = get_connection()
    cur = conn.cursor()
    stats: dict = {}
    queries = {
        "total_books": "SELECT COUNT(*) FROM books WHERE is_active=1",
        "available_books": "SELECT SUM(available_copies) FROM books WHERE is_active=1",
        "total_members": "SELECT COUNT(*) FROM users WHERE role='member' AND is_active=1",
        "active_issues": "SELECT COUNT(*) FROM transactions WHERE status IN ('issued','overdue')",
        "overdue_count": "SELECT COUNT(*) FROM transactions WHERE status='overdue'",
        "total_fines": "SELECT COALESCE(SUM(fine_amount),0) FROM transactions WHERE fine_paid=0 AND fine_amount>0",
        "today_issues": "SELECT COUNT(*) FROM transactions WHERE DATE(created_at)=CURDATE()",
        "today_returns": "SELECT COUNT(*) FROM transactions WHERE return_date=CURDATE()",
    }
    for key, q in queries.items():
        cur.execute(q)
        val = cur.fetchone()[0]
        stats[key] = float(val) if isinstance(val, Decimal) else (val or 0)

    # Monthly issue trend (last 6 months)
    cur.execute("""SELECT DATE_FORMAT(issue_date,'%b %Y') AS month, COUNT(*) AS cnt
                   FROM transactions
                   WHERE issue_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                   GROUP BY DATE_FORMAT(issue_date,'%Y-%m'), DATE_FORMAT(issue_date,'%b %Y')
                   ORDER BY MIN(issue_date)""")
    stats["monthly_trend"] = _rows(cur)

    # Top 5 books
    cur.execute("""SELECT b.title, COUNT(t.id) AS borrow_count
                   FROM transactions t JOIN books b ON t.book_id=b.id
                   GROUP BY t.book_id, b.title ORDER BY borrow_count DESC LIMIT 5""")
    stats["top_books"] = _rows(cur)

    # Category distribution
    cur.execute("""SELECT c.name, COUNT(b.id) AS cnt
                   FROM categories c LEFT JOIN books b ON b.category_id=c.id AND b.is_active=1
                   GROUP BY c.id, c.name ORDER BY cnt DESC""")
    stats["category_dist"] = _rows(cur)

    cur.close(); conn.close()
    return stats


def get_recent_activity(limit: int = 20) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""SELECT a.*, u.full_name AS user_name
                   FROM activity_log a LEFT JOIN users u ON a.user_id=u.id
                   ORDER BY a.created_at DESC LIMIT %s""", (limit,))
    result = [_fix(r) for r in _rows(cur)]
    cur.close(); conn.close()
    return result