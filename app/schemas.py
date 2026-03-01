from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any

class UserRequest(BaseModel):
    message: str

class User(BaseModel):
    user_id: str
    role: str

class SystemResponse(BaseModel):
    trace_id: str
    workflow: str
    result: Dict[str, Any]

class CompliancePolicyReviewParameters(BaseModel):
    document_text: str = Field(..., min_length=50)
    policy_domain: str = Field(..., min_length=2)
    risk_tolerance_level: Literal["low", "medium", "high"]
    document_title: Optional[str] = None


class CompliancePolicyReviewResult(BaseModel):
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: Literal["low", "medium", "high"]
    violations_detected: List[str]
    escalation_required: bool
    summary: str = Field(..., min_length=10)

class WorkflowError(BaseModel):
    status: Literal["rejected"] = "rejected"
    error: str
    details: List[Dict[str, Any]]

class VendorRiskIntakeParameters(BaseModel):
    vendor_name: str = Field(..., min_length=2)
    vendor_description: str = Field(..., min_length=50)
    data_types: List[str] = Field(default_factory=list)
    access_level: Literal["low", "medium", "high"]
    criticality: Literal["low", "medium", "high"]
    notes: Optional[str] = None

class VendorRiskIntakeResult(BaseModel):
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: Literal["low", "medium", "high"]
    required_controls: List[str]
    due_diligence_questions: List[str]
    escalation_required: bool
    summary: str = Field(..., min_length=10)

class FinancialAnomalySummaryParameters(BaseModel):
    period: str = Field(..., min_length=4)  # e.g. "2026-01" or "2026-Q1"
    transactions: List[Dict[str, Any]] = Field(..., min_length=1)
    risk_tolerance_level: Literal["low", "medium", "high"]
    currency: Optional[str] = "USD"
    notes: Optional[str] = None


class FinancialAnomalySummaryResult(BaseModel):
    anomaly_score: int = Field(..., ge=0, le=100)
    anomaly_level: Literal["low", "medium", "high"]
    flagged_transactions: List[str]
    escalation_required: bool
    summary: str = Field(..., min_length=10)