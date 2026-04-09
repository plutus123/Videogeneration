"""Tavily-powered news search with whitelisted domains and weekly date filtering.

Supports AMCA-related keyword search and key player/stakeholder/vendor search.
Date filtering: Monday of current week → today (weekly window).

Post-search pre-filtering: Discards obviously non-aerospace articles
BEFORE they reach GPT curation, using keyword-based scoring.
"""

import os
import json
import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Whitelisted domains (news + government)
# ---------------------------------------------------------------------------
DEFAULT_WHITELIST = [
    # Indian news / defence portals
    "defence.in",
    "defencenews.in",
    "idrw.org",
    "aljazeera.com",
    "economictimes.indiatimes.com",
    "m.economictimes.com",
    "geaerospace.com",
    "manufacturingtodayindia.com",
    "storyboard18.com",
    "defencewatch.in",
    "thehindu.com",
    "timesofindia.indiatimes.com",
    "newsonair.gov.in",
    "deccanherald.com",
    "business-standard.com",
    "indianexpress.com",
    "visionias.in",
    "reuters.com",
    "bloomberg.com",
    "flightglobal.com",
    "janes.com",
    "rolls-royce.com",
    "airbus.com",
    "boeing.com",
    "livemint.com",
    "ndtv.com",
    "moneycontrol.com",
    "aninews.in",
    # Government websites (whitelisted)
    "pib.gov.in",
    "mod.gov.in",
    "mea.gov.in",
]

# ---------------------------------------------------------------------------
# AMCA-related keyword search queries (targeted, less noise)
# ---------------------------------------------------------------------------
AMCA_KEYWORD_QUERIES = [
    # Direct AMCA queries (highest priority)
    "AMCA fighter jet India latest news",
    "AMCA Advanced Medium Combat Aircraft India",
    "AMCA prototype test India 2026",
    "India 5th generation fighter aircraft",
    "India fifth generation stealth fighter",
    # Defence procurement & manufacturing (India-specific)
    "India defence procurement tenders RFI",
    "India defence manufacturing Make in India",
    "Atmanirbhar Bharat defence aerospace",
    "India defence export order",
    "Indian Air Force fighter aircraft new",
    # Competitor programs (directly relevant to AMCA context)
    "GCAP fighter jet contract",
    "FCAS future combat air system Europe",
    # Strategic defence tech (India focus)
    "India defence Transfer of Technology",
    "India fighter engine development Kaveri",
    "India defence test facility prototype",
]

# ---------------------------------------------------------------------------
# Key Player / Stakeholder / Vendor search queries
# ---------------------------------------------------------------------------
KEY_PLAYER_QUERIES = [
    "DRDO AMCA India fighter development",
    "GTRE Kaveri engine India",
    "HAL Hindustan Aeronautics fighter AMCA",
    "Tata Advanced Systems defence India",
    "L&T defence aerospace India contract",
    "Bharat Forge defence India",
    "Adani Defence India aerospace",
    "Reliance Defence India aerospace",
]

# Combine all queries
SEARCH_QUERIES = AMCA_KEYWORD_QUERIES + KEY_PLAYER_QUERIES

# ---------------------------------------------------------------------------
# Post-search pre-filter: reject obviously non-aerospace articles
# ---------------------------------------------------------------------------
# These words in title STRONGLY indicate irrelevant articles
REJECT_TITLE_PATTERNS = [
    r"\bTCS\b", r"\bInfosys\b", r"\bWipro\b", r"\bHCL Tech\b",
    r"\bcricket\b", r"\bIPL\b", r"\bbollywood\b", r"\bentertainment\b",
    r"\bcensus\b", r"\bagriculture\b", r"\bfarm fair\b", r"\bfertiliser\b",
    r"\bstock market\b", r"\bsensex\b", r"\bnifty\b", r"\bmutual fund\b",
    r"\bhome loan\b", r"\bEMI\b", r"\bpersonal finance\b",
    r"\breal estate\b", r"\bproperty\b",
    r"\bworkforce\b.*\bchurn\b", r"\btalent\b.*\battrition\b",
    r"\bjobs\b.*\bAI\b", r"\bAI\b.*\bjobs\b",
    r"\brepo rate\b", r"\bRBI\b.*\brate\b",
    r"\bharikishan\b", r"\bvidisha\b",
    r"\bBSE\b.*\bshares\b", r"\bshares\b.*\bmuted\b",
    r"\bIPO\b(?!.*(?:defence|aerospace|fighter|DRDO|HAL))",
]

