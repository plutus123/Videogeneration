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
- 1 article = 1 scene. NEVER combine multiple articles into a single scene.
- CRITICAL: If an article contains MULTIPLE distinct news items (e.g., FCAS pitch, Pinaka export, AMCA update, defense exports), create SEPARATE scenes for each distinct topic.
- Distribute proportionally: a section with 1 article gets 1 scene, a section with 8 articles gets 8 scenes.
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
- CRITICAL ANTI-HALLUCINATION RULE: visual_prompts must ONLY reference EXACT data points from the scene (headline_stat, bullet_points). NEVER include generic filler text like "75%" or placeholder percentages. If no specific percentage exists in the data, DO NOT invent one in the visual.

Output JSON:
{
  "textual_summary": "Factual summary covering all articles",
  "scenes": [
    {
      "scene_number": 1,
      "section": "SECTION NAME",
      "article_source": "Article title or URL this scene is based on",
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
- 1 article = 1 scene. NEVER combine multiple articles into a single scene.
- CRITICAL: If an article contains MULTIPLE distinct news items (e.g., FCAS pitch, Pinaka export, AMCA update, defense exports), create SEPARATE scenes for each distinct topic.
- Distribute proportionally: a section with 1 article gets 1 scene, a section with 8 articles gets 8 scenes.
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

CRITICAL ANTI-HALLUCINATION RULE for visual_prompts: ONLY use EXACT data from headline_stat and bullet_points. NEVER invent percentages like "75%" or generic stats. If the data doesn't have a specific number, the visual must NOT include one.

Every visual_prompt MUST begin with: " briefing infographic,dossier style, horizontal landscape layout, cream parchment background (#F2EDE0)."
TEXT REQUIREMENT: Every visual_prompt MUST explicitly command the image generator to render the exact SECTION NAME prominently in clean, bold, typography at the very top edge of the image.

For each scene you MUST also provide these structured fields:
- "category_label": ALL-CAPS topic label (e.g. "GEOPOLITICAL UPDATE", "INDUSTRY UPDATE", "MARKET SHIFT", "DEFENSE INTEL", "TECH BREAKTHROUGH")
- "headline_stat": the single most impactful number or short phrase for the large stat display (e.g. "$1B", "8.2%", "98%", "13-TON")
- "headline_caption": a short caption below the stat (e.g. "GE Aerospace U.S. Investment")
- "icon_type": one of: jet (for aviation/aerospace companies), ship (maritime), factory (manufacturing sites), shield (defense), chart (data), globe (trade), drone, rocket
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
      "article_source": "Article title or URL this scene is based on",
      "duration_seconds": 12,
      "category_label": "GEOPOLITICAL UPDATE",
      "headline_stat": "$1B",
      "headline_caption": "GE Aerospace U.S. Investment",
      "icon_type": "jet",
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

# ---------------------------------------------------------------------------
# 3-SLIDE BRIEFING prompt — answers 3 key questions
# ---------------------------------------------------------------------------
THREE_SLIDE_BRIEFING_PROMPT = """You are an expert video producer creating a 3-SLIDE WEEKLY INTELLIGENCE BRIEFING video for the leadership team of an Indian aerospace & defence company working on the AMCA program.

The video has EXACTLY 3 slides. Each slide answers ONE key question.

STRICT RULES:
- EXACTLY 3 scenes. No more. No less.
- Target TOTAL duration: 40-45 seconds.
- Each scene: ~13-15 seconds, with audio_script of 33-38 words.
- TTS reads at 2.5 words per second.
- duration_seconds MUST match audio_script word count / 2.5.
- ONLY use facts from the provided context. NEVER hallucinate.
- CRITICAL: Narration must be EXTREMELY DENSE and INFORMATION-PACKED. Every single word must carry maximum information. No filler phrases. Name specific companies, figures, dates. Do NOT miss important developments — compress, don't skip.

THE 3 QUESTIONS (one per slide):

SLIDE 1: "WHAT HAPPENED?"
- Cover the most important AMCA/defence developments from this period
- Name specific companies, deals, dollar figures, dates
- Section label: "KEY DEVELOPMENTS"

SLIDE 2: "WHY DOES IT MATTER?"
- Analyze the strategic implications of the developments from Slide 1
- How do they impact the AMCA program, Indian defence manufacturing, key stakeholders?
- Connect the dots between different developments
- Section label: "STRATEGIC IMPACT"

SLIDE 3: "WHAT'S NEXT?"
- Outlook: what should leadership watch for in the coming weeks/months?
- Upcoming milestones, decisions, deadlines, risks
- Section label: "OUTLOOK & WATCH LIST"

NARRATION RULES:
- Slide 1 audio MUST start with: "This week:"
- Slide 2 audio MUST start with: "Why it matters:"
- Slide 3 audio MUST start with: "Watch for:"
- Tone: professional, executive-briefing, factual, confident.
- Preserve ALL numbers, names, dollar figures, percentages.
- No ellipses (...) or multiple dashes (--) — they cause TTS pauses.
- Write in TELEGRAPHIC style: dense facts, no filler words. Example: "This week: ADA shortlisted Tata, L&T-BEL, and Bharat Forge consortia for AMCA prototype. HAL excluded. GE-HAL finalizing F414 assembly in India."

VISUAL STYLE — DOSSIER INFOGRAPHIC:
Each visual_prompt must describe an intelligence briefing infographic card with EXACTLY these rules:

BACKGROUND & TEXTURE:
- Off-white/cream parchment background (#F2EDE0), NOT pure white
- Subtle grid overlay at very low opacity
- Technical crosshair/registration marks (+) in corners
- Horizontal/landscape orientation

TYPOGRAPHY:
- Headlines: Bold dark navy (#1A2744), large sans-serif
- Body: IBM Plex Mono or similar monospace in dark charcoal
- Labels: All-caps monospace, letter-spaced
- Accent subheadings: Steel blue (#4A90B8)

COLOR PALETTE (strict 4-color max):
- Dark navy: #1A2744 (headers)
- Burnt orange: #C0622A (alerts/warnings)
- Steel blue: #4A8FB5 (data highlights)
- Olive green: #6B7A45 (secondary)
- Background cream: #F2EDE0

LAYOUT:
- Clean ruled border around entire composition
- 2-4 clearly separated card regions with thin borders
- Mix of bold KEY STAT (large, left/center) with supporting bullet points
- Flat technical blueprint iconography (jets, factories, shields, charts)

CONTENT STRUCTURE for each card:
- Top: ALL-CAPS category label + question
- Center-left: 1 large bold headline stat or icon
- Center-right: 3-5 monospace bullet points
- Bottom: thin rule + source label in small monospace

Every visual_prompt MUST begin with: "Intelligence briefing infographic, dossier style, horizontal landscape layout, cream parchment background (#F2EDE0)."

ANTI-HALLUCINATION: visual_prompts must ONLY reference EXACT data from headline_stat and bullet_points. NEVER invent percentages or stats.

Output JSON:
{
  "textual_summary": "Factual summary covering all articles",
  "scenes": [
    {
      "scene_number": 1,
      "section": "KEY DEVELOPMENTS",
      "question": "What happened?",
      "article_source": "Primary articles this scene covers",
      "duration_seconds": 50,
      "category_label": "KEY DEVELOPMENTS",
      "headline_stat": "$1.5B",
      "headline_caption": "F414 Engine Deal",
      "icon_type": "jet",
      "bullet_points": ["Fact 1", "Fact 2", "Fact 3", "Fact 4"],
      "source_label": "Sources: defence.in, janes.com | Q1 2026",
      "accent_color": "blue",
      "visual_prompt": "Intelligence briefing infographic, dossier style, horizontal landscape layout, cream parchment background (#F2EDE0). [detailed card description]",
      "audio_script": "This week in Indian defence aerospace... [100-150 words covering key facts]",
      "on_screen_text": "WHAT HAPPENED?"
    },
    {
      "scene_number": 2,
      "section": "STRATEGIC IMPACT",
      "question": "Why does it matter?",
      ...
    },
    {
      "scene_number": 3,
      "section": "OUTLOOK & WATCH LIST",
      "question": "What's next?",
      ...
    }
  ],
  "overall_style": "flat infographic, technical illustration"
}

"""



def generate_scene_plan(context, model=None, style="infographic", slides=3):
    """Generate a scene plan using GPT.

    Args:
        context:  Assembled article context string.
        model:    Override chat deployment name.
        style:    "photo" for photorealistic, "infographic" for classified dossier.
        slides:   3 for 3-slide Q&A briefing (default), 0 for full multi-scene.
    """
    client = get_azure_client()
    deployment = model or get_chat_deployment()

    if slides == 3:
        prompt = THREE_SLIDE_BRIEFING_PROMPT
    elif style == "infographic":
        prompt = INFOGRAPHIC_PRODUCER_PROMPT
    else:
        prompt = VIDEO_PRODUCER_PROMPT

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are an expert video producer and Indian defence aerospace analyst. Output valid JSON only."},
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


def build_context_from_curated(curated_articles):
    """Build scene planner context string from curated articles.

    Handles both formats:
      - AlphaSense-style: thematic_sections with articles
      - Legacy flat: selected_articles with buckets
    """
    parts = []

    # AlphaSense-style format (thematic_sections)
    if "thematic_sections" in curated_articles and curated_articles["thematic_sections"]:
        sections = curated_articles["thematic_sections"]
        total = sum(len(s.get("articles", [])) for s in sections)
        parts.append(f"\n=== VIDEO HAS {len(sections)} SECTIONS ({total} articles total) ===")

        for idx, section in enumerate(sections, 1):
            articles = section.get("articles", [])
            if not articles:
                continue
            title = section.get("section_title", f"Section {idx}")
            parts.append(f"\n--- SECTION {idx}: {title} ({len(articles)} articles) ---")
            if section.get("section_summary"):
                parts.append(f"Section Summary: {section['section_summary']}")

            for article in articles:
                parts.append(
                    f"\nARTICLE [{article.get('citation_number', '?')}]: {article.get('title', 'N/A')}\n"
                    f"Source URL: {article.get('url', 'N/A')}\n"
                    f"Source: {article.get('source_name', '')} ({article.get('source_type', '')})\n"
                    f"Score: {article.get('importance_score', '?')}/10\n"
                    f"Key Players: {', '.join(article.get('key_players_mentioned', []))}\n"
                    f"Keywords: {', '.join(article.get('amca_keywords_found', []))}\n"
                    f"Summary: {article.get('summary', '')}\n"
                    f"Key Facts: {json.dumps(article.get('key_facts', []))}\n"
                )
    else:
        # Legacy flat format
        articles = curated_articles.get("selected_articles", [])
        buckets = {"amca_program": [], "key_players": [], "defence_tech": []}
        for article in articles:
            b = article.get("bucket", "defence_tech")
            if b in buckets:
                buckets[b].append(article)
            else:
                buckets["defence_tech"].append(article)

        total = len(articles)
        parts.append(f"\n=== VIDEO HAS {len([b for b in buckets if buckets[b]])} SECTIONS ({total} articles total) ===")

        section_idx = 1
        for bucket_key, articles_list in buckets.items():
            if not articles_list:
                continue
            parts.append(f"\n--- SECTION {section_idx}: Defence ({len(articles_list)} articles) ---")
            for article in articles_list:
                parts.append(
                    f"\nARTICLE: {article.get('title', 'N/A')}\n"
                    f"Source URL: {article.get('url', 'N/A')}\n"
                    f"Score: {article.get('importance_score', '?')}/10\n"
                    f"Key Players: {', '.join(article.get('key_players_mentioned', []))}\n"
                    f"Keywords: {', '.join(article.get('amca_keywords_found', []))}\n"
                    f"Summary: {article.get('summary', '')}\n"
                    f"Key Facts: {json.dumps(article.get('key_facts', []))}\n"
                )
            section_idx += 1

    return "\n".join(parts)

