"""Curation agent: filters, ranks, and categorizes articles around AMCA and Indian defence aerospace.

Focus areas:
1. AMCA Program Updates (tenders, RFI, RFQ, airframe, engine, prototype, etc.)
2. Key Players & Stakeholders (DRDO, GTRE, HAL, Tata, L&T, Bharat Forge, Adani Defence, Reliance)
3. Defence Technology & Manufacturing (5th/6th gen tech, ToT, MRO, assembly line, etc.)

Each curated article includes its source URL for traceability.

Curation modes:
- PRIMARY: GPT-5-nano (intelligent, context-aware filtering)
- FALLBACK: Local tiered keyword scoring (when GPT unavailable)
"""

import json
import os


# ---------------------------------------------------------------------------
# Tiered keyword system for accurate relevance scoring
# ---------------------------------------------------------------------------

# Tier 1: AMCA-SPECIFIC — gold-standard signals (5 points each)
TIER1_AMCA_SPECIFIC = [
    "AMCA", "Advanced Medium Combat Aircraft",
    "Kaveri engine", "GTRE", "DRDO ADA", "ADA Bangalore",
    "5th generation fighter India", "fifth generation fighter India",
    "6th generation", "sixth generation",
    "AMCA Mark", "AMCA Mk",
]

# Tier 2: HIGH-VALUE — strong relevance signals (3 points each)
TIER2_HIGH_VALUE = [
    "Tenders", "RFI", "RFQ", "RFP",
    "Transfer of Technology", "ToT",
    "prototype", "Test bed", "Test facility",
    "Assembly line", "FCAS", "GCAP",
    "Make in India defence", "Atmanirbhar Bharat defence", "Atmanirbhar Bharat",
    "Self Reliance defence", "combat aircraft India",
    "stealth fighter", "stealth aircraft",
    "defence manufacturing India", "defence procurement India",
    "defence export India",
    # India-specific defence terms
    "Indian Air Force", "IAF", "Indian Navy defence", "Indian Army defence",
    "Indian Army unmanned", "Indian Army technology",
    "India defence budget", "India military",
    "Tejas fighter", "Tejas Mark", "LCA Tejas",
    "BrahMos", "Akash missile",
]

# Tier 3: CONTEXTUAL — only count if Tier 1 or Tier 2 also matched (1 point each)
TIER3_CONTEXTUAL = [
    "airframe", "engine", "Thrust", "MRO",
    "manufacturing unit", "R&D", "R&T",
    "engine production", "Supply chain",
    "defence", "defense", "aerospace", "aviation",
    "fighter", "combat aircraft",
]

# Key Players — full names (4 points each)
KEY_PLAYERS = [
    "DRDO", "GTRE", "HAL", "Hindustan Aeronautics",
    "Tata Advanced Systems", "TASL",
    "Larsen & Toubro defence", "L&T defence",
    "Bharat Forge",
    "Adani Defence",
    "Reliance Defence",
    "BEL", "Bharat Electronics",
    "Mazagon Dock", "MDL",
    "Indian Air Force", "Indian Army", "Indian Navy",
]

# Key Players — short names (1 point, only counted if other signals present)
KEY_PLAYERS_SHORT = [
    "Tata", "L&T", "Adani", "Reliance",
]


