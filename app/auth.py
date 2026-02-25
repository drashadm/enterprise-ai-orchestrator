from fastapi import Header, HTTPException
from app.schemas import User

ROLE_MAP = {
    "finance_user": "finance_analyst",
    "ops_user": "ops_manager",
    "admin_user": "admin"
}

def get_current_user(x_user: str = Header(...)):
    if x_user not in ROLE_MAP:
        raise HTTPException(status_code=403, detail="Unauthorized user")
    return User(user_id=x_user, role=ROLE_MAP[x_user])
