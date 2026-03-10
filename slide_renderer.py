"""Renders presentation slides as HTML, captures them as images, and assembles the final video."""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Dict
from mutagen.mp3 import MP3


def get_audio_duration(audio_path):
    try:
        return MP3(audio_path).info.length
    except Exception:
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path],
                capture_output=True, text=True,
            )
            return float(result.stdout.strip())
        except Exception:
            return 8.0


def _latex_to_html(equation):
    eq = equation
    eq = eq.replace("\\dot{m}", "\u1E41")
    eq = eq.replace("\\times", " \u00D7 ")
    eq = eq.replace("\\cdot", " \u00B7 ")
    eq = re.sub(r"\\sqrt\{([^}]+)\}", r"\u221A(\1)", eq)
    eq = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}", r"(\1)/(\2)", eq)
    eq = re.sub(r"(\w)_(\w)", r"\1<sub>\2</sub>", eq)
    eq = re.sub(r"_\{([^}]+)\}", r"<sub>\1</sub>", eq)
    eq = re.sub(r"\^(\w)", r"<sup>\1</sup>", eq)
    eq = re.sub(r"\^\{([^}]+)\}", r"<sup>\1</sup>", eq)
    eq = eq.replace("{", "").replace("}", "")
    return eq


BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    width: 1920px; height: 1080px; overflow: hidden;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: linear-gradient(135deg, #0a0a2e 0%, #1a1a4e 30%, #0d1b3e 60%, #0a0a2e 100%);
    color: white;
}
.slide {
    width: 1920px; height: 1080px; position: relative;
    display: flex; flex-direction: column; padding: 60px 80px;
}
.bg-orb {
    position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.12; z-index: 0;
}
.bg-orb-1 { width: 500px; height: 500px; background: #00D4FF; top: -100px; right: -100px; }
.bg-orb-2 { width: 400px; height: 400px; background: #7B61FF; bottom: -80px; left: -80px; }
.grid-overlay {
    position: absolute; inset: 0; z-index: 0;
    background-image:
        linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px);
    background-size: 60px 60px;
}
.content { position: relative; z-index: 1; flex: 1; display: flex; flex-direction: column; }
.progress-bar {
    position: absolute; bottom: 0; left: 0; height: 3px;
    background: linear-gradient(90deg, #00D4FF, #7B61FF); z-index: 2;
}
"""


def generate_slide_html(slide_data, presentation_title=""):
    title = slide_data.get("title", "")
    text = slide_data.get("text", "")
    equation = slide_data.get("equation", "")
    slide_index = slide_data.get("slide_index", 0)
    total_slides = slide_data.get("total_slides", 1)
    slide_type = slide_data.get("slide_type", "")
    is_title = slide_data.get("animation", "") == "title" or slide_index == 0

    equation_html = ""
    if equation:
        equation_html = f'<div class="eq-block"><span class="eq">{_latex_to_html(equation)}</span></div>'

    if slide_type == "closing":
        return _closing_slide_html(presentation_title, total_slides)
    elif is_title:
        return _title_slide_html(presentation_title or title, text, total_slides)
    else:
        return _content_slide_html(title, text, equation_html, slide_index, total_slides, presentation_title)


def _title_slide_html(title, subtitle, total_slides):
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
{BASE_CSS}
.center {{ flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; gap:28px; }}
.main-title {{
    font-size:72px; font-weight:800; line-height:1.2; max-width:1400px; letter-spacing:-1px;
    background: linear-gradient(135deg, #00D4FF 0%, #7B61FF 50%, #00D4FF 100%);
    background-size:200% auto; -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}}
.divider {{ width:120px; height:4px; background:linear-gradient(90deg,#00D4FF,#7B61FF); border-radius:2px; }}
.subtitle {{ font-size:28px; color:rgba(255,255,255,0.65); font-weight:300; max-width:900px; line-height:1.6; }}
</style></head><body>
<div class="slide">
    <div class="bg-orb bg-orb-1"></div><div class="bg-orb bg-orb-2"></div><div class="grid-overlay"></div>
    <div class="content"><div class="center">
        <div class="main-title">{title}</div>
        <div class="divider"></div>
        <div class="subtitle">{subtitle}</div>
    </div></div>
    <div class="progress-bar" style="width:{100/total_slides}%"></div>
</div></body></html>"""


def _content_slide_html(title, text, equation_html, slide_index, total_slides, presentation_title):
    progress = ((slide_index + 1) / total_slides) * 100
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
{BASE_CSS}
.header {{ margin-bottom:8px; }}
.pres-label {{ font-size:13px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:2px; margin-bottom:10px; }}
.slide-title {{
    font-size:52px; font-weight:700; line-height:1.2;
    background:linear-gradient(135deg,#00D4FF,#7B61FF); -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}}
.accent {{ width:70px; height:4px; background:linear-gradient(90deg,#00D4FF,#7B61FF); border-radius:2px; margin-top:12px; }}
.body {{ flex:1; display:flex; align-items:center; }}
.card {{
    background:rgba(255,255,255,0.035); border:1px solid rgba(255,255,255,0.07);
    border-radius:20px; padding:48px 52px; max-width:1200px;
    display:flex; flex-direction:column; gap:32px;
}}
.card-text {{ font-size:30px; line-height:1.75; color:rgba(255,255,255,0.88); }}
.eq-block {{
    background:rgba(123,97,255,0.06); border:1px solid rgba(123,97,255,0.14);
    border-radius:16px; padding:36px 48px; display:flex; align-items:center; justify-content:center;
}}
.eq {{
    font-family:'JetBrains Mono',monospace; font-size:48px; font-weight:500; letter-spacing:2px;
    background:linear-gradient(135deg,#FFD700,#FFA500); -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}}
</style></head><body>
<div class="slide">
    <div class="bg-orb bg-orb-1"></div><div class="bg-orb bg-orb-2"></div><div class="grid-overlay"></div>
    <div class="content">
        <div class="header">
            <div class="pres-label">{presentation_title}</div>
            <div class="slide-title">{title}</div>
            <div class="accent"></div>
        </div>
        <div class="body"><div class="card">
            <div class="card-text">{text}</div>
            {equation_html}
        </div></div>
    </div>
    <div class="progress-bar" style="width:{progress}%"></div>
</div></body></html>"""


def _closing_slide_html(presentation_title, total_slides):
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
{BASE_CSS}
.center {{ flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; gap:28px; }}
.thank-you {{
    font-size:68px; font-weight:800; line-height:1.2;
    background:linear-gradient(135deg,#00D4FF 0%,#7B61FF 50%,#00D4FF 100%);
    background-size:200% auto; -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}}
.divider {{ width:120px; height:4px; background:linear-gradient(90deg,#00D4FF,#7B61FF); border-radius:2px; }}
.message {{ font-size:26px; color:rgba(255,255,255,0.55); font-weight:300; max-width:800px; line-height:1.7; }}
.pres-name {{ font-size:18px; color:rgba(255,255,255,0.3); margin-top:40px; text-transform:uppercase; letter-spacing:3px; }}
</style></head><body>
<div class="slide">
    <div class="bg-orb bg-orb-1"></div><div class="bg-orb bg-orb-2"></div><div class="grid-overlay"></div>
    <div class="content"><div class="center">
        <div class="thank-you">Thank You</div>
        <div class="divider"></div>
        <div class="message">Thank you for your time and attention. We hope this presentation provided valuable insights.</div>
        <div class="pres-name">{presentation_title}</div>
    </div></div>
    <div class="progress-bar" style="width:100%"></div>
</div></body></html>"""


def render_slides_to_images(slides_data, output_dir="assets/slide_images"):
    from playwright.sync_api import sync_playwright

    os.makedirs(output_dir, exist_ok=True)
    image_paths = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        for i, slide_data in enumerate(slides_data):
            html = generate_slide_html(slide_data, slide_data.get("presentation_title", ""))
            html_path = os.path.join(output_dir, f"slide_{i}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

            page.goto(f"file://{os.path.abspath(html_path)}")
            page.wait_for_timeout(500)

            img_path = os.path.join(output_dir, f"slide_{i}.png")
            page.screenshot(path=img_path, full_page=False)
            image_paths.append(img_path)

        browser.close()

    return image_paths


def build_video_from_slides(
    image_paths,
    narration_dir="assets/narration",
    slide_ids=None,
    output_path="assets/outputs/final_video.mp4",
    transition_duration=0.8,
    min_slide_duration=5.0,
    padding=1.5,
):
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, vfx

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    clips = []

    for i, img_path in enumerate(image_paths):
        audio_path = None
        duration = min_slide_duration

        if slide_ids and i < len(slide_ids):
            candidate = os.path.join(narration_dir, f"{slide_ids[i]}.mp3")
            if os.path.exists(candidate):
                audio_path = candidate
                duration = get_audio_duration(audio_path) + padding

        duration = max(duration, min_slide_duration)
        clip = ImageClip(img_path).with_duration(duration).resized((1920, 1080))

        if audio_path:
            clip = clip.with_audio(AudioFileClip(audio_path))

        clips.append(clip)

    if not clips:
        raise ValueError("No slides to build video from")

    clips[0] = clips[0].with_effects([vfx.FadeIn(1.0)])
    clips[-1] = clips[-1].with_effects([vfx.FadeOut(1.5)])

    if len(clips) > 1 and transition_duration > 0:
        for i in range(1, len(clips)):
            clips[i] = clips[i].with_effects([vfx.CrossFadeIn(transition_duration)])
        final = concatenate_videoclips(clips, method="compose", padding=-transition_duration)
    else:
        final = concatenate_videoclips(clips, method="compose")

    final.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac", bitrate="5000k", preset="medium", threads=4)

    for clip in clips:
        clip.close()
    final.close()
    return output_path
