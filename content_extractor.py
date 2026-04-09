import json
import requests
import cloudscraper
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from utils.azure_client import get_azure_client, get_chat_deployment

# Government / protected domains that may need heavier scraping
GOV_DOMAINS = [
    "pib.gov.in",
    "mod.gov.in",
    "mea.gov.in",
]

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
})

_REMOVE_TAGS = {"script", "style", "nav", "header", "footer", "aside",
                "noscript", "svg", "form", "button", "iframe"}
_NOISE_CLASSES = {"sidebar", "widget", "advert", "promo", "related",
                  "comment", "social", "share", "newsletter", "popup"}


def _is_gov_domain(url: str) -> bool:
    """Check if a URL belongs to a government domain."""
    domain = urlparse(url).netloc.replace("www.", "")
    return any(d in domain for d in GOV_DOMAINS)


def _fetch_with_playwright(url: str, timeout: int = 30, stealth: bool = False) -> str | None:
    """LAST RESORT: Fetch page HTML using Playwright (headless Chromium).
    Heavy — only used when requests and cloudscraper fail.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("    Playwright not installed (optional). Skipping.")
        return None
    try:
        with sync_playwright() as p:
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
            browser = p.chromium.launch(headless=True, args=launch_args)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.6778.109 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
            )

            if stealth:
                page = context.new_page()
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.chrome = { runtime: {} };
                """)
            else:
                page = context.new_page()

            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print(f"    Playwright failed: {type(e).__name__}: {str(e)[:100]}")
        return None


def _extract_title(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", property="og:title")
    if meta and meta.get("content", "").strip():
        return meta["content"].strip()
    meta = soup.find("meta", attrs={"name": "twitter:title"})
    if meta and meta.get("content", "").strip():
        return meta["content"].strip()
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        h1_text = h1.get_text(strip=True)
        if 10 < len(h1_text) < 200:
            return h1_text
    title_tag = soup.find("title")
    if title_tag and title_tag.get_text(strip=True):
        raw = title_tag.get_text(strip=True)
        for sep in ["|", " - ", " – ", " — "]:
            if sep in raw:
                raw = raw.split(sep)[0].strip()
                break
        if len(raw) > 10:
            return raw
    return ""


def _extract_article_text(soup: BeautifulSoup) -> str:
    for tag in soup.find_all(_REMOVE_TAGS):
        tag.decompose()
    article_body = (
        soup.find("article")
        or soup.find("div", class_=lambda c: c and any(
            k in " ".join(c).lower()
            for k in ("article", "story", "post-content", "entry-content")
        ))
        or soup.find("div", {"role": "main"})
        or soup.find("main")
    )
    if article_body:
        for el in list(article_body.find_all(True)):
            if el.parent is None:
                continue
            classes = " ".join(el.get("class") or [])
            el_id = el.get("id") or ""
            combined = (classes + " " + el_id).lower()
            if any(n in combined for n in _NOISE_CLASSES):
                el.decompose()
    target = article_body if article_body else soup.body or soup
    text = target.get_text(separator="\n", strip=True)
    lines, prev = [], None
    for line in text.split("\n"):
        line = line.strip()
        if line and line != prev:
            lines.append(line)
            prev = line
    return "\n".join(lines)


def _parse_response(resp) -> dict | None:
    soup = BeautifulSoup(resp.text, "html.parser")
    title = _extract_title(soup)
    text = _extract_article_text(soup)
    if not text or len(text) < 100:
        return None
    return {"title": title, "content": text}


def _parse_html(html: str, url: str) -> dict | None:
    """Parse raw HTML string (e.g. from Playwright)."""
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)
    text = _extract_article_text(soup)
    if not text or len(text) < 100:
        return None
    return {"title": title or url, "content": text}


def _is_access_denied(result: dict | None) -> bool:
    """Check if the extracted content is an access denied page."""
    if not result:
        return True
    title = (result.get("title", "") or "").lower()
    content = (result.get("content", "") or "").lower()
    return "access denied" in title or "access denied" in content[:200]


def fetch_article(url: str, timeout: int = 30) -> dict | None:
    """Fetch and extract article content from a URL.

    Scraping chain (lightest first, heaviest last):
        1. requests (fast, no dependencies)
        2. cloudscraper (handles Cloudflare, still lightweight)
        3. Playwright (headless browser, heavy — LAST RESORT only)

    All sites go through the same chain. Gov sites are NOT special-cased
    to use Playwright first — they go through requests/cloudscraper first.
    """
    is_gov = _is_gov_domain(url)
    
    # --- Step 1: Try requests (fastest) ---
    try:
        resp = _SESSION.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        result = _parse_response(resp)
        if result and not _is_access_denied(result):
            if result["title"]:
                return result
            result["title"] = url
            return result
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 0
        if status != 403:
            print(f"    requests failed: HTTP {status}")
            # Don't fall through for non-403 errors unless it's a gov site
            if not is_gov:
                return None
    except Exception as e:
        print(f"    requests failed: {type(e).__name__}")

    # --- Step 2: Try cloudscraper (handles Cloudflare) ---
    print(f"    Trying cloudscraper...")
    try:
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        resp = scraper.get(url, timeout=timeout)
        resp.raise_for_status()
        result = _parse_response(resp)
        if result and not _is_access_denied(result):
            if not result["title"]:
                result["title"] = url
            return result
    except Exception as cs_e:
        print(f"    cloudscraper failed: {type(cs_e).__name__}")

    # --- Step 3: LAST RESORT — Playwright (heavy, headless browser) ---
    print(f"    Trying Playwright (last resort)...")
    html = _fetch_with_playwright(url, timeout=timeout, stealth=is_gov)
    if html:
        result = _parse_html(html, url)
        if result and not _is_access_denied(result):
            return result

    print(f"    All extraction methods failed for this URL")
    return None


