"""Tavily-powered news search for AMCA/Indian defence aerospace.

Covers ALL user-specified search dimensions:
  1. AMCA-specific direct queries
  2. All AMCA-related technology & procurement keyword queries
  3. Key player/stakeholder/vendor queries

Date filtering: Quarterly (90 days) by default.
No hardcoded pre-filtering — the LLM curation agent handles intelligent filtering.
"""

import os
import json
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Whitelisted domains (news + government + defence portals)
# ---------------------------------------------------------------------------
DEFAULT_WHITELIST = [
    # Indian news / defence portals
    "defence.in",
    "defencenews.in",
    "idrw.org",
    "defencewatch.in",
    "indiandefencereview.com",
    "defencexp.com",
    "forceindia.net",
    "bharatshakti.in",
    "spsmai.com",
    "spsnavalforces.com",
    "spslandforces.com",
    "spsaviation.com",
    # Major Indian news outlets
    "economictimes.indiatimes.com",
    "m.economictimes.com",
    "timesofindia.indiatimes.com",
    "thehindu.com",
    "hindustantimes.com",
    "indianexpress.com",
    "business-standard.com",
    "livemint.com",
    "ndtv.com",
    "moneycontrol.com",
    "theprint.in",
    "wionews.com",
    "news18.com",
    "firstpost.com",
    "deccanherald.com",
    "newsonair.gov.in",
    "aninews.in",
    # Industry / trade media
    "geaerospace.com",
    "manufacturingtodayindia.com",
    "storyboard18.com",
    "visionias.in",
    "aljazeera.com",
    # International defence / aerospace
    "reuters.com",
    "bloomberg.com",
    "flightglobal.com",
    "janes.com",
    "defensenews.com",
    "aviationweek.com",
    "thedrive.com",
    "bulgarianmilitary.com",
    "eurasiantimes.com",
    # OEM / Industry sites
    "rolls-royce.com",
    "airbus.com",
    "boeing.com",
    "safran-group.com",
    "hal-india.co.in",
    "larsentoubro.com",
    "bharatforge.com",
    "bel-india.in",
    "midhani-india.in",
    "ptcindustries.com",
    # Government websites
    "pib.gov.in",
    "mod.gov.in",
    "mea.gov.in",
    "drdo.gov.in",
    "ada.gov.in",
]

# ---------------------------------------------------------------------------
# AMCA DIRECT search queries
# ---------------------------------------------------------------------------
# These run WITHOUT domain restriction to catch niche stories from any source
AMCA_DIRECT_QUERIES = [
    "AMCA fighter jet India latest news",
    "AMCA Advanced Medium Combat Aircraft India update",
    "AMCA prototype development India ADA",
    "AMCA Mk1 Mk2 India stealth fighter engine",
    "AMCA consortium shortlisting India L&T Tata Bharat Forge",
    "AMCA HAL exclusion consortium bid India",
    "India 5th generation fighter aircraft AMCA stealth",
    "India fifth generation stealth fighter development DRDO",
    "India 6th generation fighter programme join",
    "AMCA stealth engine intake aerodynamic breakthrough",
    "AMCA stealth missile Astra folding fin internal",
    "AMCA budget Rs 150 billion prototype funding India",
    "HAL Su-57 India co-production stealth fighter",
    "India fighter jet race private sector AMCA",
]