# These words in title indicate RELEVANT articles (keep even if matched above)
KEEP_TITLE_PATTERNS = [
    r"\bAMCA\b", r"\bfighter\b", r"\bstealth\b", r"\bdefence\b", r"\bdefense\b",
    r"\baerospace\b", r"\bDRDO\b", r"\bHAL\b", r"\bGTRE\b", r"\bKaveri\b",
    r"\bGCAP\b", r"\bFCAS\b", r"\bdrone\b", r"\bunmanned\b", r"\bmissile\b",
    r"\bIndian Air Force\b", r"\bIndian Army\b", r"\bIndian Navy\b",
    r"\bBrahMos\b", r"\bTejas\b", r"\bwarship\b", r"\bsubmarine\b",
    r"\bfighter jet\b", r"\bcombat aircraft\b", r"\bweapon\b",
    r"\btorpedo\b", r"\bfrigate\b", r"\bdestroyer\b",
    r"\baircraft carrier\b", r"\bhelicopter\b.*\bmilitary\b",
    r"\bTransfer of Technology\b", r"\bMake in India\b.*\bdefence\b",
    r"\bdefence export\b", r"\bdefence procurement\b",
    r"\bRolls.Royce\b", r"\bGE Aerospace\b", r"\bSafran\b",
]


def _is_aerospace_relevant(title):
    """Quick check: is this title about aerospace/defence?

    Returns True if article should PASS (keep), False if it should be REJECTED.
    """
    title_lower = title.lower()

    # First check: if title matches a KEEP pattern, always pass
    for pattern in KEEP_TITLE_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return True

    # Second check: if title matches a REJECT pattern, reject
    for pattern in REJECT_TITLE_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return False

    # Default: pass through to GPT curation (let GPT decide)
    return True


def _get_tavily_client():
    """Create Tavily client. Returns None if API key not set."""
    try:
        from tavily import TavilyClient
    except ImportError:
        print("ERROR: tavily-python not installed. Run: pip install tavily-python")
        return None
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        print("ERROR: TAVILY_API_KEY not set in .env")
        return None
    return TavilyClient(api_key=api_key)