# ---------------------------------------------------------------------------
# GPT Curation Prompt
# ---------------------------------------------------------------------------
CURATION_PROMPT = """You are a senior defence intelligence analyst at an Indian aerospace company specializing in India's AMCA (Advanced Medium Combat Aircraft) program and Indian defence aerospace.

You are curating news articles. Your job:
1. FILTER — be VERY strict. ONLY keep articles about:
   - India's AMCA program, Indian fighter/combat aircraft, Indian defence programs
   - Key Indian defence stakeholders: DRDO, GTRE, HAL, Tata Advanced Systems, L&T, Bharat Forge, Adani Defence, Reliance Defence
   - AMCA-related topics: tenders, RFI, RFQ, airframe, engine, prototypes, test facilities, assembly lines
   - Strategic programs relevant to India: FCAS, GCAP, Transfer of Technology, Make in India defence
   - Indian defence procurement, manufacturing, and exports

   REJECT articles that are:
   - Non-aerospace (HR, jobs, census, finance, entertainment, AI/tech, cricket, politics)
   - About non-Indian companies with NO connection to Indian defence
   - Generic international defence news with no India angle
   - About Reliance/Tata/L&T/Adani in NON-DEFENCE contexts (telecom, infrastructure, etc.)
   - From paywalled sources with no readable content

2. RANK remaining articles by importance (1-10):
   - 9-10: Directly about AMCA, Kaveri engine, Indian 5th/6th gen fighter
   - 7-8: About key stakeholders (DRDO, HAL, etc.) in defence/aerospace context
   - 5-6: About Indian defence manufacturing, procurement, exports
   - 3-4: About global defence programs relevant to India (FCAS, GCAP, ToT)

3. Tag each article with a bucket:
   - "amca_program" — directly about AMCA, Indian fighter development, Kaveri engine
   - "key_players" — about DRDO, GTRE, HAL, Tata, L&T, Bharat Forge, Adani Defence, Reliance in DEFENCE context
   - "defence_tech" — defence technology, manufacturing, ToT, MRO, FCAS, GCAP, Make in India defence

4. CRITICAL: Preserve the original article URL.

OUTPUT valid JSON ONLY:
{
  "selected_articles": [
    {
      "url": "ORIGINAL_ARTICLE_URL_HERE",
      "title": "...",
      "bucket": "amca_program" | "key_players" | "defence_tech",
      "importance_score": 1-10,
      "key_facts": ["fact1", "fact2", "fact3"],
      "summary": "2-3 sentence summary preserving all numbers, dates, company names",
      "key_players_mentioned": ["DRDO", "HAL", ...],
      "amca_keywords_found": ["prototype", "engine", ...]
    }
  ]
}

Select ONLY genuinely relevant aerospace/defence articles. Better to return 3 good articles than 15 irrelevant ones.

ARTICLES:
"""


def _score_article(article):
    """Score an article using tiered keywords. Scores title + content only (not raw_content)."""
    title = article.get("title", "").lower()
    content = article.get("content", "").lower()
    text = title + " " + content

    t1_hits = [kw for kw in TIER1_AMCA_SPECIFIC if kw.lower() in text]
    t2_hits = [kw for kw in TIER2_HIGH_VALUE if kw.lower() in text]

    # Tier 3 only counted if Tier 1 or Tier 2 present
    t3_hits = []
    if t1_hits or t2_hits:
        t3_hits = [kw for kw in TIER3_CONTEXTUAL if kw.lower() in text]

    players_full = [p for p in KEY_PLAYERS if p.lower() in text]

    # Short names only if other signals present
    players_short = []
    if t1_hits or t2_hits or players_full:
        players_short = [p for p in KEY_PLAYERS_SHORT if p.lower() in text]

    score = (len(t1_hits) * 5) + (len(t2_hits) * 3) + (len(t3_hits) * 1) + \
            (len(players_full) * 4) + (len(players_short) * 1)

    all_keywords = t1_hits + t2_hits + t3_hits
    all_players = players_full + players_short

    return score, t1_hits, t2_hits, t3_hits, all_players, all_keywords


def _assign_bucket(t1_hits, t2_hits, players_found):
    """Assign article to a bucket based on keyword tiers."""
    amca_specific = {"AMCA", "Advanced Medium Combat Aircraft", "Kaveri engine",
                     "GTRE", "DRDO ADA", "ADA Bangalore", "AMCA Mark", "AMCA Mk",
                     "5th generation fighter India", "fifth generation fighter India",
                     "6th generation", "sixth generation"}

    if any(kw in amca_specific for kw in t1_hits):
        return "amca_program"
    if players_found:
        return "key_players"
    return "defence_tech"


