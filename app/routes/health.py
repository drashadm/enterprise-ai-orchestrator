from fastapi import APIRouter
import sqlite3

router = APIRouter()

@router.get("/health")
def health():
    # Basic DB connectivity check
    try:
        c = sqlite3.connect("data/logs.sqlite")
        c.cursor().execute("SELECT 1").fetchone()
        c.close()
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "ok",
        "db_ok": db_ok
    }