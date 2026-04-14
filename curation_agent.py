"""Curation agent: AlphaSense-grade content curation for AMCA and Indian defence aerospace.

Produces a structured intelligence report with:
  - Thematic sections (like AlphaSense: Consortium, Tech Breakthroughs, Engine, Strategy)
  - Citation-backed facts with [N] references
  - Source type classification (News, Press Release, Analyst Report)
  - Precise data preservation (dollar figures, percentages, dates)

Curation modes:
  - PRIMARY: GPT-5-nano (intelligent, context-aware structured curation)
  - FALLBACK: Local tiered keyword scoring (when GPT unavailable)
"""

import json
import os


# ---------------------------------------------------------------------------
# Tiered keyword system for local fallback scoring
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
    "Assembly line", "airframe", "Thrust",
    "Make in India defence", "Atmanirbhar Bharat defence", "Atmanirbhar Bharat",
    "Self Reliance defence", "combat aircraft India",
    "stealth fighter", "stealth aircraft",
    "defence manufacturing India", "defence procurement India",
    "defence export India",
    "Indian Air Force", "IAF", "Indian Navy defence", "Indian Army defence",
    "Indian Army unmanned", "Indian Army technology",
    "India defence budget", "India military",
    "Tejas fighter", "Tejas Mark", "LCA Tejas",
    "BrahMos", "Akash missile", "Astra missile",
    "MRO", "engine production", "R&D", "R&T",
    "manufacturing unit", "Supply chain",
    "titanium", "superalloy", "forging",
    "wind tunnel", "radar evading", "stealth technology",
    "F414", "Safran", "GE Aerospace",
]

# Tier 3: CONTEXTUAL — only count if Tier 1 or Tier 2 also matched (1 point each)
TIER3_CONTEXTUAL = [
    "engine", "defence", "defense", "aerospace", "aviation",
    "fighter", "combat aircraft", "indigenous", "self reliance",
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
    "PTC Industries", "MIDHANI",
    "Data Patterns", "BEML",
    "Indian Air Force", "Indian Army", "Indian Navy",
    "ADA", "Aeronautical Development Agency",
]

# Key Players — short names (1 point, only counted if other signals present)
KEY_PLAYERS_SHORT = [
    "Tata", "L&T", "Adani", "Reliance",
]


