"""Excel export utility for Tavily search results and curated articles.

Produces a single .xlsx workbook with two sheets:
  - Sheet 1: "Tavily Search Results" — all raw articles from Tavily
  - Sheet 2: "Curated Articles"      — GPT-filtered articles with scores

Styled with headers, column widths, and hyperlinked URLs for readability.
"""

import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------
HEADER_FONT = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="1A2744", end_color="1A2744", fill_type="solid")
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)

DATA_FONT = Font(name="Calibri", size=10)
DATA_ALIGN = Alignment(vertical="top", wrap_text=True)
URL_FONT = Font(name="Calibri", size=10, color="0563C1", underline="single")

THIN_BORDER = Border(
    left=Side(style="thin", color="D9D9D9"),
    right=Side(style="thin", color="D9D9D9"),
    top=Side(style="thin", color="D9D9D9"),
    bottom=Side(style="thin", color="D9D9D9"),
)

# Alternating row fill
ROW_FILL_ALT = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")


def _style_header(ws, headers, col_widths):
    """Write header row with styling."""
    for col_idx, (header, width) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGN
        cell.border = THIN_BORDER
        ws.column_dimensions[cell.column_letter].width = width

    # Freeze header row
    ws.freeze_panes = "A2"


def _write_data_cell(ws, row, col, value, is_url=False):
    """Write a styled data cell."""
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = URL_FONT if is_url else DATA_FONT
    cell.alignment = DATA_ALIGN
    cell.border = THIN_BORDER

    # Alternating row colors
    if row % 2 == 0:
        cell.fill = ROW_FILL_ALT

    # Make URLs clickable
    if is_url and value and isinstance(value, str) and value.startswith("http"):
        cell.hyperlink = value

    return cell


def _write_tavily_sheet(wb, search_results):
    """Write Tavily search results to the first sheet."""
    ws = wb.active
    ws.title = "Tavily Search Results"

    headers = [
        "#", "Title", "URL", "Domain", "Published Date",
        "Tavily Score", "Content Preview"
    ]
    col_widths = [5, 50, 45, 20, 22, 14, 70]
    _style_header(ws, headers, col_widths)

    for i, article in enumerate(search_results, 1):
        row = i + 1
        content = article.get("content", "")
        # Trim content to first 500 chars for readability
        preview = content[:500].replace("\n", " ").strip()
        if len(content) > 500:
            preview += "..."

        _write_data_cell(ws, row, 1, i)
        _write_data_cell(ws, row, 2, article.get("title", "N/A"))
        _write_data_cell(ws, row, 3, article.get("url", ""), is_url=True)
        _write_data_cell(ws, row, 4, article.get("domain", ""))
        _write_data_cell(ws, row, 5, article.get("published_date", ""))
        _write_data_cell(ws, row, 6, round(article.get("score", 0), 4))
        _write_data_cell(ws, row, 7, preview)

    # Auto-filter
    ws.auto_filter.ref = f"A1:G{len(search_results) + 1}"
    return ws


def _write_curated_sheet(wb, curated_data):
    """Write curated articles to the second sheet."""
    ws = wb.create_sheet("Curated Articles")

    headers = [
        "#", "Title", "URL", "Bucket", "Importance Score",
        "Summary", "Key Facts", "Key Players", "AMCA Keywords"
    ]
    col_widths = [5, 45, 45, 18, 16, 60, 50, 30, 30]
    _style_header(ws, headers, col_widths)

    articles = curated_data.get("selected_articles", [])
    for i, article in enumerate(articles, 1):
        row = i + 1

        # Format lists as newline-separated strings
        key_facts = "\n".join(f"• {f}" for f in article.get("key_facts", []))
        key_players = ", ".join(article.get("key_players_mentioned", []))
        amca_keywords = ", ".join(article.get("amca_keywords_found", []))

        _write_data_cell(ws, row, 1, i)
        _write_data_cell(ws, row, 2, article.get("title", "N/A"))
        _write_data_cell(ws, row, 3, article.get("url", ""), is_url=True)
        _write_data_cell(ws, row, 4, article.get("bucket", ""))
        _write_data_cell(ws, row, 5, article.get("importance_score", 0))
        _write_data_cell(ws, row, 6, article.get("summary", ""))
        _write_data_cell(ws, row, 7, key_facts)
        _write_data_cell(ws, row, 8, key_players)
        _write_data_cell(ws, row, 9, amca_keywords)

    # Auto-filter
    if articles:
        ws.auto_filter.ref = f"A1:I{len(articles) + 1}"
    return ws


def export_to_excel(search_results, curated_data, output_path):
    """Export Tavily search results and curated articles to a styled Excel workbook.

    Args:
        search_results: List of article dicts from Tavily search.
        curated_data:   Dict with 'selected_articles' key from curation agent.
        output_path:    Path for the output .xlsx file.

    Returns:
        Path to the created Excel file.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    wb = Workbook()

    # Sheet 1: Raw Tavily results
    _write_tavily_sheet(wb, search_results)

    # Sheet 2: Curated articles
    _write_curated_sheet(wb, curated_data)

    wb.save(output_path)
    wb.close()

    num_search = len(search_results)
    num_curated = len(curated_data.get("selected_articles", []))
    print(f"  📊 Excel exported: {output_path}")
    print(f"     Sheet 1: {num_search} search results")
    print(f"     Sheet 2: {num_curated} curated articles")

    return output_path
