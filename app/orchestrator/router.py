from app.services.finance_api import generate_financial_report
from app.services.crm_api import sync_client
from app.services.risk_api import generate_risk_report

# Role-based access control (RBAC) for workflows
ROLE_WORKFLOW_ALLOWLIST = {
    "finance_analyst": {"generate_financial_report", "generate_risk_report"},
    "ops_manager": {"sync_client", "generate_risk_report"},
    "compliance_officer": {"generate_risk_report"},
    "admin": {"generate_financial_report", "generate_risk_report", "sync_client"},
}

def route_workflow(decision, user):
    workflow = decision.get("workflow")
    params = decision.get("parameters", {})

    if not workflow:
        return {"error": "Missing workflow in decision"}

    allowed = ROLE_WORKFLOW_ALLOWLIST.get(user.role, set())
    if workflow not in allowed:
        return {
            "error": "Forbidden workflow for role",
            "workflow": workflow,
            "role": user.role,
            "allowed_workflows": sorted(list(allowed)),
        }

    if workflow == "generate_risk_report":
        return generate_risk_report(params)

    if workflow == "sync_client":
        return sync_client(params)

    if workflow == "generate_financial_report":
        return generate_financial_report(params)

    return {"error": "Unknown workflow", "workflow": workflow}
