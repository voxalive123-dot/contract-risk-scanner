from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
logger = logging.getLogger("voxarisk.ai_explain")
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

    normalized_score: int | None = None
    risk_score: int | None = Field(default=None, exclude=True)
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    flags: list[str] = Field(default_factory=list)
    findings: list[AIExplainFinding] = Field(default_factory=list)
    meta: AIExplainMeta
    source_type: str | None = None
    extraction_method: str | None = None
    confidence_hint: float | None = None
    has_extractable_text: bool | None = None

    @model_validator(mode="after")
    def ensure_normalized_score(self):
        if self.normalized_score is None:
            if self.risk_score is None:
                raise ValueError("normalized_score is required")
            self.normalized_score = self.risk_score
        return self


class AIEvidenceNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    title: str
    explanation: str
    evidence_excerpt: str


class AISummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executive_overview: str = ""
    primary_risk_drivers: list[str] = Field(default_factory=list)
    recommended_review_focus: list[str] = Field(default_factory=list)
    evidence_signals: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)
    boundary_note: str = ""


class AIExplainAvailableResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available"]
    model: str
    source: Literal["ai"] = "ai"
    ai_summary: str


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
    normalized_score = payload.get("normalized_score")
    system_prompt = (
        "You are generating a VoxaRisk AI explanation layer as a board-level commercial briefing. "
        "You must augment deterministic findings only. "
        "Do not change, recalculate, reinterpret, or override normalized_score, severity, flags, findings, top_risks, or confidence. "
        "Only discuss the supplied normalized_score; do not refer to any other score field, internal score, uncalibrated score, or alternate score value. "
        f"If referring to score, use exactly: normalized exposure score of {normalized_score}. "
        "You may also use qualitative wording such as elevated risk posture or high risk posture. "
        "Do not invent risks, clauses, or evidence. "
        "For evidence_signals, use only supplied deterministic findings and matched evidence. "
        "Do not provide legal advice, legal opinion, contract approval, or any guarantee of safety. "
        "If evidence is limited, findings are sparse, or confidence is weak, say so plainly. "
        "Return JSON only with keys: executive_overview, primary_risk_drivers, recommended_review_focus, evidence_signals, uncertainty_notes, boundary_note. "
        "primary_risk_drivers, recommended_review_focus, evidence_signals, and uncertainty_notes must be arrays of concise strings. "
        "boundary_note must state that this is not legal advice, legal opinion, contract approval, or a guarantee that a contract is safe."
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
                "Create a concise executive AI Review briefing grounded only in this deterministic VoxaRisk analysis. "
                "Use the normalized exposure score only, never a raw score.\n"
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
) -> dict[str, Any] | str:
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
    except json.JSONDecodeError:
        plain_text = raw_content.strip()
        if not plain_text:
            raise AIProviderError("Provider returned empty content")
        return plain_text


def _stringify_provider_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return "\n".join(
            item
            for item in (_stringify_provider_value(item) for item in value)
            if item
        ).strip()
    if isinstance(value, dict):
        preferred_keys = (
            "executive_overview",
            "primary_risk_drivers",
            "recommended_review_focus",
            "evidence_signals",
            "boundary_note",
            "overview",
            "risk_posture_summary",
            "summary",
            "explanation",
            "executive_summary",
            "review_notes",
            "content",
            "text",
            "negotiation_focus",
            "evidence_notes",
            "uncertainty_notes",
            "boundary_notice",
        )
        parts: list[str] = []
        used: set[str] = set()
        for key in preferred_keys:
            if key in value:
                text = _stringify_provider_value(value.get(key))
                if text:
                    parts.append(text)
                    used.add(key)
        for key, nested in value.items():
            if key in used:
                continue
            text = _stringify_provider_value(nested)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
    return ""


def _normalize_score_language(text: str, normalized_score: int) -> str:
    normalized = str(normalized_score)
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    cleaned: list[str] = []

    for chunk in chunks:
        item = chunk.strip()
        if not item:
            continue

        lower = item.lower()
        if (
            "risk_score" in lower
            or "raw score" in lower
            or "raw risk score" in lower
            or "unnormalised score" in lower
            or "unnormalized score" in lower
        ):
            continue

        if "score" in lower:
            numbers = [int(value) for value in re.findall(r"\b\d{1,3}\b", item)]
            if any(value != normalized_score for value in numbers):
                continue
            item = re.sub(r"\brisk score\b", "normalized exposure score", item, flags=re.IGNORECASE)
            item = re.sub(r"\bnormalized score\b", "normalized exposure score", item, flags=re.IGNORECASE)

        if normalized in item and "score" in item.lower() and "normalized exposure score" not in item.lower():
            item = re.sub(r"\bscore\b", "normalized exposure score", item, count=1, flags=re.IGNORECASE)

        cleaned.append(item)

    return "\n".join(cleaned).strip()


