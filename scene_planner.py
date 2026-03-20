import os
import json
from utils.azure_client import get_azure_client, get_chat_deployment

# ---------------------------------------------------------------------------
# Original photo-style prompt (backward compatible)
# ---------------------------------------------------------------------------
VIDEO_PRODUCER_PROMPT = """You are an expert video producer creating a corporate intelligence briefing video for the leadership team of Rolls-Royce (aviation/defence company).

STRICT DURATION RULES (TTS reads at 2.5 words per second):
- Target video: exactly between 120 and 180 seconds (2 to 3 minutes).
- There is NO strict word count limit per scene, but you MUST adjust your total script length dynamically so that the entire video fits perfectly within the 2-3 minute window.
- Each scene's duration_seconds MUST exactly match its audio_script length (words divided by 2.5).
- Ensure you cover ALL categories and ALL articles comprehensively within this time limit.

SCENE NUMBERING AND DISTRIBUTION:
- Start from scene_number 1.
- ALL sections from the context MUST appear. No section may be skipped.
- 1 article = 1 scene. Multiple related articles can share 1 scene.
- Distribute proportionally: a section with 1 article gets 1 scene, a section with 8 articles gets 5-7 scenes.
- STRICT RULE: NEVER mix information across categories. A scene for a specific section MUST ONLY use facts from that section's articles. Do not hallucinate.

NARRATION RULES:
- Write detailed enough audio_scripts to cover key facts, paced dynamically.
- ONLY use facts explicitly stated in the provided context for the current section. Do NOT hallucinate.
- Avoid punctuation like ellipses (...) or multiple dashes (--) which cause long undesirable pauses in TTS.
- Write in a single consistent authoritative corporate narrator voice.
- Focus strictly on competitive intelligence, significant strategic moves, supply chain resilience, and capacity scaling.
- The audio_script of the VERY FIRST scene of each section MUST begin using these exact specific intro styles:
    * Macroeconomic: "Macroeconomic Context: ..."
    * Civil: "Civil Aviation Update: ..."
    * Defence: "Defence Sector Initiatives: ..."
    * PowerSystems: "Power Systems Network: ..."
    * SMR/ Nuclear: "SMR and Nuclear Developments: ..."
- Use smooth transitions for subsequent scenes: "Meanwhile...", "Turning to...", "In parallel..."
- Preserve key numbers, names, dollar figures, percentages.
- Tone: professional, executive-briefing style, factual, confident.

VISUAL STYLE:
- Color palette: deep navy blue (#1B2A4A), silver/platinum (#C0C0C0), white, with subtle gold (#B8860B) accents.
- Aesthetic: clean corporate boardroom style, NOT futuristic or cartoon-animated.
- Think: polished executive presentation slides, professional photography, real-world settings.
- Backgrounds: clean gradients (navy to dark blue), subtle geometric patterns, professional overlays.
- Data visuals: clean bar charts, minimalist infographics with navy/silver/white palette.
- Settings: real boardrooms, aircraft hangars, defence facilities, factory floors, diplomatic halls.
- No neon, no sci-fi, no cartoon characters, no overly stylized graphics.
- visual_prompt describes a SINGLE photorealistic corporate-style image (not video or animation).
- Every visual_prompt MUST include: "Corporate photography style, clean professional aesthetic".
- TEXT REQUIREMENT: Every visual_prompt MUST explicitly command the image generator to render the exact SECTION NAME prominently in clean, bold, typography at the very top edge of the image.

Output JSON:
{
  "textual_summary": "Factual summary covering all articles",
  "scenes": [
    {
      "scene_number": 1,
      "section": "SECTION NAME",
      "duration_seconds": 12,
      "visual_prompt": "Corporate photography style, clean professional aesthetic. [scene description]",
      "audio_script": "Max 30 words narration with key facts.",
      "on_screen_text": "Short label with key number"
    }
  ],
  "overall_style": "Corporate, photorealistic, professional"
}

"""

