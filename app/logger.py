import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

DB_PATH = Path("data/logs.sqlite")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def _json_dumps_safe(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return json.dumps({"_error": "json_dump_failed", "type": str(type(obj))})

def _ensure_tables(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT,
            user_id TEXT,
            role TEXT,
            request_message TEXT,
            workflow TEXT,
            confidence REAL,
            decision_json TEXT,
            result_json TEXT,
            created_at TEXT
        )
    """)
    # Helpful index for quick lookups
    cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_trace_id ON logs(trace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at)")
    conn.commit()

def log_event(trace_id: str, user, decision: Dict[str, Any], result: Dict[str, Any], request_message: str = "") -> None:
    conn = sqlite3.connect(str(DB_PATH))
    try:
        _ensure_tables(conn)
        cur = conn.cursor()

        workflow = (decision or {}).get("workflow")
        confidence = (decision or {}).get("confidence", 0.0)

        cur.execute(
            """
            INSERT INTO logs
            (trace_id, user_id, role, request_message, workflow, confidence, decision_json, result_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace_id,
                getattr(user, "user_id", "unknown"),
                getattr(user, "role", "unknown"),
                request_message or "",
                str(workflow),
                float(confidence) if confidence is not None else 0.0,
                _json_dumps_safe(decision or {}),
                _json_dumps_safe(result or {}),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()