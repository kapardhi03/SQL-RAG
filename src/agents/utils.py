from typing import Any

from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import ChatMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.config import merge_configs
from pydantic import BaseModel, Field


# Given a list of rows, this converts them to a markdown table
# LLM understands markdown better than json, as the training data is in markdown
def convert_rows_to_markdown(rows):
    if not rows:
        return ""
    headers = rows[0].keys()
    markdown = "| " + " | ".join(headers) + " |\n"
    markdown += "| " + " | ".join("---" for _ in headers) + " |\n"
    for row in rows:
        markdown += "| " + " | ".join(str(row[h]) for h in headers) + " |\n"
    return markdown


# Custom event
class CustomData(BaseModel):
    "Custom data being sent by an agent"

    type: str = Field(
        description="The type of custom data, used in dispatch events",
        default="custom_data",
    )
    data: dict[str, Any] = Field(description="The custom data")

    def to_langchain(self) -> ChatMessage:
        return ChatMessage(content=[self.data], role="custom")

    async def adispatch(self, config: RunnableConfig | None = None) -> None:
        dispatch_config = RunnableConfig(
            tags=["custom_data_dispatch"],
        )
        await adispatch_custom_event(
            name=self.type,
            data=self.data,
            config=merge_configs(config, dispatch_config),
        )
