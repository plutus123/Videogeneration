# Vizh -- Presentation Video Generator

Turns a simple JSON file into a narrated, professional-looking presentation video.

## How it works

1. You write a JSON file describing your slides (title, text, optional equations).
2. The tool sends each slide to **GPT-4o-mini**, which generates a Manim scene script as a backup and structured slide data.
3. Each slide is rendered as a high-quality **HTML page** (styled with CSS gradients, glassmorphism cards, and Inter font) and captured as a 1920x1080 screenshot via a headless Chromium browser (Playwright).
4. **Narration** is generated per-slide using GPT (context-aware so it flows naturally) and converted to audio with OpenAI TTS.
5. The screenshots and audio files are assembled into an MP4 with crossfade transitions using MoviePy.

The result is a polished 1080p video with synced voiceover, smooth transitions, and a closing "Thank You" slide -- ready for a meeting or presentation.

## Quick start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install Playwright's bundled browser
playwright install chromium

# Set your OpenAI key
echo "OPENAI_API_KEY=sk-..." > .env

# Generate the video
python main.py example_input.json
```

The final video lands in `assets/outputs/final_video.mp4`.

## Input format

```json
{
  "title": "How Rockets Reach Orbit",
  "scenes": [
    { "title": "Introduction", "text": "Rockets allow spacecraft to escape Earth's gravity.", "animation": "title" },
    { "title": "Newton's Third Law", "text": "Gas goes down, rocket goes up.", "equation": "F = \\dot{m} \\times v_e" },
    { "title": "Orbital Velocity", "text": "7.8 km/s to stay in LEO.", "equation": "v = \\sqrt{GM/r}" }
  ]
}
```

Each object in `scenes` becomes one slide. The first scene is treated as the title slide. A "Thank You" closing slide is appended automatically.

## CLI options

```
python main.py INPUT_JSON [--skip-generation] [--no-tts] [--output-dir DIR] [--scenes-dir DIR]
```

- `--skip-generation` -- reuse previously generated slide data and narration (skip GPT calls).
- `--no-tts` -- produce a silent video (no narration).
- `--output-dir` -- where to write the final video (default `assets/outputs`).
- `--scenes-dir` -- where generated scene files live (default `generated_scenes`).

## Project layout

```
main.py              Entry point -- orchestrates the four pipeline steps
gpt_formatter.py     Calls GPT to produce Manim scripts + slide JSON + narration
slide_renderer.py    HTML/CSS slide templates, Playwright capture, MoviePy video assembly
utils/
  tts_utils.py       Narration text generation (GPT) and text-to-speech (OpenAI / gTTS)
assets/
  narration/         Generated .mp3 and .txt narration files
  slide_images/      Captured slide screenshots
  outputs/           Final video
generated_scenes/    GPT-generated Manim .py files and slide .json metadata
```

## Requirements

- Python 3.10+
- An OpenAI API key (for GPT and TTS)
- ffmpeg (for video encoding)

## License

MIT

