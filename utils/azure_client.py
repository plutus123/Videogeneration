import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()


def get_azure_client() -> AzureOpenAI:
    """Get Azure OpenAI client for chat completions.

    Falls back to TTS endpoint if AZURE_OPENAI_ENDPOINT is not set,
    since both models may be deployed on the same Azure resource.
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_TTS_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_TTS_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")

    if not endpoint or not api_key:
        raise RuntimeError(
            "Missing Azure OpenAI credentials. Set AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY "
            "(or AZURE_TTS_ENDPOINT + AZURE_TTS_API_KEY) in .env"
        )

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )


def get_tts_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_TTS_ENDPOINT"),
        api_key=os.getenv("AZURE_TTS_API_KEY"),
        api_version=os.getenv("AZURE_TTS_API_VERSION", "2025-03-01-preview"),
    )


def get_chat_deployment() -> str:
    return os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-5-nano")


def get_image_deployment() -> str:
    return os.getenv("AZURE_OPENAI_IMAGE_DEPLOYMENT", "gpt-image-1.5")


def get_tts_deployment() -> str:
    return os.getenv("AZURE_TTS_DEPLOYMENT", "tts")
