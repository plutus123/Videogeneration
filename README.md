RR-Video Generator

Generates cinematic narrated videos from news URLs or a pre-built JSON scene plan. Extracts content from articles, uses GPT to plan scenes, generates AI images, narrates with TTS, and assembles a polished MP4.

## How it works

### Mode 1: From URLs (full pipeline)

1. Provide a `urls_config.json` with categorized article URLs.
2. Articles are fetched and text extracted (with fallback summaries for blocked sites).
3. GPT generates a scene-by-scene video plan from the extracted content.
4. Each scene's image is generated via the **GPT image model**, with `on_screen_text` overlaid via Pillow.
5. **Narration audio** is generated from each scene's `audio_script` using OpenAI TTS.
6. Images and audio are assembled into an MP4 with crossfade transitions using MoviePy.

### Mode 2: From scene JSON (direct)

1. Provide a pre-built scene JSON (like `example_input.json`).
2. Steps 4-6 above run directly.

## Quick start

```bash

# From URLs (extract + plan + generate video)
python main.py urls_config.json --from-urls

# From pre-built scene JSON
python main.py example_input.json

# Just generate the scene plan (no video)
python main.py urls_config.json --from-urls --plan-only
```

Output: `assets/outputs/final_video.mp4`

## URLs config format

```json
{
  "section_mapping": {
    "Macroeconomic": ["Macroeconomic"],
    "Competitors": ["Civil", "Defence", "PowerSystems"]
  },
  "categories": {
    "Civil": [
      {
        "url": "https://example.com/article",
        "title": "Article Title",
        "fallback_summary": "Used if the URL cannot be fetched."
      }
    ]
  }
}
```

## Scene JSON format

```json
{
  "textual_summary": "A brief overview of the video content.",
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 8,
      "visual_prompt": "A cinematic aerial shot of...",
      "audio_script": "Narration text spoken during this scene.",
      "on_screen_text": "Headline text overlaid on the image"
    }
  ],
  "overall_style": "Cinematic documentary style with warm lighting."
}
```
