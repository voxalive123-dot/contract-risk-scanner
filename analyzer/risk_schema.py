from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RiskRule(BaseModel):
    id: str
    category: str
    title: str
    severity: int = Field(ge=1, le=5)
    weight: int = Field(ge=1)
    rationale: str
    patterns: List[str]
    negative_patterns: List[str] = Field(default_factory=list)
    min_matches: int = Field(default=1, ge=1)
    max_span_chars: int = Field(default=120, ge=1)
    tags: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @field_validator("id", "category", "title", "rationale")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("must be a string")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned

    @field_validator("patterns")
    @classmethod
    def validate_patterns(cls, value: List[str]) -> List[str]:
        if not isinstance(value, list):
            raise ValueError("patterns must be a list")
        if not value:
            raise ValueError("patterns must not be empty")
        cleaned: List[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("all patterns must be strings")
            item_clean = item.strip()
            if not item_clean:
                raise ValueError("patterns must not contain empty strings")
            cleaned.append(item_clean)
        return cleaned

    @field_validator("negative_patterns", "tags")
    @classmethod
    def validate_string_lists(cls, value: List[str]) -> List[str]:
        if not isinstance(value, list):
            raise ValueError("must be a list")
        cleaned: List[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("all items must be strings")
            item_clean = item.strip()
            if not item_clean:
                raise ValueError("list items must not be empty")
            cleaned.append(item_clean)
        return cleaned
