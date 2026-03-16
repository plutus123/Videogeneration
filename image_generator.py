import os
import sys
import base64
import urllib.request
from PIL import Image, ImageDraw, ImageFont
from utils.azure_client import get_azure_client, get_image_deployment

if sys.platform == "win32":
    FONT_PATHS = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\calibri.ttf",
        "C:\\Windows\\Fonts\\verdana.ttf",
    ]
else:
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


def generate_scene_image(prompt, output_path, style="", model=None, max_retries=3):
    client = get_azure_client()
    deployment = model or get_image_deployment()
    full_prompt = prompt
    if style:
        full_prompt = f"{prompt}\n\nOverall visual style: {style}"

    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.images.generate(
                model=deployment,
                prompt=full_prompt,
                n=1,
                size="1024x1024",
                timeout=120,
            )

            img = response.data[0]
            if hasattr(img, "b64_json") and img.b64_json:
                image_bytes = base64.b64decode(img.b64_json)
            elif hasattr(img, "url") and img.url:
                with urllib.request.urlopen(img.url, timeout=60) as resp:
                    image_bytes = resp.read()
            else:
                raise RuntimeError("Azure image response has neither b64_json nor url")

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(image_bytes)

            return output_path
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                import time
                wait = 5 * attempt
                print(f"    Retry {attempt}/{max_retries} after error: {str(e)[:80]}... waiting {wait}s")
                time.sleep(wait)

    raise RuntimeError(f"Image generation failed after {max_retries} attempts: {last_err}")


def add_text_overlay(image_path, text, output_path=None):
    if not text:
        return image_path
    if output_path is None:
        output_path = image_path

    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bar_h = int(h * 0.12)
    bar_y = h - bar_h

    navy = (27, 42, 74)
    for y in range(bar_h):
        alpha = int(220 * (y / bar_h))
        draw.line([(0, bar_y + y), (w, bar_y + y)], fill=(*navy, alpha))

    gold = (184, 134, 11)
    draw.line([(0, bar_y), (w, bar_y)], fill=(*gold, 180), width=2)

    font_size = int(bar_h * 0.38)
    font = _load_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (w - tw) // 2
    ty = bar_y + (bar_h - th) // 2

    draw.text((tx + 1, ty + 1), text, fill=(0, 0, 0, 120), font=font)
    draw.text((tx, ty), text, fill=(255, 255, 255, 245), font=font)

    result = Image.alpha_composite(img, overlay)
    result.convert("RGB").save(output_path, quality=95)
    return output_path
