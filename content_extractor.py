import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
})

_REMOVE_TAGS = {"script", "style", "nav", "header", "footer", "aside",
                "noscript", "svg", "form", "button", "iframe"}
_NOISE_CLASSES = {"sidebar", "widget", "advert", "promo", "related",
                  "comment", "social", "share", "newsletter", "popup"}


def _extract_article_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(_REMOVE_TAGS):
        tag.decompose()
    for el in list(soup.find_all(True)):
        if el.parent is None:
            continue
        classes = " ".join(el.get("class") or [])
        el_id = el.get("id") or ""
        combined = (classes + " " + el_id).lower()
        if any(n in combined for n in _NOISE_CLASSES):
            el.decompose()
    article_body = (
        soup.find("article") or
        soup.find("div", class_=lambda c: c and any(
            k in " ".join(c).lower() for k in ("article", "story", "post-content", "entry-content")
        )) or
        soup.find("div", {"role": "main"}) or
        soup.find("main")
    )
    target = article_body if article_body else soup.body or soup
    text = target.get_text(separator="\n", strip=True)
    lines = []
    prev = None
    for line in text.split("\n"):
        line = line.strip()
        if line and line != prev:
            lines.append(line)
            prev = line
    return "\n".join(lines)


def fetch_article(url: str, timeout: int = 20) -> str | None:
    try:
        resp = _SESSION.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        text = _extract_article_text(resp.text)
        if len(text) > 10000:
            text = text[:10000] + "\n[...truncated...]"
        return text
    except Exception:
        return None


def extract_content(urls_config_path: str, save_path: str = "extracted_content.json"):
    with open(urls_config_path) as f:
        config = json.load(f)
    categories = config.get("categories", {})
    section_mapping = config.get("section_mapping", {})
    results = {}
    stats = {"fetched": 0, "fallback": 0, "failed": 0}
    for category, articles in categories.items():
        results[category] = []
        for article in articles:
            url = article["url"]
            title = article.get("title", url)
            fallback = article.get("fallback_summary", "")
            print(f"  [{category}] {title[:70]}...")
            content = fetch_article(url)
            source = "live"
            if not content or len(content) < 100:
                if fallback:
                    content = fallback
                    source = "fallback"
                    print(f"    Using fallback ({len(fallback)} chars)")
                else:
                    content = ""
                    source = "none"
                    print(f"    No content available")
            if source == "live":
                stats["fetched"] += 1
                print(f"    Fetched OK ({len(content)} chars)")
            elif source == "fallback":
                stats["fallback"] += 1
            else:
                stats["failed"] += 1
            results[category].append({
                "url": url,
                "title": title,
                "source": source,
                "content": content
            })
    save_data = {
        "stats": stats,
        "section_mapping": section_mapping,
        "articles": results,
    }
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {save_path}")
    print(f"Stats: {stats['fetched']} fetched, {stats['fallback']} fallback, {stats['failed']} failed")
    return results, section_mapping


def load_extracted_content(path: str = "extracted_content.json"):
    with open(path) as f:
        data = json.load(f)
    return data["articles"], data["section_mapping"]


def build_context(fetched_data: dict, section_mapping: dict) -> str:
    parts = []
    for section_name, categories in section_mapping.items():
        parts.append(f"\nVIDEO SECTION: {section_name.upper()}")
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
    return "\n".join(parts)
