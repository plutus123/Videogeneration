RR-Video Generator

Generates narrated intelligence briefing videos from news articles. Uses Azure OpenAI for scene planning, image generation, and TTS narration. Outputs two MP4 videos (with and without voiceover).

## Modes

### Mode 1: Auto (Tavily search pipeline)

Searches for aviation/defence news via Tavily, curates with GPT, generates a 3-slide weekly briefing.

```bash
python main.py auto
python main.py auto --days-back 14 --plan-only
python main.py auto --output-dir assets/runs/my_run
```

### Mode 2: URLs (full extraction pipeline)

Extracts content from a `urls_config.json`, plans scenes via GPT, generates video.

```bash
python main.py urls urls_config.json
python main.py urls urls_config.json --plan-only
python main.py urls urls_config.json --version v2
```

### Mode 3: Scene (from existing scene plan)

Generates video directly from a pre-built scene plan JSON.

```bash
python main.py scene generated_scene_plan.json
python main.py scene generated_scene_plan.json --version v2
```

## Output

All modes produce two videos in the output directory:
- `final_with_voiceover.mp4`
- `final_without_voiceover.mp4`

## Common flags

| Flag | Description |
|------|-------------|
| `--style photo\|infographic` | Visual style (default: infographic) |
| `--skip-images` | Skip image generation (use cached) |
| `--skip-audio` | Skip audio generation (use cached) |
| `--voice` | TTS voice name (default: alloy) |
| `--model` | Override image model deployment |
| `--version` | Version tag for run directory |

## Setup

Requires a `.env` file with Azure OpenAI and Tavily API keys. See `utils/azure_client.py` for expected environment variables.

```bash
pip install -r requirements.txt
playwright install chromium  # optional, for scraping fallback
```
