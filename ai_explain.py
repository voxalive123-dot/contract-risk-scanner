from __future__ import annotations

import json
import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
AI_BOUNDARY_NOTICE = (
    "This AI explanation is not legal advice, legal opinion, contract approval, "
    "or a guarantee that a contract is safe."
)


class AIExplainFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str | None = None
    title: str | None = None
    category: str | None = None
    severity: int | None = None
    rationale: str | None = None
    matched_text: str | None = None


class AIExplainTopRisk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str | None = None
    title: str | None = None
    category: str | None = None
    severity: int | None = None
    weight: int | None = None


class AIExplainMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidence: float | None = None
    top_risks: list[AIExplainTopRisk] = Field(default_factory=list)
    matched_rule_count: int | None = None
    suppressed_rule_count: int | None = None
    contradiction_count: int | None = None


class AIExplainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_score: int
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    flags: list[str] = Field(default_factory=list)
    findings: list[AIExplainFinding] = Field(default_factory=list)
    meta: AIExplainMeta
    source_type: str | None = None
    extraction_method: str | None = None
    confidence_hint: float | None = None
    has_extractable_text: bool | None = None


class AIEvidenceNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    title: str
    explanation: str
    evidence_excerpt: str


class AISummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overview: str
    risk_posture_summary: str
    negotiation_focus: list[str] = Field(default_factory=list)
    evidence_notes: list[AIEvidenceNote] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)
    boundary_notice: str


class AIExplainAvailableResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available"]
    model: str
    ai_summary: AISummary


class AIProviderError(Exception):
    pass


def openai_api_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def get_openai_model() -> str:
    configured = os.getenv("OPENAI_MODEL", "").strip()
    return configured or DEFAULT_OPENAI_MODEL


def _merge_unique(items: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = (item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return merged


def _sanitize_request(request: AIExplainRequest) -> dict[str, Any]:
    return request.model_dump(mode="json")


def _build_uncertainty_notes(request: AIExplainRequest) -> list[str]:
    notes: list[str] = []

    confidence = request.meta.confidence
    confidence_hint = request.confidence_hint
    findings_count = len(request.findings)
    matched_count = request.meta.matched_rule_count or findings_count

    if confidence is None or confidence < 0.55:
        notes.append(
            "Deterministic confidence is limited, so this explanation should be treated as cautious review support rather than a strong conclusion."
        )

    if findings_count == 0 or matched_count == 0:
        notes.append(
            "Few or no deterministic findings were supplied, so the explanation should be read as low-signal context rather than a strong risk narrative."
        )
    elif findings_count <= 1:
        notes.append(
            "Only a small number of deterministic findings were supplied, so the explanation may not reflect the full commercial context of the agreement."
        )

    if request.source_type in {"pdf", "image"}:
        if request.has_extractable_text is False:
            notes.append(
                "Source extraction appears limited, which may reduce the completeness of the evidence available for explanation."
            )
        if confidence_hint is None or confidence_hint < 0.7:
            notes.append(
                "OCR or document extraction quality appears limited, so evidence should be checked against the source file before relying on the explanation."
            )
        if request.extraction_method and request.extraction_method.lower() != "direct":
            notes.append(
                "The source did not use a clean direct-text path, so wording and clause capture may be incomplete."
            )

    if (request.meta.contradiction_count or 0) > 0:
        notes.append(
            "The deterministic scan detected conflicting or offsetting signals, so the explanation should be read alongside the underlying findings rather than as a settled conclusion."
        )

    return _merge_unique(notes)


def _build_messages(
    payload: dict[str, Any],
    uncertainty_notes: list[str],
) -> list[dict[str, str]]:
    system_prompt = (
        "You are generating a VoxaRisk AI explanation layer. "
        "You must augment deterministic findings only. "
        "Do not change, recalculate, reinterpret, or override risk_score, severity, flags, findings, top_risks, or confidence. "
        "Do not invent risks, clauses, or evidence. "
        "Do not provide legal advice, legal opinion, contract approval, or any guarantee of safety. "
        "Use only the supplied deterministic findings and matched evidence. "
        "If evidence is limited, findings are sparse, or confidence is weak, say so plainly. "
        "Return JSON only with keys: overview, risk_posture_summary, negotiation_focus, evidence_notes, uncertainty_notes, boundary_notice. "
        "boundary_notice must state that this is not legal advice, legal opinion, contract approval, or a guarantee that a contract is safe."
    )

    user_payload = {
        "deterministic_analysis": payload,
        "required_uncertainty_notes": uncertainty_notes,
        "boundary_notice": AI_BOUNDARY_NOTICE,
    }

    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "Create a concise executive explanation grounded only in this deterministic VoxaRisk analysis.\n"
                + json.dumps(user_payload, ensure_ascii=True)
            ),
        },
    ]


def _extract_completion_text(completion: Any) -> str:
    choices = getattr(completion, "choices", None)
    if not choices:
        raise AIProviderError("Missing completion choices")

    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)

    if not content:
        raise AIProviderError("Missing completion content")

    return content


def _call_openai_json(
    payload: dict[str, Any],
    *,
    model: str,
    uncertainty_notes: list[str],
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise AIProviderError("OPENAI_API_KEY missing")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AIProviderError("OpenAI SDK not installed") from exc

    client = OpenAI(api_key=api_key)
    messages = _build_messages(payload, uncertainty_notes)

    try:
        completion = client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=messages,
        )
    except Exception as exc:  # pragma: no cover - exercised via mocked failure path
        raise AIProviderError("OpenAI provider call failed") from exc

    raw_content = _extract_completion_text(completion)

    try:
        return json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise AIProviderError("Provider did not return valid JSON") from exc


def generate_ai_explanation(request: AIExplainRequest) -> AIExplainAvailableResponse:
    payload = _sanitize_request(request)
    uncertainty_notes = _build_uncertainty_notes(request)
    model = get_openai_model()

    provider_payload = _call_openai_json(
        payload,
        model=model,
        uncertainty_notes=uncertainty_notes,
    )

    try:
        summary = AISummary.model_validate(provider_payload)
    except ValidationError as exc:
        raise AIProviderError("Provider output failed schema validation") from exc

    allowed_by_rule_id = {
        finding.rule_id: finding
        for finding in request.findings
        if finding.rule_id
    }

    validated_notes: list[AIEvidenceNote] = []
    for note in summary.evidence_notes:
        deterministic_finding = allowed_by_rule_id.get(note.rule_id)
        if deterministic_finding is None:
            raise AIProviderError("Provider referenced unknown rule_id")

        excerpt = (note.evidence_excerpt or "").strip()
        deterministic_excerpt = (deterministic_finding.matched_text or "").strip()
        if not excerpt:
            excerpt = deterministic_excerpt
        if excerpt and deterministic_excerpt and excerpt not in deterministic_excerpt and deterministic_excerpt not in excerpt:
            raise AIProviderError("Provider evidence note was not anchored to deterministic excerpt")

        validated_notes.append(
            AIEvidenceNote(
                rule_id=note.rule_id,
                title=note.title,
                explanation=note.explanation,
                evidence_excerpt=excerpt,
            )
        )

    summary.evidence_notes = validated_notes
    summary.uncertainty_notes = _merge_unique(uncertainty_notes + summary.uncertainty_notes)
    summary.boundary_notice = AI_BOUNDARY_NOTICE

    return AIExplainAvailableResponse(
        status="available",
        model=model,
        ai_summary=summary,
    )
