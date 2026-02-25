from fastapi import FastAPI, Depends
from app.schemas import UserRequest, SystemResponse
from app.auth import get_current_user
from app.orchestrator.agent import handle_request
from app.routes.health import router as health_router
from app.routes.eval import router as eval_router

app = FastAPI(title="Enterprise AI Orchestrator")

app.include_router(health_router)
app.include_router(eval_router)

@app.post("/execute", response_model=SystemResponse)
async def execute(req: UserRequest, user=Depends(get_current_user)):
    result = await handle_request(req, user)
    return result