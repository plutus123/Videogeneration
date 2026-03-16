import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()


def get_azure_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
    )


def get_chat_deployment() -> str:
    return os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-5-nano")


def get_image_deployment() -> str:
    return os.getenv("AZURE_OPENAI_IMAGE_DEPLOYMENT", "gpt-image-1.5")


def get_tts_deployment() -> str:
    return os.getenv("AZURE_OPENAI_TTS_DEPLOYMENT", "gpt-4o-mini-tts")