def _try_get_gpt_client():
    """Try to get Azure OpenAI chat client. Returns (client, deployment) or (None, None)."""
    try:
        from utils.azure_client import get_azure_client, get_chat_deployment
        client = get_azure_client()
        deployment = get_chat_deployment()
        return client, deployment
    except Exception as e:
        print(f"  ⚠️  Azure OpenAI not available: {e}")
        return None, None


def _print_curated_articles(articles, mode):
    """Print curated articles summary."""
    print(f"\n  === CURATED ARTICLES ({mode}) ===")
    for article in articles:
        print(f"  [{article.get('bucket', '?')}] (Score: {article.get('importance_score', '?')}/10)")
        print(f"    Title: {article.get('title', 'N/A')}")
        print(f"    URL:   {article.get('url', 'N/A')}")
        if article.get("key_players_mentioned"):
            print(f"    Players: {', '.join(article['key_players_mentioned'])}")
        print()


def curate_articles_local(search_results, save_path="curated_articles.json"):
    """FALLBACK: Local keyword-based curation when GPT is unavailable."""
    print("  ⚠️  Using LOCAL keyword curation (GPT unavailable)...")

    scored_articles = []
    for article in search_results:
        score, t1, t2, t3, players, keywords = _score_article(article)
        if score == 0:
            continue

        bucket = _assign_bucket(t1, t2, players)
        importance = min(10, max(1, score // 2))
        content = article.get("content", "")
        summary = content[:400] + "..." if len(content) > 400 else content

        scored_articles.append({
            "url": article.get("url", ""),
            "title": article.get("title", "N/A"),
            "bucket": bucket,
            "importance_score": importance,
            "key_facts": [],
            "summary": summary,
            "key_players_mentioned": players,
            "amca_keywords_found": keywords,
        })

    scored_articles.sort(key=lambda x: x["importance_score"], reverse=True)
    selected = scored_articles[:15]
    result = {"selected_articles": selected}

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"  Curated {len(selected)} articles (local) -> {save_path}")

    _print_curated_articles(selected, "LOCAL")
    return result


def curate_articles_gpt(search_results, client, deployment, save_path="curated_articles.json"):
    """PRIMARY: GPT-based curation using gpt-5-nano."""
    # Pre-score to prioritize articles sent to GPT
    for article in search_results:
        score, _, _, _, _, _ = _score_article(article)
        article["_relevance_score"] = score

    search_results.sort(key=lambda x: x.get("_relevance_score", 0), reverse=True)

    # Build context — top 30 articles, content only (no raw_content noise)
    articles_text = ""
    for i, article in enumerate(search_results[:30], 1):
        content = article.get("content", "")[:2000]
        articles_text += (
            f"\n--- Article {i} ---\n"
            f"URL: {article['url']}\n"
            f"Title: {article.get('title', 'N/A')}\n"
            f"Published: {article.get('published_date', 'N/A')}\n"
            f"Content: {content}\n"
        )

    print("  Curating with GPT-5-nano...")
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are an Indian defence aerospace analyst. Output valid JSON only. Reject non-aerospace articles strictly."},
            {"role": "user", "content": CURATION_PROMPT + articles_text},
        ],
        response_format={"type": "json_object"},
        timeout=120,
    )
    result = json.loads(response.choices[0].message.content)

    for article in result.get("selected_articles", []):
        if not article.get("url"):
            article["url"] = "URL not available"

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"  Curated {len(result.get('selected_articles', []))} articles -> {save_path}")

    _print_curated_articles(result.get("selected_articles", []), "GPT")
    return result


def curate_articles(search_results, save_path="curated_articles.json"):
    """Filter and rank search results for AMCA/Indian defence relevance.

    PRIMARY: GPT-5-nano | FALLBACK: Local keyword scoring
    """
    client, deployment = _try_get_gpt_client()

    if client:
        try:
            return curate_articles_gpt(search_results, client, deployment, save_path)
        except Exception as e:
            print(f"  ⚠️  GPT curation failed: {type(e).__name__}: {e}")
            print(f"  Falling back to local keyword curation...")

    return curate_articles_local(search_results, save_path)
