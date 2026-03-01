from __future__ import annotations

from typing import Any, Dict, List

from pydantic import ValidationError

from app.schemas import CompliancePolicyReviewResult, VendorRiskIntakeResult
from app.schemas import FinancialAnomalySummaryResult
from app.services.compliance_api import compliance_policy_review
from app.services.vendor_risk_api import vendor_risk_intake
from app.services.financial_anomaly_api import financial_anomaly_summary


def _risk_level_from_score(score: int) -> str:
    if score < 30:
        return "low"
    if score < 70:
        return "medium"
    return "high"


def _escalation_from_threshold(score: int, risk_tolerance_level: str) -> bool:
    if risk_tolerance_level == "low":
        return score >= 30
    if risk_tolerance_level == "medium":
        return score >= 60
    return score >= 80


def run_compliance_workflow_suite() -> Dict[str, Any]:
    tests: List[Dict[str, Any]] = [
        {
            "name": "compliance_valid_privacy_low_tolerance",
            "params": {
                "document_text": (
                    "Our company collects customer emails and shares them with third-party marketing vendors "
                    "without providing opt-out controls. Data retention is indefinite and there is no documented "
                    "deletion policy."
                ),
                "policy_domain": "privacy",
                "risk_tolerance_level": "low",
            },
            "expect": {
                "should_error": False,
                "risk_tolerance_level": "low",
            },
        },
        {
            "name": "compliance_short_document_rejected_by_router_contract",
            "params": {
                "document_text": "Short policy.",
                "policy_domain": "privacy",
                "risk_tolerance_level": "low",
            },
            "expect": {"should_error": True},
        },
        {
            "name": "compliance_invalid_risk_tolerance_level",
            "params": {
                "document_text": (
                    "We share customer emails with partners for marketing. There is no opt-out mechanism."
                ),
                "policy_domain": "privacy",
                "risk_tolerance_level": "extreme",
            },
            "expect": {"should_error": True},
        },
    ]

    results: List[Dict[str, Any]] = []
    passed = 0

    for t in tests:
        name = t["name"]
        params = t["params"]
        expect = t["expect"]

        try:
            out = compliance_policy_review(params)
            has_error = isinstance(out, dict) and ("error" in out)

            if expect.get("should_error"):
                ok = has_error
                results.append(
                    {"test": name, "ok": ok, "error": out.get("error") if has_error else None}
                )
                if ok:
                    passed += 1
                continue

            try:
                validated = CompliancePolicyReviewResult(**out)
            except ValidationError as ve:
                results.append(
                    {
                        "test": name,
                        "ok": False,
                        "error": "schema_validation_failed",
                        "details": ve.errors(),
                    }
                )
                continue

            score = int(validated.risk_score)
            expected_level = _risk_level_from_score(score)
            expected_escalation = _escalation_from_threshold(
                score, expect.get("risk_tolerance_level", "low")
            )

            level_ok = (validated.risk_level == expected_level)
            escalation_ok = (validated.escalation_required == expected_escalation)

            quotes_ok = True
            for v in validated.violations_detected:
                if '"' not in v:
                    quotes_ok = False
                    break

            ok = (not has_error) and level_ok and escalation_ok and quotes_ok

            results.append(
                {
                    "test": name,
                    "ok": ok,
                    "risk_score": validated.risk_score,
                    "risk_level": validated.risk_level,
                    "expected_risk_level": expected_level,
                    "escalation_required": validated.escalation_required,
                    "expected_escalation_required": expected_escalation,
                    "violations_count": len(validated.violations_detected),
                    "quotes_ok": quotes_ok,
                }
            )

            if ok:
                passed += 1

        except Exception as e:
            results.append(
                {
                    "test": name,
                    "ok": False,
                    "error_type": e.__class__.__name__,
                    "error": str(e)[:300],
                }
            )

    return {
        "suite": "workflow_execution_compliance",
        "passed": passed,
        "total": len(tests),
        "results": results,
    }


