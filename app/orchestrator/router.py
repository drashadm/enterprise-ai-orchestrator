from app.services.finance_api import generate_financial_report
from app.services.crm_api import sync_client
from app.services.risk_api import generate_risk_report
from app.services.compliance_api import compliance_policy_review
from app.services.vendor_risk_api import vendor_risk_intake
from app.services.financial_anomaly_api import financial_anomaly_summary
from pydantic import ValidationError
from app.schemas import CompliancePolicyReviewParameters
from app.schemas import VendorRiskIntakeParameters
from app.schemas import FinancialAnomalySummaryParameters

# Role-based access control (RBAC) for workflows
ROLE_WORKFLOW_ALLOWLIST = {
    "finance_analyst": {"generate_financial_report", "generate_risk_report", "financial_anomaly_summary"},
    "ops_manager": {"sync_client", "generate_risk_report", "vendor_risk_intake"},
    "compliance_officer": {"generate_risk_report", "compliance_policy_review", "vendor_risk_intake", "financial_anomaly_summary"},
    "admin": {"generate_financial_report", "generate_risk_report", "sync_client", "compliance_policy_review", "vendor_risk_intake", "financial_anomaly_summary"},
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
  
    if workflow == "compliance_policy_review":
        try:
            validated = CompliancePolicyReviewParameters(**params)
        except ValidationError as e:
            return {"error": "Invalid parameters", "details": e.errors()}
        return compliance_policy_review(validated.model_dump())
    
    if workflow == "vendor_risk_intake":
        try:
            validated = VendorRiskIntakeParameters(**params)
        except ValidationError as e:
            return {"error": "Invalid parameters", "details": e.errors()}
        return vendor_risk_intake(validated.model_dump())
    
    if workflow == "financial_anomaly_summary":
        try:
            validated = FinancialAnomalySummaryParameters(**params)
        except ValidationError as e:
            return {"error": "Invalid parameters", "details": e.errors()}
        return financial_anomaly_summary(validated.model_dump())

    return {"error": "Unknown workflow", "workflow": workflow}
