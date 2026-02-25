from pydantic import BaseModel
from typing import Dict, Any

class UserRequest(BaseModel):
    message: str

class User(BaseModel):
    user_id: str
    role: str

class SystemResponse(BaseModel):
    trace_id: str
    workflow: str
    result: Dict[str, Any]