# ---------------------------------------------------------------------------
# ALL AMCA-related keyword queries
# User-specified keywords:
#   Tenders, RFI, RFQ, airframe, engine, Thrust, 5th/6th Gen tech,
#   Transfer of Technology, prototype, MRO, manufacturing unit, R&D, R&T,
#   engine production, Test bed, Test facility, Assembly line,
#   Make in India, Self Reliance, Supply chain
# ---------------------------------------------------------------------------
AMCA_KEYWORD_QUERIES = [
    # Tenders, RFI, RFQ
    "India defence tenders aerospace fighter RFI",
    "India defence RFQ aerospace procurement",
    "India defence RFP fighter aircraft bid",
    # Airframe
    "India fighter aircraft airframe development indigenous",
    "India airframe manufacturing aerospace defence",
    # Engine, Thrust, Engine Production
    "India defence engine development thrust fighter",
    "Kaveri engine GTRE India latest",
    "India jet engine production manufacturing indigenous",
    "India aero engine development programme",
    "GE F414 engine India Transfer of Technology",
    "Safran engine India AMCA co-development",
    # 5th/6th Gen tech
    "India stealth technology 5th generation fighter",
    "sixth generation fighter aircraft technology India",
    "India stealth fighter radar evading technology",
    # Transfer of Technology
    "India defence Transfer of Technology aerospace deal",
    "India ToT defence agreement aerospace",
    # Prototype
    "India defence prototype fighter aircraft development",
    "AMCA prototype ADA DRDO development",
    # MRO
    "India defence MRO maintenance repair overhaul",
    "India aerospace MRO facility expansion",
    # Manufacturing unit, Assembly line
    "India defence manufacturing unit aerospace new",
    "India defence assembly line fighter aircraft production",
    "India defence production facility aerospace",
    # R&D, R&T
    "India defence R&D research development aerospace",
    "India defence research technology aerospace innovation",
    "ADA DRDO research AMCA stealth technology",
    # Test bed, Test facility
    "India defence test bed test facility aerospace",
    "India aerospace wind tunnel testing facility",
    "India defence testing facility prototype validation",
    # Make in India, Self Reliance
    "Make in India defence aerospace manufacturing latest",
    "Atmanirbhar Bharat defence self reliance aerospace",
    "India defence indigenisation self reliance programme",
    # Supply chain
    "India defence supply chain aerospace component",
    "India defence vendor supply ecosystem aerospace",
    # Defence export
    "India defence export order aerospace latest",
    "India defence export deal contract",
    # Weapons / Missiles for AMCA
    "Astra missile India AMCA integration",
    "Astra Mk2 Mk3 India BVRAAM ramjet",
    "India air-to-air missile stealth fighter internal carriage",
    # Materials / Forging
    "India aerospace materials titanium superalloy indigenous",
    "India defence forging aerospace component manufacturing",
    "PTC Industries Aerolloy titanium forging India aerospace",
    "MIDHANI airworthiness certification aero engine alloy India",
    "India open die forging aerospace superalloy titanium",
    # Budget / Financial
    "India defence budget FY27 capital outlay aerospace",
    "India defence capital expenditure Make in India",
]

# ---------------------------------------------------------------------------
# Key Player / Stakeholder / Vendor search queries
# ---------------------------------------------------------------------------
KEY_PLAYER_QUERIES = [
    "DRDO AMCA India fighter development latest",
    "DRDO ADA Aeronautical Development Agency India",
    "GTRE Kaveri engine India 120kN thrust development",
    "GTRE EOI aero engine development production partner India",
    "HAL Hindustan Aeronautics fighter Tejas AMCA order",
    "HAL India defence aerospace contract backlog",
    "Tata Advanced Systems TASL defence India AMCA bid",
    "L&T defence aerospace India contract order",
    "L&T BEL joint venture AMCA consortium India",
    "Bharat Forge defence India aerospace forging titanium",
    "Bharat Forge BEML Data Patterns AMCA consortium",
    "Adani Defence India aerospace manufacturing Leonardo",
    "Reliance Defence India aerospace",
    "BEL Bharat Electronics defence India order radar",
    "Mazagon Dock shipbuilding India defence naval submarine",
    "PTC Industries Aerolloy titanium forging aerospace India",
    "PTC Industries Lucknow intelligent forging system",
    "MIDHANI India aero engine alloy airworthiness certification",
    "GE Aerospace India F414 engine $1.5 billion deal ToT",
    "GE F414 HAL co-production technology transfer India",
    "Safran India AMCA Mk2 engine $7 billion co-development",
    "Safran GTRE engine joint venture 110kN 140kN India",
    "Rolls-Royce India fighter engine AMCA push",
]

# Combine all queries
SEARCH_QUERIES = AMCA_DIRECT_QUERIES + AMCA_KEYWORD_QUERIES + KEY_PLAYER_QUERIES


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


