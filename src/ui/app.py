import asyncio
import os
from typing import AsyncGenerator

import streamlit as st

from client.client import Client
from models.schemas import ChatMessage

APP_TITLE = "SQ-RAG"
WELCOME = "Hello! I am SQL-RAG. Ask me anything about the database."
PAGE_TITLE = "Chat with SQL"


def clear_conversation() -> None:
    st.session_state.messages = []
    st.session_state.client = None


async def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
    )

    models = {
        "OpenAI GPT-4o": "gpt-4o",
        "OpenAI GPT-4o-mini": "gpt-4o-mini",
        "AzureOpenAI GPT-4o": "azure-gpt-4o",
        "AzureOpenAI GPT-4o-mini": "azure-gpt-4o-mini",
        "Claude 3.5 Haiku": "claude-3-haiku",
        "Claude 3.5 Sonnet": "claude-3-sonnet",
        "Gemini 2.0 Flash": "gemini-2.0-flash",
        "Gemini 2.5 Flash Preview 04-17": "gemini-2.5-flash",
    }

    with st.sidebar:
        st.title(APP_TITLE)

        st.header("Settings")
        selected_model = st.radio(
            "**Choose an LLM**",
            list(models.keys()),
            index=0,
            label_visibility="visible",
        )
        if selected_model:
            st.session_state.selected_model = models[selected_model]

    if "client" not in st.session_state or st.session_state.client is None:
        clear_conversation()
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        st.session_state.client = Client(base_url=base_url)

    client: Client = st.session_state.client
    messages: list[ChatMessage] = st.session_state.messages
    model: str = st.session_state.selected_model

    st.title(PAGE_TITLE)

    if len(st.session_state.messages) == 0:
        with st.chat_message("ai"):
            st.write(WELCOME)

    st.button("", on_click=clear_conversation, icon=":material/restart_alt:")

    async def amessage_iter() -> AsyncGenerator[ChatMessage, None]:
        for m in messages:
            yield m

    await draw_messages(amessage_iter())

    if user_input := st.chat_input():
        messages.append(ChatMessage(role="user", content=user_input))
        st.chat_message("user").write(user_input)

        stream = client.astream(
            message=user_input.strip(),
            model=model,
        )
        await draw_messages(stream, is_new=True)
        st.rerun()


async def draw_messages(
    messages_generator: AsyncGenerator[ChatMessage | str, None], is_new: bool = False
) -> None:

    last_message_type = None
    st.session_state.last_message = None

    while msg := await anext(messages_generator, None):
        if isinstance(msg, str):
            st.write(msg)
            continue

        if not isinstance(msg, ChatMessage):
            st.error(f"Unexpected message type: {type(msg)}")
            st.write(msg)
            st.stop()

        match msg.role:
            case "user":
                last_message_type = "user"
                st.chat_message("user").write(msg.content)

            case "ai":
                if is_new:
                    st.session_state.messages.append(msg)

                if last_message_type != "ai":
                    last_message_type = "ai"
                    st.session_state.last_message = st.chat_message("ai")

                with st.session_state.last_message:
                    if msg.content:
                        st.write(msg.content)

                    if msg.tool_calls:
                        call_results = {}
                        for tool_call in msg.tool_calls:
                            status = st.status(
                                f"""Tool Call: {tool_call["name"]}""",
                                state="running" if is_new else "complete",
                            )
                            call_results[tool_call["id"]] = status
                            status.write("Input:")
                            status.write(tool_call["args"])

                        for _ in range(len(call_results)):
                            tool_result: ChatMessage = await anext(messages_generator)
                            if tool_result.role != "tool":
                                st.error(
                                    f"Unexpected ChatMessage type: {tool_result.role}"
                                )
                                st.write(tool_result)
                                st.stop()

                            if is_new:
                                st.session_state.messages.append(tool_result)
                            status = call_results[tool_result.tool_call_id]
                            status.write("Output:")
                            status.write(tool_result.content)
                            status.update(state="complete")


if __name__ == "__main__":
    asyncio.run(main())
