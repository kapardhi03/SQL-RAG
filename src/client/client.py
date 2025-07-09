import json
from typing import AsyncGenerator
from uuid import uuid4

import httpx

from models.schemas import ChatMessage, StreamInput


# Client is created from the streamlit UI and it is used to interact and stream data from the server
class Client:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
    ):
        self.base_url = base_url
        self.thread_id = str(uuid4())
        self.headers = {
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        }

    # Send a message to the server and stream the response
    # response is a stream of ChatMessages or strings
    async def astream(
        self,
        message: str,
        model: str,
        stream_tokens: bool = True,
        timeout: int = 60,
    ) -> AsyncGenerator[ChatMessage | str, None]:
        request = StreamInput(
            message=message,
            model=model,
            thread_id=self.thread_id,
            stream_tokens=stream_tokens,
        )

        # Asynchronously stream data from the server
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/stream",
                json=request.model_dump(),
                headers=self.headers,
            ) as response:
                if response.status_code != 200:
                    raise Exception(
                        f"Error: {response.status_code} - {await response.aread()}"
                    )

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        parsed = self.parse_stream_line(line)
                        if parsed is None:
                            break
                        yield parsed
                    except Exception as e:
                        print(f"Error parsing message: {e}, raw: {line}")

    def parse_stream_line(self, line: str) -> ChatMessage | str | None:
        # The data from server comes in a specific format
        # The first line is always "data: "
        line = line.strip()
        prefix = "data: "
        if line.startswith(prefix):
            line = line[len(prefix) :]
            if line == "DONE!":
                return None
            try:
                parsed = json.loads(line)
            except Exception as e:
                raise Exception(
                    f"Error JSON parsing message from server: {e}, raw data: {line}"
                )

            if parsed["status"]:
                return ChatMessage.model_validate(parsed["data"])
            else:
                raise Exception(f"Error: {e}, content: {parsed['data']}")
        return None


# async def main():
#     client = Client()
#     async for msg in client.astream("what are dairy products", "gemini-2.0-flash"):
#         print(msg)

# if __name__ == "__main__":
#     import asyncio

#     asyncio.run(main())
