# AMCA Defence Intelligence Video Generator

Automated weekly video briefing pipeline for Indian aerospace & defence news. Searches, curates, and generates a 2-3 minute narrated video with infographic-style slides.

## Pipeline Flow

```
Tavily Search → Post-filter → GPT Curation → Scene Plan → Image Gen → TTS → Video Assembly
```

1. **Search** — Queries Tavily for AMCA, Indian defence, key player news within the current week (Monday→today)
2. **Pre-filter** — Rejects obviously non-aerospace articles by title (IT, cricket, finance, etc.)
3. **Curate** — GPT-5-nano filters for genuine Indian aerospace/defence relevance (local keyword fallback)
4. **Scene Plan** — GPT generates a structured video plan: visual prompts, narration scripts, timings
5. **Image Generation** — Azure OpenAI generates infographic-style dossier slides
6. **TTS** — Azure TTS narrates each scene in an executive briefing voice
7. **Video Assembly** — MoviePy composes final MP4 (with and without voiceover)

## Usage

```bash
# Full pipeline (search → video)
python main.py

# Plan only — verify search + curation + scene plan quality before generating
python main.py --plan-only

# Custom output directory
python main.py --output-dir assets/runs/custom_name

# Photorealistic style instead of infographic
python main.py --style photo

# Skip cached steps
python main.py --skip-images --skip-audio
```

## Output

All runs produce files in the output directory (`assets/runs/auto/` by default):
- `tavily_results.json` — Raw search results
- `curated_articles.json` — GPT-curated articles
- `generated_scene_plan.json` — Video scene plan
- `images/scene_N.png` — Infographic slides
- `audio/scene_N.mp3` — TTS narration clips
- `outputs/final_with_voiceover.mp4` — Final video with narration
- `outputs/final_without_voiceover.mp4` — Silent version

## Flags

| Flag | Description |
|------|-------------|
| `--style photo\|infographic` | Visual style (default: infographic) |
| `--plan-only` | Stop after generating scene plan |
| `--skip-images` | Skip image generation (use cached) |
| `--skip-audio` | Skip audio generation (use cached) |
| `--voice` | TTS voice name (default: alloy) |
| `--model` | Override image model deployment |
| `--days-back N` | Override search window (default: auto weekly) |
| `--output-dir` | Output directory (default: assets/runs/auto) |

## Setup

Requires a `.env` file with Azure OpenAI and Tavily API keys:

```
TAVILY_API_KEY=tvly-xxxxx
AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
AZURE_OPENAI_API_KEY=xxxxx
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5-nano
AZURE_OPENAI_IMAGE_DEPLOYMENT=gpt-image-1.5
AZURE_TTS_ENDPOINT=https://xxx.openai.azure.com/
AZURE_TTS_API_KEY=xxxxx
AZURE_TTS_DEPLOYMENT=tts
```

```bash
pip install -r requirements.txt
playwright install chromium  # optional, for scraping fallback
```

## Cross-Platform

Runs on both **macOS** and **Windows**. Font paths for text overlays are auto-detected by OS.