def _clean_score_list(items: list[str], normalized_score: int) -> list[str]:
    return _merge_unique(
        item
        for item in (_normalize_score_language(value, normalized_score) for value in items)
        if item
    )


def _join_briefing_parts(parts: list[str]) -> str:
    body = "\n\n".join(part.strip() for part in parts if part and part.strip()).strip()
    if not body:
        return ""
    if "not legal advice" not in body.lower():
        body = f"{body}\n\nBoundary note\n{AI_BOUNDARY_NOTICE}"
    return body.strip()


def _structured_summary_has_content(summary: AISummary) -> bool:
    if summary.executive_overview.strip():
        return True
    if any(item.strip() for item in summary.primary_risk_drivers):
        return True
    if any(item.strip() for item in summary.recommended_review_focus):
        return True
    if any(item.strip() for item in summary.evidence_signals):
        return True
    return False


def _format_structured_summary(summary: AISummary, normalized_score: int) -> str:
    overview = _normalize_score_language(summary.executive_overview, normalized_score)
    primary_risk_drivers = _clean_score_list(summary.primary_risk_drivers, normalized_score)
    recommended_review_focus = _clean_score_list(summary.recommended_review_focus, normalized_score)
    evidence_signals = _clean_score_list(summary.evidence_signals, normalized_score)
    uncertainty_notes = _clean_score_list(summary.uncertainty_notes, normalized_score)

    parts: list[str] = []
    if overview:
        parts.append(f"Executive overview\n{overview}")
    if primary_risk_drivers:
        parts.append("Primary risk drivers\n" + "\n".join(f"- {item}" for item in primary_risk_drivers))
    if recommended_review_focus:
        parts.append("Recommended review focus\n" + "\n".join(f"- {item}" for item in recommended_review_focus))
    if evidence_signals:
        parts.append("Evidence signals\n" + "\n".join(f"- {item}" for item in evidence_signals))
    if uncertainty_notes:
        parts.append("Uncertainty notes\n" + "\n".join(f"- {item}" for item in uncertainty_notes))
    parts.append(f"Boundary note\n{AI_BOUNDARY_NOTICE}")

    return _join_briefing_parts(parts)


def _plain_text_summary_from_provider_output(
    provider_output: dict[str, Any] | str,
    uncertainty_notes: list[str],
    normalized_score: int,
) -> str:
    text = _normalize_score_language(_stringify_provider_value(provider_output), normalized_score)
    if not text:
        raise AIProviderError("Provider returned empty content")

    parts = [text]
    cleaned_uncertainty = _clean_score_list(uncertainty_notes, normalized_score)
    if cleaned_uncertainty:
        parts.append("Uncertainty notes\n" + "\n".join(f"- {item}" for item in cleaned_uncertainty))
    parts.append(f"Boundary note\n{AI_BOUNDARY_NOTICE}")
    return _join_briefing_parts(parts)


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
    except ValidationError:
        logger.warning("AI provider output schema invalid; using plain-text fallback")
        return AIExplainAvailableResponse(
            status="available",
            model=model,
            ai_summary=_plain_text_summary_from_provider_output(
                provider_payload,
                uncertainty_notes,
                request.normalized_score,
            ),
        )

    if not _structured_summary_has_content(summary):
        logger.warning("AI provider output schema invalid; using plain-text fallback")
        return AIExplainAvailableResponse(
            status="available",
            model=model,
            ai_summary=_plain_text_summary_from_provider_output(
                provider_payload,
                uncertainty_notes,
                request.normalized_score,
            ),
        )

    summary.uncertainty_notes = _merge_unique(uncertainty_notes + summary.uncertainty_notes)
    summary.boundary_note = AI_BOUNDARY_NOTICE

    return AIExplainAvailableResponse(
        status="available",
        model=model,
        ai_summary=_format_structured_summary(summary, request.normalized_score),
    )
