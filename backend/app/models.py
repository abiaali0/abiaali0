from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class Rule(BaseModel):
    attribute: str = Field(min_length=1, max_length=80)
    operator: Literal["equals", "in", "starts_with"] = "equals"
    value: str = Field(min_length=1, max_length=250)
    enabled: bool = True


class FlagCreate(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,63}$")
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=300)
    environment: Literal["development", "staging", "production"] = "development"
    enabled: bool = False
    rollout: float = Field(default=0, ge=0, le=100)
    rules: list[Rule] = []


class FlagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=300)
    enabled: bool | None = None
    rollout: float | None = Field(default=None, ge=0, le=100)
    rules: list[Rule] | None = None


class EvaluationRequest(BaseModel):
    flag_key: str
    user_id: str = Field(min_length=1, max_length=150)
    attributes: dict[str, Any] = {}


class EvaluationResult(BaseModel):
    flag_key: str
    user_id: str
    enabled: bool
    reason: str
    environment: str
