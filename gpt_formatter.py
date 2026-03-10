"""Uses GPT to generate Manim scene scripts and slide metadata from structured JSON input."""

import os
import json
import re
import asyncio
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from utils.tts_utils import generate_narration_text, text_to_speech

load_dotenv()

SYSTEM_PROMPT = """You are an expert Manim animator. Output Python Manim scene scripts for educational slides.

Design rules:
- Dark background, title in "#00D4FF", body in WHITE, equations in "#FFD700"
- Use RoundedRectangle cards, underlines, smooth animations (Write, FadeIn, GrowFromCenter)
- Scale all text to fit: if obj.width > 11: obj.scale_to_fit_width(11)
- Use .next_to() or .to_edge() for positioning -- never leave objects at origin
- LaggedStart syntax: LaggedStart(*[FadeIn(o) for o in objs], lag_ratio=0.2)
- self.wait(3) after content, fade out at end

Output ONLY valid Python code, no markdown."""


def _strip_code_fences(text):
    if text.startswith("```python"):
        text = text[9:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def load_structured_input(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_scene_script(section_name, section_content, scene_data=None):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_scene(section_name, section_content, scene_data)

    client = OpenAI(api_key=api_key)
    safe_class = re.sub(r"[^a-zA-Z0-9]", "", section_name.replace(" ", "").replace("'", ""))

    content_desc = f"Title: {section_name}\nText: {section_content}"
    if scene_data and scene_data.get("equation"):
        content_desc += f"\nEquation (LaTeX): {scene_data['equation']}"

    prompt = f"""Create a professional Manim scene.

{content_desc}

Class name: {safe_class}Scene(Scene). Use cards, accent colors, smooth animations.
Return ONLY Python code."""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            temperature=0.7,
            max_completion_tokens=3000,
        )
        return _strip_code_fences(resp.choices[0].message.content.strip())
    except Exception:
        return _fallback_scene(section_name, section_content, scene_data)


def _fallback_scene(section_name, section_content, scene_data=None):
    safe_class = re.sub(r"[^a-zA-Z0-9]", "", section_name.replace(" ", "").replace("'", ""))
    safe_content = section_content.replace('"', "'").replace("\n", " ")

    words, lines, cur = safe_content.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 50 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w) if cur else w
    if cur:
        lines.append(cur)
    lines = lines[:4]

    text_block, names, prev = "", [], None
    for i, line in enumerate(lines):
        v = f"line{i}"
        names.append(v)
        text_block += f'        {v} = Text("{line}", font_size=26, color=WHITE)\n'
        text_block += f"        if {v}.width > 11: {v}.scale_to_fit_width(11)\n"
        if prev:
            text_block += f"        {v}.next_to({prev}, DOWN, buff=0.3)\n"
        prev = v

    group = ", ".join(names)
    eq_block = ""
    if scene_data and scene_data.get("equation"):
        eq = scene_data["equation"]
        eq_block = f'''
        equation = MathTex(r"{eq}", font_size=48, color="#FFD700")
        if equation.width > 10: equation.scale_to_fit_width(10)
        equation.next_to({prev}, DOWN, buff=0.6)
        self.play(Write(equation), run_time=1.5)
        self.wait(3)
'''

    return f'''from manim import *

class {safe_class}Scene(Scene):
    def construct(self):
        title = Text("{section_name}", font_size=48, color="#00D4FF", weight=BOLD)
        title.to_edge(UP, buff=0.5)
        if title.width > 12: title.scale_to_fit_width(12)
        underline = Line(LEFT * title.width/2, RIGHT * title.width/2, color="#00D4FF", stroke_width=3)
        underline.next_to(title, DOWN, buff=0.15)
        self.play(Write(title), run_time=1.2)
        self.play(Create(underline), run_time=0.5)
        self.wait(1)

        card = RoundedRectangle(corner_radius=0.3, width=12, height=3.5,
                                fill_color="#1a1a2e", fill_opacity=0.8,
                                stroke_color="#00D4FF", stroke_width=1.5)
        card.next_to(underline, DOWN, buff=0.5)
        self.play(FadeIn(card), run_time=0.8)

{text_block}
        body = VGroup({group})
        body.move_to(card)
        self.play(*[FadeIn(t, shift=UP*0.3) for t in [{group}]], run_time=1.5)
        self.wait(3)
{eq_block}
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=1)
        self.wait(0.5)
'''


def generate_all_scenes(structured_input, output_dir="generated_scenes", enable_tts=False):
    os.makedirs(output_dir, exist_ok=True)
    generated_files = []

    scenes_list = []
    if "scenes" in structured_input:
        for s in structured_input["scenes"]:
            scenes_list.append((s.get("title", "Untitled"), s.get("text", ""), s))
    elif "full_text" in structured_input:
        for name, content in structured_input["full_text"].items():
            scenes_list.append((name, content, {}))
    else:
        return []

    presentation_title = structured_input.get("title", "Presentation")
    total_slides = len(scenes_list)

    for idx, (name, content, scene_data) in enumerate(scenes_list):
        scene_code = generate_scene_script(name, content, scene_data=scene_data)

        safe_name = re.sub(r"[^a-z0-9_]", "", name.lower().replace(" ", "_").replace("'", ""))
        filepath = os.path.join(output_dir, f"{safe_name}_scene.py")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(scene_code)

        slide_json = {
            "title": name, "text": content,
            "equation": scene_data.get("equation", "") if scene_data else "",
            "animation": scene_data.get("animation", "") if scene_data else "",
            "slide_index": idx, "total_slides": total_slides,
            "presentation_title": presentation_title,
        }
        with open(os.path.join(output_dir, f"{safe_name}_slide.json"), "w", encoding="utf-8") as f:
            json.dump(slide_json, f, indent=2)

        if enable_tts:
            try:
                narration_text = asyncio.run(generate_narration_text(
                    name, content, slide_index=idx,
                    total_slides=total_slides, presentation_title=presentation_title,
                ))
                if narration_text:
                    narration_dir = Path("assets/narration")
                    narration_dir.mkdir(parents=True, exist_ok=True)
                    (narration_dir / f"{safe_name}.txt").write_text(narration_text, encoding="utf-8")
                    asyncio.run(text_to_speech(narration_text, str(narration_dir / f"{safe_name}.mp3")))
            except Exception as e:
                print(f"TTS failed for '{name}': {e}")

        generated_files.append(filepath)

    return generated_files