# ---------------------------------------------------------------------------
# Dossier / infographic style prompt
# ---------------------------------------------------------------------------
INFOGRAPHIC_PRODUCER_PROMPT = """You are an expert video producer creating an INTELLIGENCE DOSSIER briefing video for the leadership team of Rolls-Royce (aviation/defence company).

STRICT DURATION RULES (TTS reads at 2.5 words per second):
- Target video: exactly between 120 and 180 seconds (2 to 3 minutes).
- There is NO strict word count limit per scene, but you MUST adjust your total script length dynamically so that the entire video fits perfectly within the 2-3 minute window.
- Each scene's duration_seconds MUST exactly match its audio_script length (words divided by 2.5).
- Ensure you cover ALL categories and ALL articles comprehensively within this time limit.

SCENE NUMBERING AND DISTRIBUTION:
- Start from scene_number 1.
- ALL sections from the context MUST appear. No section may be skipped.
- 1 article = 1 scene. Multiple related articles can share 1 scene.
- Distribute proportionally: a section with 1 article gets 1 scene, a section with 8 articles gets 5-7 scenes.
- STRICT RULE: NEVER mix information across categories. A scene for a specific section MUST ONLY use facts from that section's articles. Do not hallucinate.

NARRATION RULES:
- Write detailed enough audio_scripts to cover key facts, paced dynamically.
- ONLY use facts explicitly stated in the provided context for the current section. Do NOT hallucinate.
- Avoid punctuation like ellipses (...) or multiple dashes (--) which cause long undesirable pauses in TTS.
- Write in a single consistent authoritative corporate narrator voice.
- Focus strictly on competitive intelligence, significant strategic moves, supply chain resilience, and capacity scaling.
- The audio_script of the VERY FIRST scene of each section MUST begin using these exact specific intro styles:
    * Macroeconomic: "Macroeconomic Context: ..."
    * Civil: "Civil Aviation Update: ..."
    * Defence: "Defence Sector Initiatives: ..."
    * PowerSystems: "Power Systems Network: ..."
    * SMR/ Nuclear: "SMR and Nuclear Developments: ..."
- Use smooth transitions for subsequent scenes: "Meanwhile...", "Turning to...", "In parallel..."
- Preserve key numbers, names, dollar figures, percentages.
- Tone: professional, executive-briefing style, factual, confident.

VISUAL STYLE — DOSSIER INFOGRAPHIC:
Each visual_prompt must describe an intelligence briefing infographic card with EXACTLY these rules:

BACKGROUND & TEXTURE:
- Off-white/cream parchment background (#F2EDE0), NOT pure white
- Subtle grid or graph-paper overlay at very low opacity
- Technical crosshair/registration marks (+) in all four corners
- Horizontal/landscape orientation

TYPOGRAPHY:
- Headlines: Bold dark navy (#1A2744), large, sans-serif (similar to Inter or Gotham)
- Body/data text: IBM Plex Mono or similar monospace font in dark charcoal
- Labels and tags: All-caps monospace, letter-spaced
- Accent subheadings: Steel blue (#4A90B8)

COLOR PALETTE (strict 4-color max per card):
- Dark navy: #1A2744 (headers, filled boxes)
- Burnt orange/terracotta: #C0622A (alerts, threat indicators, warnings)
- Steel blue: #4A8FB5 (data highlights, arrows, positive metrics)
- Olive/military green: #6B7A45 (secondary elements, competitor indicators)
- Background cream: #F2EDE0

LAYOUT:
- Clean ruled border around entire composition
- Information divided into 2-4 clearly separated card regions with thin border lines
- Mix of a bold KEY STAT or icon (large, left or center) with supporting bullet points in monospace
- Use flat, technical, blueprint-like iconography (ships, factories, jets, maps, shields, drones, rockets, charts)
- Arrows and flow indicators should be chunky and directional

CONTENT STRUCTURE for each card:
- Top: ALL-CAPS category label (e.g. "GEOPOLITICAL UPDATE" or "MARKET ALERT")
- Center-left: 1 large bold headline stat, figure, or flat technical icon
- Center-right: 3-5 monospace bullet points summarizing key facts
- Bottom strip: thin rule + source label in small monospace

MOOD: news briefing meets premium financial research report.
Serious, structured, data-dense but visually clean. No gradients. No photos.
Flat technical illustration only. No photorealism. No cartoon. No sci-fi. No watermarks.

Every visual_prompt MUST begin with: " briefing infographic,dossier style, horizontal landscape layout, cream parchment background (#F2EDE0)."
TEXT REQUIREMENT: Every visual_prompt MUST explicitly command the image generator to render the exact SECTION NAME prominently in clean, bold, typography at the very top edge of the image.

For each scene you MUST also provide these structured fields:
- "category_label": ALL-CAPS topic label (e.g. "GEOPOLITICAL UPDATE", "INDUSTRY UPDATE", "MARKET SHIFT", "DEFENSE INTEL", "TECH BREAKTHROUGH")
- "headline_stat": the single most impactful number or short phrase for the large stat display (e.g. "$1B", "8.2%", "98%", "13-TON")
- "headline_caption": a short caption below the stat (e.g. "GE Aerospace U.S. Investment")
- "icon_type": one of: jet, ship, factory, shield, chart, globe, drone, rocket
- "bullet_points": array of 3-5 short fact strings in monospace style
- "source_label": attribution line (e.g. "Source: geaerospace.com | Mar 2026")
- "accent_color": one of: "orange" (threats/alerts), "blue" (data/positive), "green" (competitor/secondary)

Output JSON:
{
  "textual_summary": "Factual summary covering all articles",
  "scenes": [
    {
      "scene_number": 1,
      "section": "SECTION NAME",
      "duration_seconds": 12,
      "category_label": "GEOPOLITICAL UPDATE",
      "headline_stat": "$1B",
      "headline_caption": "GE Aerospace U.S. Investment",
      "icon_type": "factory",
      "bullet_points": ["30+ communities across 17 states", "5,000 new jobs", "Defence: $275M allocated"],
      "source_label": "Source: geaerospace.com | Mar 2026",
      "accent_color": "blue",
      "visual_prompt": "Intelligence briefing infographic, dossier style, cream parchment background (#F2EDE0). [detailed card description with layout, stats, icons, bullet points]",
      "audio_script": "Max 30 words narration with key facts.",
      "on_screen_text": "Short label with key number"
    }
  ],
  "overall_style": " flat infographic, technical illustration"
}

"""


def generate_scene_plan(context, model=None, style="infographic"):
    """Generate a scene plan using GPT.

    Args:
        context:  Assembled article context string.
        model:    Override chat deployment name.
        style:    "photo" for photorealistic, "infographic" for classified dossier.
    """
    client = get_azure_client()
    deployment = model or get_chat_deployment()

    if style == "infographic":
        prompt = INFOGRAPHIC_PRODUCER_PROMPT
    else:
        prompt = VIDEO_PRODUCER_PROMPT

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are an expert video producer and aviation analyst. Output valid JSON only."},
            {"role": "user", "content": prompt + context}
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