def _summarize_article(title: str, content: str, category: str) -> str:
    client = get_azure_client()
    deployment = get_chat_deployment()
    prompt = (
        f"You are an aviation and defence industry analyst specializing in AMCA (Advanced Medium Combat Aircraft) "
        f"and Indian defence programs. "
        f"Summarize the following article in 150-300 words. "
        f"Preserve ALL key facts: numbers, dollar figures, percentages, dates, "
        f"company names, product names, and strategic details. "
        f"Focus on what matters for India's AMCA program, defence manufacturing, "
        f"and the key stakeholders (DRDO, GTRE, HAL, Tata, L&T, Bharat Forge, Adani Defence, Reliance).\n\n"
        f"Category: {category}\n"
        f"Title: {title}\n\n"
        f"Article:\n{content[:8000]}\n\n"
        f"Summary:"
    )
    try:
        resp = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            timeout=60,
        )
        summary = resp.choices[0].message.content.strip()
        refusal_phrases = [
            "i'm unable to", "i cannot provide", "i am unable to",
            "isn't a single article", "not a coherent article",
            "no body content", "category/search results page",
        ]
        if any(phrase in summary.lower() for phrase in refusal_phrases):
            return None
        return summary
    except Exception as e:
        print(f"    Summarization failed: {e}")
        return None


def extract_content(urls_config_path: str, save_path: str = "extracted_content.json"):
    with open(urls_config_path) as f:
        config = json.load(f)
    categories = config.get("categories", {})
    section_mapping = config.get("section_mapping", {})
    results = {}
    stats = {"fetched": 0, "failed": 0}
    for category, articles in categories.items():
        results[category] = []
        for article in articles:
            url = article["url"]
            print(f"  [{category}] {url[:80]}...")
            result = fetch_article(url)
            if not result:
                stats["failed"] += 1
                print(f"    FAILED")
                results[category].append({
                    "url": url, "title": url,
                    "source": "failed", "content": ""
                })
            else:
                title = result["title"]
                content = result["content"]
                print(f"    OK: {title[:60]}... ({len(content)} chars)")
                print(f"    Summarizing for aviation context...")
                summary = _summarize_article(title, content, category)
                if not summary:
                    stats["failed"] += 1
                    print(f"    Summarization rejected (not a real article)")
                    results[category].append({
                        "url": url, "title": url,
                        "source": "failed", "content": ""
                    })
                else:
                    stats["fetched"] += 1
                    print(f"    Summary: {len(summary)} chars")
                    results[category].append({
                        "url": url, "title": title,
                        "source": "live", "content": summary
                    })
    save_data = {
        "stats": stats,
        "section_mapping": section_mapping,
        "articles": results,
    }
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {save_path}")
    print(f"Stats: {stats['fetched']} fetched, {stats['failed']} failed")
    return results, section_mapping


def _resolve_categories(section_cfg):
    if isinstance(section_cfg, list):
        return section_cfg, ""
    return section_cfg.get("categories", []), section_cfg.get("narration_hint", "")


def build_context(fetched_data: dict, section_mapping: dict) -> str:
    parts = []
    section_idx = 1
    total_sections = len(section_mapping)
    parts.append(f"\n=== VIDEO HAS {total_sections} SECTIONS (in this exact order) ===")
    for section_name, section_cfg in section_mapping.items():
        categories, narration_hint = _resolve_categories(section_cfg)
        article_count = sum(
            1 for cat in categories
            if cat in fetched_data
            for a in fetched_data[cat]
            if a["content"]
        )
        parts.append(f"\n--- SECTION {section_idx}: {section_name.upper()} ({article_count} articles, allocate {max(1, article_count)} scenes) ---")
        if narration_hint:
            parts.append(f"NARRATION STYLE: {narration_hint}")
        for cat in categories:
            if cat not in fetched_data:
                continue
            parts.append(f"\nCategory: {cat}")
            for article in fetched_data[cat]:
                if article["content"]:
                    parts.append(
                        f"\nARTICLE: {article['title']}\n"
                        f"Source: {article['url']}\n"
                        f"{article['content']}\n"
                    )
        section_idx += 1
    return "\n".join(parts)
