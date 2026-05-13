from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RoleConfig(BaseModel):
    role_id: str = "default"
    name: str = "默认角色"
    system_prompt: str = ""
    personality: str = "自然、友好、不过度热情"
    language_style: str = "简洁、口语化"
    expertise: str = ""
    constraints: list[str] = Field(default_factory=list)
    example_replies: list[str] = Field(default_factory=list)


class InboundMessage(BaseModel):
    contact_id: str
    contact_name: str | None = None
    sender_id: str | None = None
    sender_name: str | None = None
    timestamp: int | None = None
    content: str
    platform_message_id: str | None = None
    raw: dict[str, Any] | None = None


class OutboundMessage(BaseModel):
    contact_id: str
    content: str


class RestoreBackupRequest(BaseModel):
    path: str


class CandidateReply(BaseModel):
    content: str


class CandidateResult(BaseModel):
    contact_id: str
    platform_message_id: str | None = None
    generated_at: datetime
    role_id: str
    candidates: list[CandidateReply]


class ChatEvent(BaseModel):
    event_id: str
    contact_id: str
    contact_name: str | None = None
    timestamp: int
    sender: str
    sender_name: str | None = None
    direction: str
    content: str
    platform_message_id: str | None = None
    ai_candidates: list[str] | None = None
    meta: dict[str, Any] | None = None
