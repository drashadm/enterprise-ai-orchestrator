import json
import os
from typing import Any, Dict

from openai import OpenAI

# --- System prompt (enterprise decision engine) ---
SYSTEM_PROMPT = """
You are an enterprise AI orchestration decision engine.

OUTPUT RULES
- Return VALID JSON only. No markdown. No extra text.
- Use schema_version "1.0".
- Choose exactly ONE workflow from the allowed list OR use "needs_clarification" when required info is missing OR "unsupported" when none apply.
- Never invent user data. If a required parameter is not provided, do NOT guess it.
- Only include parameters defined for the selected workflow. No extra parameter keys.
- Confidence must be a number from 0.0 to 1.0.
- If workflow != "needs_clarification", missing_fields MUST be [].

ALLOWED WORKFLOWS
- generate_risk_report
- generate_financial_report
- sync_client
- compliance_policy_review
- vendor_risk_intake
- financial_anomaly_summary
- needs_clarification
- unsupported

PARAMETER REQUIREMENTS
1) sync_client
   Required: client_id (string or int)
   Optional: fields_to_update (object), source (string)

2) generate_financial_report
   Required: client_id (string or int), period (string; e.g., "2026-Q1" or "2026-01")
   Optional: report_type (string), currency (string)

3) generate_risk_report
   Required: client_id (string or int), risk_domain (string; e.g., "credit", "vendor", "cyber", "aml")
   Optional: as_of_date (ISO8601 date), notes (string)

4) compliance_policy_review
   Required: document_text (string), policy_domain (string), risk_tolerance_level (string; "low"|"medium"|"high")
   Optional: document_title (string)

5) vendor_risk_intake
   Required: vendor_name (string), vendor_description (string), access_level (string; "low"|"medium"|"high"), criticality (string; "low"|"medium"|"high")
   Optional: data_types (array of strings), notes (string)

6) financial_anomaly_summary
   Required: period (string), risk_tolerance_level (string; "low"|"medium"|"high"), transactions (array of objects)
   Optional: currency (string), notes (string)

RESPONSE FORMAT (JSON ONLY)
{
  "schema_version": "1.0",
  "workflow": "<workflow_name>",
  "parameters": { ... },
  "confidence": <0.0-1.0>,
  "rationale": "<one sentence max>",
  "missing_fields": [ ... ]
}

GUIDANCE
- If the user intent is unclear or required fields are missing: set workflow="needs_clarification", list missing_fields, and set parameters={} (empty).
- If the request does not match any workflow: set workflow="unsupported" and explain briefly in rationale.
- If the user provides key=value pairs or "field: value" text, extract those into parameters when they match a workflow's required/optional fields.
""".strip()


ALLOWED_WORKFLOWS = {
    "generate_risk_report",
    "generate_financial_report",
    "sync_client",
    "compliance_policy_review",
    "vendor_risk_intake",
    "financial_anomaly_summary",
    "needs_clarification",
    "unsupported",
}


def _clamp01(x: Any) -> float:
    try:
        v = float(x)
    except Exception:
        return 0.0
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _parse_json_strict(text: str) -> Dict[str, Any]:
    """
    Strict JSON parsing with a small safety shim in case the model wraps JSON in whitespace.
    We do NOT attempt aggressive extraction. If it's not JSON, it's an error.
    """
    text = (text or "").strip()
    return json.loads(text)


def interpret_request(message: str) -> Dict[str, Any]:
    """
    Returns a decision dict shaped like:
    {
      "schema_version": "1.0",
      "workflow": "...",
      "parameters": {...},
      "confidence": 0.0-1.0,
      "rationale": "...",
      "missing_fields": [...]
    }
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    client = OpenAI(api_key=api_key)

    # Force JSON-only output via response_format when available.
    # If your installed openai SDK/model doesn't support response_format, it will error;
    # in that case, remove response_format and rely on the prompt rules.
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        response_format={"type": "json_object"},
    )

    content = resp.choices[0].message.content
    decision = _parse_json_strict(content)

    # --- Validate minimally to protect router ---
    schema_version = str(decision.get("schema_version", "")).strip()
    workflow = str(decision.get("workflow", "")).strip()
    parameters = decision.get("parameters", {})
    rationale = str(decision.get("rationale", "")).strip()
    missing_fields = decision.get("missing_fields", [])
    confidence = _clamp01(decision.get("confidence", 0.0))

    if schema_version != "1.0":
        raise ValueError("Invalid schema_version returned by LLM")

    if workflow not in ALLOWED_WORKFLOWS:
        raise ValueError(f"Invalid workflow returned by LLM: {workflow}")

    if not isinstance(parameters, dict):
        raise ValueError("parameters must be an object")

    if not isinstance(missing_fields, list):
        raise ValueError("missing_fields must be a list")

    # Enforce the prompt contract strictly
    if workflow != "needs_clarification" and len(missing_fields) != 0:
        # normalize to strict contract
        missing_fields = []

    # Write back normalized fields
    decision["schema_version"] = "1.0"
    decision["workflow"] = workflow
    decision["parameters"] = parameters
    decision["confidence"] = confidence
    decision["rationale"] = rationale[:200]
    decision["missing_fields"] = missing_fields

    return decision