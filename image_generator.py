"""Generates scene images using OpenAI's image generation API and adds text overlays with Pillow."""

import os
import base64
import urllib.request
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

FONT_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/SFNSDisplay.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _load_font(size=40):
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_scene_image(prompt, output_path, style="", model="gpt-image-1.5"):
    client = OpenAI()
    full_prompt = prompt
    if style:
        full_prompt = f"{prompt}\n\nOverall visual style: {style}"

    response = client.images.generate(
        model=model,
        prompt=full_prompt,
        n=1,
        size="1536x1024",
    )

    img = response.data[0]
    if img.b64_json:
        image_bytes = base64.b64decode(img.b64_json)
    else:
        with urllib.request.urlopen(img.url) as resp:
            image_bytes = resp.read()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(image_bytes)

    return output_path


def add_text_overlay(image_path, text, output_path=None):
    if not text:
        return image_path
    if output_path is None:
        output_path = image_path

    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bar_h = int(h * 0.1)
    bar_y = h - bar_h

    for y in range(bar_h):
        alpha = int(190 * (y / bar_h))
        draw.line([(0, bar_y + y), (w, bar_y + y)], fill=(0, 0, 0, alpha))

    font_size = int(bar_h * 0.42)
    font = _load_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (w - tw) // 2
    ty = bar_y + (bar_h - th) // 2

    draw.text((tx + 2, ty + 2), text, fill=(0, 0, 0, 180), font=font)
    draw.text((tx, ty), text, fill=(255, 255, 255, 240), font=font)

    result = Image.alpha_composite(img, overlay)
    result.convert("RGB").save(output_path, quality=95)
    return output_path
