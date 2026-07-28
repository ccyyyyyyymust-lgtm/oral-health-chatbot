from typing import Literal

from pydantic import BaseModel, Field, model_validator


Region = Literal[
    "England",
    "Wales",
    "Scotland",
    "Northern Ireland",
    "Not sure",
]
AgeGroup = Literal["Not provided", "0-3", "3-6", "7+"]
Category = Literal["general", "brushing", "toothache", "urgent"]


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2_000)


class ChatRequest(BaseModel):
    # `message` remains supported for older clients. New clients send `messages`.
    message: str | None = Field(default=None, min_length=1, max_length=500)
    messages: list[ConversationMessage] = Field(default_factory=list, max_length=12)
    region: Region = "Not sure"
    age_group: AgeGroup = "Not provided"

    @model_validator(mode="after")
    def require_user_message(self) -> "ChatRequest":
        if self.message:
            return self
        if self.messages and self.messages[-1].role == "user":
            return self
        raise ValueError("Provide message or end messages with a user message.")

    def latest_message(self) -> str:
        if self.messages:
            return self.messages[-1].content
        return self.message or ""

    def conversation(self) -> list[ConversationMessage]:
        if self.messages:
            return self.messages
        return [ConversationMessage(role="user", content=self.message or "")]


class SourceLink(BaseModel):
    title: str
    url: str


class ChatResponse(BaseModel):
    reply: str
    category: Category
    urgent: bool
    region: Region
    age_group: AgeGroup
    needs_age_group: bool = False
    source_gap: bool = False
    sources: list[SourceLink] = Field(default_factory=list)
    response_mode: Literal["safety", "llm", "fallback"] = "fallback"

