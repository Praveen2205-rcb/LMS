from __future__ import annotations
from backend.database import get_connection


def log_action(user_id: int | None, action: str, entity_type: str = "",
               entity_id: int | None = None, description: str = "",
               ip_address: str = "") -> None:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""INSERT INTO activity_log
                       (user_id,action,entity_type,entity_id,description,ip_address)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (user_id, action, entity_type, entity_id, description, ip_address))
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Logger error: {e}")
