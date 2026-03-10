"""Converts text to speech using OpenAI TTS API, with gTTS as a fallback."""

import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def text_to_speech(text, output_path, voice="alloy"):
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            resp = client.audio.speech.create(model="tts-1", voice=voice, input=text)
            resp.stream_to_file(str(output_file))
            return str(output_file)
        except Exception:
            pass

    try:
        from gtts import gTTS
        gTTS(text=text, lang="en", slow=False).save(str(output_file))
        return str(output_file)
    except Exception:
        return None
