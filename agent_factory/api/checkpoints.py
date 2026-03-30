from __future__ import annotations

from pydantic import BaseModel, Field


class CheckpointDecision(BaseModel):
    decision: str = Field(description="retry | degrade | abort")
    notes: str = ""


class CheckpointPreview(BaseModel):
    checkpoint: str
    payload: dict