def get_quarterly_date_range():
    """Calculate a 90-day (quarterly) lookback window.

    Returns:
        Tuple of (start_date, today_date, days_back)
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=90)
    return start, today, 90


def get_weekly_date_range():
    """Calculate the Monday→today date range for current week filtering.

    Returns:
        Tuple of (monday_date, today_date, days_back)
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    days_back = max(days_since_monday, 1)
    return monday, today, days_back


def search_aviation_news(
    queries=None,
    whitelist=None,
    days_back=None,
    max_results_per_query=10,
    save_path="tavily_results.json",
    date_mode="quarter",
):
    """Search whitelisted sites for AMCA/defence news.

    No hardcoded pre-filtering — all articles that Tavily returns from the
    whitelisted domains are passed through. The LLM curation agent does the
    intelligent filtering downstream.

    Args:
        queries:   List of search query strings. Defaults to SEARCH_QUERIES.
        whitelist: List of domain strings. Defaults to DEFAULT_WHITELIST.
        days_back: How many days back to search. Auto-calculated if None.
        max_results_per_query: Max results per query from Tavily (default: 10).
        save_path: Where to save raw search results.
        date_mode: "quarter" (default, 90 days) or "week" (Monday-today).

    Returns:
        List of unique article dicts: {url, title, content, score, published_date, domain}
    """
    client = _get_tavily_client()
    if not client:
        return []

    queries = queries or SEARCH_QUERIES
    whitelist = whitelist or DEFAULT_WHITELIST

    # Calculate date range based on mode
    if date_mode == "week":
        start_date, today, auto_days_back = get_weekly_date_range()
    else:
        start_date, today, auto_days_back = get_quarterly_date_range()

    if days_back is None:
        days_back = auto_days_back

    print(f"  Date range: {start_date.strftime('%d %B %Y')} → {today.strftime('%d %B %Y')} ({days_back} days)")

    all_results = []
    seen_urls = set()

    def _run_queries(query_list, use_whitelist, label):
        """Run a batch of queries and collect results."""
        print(f"\n  --- {label}: {len(query_list)} queries, max {max_results_per_query} each ---")
        for query in query_list:
            print(f"  Searching: {query}")
            try:
                search_params = {
                    "query": query,
                    "search_depth": "advanced",
                    "topic": "news",
                    "max_results": max_results_per_query,
                    "days": days_back,
                    "include_raw_content": True,
                }
                if use_whitelist:
                    search_params["include_domains"] = whitelist
                response = client.search(**search_params)
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

    # PASS 1: AMCA-specific queries WITHOUT domain restriction
    # These are highly specific — we want to catch niche stories from any source
    _run_queries(AMCA_DIRECT_QUERIES, use_whitelist=False, label="Pass 1: AMCA-specific (open web)")

    # PASS 2: Keyword + key player queries WITH domain whitelist
    # These are broader — we restrict to trusted sources for quality
    _run_queries(AMCA_KEYWORD_QUERIES + KEY_PLAYER_QUERIES, use_whitelist=True, label="Pass 2: Keywords + Players (whitelisted)")


    # ─── Post-filter: Date window only ───────────────────────────────
    # No content-based filtering — let the LLM curation agent handle that.
    filtered_results = []
    date_rejected = 0
    for article in all_results:
        pub = article.get("published_date", "")
        if pub:
            try:
                try:
                    pub_date = parsedate_to_datetime(pub).replace(tzinfo=None)
                except Exception:
                    pub_date = datetime.fromisoformat(pub.replace("Z", "+00:00")).replace(tzinfo=None)
                if pub_date.date() < start_date.date():
                    date_rejected += 1
                    continue
            except (ValueError, TypeError):
                pass  # If date parsing fails, keep the article
        filtered_results.append(article)

    print(f"\n  Post-filter: {len(all_results)} → {len(filtered_results)} articles ({date_rejected} date-rejected)")

    all_results = filtered_results

    # Sort by relevance score descending
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Save raw results
    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({
                "search_date": datetime.now().isoformat(),
                "date_range_start": start_date.strftime("%Y-%m-%d"),
                "date_range_end": today.strftime("%Y-%m-%d"),
                "days_back": days_back,
                "date_mode": date_mode,
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
