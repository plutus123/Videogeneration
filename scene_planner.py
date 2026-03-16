import os
import json
from utils.azure_client import get_azure_client, get_chat_deployment

VIDEO_PRODUCER_PROMPT = """You are an expert video producer and aviation/defence analyst.
Create a scene plan for a 2-3 minute animated news explainer video.

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
- Write in a single consistent professional male narrator voice.
- Use smooth transitions between scenes: "Meanwhile...", "Turning to...", "In parallel..."
- Preserve key numbers, names, dollar figures, percentages.
- Be information-dense but extremely concise.

VISUAL STYLE:
- Cinematic: low-angle wide shot, overhead view, close-up, medium shot.
- Modern high-tech aesthetic, animated infographics for data.
- visual_prompt describes a SINGLE still image (not video).

Output JSON:
{
  "textual_summary": "Factual summary covering all articles",
  "scenes": [
    {
      "scene_number": 1,
      "section": "SECTION NAME",
      "duration_seconds": 12,
      "visual_prompt": "Single-image description for image generation",
      "audio_script": "Max 30 words narration with key facts.",
      "on_screen_text": "Short label with key number"
    }
  ],
  "overall_style": "Visual style description"
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
