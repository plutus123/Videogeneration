# Vizh -- Scene-Based Video Generator

Generates cinematic narrated videos from a JSON scene description. Each scene is turned into an AI-generated image (via OpenAI's image API), narrated with TTS, and assembled into a polished MP4.

## How it works

1. You write a JSON file describing your scenes -- each with a `visual_prompt`, `audio_script`, and `on_screen_text`.
2. For each scene, an image is generated using the **GPT image model** from the visual prompt.
3. The `on_screen_text` is overlaid on each image as a clean text banner (Pillow).
4. **Narration audio** is generated from each scene's `audio_script` using OpenAI TTS.
5. Images and audio are assembled into an MP4 with crossfade transitions using MoviePy.

## Quick start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "OPENAI_API_KEY=sk-..." > .env

python main.py example_input.json
```

Output: `assets/outputs/final_video.mp4`

## Input format

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

## CLI options

```
python main.py INPUT_JSON [--output PATH] [--skip-images] [--skip-audio] [--model MODEL] [--voice VOICE]
```

- `--skip-images` -- reuse existing images in `assets/images/`
- `--skip-audio` -- reuse existing audio in `assets/audio/`
- `--model` -- image generation model (default `gpt-image-1`)
- `--voice` -- TTS voice: alloy, echo, fable, onyx, nova, shimmer (default `alloy`)

## Project layout

```
main.py              Entry point -- orchestrates the three pipeline steps
image_generator.py   GPT image generation + Pillow text overlay
video_builder.py     MoviePy video assembly with transitions
utils/
  tts_utils.py       Text-to-speech (OpenAI TTS / gTTS fallback)
assets/
  images/            Generated scene images
  audio/             Generated narration audio
  outputs/           Final video
```

## Requirements

- Python 3.10+
- OpenAI API key (image generation + TTS)
- ffmpeg (for video encoding)

## License

MIT
