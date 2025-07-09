import os
from typing import Union

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from config import settings

models: dict[str, Union[BaseChatModel]] = {}

# OpenAI API
if settings.OPENAI_API_KEY:
    models["gpt-4o-mini"] = ChatOpenAI(
        model="gpt-4o-mini", temperature=0, streaming=True, stream_usage=True
    )
    models["gpt-4o"] = ChatOpenAI(
        model="gpt-4o", temperature=0, streaming=True, stream_usage=True
    )

# OpenAI API with Azure
if settings.AZURE_GPT_ENDPOINT and settings.AZURE_GPT_KEY:
    models["azure-gpt-4o"] = AzureChatOpenAI(
        api_version="2025-01-01-preview",
        azure_endpoint=settings.AZURE_GPT_ENDPOINT,
        api_key=settings.AZURE_GPT_KEY,
        model="gpt-4o",
    )

    models["azure-gpt-4o-mini"] = AzureChatOpenAI(
        api_version="2025-01-01-preview",
        azure_endpoint=settings.AZURE_GPT_ENDPOINT,
        api_key=settings.AZURE_GPT_KEY,
        model="gpt-4o-mini",
    )

# Anthropic API
if settings.ANTHROPIC_API_KEY:
    models["claude-3-haiku"] = ChatAnthropic(
        model="claude-3-haiku-20240307",
        temperature=0,
        streaming=True,
        stream_usage=True,
    )
    models["claude-3-sonnet"] = ChatAnthropic(
        model="claude-3-5-sonnet-latest",
        temperature=0,
        streaming=True,
        stream_usage=True,
    )

# Google API
if settings.GOOGLE_API_KEY:
    models["gemini-2.5-flash"] = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-001", temperature=0, streaming=True, stream_usage=True
    )
    models["gemini-2.0-flash"] = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-preview-04-17",
        temperature=0,
        streaming=True,
        stream_usage=True,
    )

# if none of the models are available, exit
if not models:
    print(
        "No LLM available. Please set environment variables to enable at least one LLM."
    )
    if os.getenv("MODE") == "dev":
        print("FastAPI initialization failed. Please use Ctrl + C to exit uvicorn.")
    exit(1)
