"""Tavily-powered news search with whitelisted domains and date filtering."""

import os
import json
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# Whitelisted domains extracted from urls_config.json
DEFAULT_WHITELIST = [
    "defence.in",
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
    "pib.gov.in",
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
]

# Search queries covering all importance criteria
SEARCH_QUERIES = [
    "Rolls-Royce aviation defence news",
    "Rolls-Royce engine order deal contract",
    "Rolls-Royce financial results revenue profit",
    "Rolls-Royce leadership CEO announcement",
    "civil aviation market update India",
    "defence aerospace market update India",
    "GE Aerospace Pratt Whitney Safran engine news",
    "aviation defence product launch update",
    "India defence procurement export deal",
    "SMR nuclear energy India update",
]


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


def search_aviation_news(
    queries=None,
    whitelist=None,
    days_back=7,
    max_results_per_query=5,
    save_path="tavily_results.json",
):
    """Search whitelisted sites for aviation/defence news from the past week.

    Args:
        queries:   List of search query strings. Defaults to SEARCH_QUERIES.
        whitelist: List of domain strings. Defaults to DEFAULT_WHITELIST.
        days_back: How many days back to search.
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

    # Sort by relevance score descending
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Save raw results
    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({
                "search_date": datetime.now().isoformat(),
                "days_back": days_back,
                "total_results": len(all_results),
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
