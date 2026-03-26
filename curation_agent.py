"""Curation agent: filters, ranks, and summarizes articles around 3 Rolls-Royce questions.

The 3 questions that drive the video:
1. What's happening in Rolls-Royce?
2. How is it affecting the market?
3. How is the competition doing?

Each question becomes one slide in the final 30-40 second video.
"""

import json
import os
from datetime import datetime, timedelta
from utils.azure_client import get_azure_client, get_chat_deployment


# ---------------------------------------------------------------------------
# Prompt for the curation/ranking step
# ---------------------------------------------------------------------------
CURATION_PROMPT = """You are a senior aviation & defence intelligence analyst at Rolls-Royce.

You have been given a set of recently discovered news articles. Your job is to:
1. FILTER out irrelevant noise (celebrity gossip, unrelated politics, duplicates).
2. RANK the remaining articles by importance using these criteria (in order):
   - Direct Rolls-Royce news (orders, contracts, financials, leadership, product updates)
   - Market-moving events (policy changes, tariffs, FTAs, airspace disruptions, energy security)
   - Competitor activity (GE Aerospace, Pratt & Whitney, Safran, Airbus, Boeing, Embraer, HAL)
   - Defence procurement and exports
   - Supply chain and manufacturing capacity shifts
3. For EACH selected article, tag it with one of these buckets:
   - "rolls_royce" — directly about Rolls-Royce
   - "market" — affects the broader aviation/defence market
   - "competition" — about competitors or competitive landscape

OUTPUT valid JSON ONLY:
{
  "selected_articles": [
    {
      "url": "...",
      "title": "...",
      "bucket": "rolls_royce" | "market" | "competition",
      "importance_score": 1-10,
      "key_facts": ["fact1", "fact2", "fact3"],
      "summary": "2-3 sentence summary preserving all numbers, dates, company names"
    }
  ]
}

Select the TOP 10-15 most important articles. Be ruthless — only include genuinely significant items.
Tag at least 1-2 articles per bucket if available. If no Rolls-Royce-specific news exists, note that.

ARTICLES:
"""


# ---------------------------------------------------------------------------
# Prompt for the 3-question summary
# ---------------------------------------------------------------------------
SUMMARY_PROMPT = """You are a senior Rolls-Royce intelligence analyst creating a WEEKLY BRIEFING for the CEO.

Based on the curated articles below, create a structured summary answering EXACTLY 3 questions.
Each answer becomes ONE slide in a 30-40 second video (so ~10-13 seconds per slide).

RULES:
- Be QUANTITATIVE: include exact numbers ($, %, units, dates) wherever available.
- Be QUALITATIVE: include strategic implications, not just facts.
- Be SPECIFIC: no generic statements like "the market is evolving". Use real data.
- Each answer should have 3-5 bullet points MAX.
- Bullet points must be concise (under 15 words each) but data-rich.
- The audio_script for each slide should be 25-33 words (10-13 seconds at 2.5 words/sec).
- The audio_script MUST directly elaborate on the bullet points shown on screen. No unrelated tangents.
- Total video: 30-40 seconds STRICT.
- For source_label use format: "Source: domain.com | w/c DD Mon" using the week-commencing Monday date.

OUTPUT valid JSON ONLY:
{
  "briefing_date": "YYYY-MM-DD",
  "slides": [
    {
      "slide_number": 1,
      "question": "What's happening in Rolls-Royce?",
      "category_label": "ROLLS-ROYCE UPDATE",
      "headline_stat": "Key number or phrase",
      "headline_caption": "Short caption",
      "icon_type": "jet",
      "bullet_points": ["Quantitative fact 1", "Quantitative fact 2", "Strategic implication"],
      "source_label": "Source: domain.com | Date",
      "accent_color": "blue",
      "audio_script": "25-33 words elaborating on the bullet points above.",
      "duration_seconds": 12.0
    },
    {
      "slide_number": 2,
      "question": "How is it affecting the market?",
      "category_label": "MARKET IMPACT",
      "headline_stat": "Key number or phrase",
      "headline_caption": "Short caption",
      "icon_type": "chart",
      "bullet_points": ["Market fact 1", "Market fact 2", "Strategic implication"],
      "source_label": "Source: domain.com | Date",
      "accent_color": "orange",
      "audio_script": "25-33 words elaborating on the bullet points above.",
      "duration_seconds": 12.0
    },
    {
      "slide_number": 3,
      "question": "How is the competition doing?",
      "category_label": "COMPETITIVE LANDSCAPE",
      "headline_stat": "Key number or phrase",
      "headline_caption": "Short caption",
      "icon_type": "shield",
      "bullet_points": ["Competitor fact 1", "Competitor fact 2", "Strategic implication"],
      "source_label": "Source: domain.com | Date",
      "accent_color": "green",
      "audio_script": "25-33 words elaborating on the bullet points above.",
      "duration_seconds": 12.0
    }
  ],
  "overall_style": "flat infographic, technical illustration"
}

CURATED ARTICLES:
"""


