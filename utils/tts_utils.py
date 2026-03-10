"""Generates narration text via GPT and converts it to speech using OpenAI TTS (with gTTS fallback)."""

import os
import asyncio
from pathlib import Path
from openai import OpenAI

NARRATOR_SYSTEM = """You are a professional presenter narrating a slideshow. Calm, clear, engaging.

Rules:
- Never start with "Welcome to" or "Hello" or greetings -- the presentation is already playing.
- 2-4 sentences, roughly 15-25 seconds when spoken.
- Sound natural, as if explaining to a colleague.
- Do not repeat the slide title verbatim.
- End each narration smoothly, no abrupt stops."""


async def generate_narration_text(section_name, section_content,
                                   slide_index=0, total_slides=1,
                                   presentation_title=""):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_narration(section_content, slide_index, total_slides)

    client = OpenAI(api_key=api_key)

    if slide_index == 0:
        hint = f"Opening slide of '{presentation_title}'. Start with a brief engaging hook, not 'welcome to'."
    elif slide_index == total_slides - 1:
        hint = "Final content slide. Wrap up naturally, no 'in conclusion'."
    else:
        hint = f"Slide {slide_index + 1} of {total_slides}. Transition naturally from the previous topic."

    prompt = f"""{hint}

Title: {section_name}
Content: {section_content}

Write 2-4 sentences (15-25 seconds spoken). Concise and natural."""

    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": NARRATOR_SYSTEM}, {"role": "user", "content": prompt}],
            temperature=0.7, max_completion_tokens=150,
        ))
        return resp.choices[0].message.content.strip()
    except Exception:
        return _fallback_narration(section_content, slide_index, total_slides)


def _fallback_narration(content, slide_index, total_slides):
    if slide_index == 0:
        return f"Let's explore how {content.lower()}"
    if slide_index == total_slides - 1:
        return f"{content} And that covers the key points."
    return content


async def text_to_speech(text, output_path, voice="alloy"):
    api_key = os.getenv("OPENAI_API_KEY")
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: client.audio.speech.create(
                model="tts-1", voice=voice, input=text,
            ))
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



