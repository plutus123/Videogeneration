import os
import json
from utils.azure_client import get_azure_client, get_chat_deployment

VIDEO_PRODUCER_PROMPT = """You are an expert video producer creating a corporate intelligence briefing video for the leadership team of Rolls-Royce (aviation/defence company).

STRICT DURATION RULES (TTS reads at 2.5 words per second):
- Target video: 150 seconds (2.5 minutes). Hard max: 180 seconds (3 minutes).
- TOTAL word count across ALL audio_scripts: MAX 400 words. Count carefully.
- Each audio_script: MAX 30 words (1-2 short sentences). This produces ~12 seconds of audio.
- Each scene duration_seconds: set to 12 (to match audio length).
- Total scenes: 12-15 maximum.

SCENE NUMBERING AND DISTRIBUTION:
- Start from scene_number 1.
- ALL sections from the context MUST appear. No section may be skipped.
- 1 article = 1 scene. Multiple related articles can share 1 scene.
- Distribute proportionally: a section with 1 article gets 1 scene, a section with 8 articles gets 5-7 scenes.

NARRATION RULES:
- Each audio_script must be exactly 1-2 sentences, max 30 words.
- Write in a single consistent authoritative corporate narrator voice.
- Use smooth transitions: "Meanwhile...", "Turning to...", "In parallel..."
- Preserve key numbers, names, dollar figures, percentages.
- Tone: professional, executive-briefing style, factual, confident.

VISUAL STYLE (Rolls-Royce Corporate Theme):
- Color palette: deep navy blue (#1B2A4A), silver/platinum (#C0C0C0), white, with subtle gold (#B8860B) accents.
- Aesthetic: clean corporate boardroom style, NOT futuristic or cartoon-animated.
- Think: polished executive presentation slides, professional photography, real-world settings.
- Backgrounds: clean gradients (navy to dark blue), subtle geometric patterns, professional overlays.
- Data visuals: clean bar charts, minimalist infographics with navy/silver/white palette.
- Settings: real boardrooms, aircraft hangars, defence facilities, factory floors, diplomatic halls.
- No neon, no sci-fi, no cartoon characters, no overly stylized graphics.
- visual_prompt describes a SINGLE photorealistic corporate-style image (not video or animation).
- Every visual_prompt MUST include: "Corporate photography style, Rolls-Royce navy and silver color theme, clean professional aesthetic"

Output JSON:
{
  "textual_summary": "Factual summary covering all articles",
  "scenes": [
    {
      "scene_number": 1,
      "section": "SECTION NAME",
      "duration_seconds": 12,
      "visual_prompt": "Corporate photography style, Rolls-Royce navy and silver color theme, clean professional aesthetic. [scene description]",
      "audio_script": "Max 30 words narration with key facts.",
      "on_screen_text": "Short label with key number"
    }
  ],
  "overall_style": "Corporate Rolls-Royce executive briefing: navy blue, silver, photorealistic, professional"
}

"""


def generate_scene_plan(context, model=None):
    client = get_azure_client()
    deployment = model or get_chat_deployment()
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are an expert video producer and aviation analyst. Output valid JSON only."},
            {"role": "user", "content": VIDEO_PRODUCER_PROMPT + context}
        ],
        response_format={"type": "json_object"},
        timeout=300,
    )
    result = response.choices[0].message.content
    return json.loads(result)


def save_scene_plan(plan, output_path):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    return output_path
