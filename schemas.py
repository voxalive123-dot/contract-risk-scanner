from pydantic import BaseModel
from typing import List, Dict, Any


class AnalyzeRequest(BaseModel):
    text: str


class Finding(BaseModel):
    rule_id: str
    message: str
    severity: str


class AnalyzeResponse(BaseModel):
    request_id: str
    risk_score: int
    risk_density: float
    confidence: float
    ruleset_version: str
    findings: List[Dict[str, Any]]
    meta: Dict[str, Any]
