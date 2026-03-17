import os
import json
from utils.azure_client import get_azure_client, get_chat_deployment

VIDEO_PRODUCER_PROMPT = """You are creating a NotebookLM-style explainer video for a Rolls-Royce aviation/defence intelligence briefing.

DURATION RULES (TTS reads ~2.5 words/sec):
- Target: 150s (2.5 min). Hard max: 180s (3 min).
- Total words across ALL audio_scripts: MAX 400. Count carefully.
- Each audio_script: MAX 30 words (1-2 short sentences).
- Each scene duration_seconds: 12.
- Total scenes: 12-15.

SCENE DISTRIBUTION:
- Start from scene_number 1.
- ALL sections MUST appear. 1 article = 1 scene. Related articles can share 1 scene.
- Proportional: 1 article section gets 1 scene, 8 article section gets 5-7 scenes.

NARRATION:
- Max 30 words per audio_script. Single professional narrator voice.
- Smooth transitions between scenes.
- Preserve key numbers, names, dollar figures, percentages.

SCENE TYPES (each scene MUST have exactly one scene_type):

1. "title" - Opening/section title card
   Required fields: title, subtitle
   Use for: first scene, section transitions

2. "big_number" - Emphasize a key statistic
   Required fields: number, label
   Use for: impactful data points ($1B, 8.2%, 3,300 etc.)

3. "comparison" - Side-by-side two-panel comparison
   Required fields: title, left_label, left_value, left_highlight, right_label, right_value, right_highlight
   Use for: before/after, old/new, two competing things

4. "steps" - Process flow (2-4 steps)
   Required fields: title, step_1, step_2, step_3 (step_4 optional)
   Use for: processes, timelines, sequences

5. "statement" - Bold text with highlighted keywords on light background
   Required fields: text, highlight_1, highlight_2 (highlight_3 optional)
   Use for: key insights, important quotes, bold conclusions

6. "key_point" - Heading with bullet points
   Required fields: heading, point_1, point_2, point_3 (point_4, point_5 optional)
   Use for: data summaries, multiple facts about one topic

ICON HINT: Every scene MUST include "icon_hint" - a 2-4 word description of a simple object/symbol to illustrate the scene (e.g. "jet engine", "shield badge", "factory building", "military aircraft", "dollar coins", "world map"). No people. No complex scenes.

VARIETY RULE: Use at least 4 different scene_types across the video. Do NOT use the same type for more than 3 consecutive scenes. Mix them for visual variety.

Output JSON:
{
  "textual_summary": "Factual summary covering all articles",
  "scenes": [
    {
      "scene_number": 1,
      "section": "SECTION NAME",
      "scene_type": "title",
      "duration_seconds": 12,
      "audio_script": "Max 30 words narration.",
      "icon_hint": "jet engine",
      "title": "Title Text",
      "subtitle": "Subtitle text"
    },
    {
      "scene_number": 2,
      "section": "SECTION NAME",
      "scene_type": "big_number",
      "duration_seconds": 12,
      "audio_script": "Max 30 words narration.",
      "icon_hint": "dollar coins",
      "number": "$1B",
      "label": "What this number represents"
    },
    {
      "scene_number": 3,
      "section": "SECTION NAME",
      "scene_type": "statement",
      "duration_seconds": 12,
      "audio_script": "Max 30 words narration.",
      "icon_hint": "military aircraft",
      "text": "Bold statement with key insight here",
      "highlight_1": "key",
      "highlight_2": "insight"
    }
  ]
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
