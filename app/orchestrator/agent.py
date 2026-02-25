import uuid
from app.services.llm_service import interpret_request
from app.orchestrator.router import route_workflow
from app.logger import log_event

async def handle_request(req, user):
    trace_id = str(uuid.uuid4())

    decision = interpret_request(req.message)

    # If LLM can't safely decide, return a controlled response (and log it)
    if decision["workflow"] in ("needs_clarification", "unsupported"):
        result = {
            "status": decision["workflow"],
            "rationale": decision.get("rationale", ""),
            "missing_fields": decision.get("missing_fields", []),
        }
        log_event(trace_id, user, decision, result, request_message=req.message)
        return {
            "trace_id": trace_id,
            "workflow": decision["workflow"],
            "result": result
        }

    result = route_workflow(decision, user)

    log_event(trace_id, user, decision, result, request_message=req.message)

    return {
        "trace_id": trace_id,
        "workflow": decision["workflow"],
        "result": result
    }