def run_vendor_workflow_suite() -> Dict[str, Any]:
    """
    Vendor workflow evaluator:
    - Calls vendor_risk_intake directly (stub v1)
    - Asserts schema validity
    - Asserts basic invariants (score bounds, risk_level validity)
    """
    tests: List[Dict[str, Any]] = [
        {
            "name": "vendor_valid_stub",
            "params": {
                "vendor_name": "Acme Payments",
                "vendor_description": (
                    "A third-party payments processor that stores customer names, emails, and partial card metadata "
                    "and provides a web dashboard for operations teams."
                ),
                "data_types": ["PII", "payment_metadata"],
                "access_level": "high",
                "criticality": "high",
                "notes": "Handles sensitive customer data and supports admin dashboard access.",
            },
            "expect": {"should_error": False},
        }
    ]

    results: List[Dict[str, Any]] = []
    passed = 0

    for t in tests:
        name = t["name"]
        params = t["params"]
        expect = t["expect"]

        try:
            out = vendor_risk_intake(params)
            has_error = isinstance(out, dict) and ("error" in out)

            if expect.get("should_error"):
                ok = has_error
                results.append(
                    {"test": name, "ok": ok, "error": out.get("error") if has_error else None}
                )
                if ok:
                    passed += 1
                continue

            try:
                validated = VendorRiskIntakeResult(**out)
            except ValidationError as ve:
                results.append(
                    {
                        "test": name,
                        "ok": False,
                        "error": "schema_validation_failed",
                        "details": ve.errors(),
                    }
                )
                continue

            score_ok = (0 <= int(validated.risk_score) <= 100)
            level_ok = validated.risk_level in {"low", "medium", "high"}
            lists_ok = isinstance(validated.required_controls, list) and isinstance(
                validated.due_diligence_questions, list
            )

            ok = (not has_error) and score_ok and level_ok and lists_ok

            results.append(
                {
                    "test": name,
                    "ok": ok,
                    "risk_score": validated.risk_score,
                    "risk_level": validated.risk_level,
                    "required_controls_count": len(validated.required_controls),
                    "questions_count": len(validated.due_diligence_questions),
                }
            )

            if ok:
                passed += 1

        except Exception as e:
            results.append(
                {
                    "test": name,
                    "ok": False,
                    "error_type": e.__class__.__name__,
                    "error": str(e)[:300],
                }
            )

    return {
        "suite": "workflow_execution_vendor_risk",
        "passed": passed,
        "total": len(tests),
        "results": results,
    }

def run_financial_workflow_suite() -> Dict[str, Any]:
    tests: List[Dict[str, Any]] = [
        {
            "name": "finance_valid_anomaly_low_tolerance",
            "params": {
                "period": "2026-01",
                "risk_tolerance_level": "low",
                "transactions": [
                    {
                        "id": "txn_001",
                        "amount": 120.55,
                        "currency": "USD",
                        "counterparty": "Coffee Shop",
                        "description": "Team coffee",
                        "timestamp": "2026-01-03T10:00:00Z",
                    },
                    {
                        "id": "txn_002",
                        "amount": 95000,
                        "currency": "USD",
                        "counterparty": "XYZ LLC",
                        "description": "Wire transfer",
                        "timestamp": "2026-01-14T12:45:00Z",
                    },
                    {
                        "id": "txn_003",
                        "amount": 95000,
                        "currency": "USD",
                        "counterparty": "XYZ LLC",
                        "description": "Wire transfer",
                        "timestamp": "2026-01-14T12:46:00Z",
                    },
                ],
                "notes": "Look for large wires and duplicates.",
            },
            "expect": {"should_error": False, "risk_tolerance_level": "low"},
        },
        {
            "name": "finance_missing_transactions_rejected",
            "params": {"period": "2026-01", "risk_tolerance_level": "low"},
            "expect": {"should_error": True},
        },
    ]

    results: List[Dict[str, Any]] = []
    passed = 0

    for t in tests:
        name = t["name"]
        params = t["params"]
        expect = t["expect"]

        try:
            out = financial_anomaly_summary(params)
            has_error = isinstance(out, dict) and ("error" in out)

            if expect.get("should_error"):
                ok = has_error
                results.append({"test": name, "ok": ok, "error": out.get("error") if has_error else None})
                if ok:
                    passed += 1
                continue

            try:
                validated = FinancialAnomalySummaryResult(**out)
            except ValidationError as ve:
                results.append({"test": name, "ok": False, "error": "schema_validation_failed", "details": ve.errors()})
                continue

            # invariants: level matches score mapping + escalation matches tolerance thresholds
            score = int(validated.anomaly_score)
            expected_level = _risk_level_from_score(score)  # reuse existing mapping helper
            expected_escalation = _escalation_from_threshold(score, expect.get("risk_tolerance_level", "low"))

            level_ok = (validated.anomaly_level == expected_level)
            escalation_ok = (validated.escalation_required == expected_escalation)

            # quote rule for flagged txns
            quotes_ok = True
            for f in validated.flagged_transactions:
                if '"' not in f:
                    quotes_ok = False
                    break

            ok = (not has_error) and level_ok and escalation_ok and quotes_ok

            results.append(
                {
                    "test": name,
                    "ok": ok,
                    "anomaly_score": validated.anomaly_score,
                    "anomaly_level": validated.anomaly_level,
                    "expected_anomaly_level": expected_level,
                    "escalation_required": validated.escalation_required,
                    "expected_escalation_required": expected_escalation,
                    "flagged_count": len(validated.flagged_transactions),
                    "quotes_ok": quotes_ok,
                }
            )

            if ok:
                passed += 1

        except Exception as e:
            results.append({"test": name, "ok": False, "error_type": e.__class__.__name__, "error": str(e)[:300]})

    return {
        "suite": "workflow_execution_financial_anomaly",
        "passed": passed,
        "total": len(tests),
        "results": results,
    }

def run_all_workflow_suites() -> Dict[str, Any]:
    suites = [run_compliance_workflow_suite(), run_vendor_workflow_suite(), run_financial_workflow_suite()]
    return {
        "suite": "workflow_execution_all",
        "passed": sum(s["passed"] for s in suites),
        "total": sum(s["total"] for s in suites),
        "suites": suites,
    }