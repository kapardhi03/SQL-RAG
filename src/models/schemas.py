from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class ToolCall(TypedDict):
    name: str
    args: dict[str, Any]
    id: str | None

    def __str__(self):
        return f"{self.name} ({self.args})"


class ChatMessage(BaseModel):
    role: Literal["user", "ai", "tool"] = Field(description="Role of the message")
    content: str = Field(description="Content of the message")
    tool_calls: list[ToolCall] = Field(
        description="Tool calls in the message.",
        default=[],
    )
    tool_call_id: Optional[str] = Field(
        default=None,
        description="Tool call that this message is responding to.",
    )
    run_id: Optional[str] = Field(default=None, description="Thread ID")

    def __str__(self):
        toolcalls = "\n".join(str(toolcall) for toolcall in self.tool_calls)
        return f"{self.role}: {self.content}" + ("\n" + toolcalls if toolcalls else "")


class UserInput(BaseModel):
    message: str = Field(description="User's input")
    model: str = Field(description="Model to use")
    thread_id: Optional[str] = Field(description="Thread ID")


class StreamInput(UserInput):
    stream_tokens: bool = Field(
        description="Whether to stream LLM tokens to the client.",
        default=True,
    )
