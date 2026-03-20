from pathlib import Path
from utils.azure_client import get_tts_client, get_tts_deployment


def text_to_speech(text, output_path, voice="alloy"):
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    client = get_tts_client()
    deployment = get_tts_deployment()
    with client.audio.speech.with_streaming_response.create(
        model=deployment, voice=voice, input=text, instructions="Speak in a calm, authoritative corporate briefing tone. Natural pacing with slight pauses between key data points. Professional but warm, like a senior executive presenting to the board. No robotic cadence."
    ) as resp:
        resp.stream_to_file(str(output_file))
    return str(output_file)