def curate_articles(search_results, save_path="curated_articles.json"):
    """Filter and rank search results using GPT.

    Args:
        search_results: List of article dicts from tavily_search.
        save_path: Where to save curated results.

    Returns:
        Dict with selected_articles.
    """
    client = get_azure_client()
    deployment = get_chat_deployment()

    # Build article context for GPT
    articles_text = ""
    for i, article in enumerate(search_results[:30], 1):  # Cap at 30 to fit context
        content = article.get("raw_content") or article.get("content", "")
        # Truncate long articles
        content = content[:3000] if len(content) > 3000 else content
        articles_text += (
            f"\n--- Article {i} ---\n"
            f"URL: {article['url']}\n"
            f"Title: {article.get('title', 'N/A')}\n"
            f"Score: {article.get('score', 'N/A')}\n"
            f"Content: {content}\n"
        )

    print("  Curating articles with GPT...")
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are an expert aviation intelligence analyst. Output valid JSON only."},
            {"role": "user", "content": CURATION_PROMPT + articles_text},
        ],
        response_format={"type": "json_object"},
        timeout=120,
    )
    result = json.loads(response.choices[0].message.content)

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"  Curated {len(result.get('selected_articles', []))} articles -> {save_path}")

    return result


def generate_briefing_summary(curated_articles, save_path="generated_scene_plan.json"):
    """Generate the 3-slide briefing summary from curated articles.

    Args:
        curated_articles: Dict with 'selected_articles' from curate_articles().
        save_path: Where to save the scene plan.

    Returns:
        Dict with slides (scene plan format).
    """
    client = get_azure_client()
    deployment = get_chat_deployment()

    articles = curated_articles.get("selected_articles", [])
    articles_text = ""
    for article in articles:
        articles_text += (
            f"\n[{article.get('bucket', 'unknown').upper()}] "
            f"(Score: {article.get('importance_score', '?')}/10)\n"
            f"Title: {article.get('title', 'N/A')}\n"
            f"URL: {article.get('url', '')}\n"
            f"Key Facts: {json.dumps(article.get('key_facts', []))}\n"
            f"Summary: {article.get('summary', '')}\n"
        )

    print("  Generating 3-slide briefing summary...")
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are an expert video producer and aviation analyst for Rolls-Royce. Output valid JSON only."},
            {"role": "user", "content": SUMMARY_PROMPT + articles_text},
        ],
        response_format={"type": "json_object"},
        timeout=120,
    )
    plan = json.loads(response.choices[0].message.content)

    # Compute week-commencing date (Monday of current week)
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    wc_label = monday.strftime("w/c %d %b")

    # Add visual_prompt and on_screen_text to each slide for compatibility
    # with the existing image generation and video pipeline
    for slide in plan.get("slides", []):
        slide["scene_number"] = slide["slide_number"]
        slide["section"] = slide.get("question", "")
        slide["article_source"] = ""

        # Build visual_prompt from structured fields
        cat = slide.get("category_label", "UPDATE")
        stat = slide.get("headline_stat", "")
        bullets = slide.get("bullet_points", [])
        icon = slide.get("icon_type", "chart")
        bullets_text = "; ".join(bullets)

        # Ensure source_label includes w/c date
        src = slide.get("source_label", "")
        if src and "w/c" not in src:
            src = src.rstrip().rstrip("|").rstrip() + f" | {wc_label}"
            slide["source_label"] = src
        elif not src:
            slide["source_label"] = f"Source: Tavily Search | {wc_label}"

        slide["visual_prompt"] = (
            f"briefing infographic, dossier style, horizontal landscape layout, "
            f"cream parchment background (#F2EDE0). "
            f"Render '{cat}' prominently at the top edge in bold dark navy typography. "
            f"Center-left: large bold '{stat}' with flat {icon} icon. "
            f"Center-right: monospace bullet points: {bullets_text}. "
            f"Bottom strip: {slide.get('source_label', '')}. "
            f"ONLY show exact data listed above. Do NOT invent any numbers."
        )
        slide["on_screen_text"] = stat

    # Wrap in scene plan format
    scene_plan = {
        "briefing_date": wc_label,
        "textual_summary": f"Weekly Rolls-Royce intelligence briefing ({wc_label}) covering company updates, market impact, and competitive landscape.",
        "scenes": plan.get("slides", []),
        "overall_style": plan.get("overall_style", "flat infographic, technical illustration"),
    }

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(scene_plan, f, indent=2, ensure_ascii=False)
        total_dur = sum(s.get("duration_seconds", 0) for s in scene_plan.get("scenes", []))
        print(f"  Generated {len(scene_plan['scenes'])} slides, {total_dur:.1f}s total -> {save_path}")

    return scene_plan
