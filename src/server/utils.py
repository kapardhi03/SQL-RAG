from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from models.schemas import ChatMessage


def langchain_to_chat_message(message: BaseMessage, run_id: str) -> ChatMessage:
    """Create a ChatMessage from a LangChain message."""
    match message:
        case HumanMessage():
            human_message = ChatMessage(
                role="user",
                content=message.content,
                run_id=run_id,
            )
            return human_message

        case AIMessage():
            ai_message = ChatMessage(
                role="ai",
                content=message.content,
                run_id=run_id,
            )
            if message.tool_calls:
                ai_message.tool_calls = message.tool_calls
            return ai_message

        case ToolMessage():
            tool_message = ChatMessage(
                role="tool",
                content=message.content,
                tool_call_id=message.tool_call_id,
                run_id=run_id,
            )
            return tool_message

        case _:
            raise ValueError(f"Unknown message type: {type(message)}")