def get_weekly_date_range():
    """Calculate the Monday→today date range for current week filtering.

    Example: If today is Friday April 10, returns:
        monday = April 6 (Monday)
        today  = April 10 (Friday)
        days_back = 4  (Friday minus Monday)

    Returns:
        Tuple of (monday_date, today_date, days_back)
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # weekday(): Monday=0, Tuesday=1, ..., Sunday=6
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    # days_back is used by Tavily: how many days back from today to search
    # We want Mon→today, so days_back = days_since_monday
    # But on Monday itself, days_back=0 means "today only", so use at least 1
    days_back = max(days_since_monday, 1)
    return monday, today, days_back


def search_aviation_news(
    queries=None,
    whitelist=None,
    days_back=None,
    max_results_per_query=5,
    save_path="tavily_results.json",
):
    """Search whitelisted sites for AMCA/defence news within the current week.

    Date filtering:
        Uses Monday of current week → today as the search window.
        The `days_back` parameter is auto-calculated to match this weekly window
        unless explicitly overridden.

    Post-search pre-filtering:
        Discards obviously non-aerospace articles BEFORE sending to GPT curation.

    Args:
        queries:   List of search query strings. Defaults to SEARCH_QUERIES.
        whitelist: List of domain strings. Defaults to DEFAULT_WHITELIST.
        days_back: How many days back to search. Auto-calculated if None.
        max_results_per_query: Max results per query from Tavily.
        save_path: Where to save raw search results.

    Returns:
        List of unique article dicts: {url, title, content, score, published_date, domain}
    """
    client = _get_tavily_client()
    if not client:
        return []

    queries = queries or SEARCH_QUERIES
    whitelist = whitelist or DEFAULT_WHITELIST

    # Calculate weekly date range
    monday, today, auto_days_back = get_weekly_date_range()
    if days_back is None:
        days_back = auto_days_back

    print(f"  Date filter: {monday.strftime('%A %d %B %Y')} → {today.strftime('%A %d %B %Y')} (days_back={days_back})")

    all_results = []
    seen_urls = set()

    for query in queries:
        print(f"  Searching: {query}")
        try:
            response = client.search(
                query=query,
                search_depth="advanced",
                topic="news",
                max_results=max_results_per_query,
                include_domains=whitelist,
                days=days_back,
                include_raw_content=True,
            )
            results = response.get("results", [])
            for r in results:
                url = r.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                domain = urlparse(url).netloc.replace("www.", "")
                all_results.append({
                    "url": url,
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "raw_content": r.get("raw_content", ""),
                    "score": r.get("score", 0),
                    "published_date": r.get("published_date", ""),
                    "domain": domain,
                })
            print(f"    Found {len(results)} results ({len(seen_urls)} unique total)")
        except Exception as e:
            print(f"    Search failed for '{query}': {type(e).__name__}: {e}")

    # ─── Post-filter 1: Date window (Mon→today) ─────────────────────
    filtered_results = []
    for article in all_results:
        pub = article.get("published_date", "")
        if pub:
            try:
                # Tavily returns RFC-2822 dates like "Mon, 06 Apr 2026 02:39:09 GMT"
                try:
                    pub_date = parsedate_to_datetime(pub).replace(tzinfo=None)
                except Exception:
                    # Fallback to ISO format
                    pub_date = datetime.fromisoformat(pub.replace("Z", "+00:00")).replace(tzinfo=None)
                if pub_date.date() < monday.date():
                    print(f"    ✗ Date-filtered: {article.get('title', '')[:60]} [{pub}]")
                    continue
            except (ValueError, TypeError):
                pass  # If date parsing fails, keep the article
        filtered_results.append(article)

    print(f"\n  Date filter: {len(all_results)} → {len(filtered_results)} articles")

    # ─── Post-filter 2: Aerospace relevance (title-based) ───────────
    aerospace_results = []
    rejected_count = 0
    for article in filtered_results:
        title = article.get("title", "")
        if _is_aerospace_relevant(title):
            aerospace_results.append(article)
        else:
            rejected_count += 1
            print(f"    ✗ Non-aerospace: {title[:70]}")

    print(f"  Aerospace filter: {len(filtered_results)} → {len(aerospace_results)} articles ({rejected_count} rejected)")
    all_results = aerospace_results

    # Sort by relevance score descending
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Save raw results
    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({
                "search_date": datetime.now().isoformat(),
                "week_start": monday.strftime("%Y-%m-%d"),
                "week_end": today.strftime("%Y-%m-%d"),
                "days_back": days_back,
                "total_results": len(all_results),
                "queries_used": queries,
                "results": all_results,
            }, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(all_results)} search results to {save_path}")

    return all_results


def load_whitelist_from_config(config_path="urls_config.json"):
    """Extract unique domains from urls_config.json to build whitelist."""
    domains = set(DEFAULT_WHITELIST)
    try:
        with open(config_path) as f:
            config = json.load(f)
        for category, articles in config.get("categories", {}).items():
            for article in articles:
                url = article.get("url", "")
                if url:
                    parsed = urlparse(url)
                    domain = parsed.netloc.replace("www.", "").replace("m.", "")
                    if domain:
                        domains.add(domain)
    except Exception:
        pass
    return list(domains)
