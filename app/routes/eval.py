from fastapi import APIRouter, Header

from app.services.llm_service import interpret_request
from app.orchestrator.evaluator import run_all_workflow_suites

router = APIRouter()

# ----------------------------
# Decision-engine eval (/eval)
# ----------------------------
TESTS = [
    {
        "name": "needs_clarification_missing_fields",
        "message": "Generate a cyber risk report",
        "expect_workflow": "needs_clarification",
        "expect_missing_fields": {"client_id", "risk_domain"},
    },
    {
        "name": "risk_report_full",
        "message": "Generate a cyber risk report for client 123 as of 2026-02-18",
        "expect_workflow": "generate_risk_report",
        "expect_missing_fields": set(),
    },
    {
        "name": "unsupported_request",
        "message": "Book a flight to Boston tomorrow",
        "expect_workflow": "unsupported",
        "expect_missing_fields": set(),
    },
]


@router.get("/eval")
def eval_suite(x_user: str = Header(None)):
    # Eval focuses on LLM decision quality, not RBAC.
    # x_user included only so you can call it consistently with your other requests.
    results = []
    passed = 0

    for t in TESTS:
        try:
            d = interpret_request(t["message"])
            workflow_ok = (d.get("workflow") == t["expect_workflow"])
            missing = set(d.get("missing_fields", []))
            missing_ok = (missing == t["expect_missing_fields"])

            ok = workflow_ok and missing_ok
            if ok:
                passed += 1

            results.append({
                "test": t["name"],
                "ok": ok,
                "workflow": d.get("workflow"),
                "missing_fields": sorted(list(missing)),
                "confidence": d.get("confidence"),
            })
        except Exception as e:
            results.append({
                "test": t["name"],
                "ok": False,
                "error_type": e.__class__.__name__,
                "error": str(e)[:300],
            })

    return {
        "suite": "decision_engine",
        "passed": passed,
        "total": len(TESTS),
        "results": results
    }


# -----------------------------------
# Workflow execution eval (/eval/workflows)
# -----------------------------------
@router.get("/eval/workflows")
def eval_workflows(x_user: str = Header(None)):
    # x_user included for consistency; workflow eval does not rely on it.
    suite = run_all_workflow_suites()
    return {
        "suite": "workflow_execution",
        "passed": suite.get("passed", 0),
        "total": suite.get("total", 0),
        "details": suite,
    }