# ---------------------------------------------------------------------------
# AlphaSense-style GPT Curation Prompt
# ---------------------------------------------------------------------------
CURATION_PROMPT = """You are a senior defence intelligence analyst at an Indian aerospace company.
Your task is to curate news articles into an AlphaSense-quality structured intelligence report
focused on India's AMCA (Advanced Medium Combat Aircraft) program and Indian defence aerospace.

=== FILTERING RULES ===
1. KEEP articles about:
   - India's AMCA program, Indian fighter/combat aircraft, Indian defence programs
   - Key Indian defence stakeholders: DRDO, ADA, GTRE, HAL, Tata Advanced Systems, L&T, Bharat Forge, Adani Defence, Reliance Defence, BEL, MIDHANI, PTC Industries, Data Patterns, BEML
   - AMCA-related topics: tenders, RFI, RFQ, RFP, airframe, engine, thrust, prototype, test facilities, assembly lines, MRO, R&D, supply chain
   - Engine programs: Kaveri, GE F414, Safran joint venture, Rolls-Royce
   - Strategic: Transfer of Technology, Make in India, Atmanirbhar Bharat, self reliance, defence exports
   - Weapons integration: Astra missile, BrahMos, stealth-ready weapons
   - Materials & manufacturing: titanium, superalloy, forging, aerospace materials

2. REJECT articles that are:
   - Non-aerospace (HR, jobs, census, finance, entertainment, cricket, politics, stock prices)
   - About companies in NON-DEFENCE contexts (telecom, infrastructure, IT)
   - Generic international defence news with ZERO India angle
   - Paywalled with no readable content

=== OUTPUT STRUCTURE (AlphaSense-style) ===
Organize curated articles into THEMATIC SECTIONS. Do NOT just list articles — group them by theme.

OUTPUT valid JSON ONLY:
{
  "report_title": "AMCA & Indian Defence Aerospace Intelligence Report — [Quarter/Period]",
  "thematic_sections": [
    {
      "section_title": "e.g. Consortium Shortlisting & Industrial Realignment",
      "section_summary": "2-3 sentence executive summary of this section's key developments",
      "articles": [
        {
          "citation_number": 1,
          "url": "ORIGINAL_ARTICLE_URL",
          "title": "Article title",
          "published_date": "date if available",
          "source_type": "News" | "Press Release" | "Government" | "Industry Report",
          "source_name": "e.g. Business Standard, PIB, Reuters",
          "importance_score": 1-10,
          "key_facts": [
            "Fact 1 with EXACT numbers, dates, dollar figures preserved",
            "Fact 2 — cite specific company names, percentages",
            "Fact 3"
          ],
          "summary": "3-5 sentence detailed summary. Preserve ALL numbers, dates, company names, dollar figures, percentages.",
          "key_players_mentioned": ["DRDO", "HAL", ...],
          "amca_keywords_found": ["prototype", "engine", "ToT", ...]
        }
      ]
    }
  ],
  "executive_summary": "Comprehensive 200-word executive summary covering ALL key developments across all sections. Written in authoritative analyst tone.",
  "citations": [
    {
      "citation_number": 1,
      "source_type": "News",
      "source_name": "Business Standard",
      "date": "04 Feb 2026",
      "title": "Full article title",
      "url": "full URL"
    }
  ]
}

=== THEMATIC SECTIONS TO USE ===
Group articles into these sections as applicable (skip sections with zero articles):
1. "AMCA Program Updates & Consortium Developments"
2. "Engine Procurement & Foreign Collaboration"
3. "Technical Breakthroughs & Stealth Integration"
4. "Key Player Updates (DRDO, HAL, Tata, L&T, Bharat Forge, etc.)"
5. "Defence Manufacturing, MRO & Supply Chain"
6. "Strategic & Policy Developments (Make in India, Defence Budget, Exports)"
7. "Weapons Systems & Platform Integration"
8. "Materials, Testing & Infrastructure"

=== CRITICAL RULES ===
- Preserve ALL numbers: dollar figures ($1.5B), percentages (80% ToT), Indian Rupees (Rs150bn)
- Preserve ALL dates, company names, product names
- Each article gets a unique citation_number starting from 1
- Better to return 5 high-quality articles than 20 low-quality ones
- Source type: "News" for news articles, "Press Release" for company PRs, "Government" for pib.gov.in/mod.gov.in

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


def _print_curated_articles(result, mode):
    """Print curated articles summary."""
    # Handle both old flat format and new AlphaSense format
    if "thematic_sections" in result:
        print(f"\n  === CURATED REPORT ({mode}) ===")
        print(f"  Title: {result.get('report_title', 'N/A')}")
        total = 0
        for section in result.get("thematic_sections", []):
            articles = section.get("articles", [])
            total += len(articles)
            print(f"\n  📑 {section.get('section_title', '?')} ({len(articles)} articles)")
            for article in articles:
                print(f"    [{article.get('citation_number', '?')}] (Score: {article.get('importance_score', '?')}/10)")
                print(f"        {article.get('title', 'N/A')}")
                print(f"        {article.get('url', 'N/A')}")
                if article.get("key_players_mentioned"):
                    print(f"        Players: {', '.join(article['key_players_mentioned'])}")
        print(f"\n  Total articles: {total}")
    else:
        # Legacy flat format
        print(f"\n  === CURATED ARTICLES ({mode}) ===")
        for article in result.get("selected_articles", []):
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

    _print_curated_articles(result, "LOCAL")
    return result


def curate_articles_gpt(search_results, client, deployment, save_path="curated_articles.json"):
    """PRIMARY: GPT-based AlphaSense-style curation using gpt-5-nano."""
    # Pre-score to prioritize articles sent to GPT
    for article in search_results:
        score, _, _, _, _, _ = _score_article(article)
        article["_relevance_score"] = score

    search_results.sort(key=lambda x: x.get("_relevance_score", 0), reverse=True)

    # Build context — send articles with full content (no truncation)
    articles_text = ""
    for i, article in enumerate(search_results[:50], 1):
        content = article.get("content", "")
        articles_text += (
            f"\n--- Article {i} ---\n"
            f"URL: {article['url']}\n"
            f"Title: {article.get('title', 'N/A')}\n"
            f"Published: {article.get('published_date', 'N/A')}\n"
            f"Domain: {article.get('domain', 'N/A')}\n"
            f"Content: {content}\n"
        )

    print("  Curating with GPT-5-nano (AlphaSense-style)...")
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are a senior Indian defence aerospace analyst producing AlphaSense-quality structured intelligence reports. Output valid JSON only. Reject non-aerospace articles strictly. Preserve ALL numbers, dates, and company names exactly as they appear."},
            {"role": "user", "content": CURATION_PROMPT + articles_text},
        ],
        response_format={"type": "json_object"},
        timeout=180,
    )
    result = json.loads(response.choices[0].message.content)

    # Ensure all articles have URLs
    for section in result.get("thematic_sections", []):
        for article in section.get("articles", []):
            if not article.get("url"):
                article["url"] = "URL not available"

    # Also build a flat selected_articles list for backward compatibility
    all_articles = []
    for section in result.get("thematic_sections", []):
        for article in section.get("articles", []):
            article["bucket"] = section.get("section_title", "defence_tech")
            all_articles.append(article)
    result["selected_articles"] = all_articles

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"  Curated {len(all_articles)} articles -> {save_path}")

    _print_curated_articles(result, "GPT")
    return result


def curate_articles(search_results, save_path="curated_articles.json"):
    """Filter and rank search results for AMCA/Indian defence relevance.

    PRIMARY: GPT-5-nano (AlphaSense-style) | FALLBACK: Local keyword scoring
    """
    client, deployment = _try_get_gpt_client()

    if client:
        try:
            return curate_articles_gpt(search_results, client, deployment, save_path)
        except Exception as e:
            print(f"  ⚠️  GPT curation failed: {type(e).__name__}: {e}")
            print(f"  Falling back to local keyword curation...")

    return curate_articles_local(search_results, save_path)
