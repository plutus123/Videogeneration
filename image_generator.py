import os
import sys
import base64
import urllib.request
from PIL import Image, ImageDraw, ImageFont
from utils.azure_client import get_azure_client, get_image_deployment


FONT_PATHS = [
    "C:\\Windows\\Fonts\\arial.ttf",
    "C:\\Windows\\Fonts\\segoeui.ttf",
    "C:\\Windows\\Fonts\\calibri.ttf",
    "C:\\Windows\\Fonts\\verdana.ttf",
]

# ---------------------------------------------------------------------------
# Style preamble prepended to every visual_prompt in infographic mode.
# Reinforces the aesthetic rules for the image-generation model.
# ---------------------------------------------------------------------------
DOSSIER_STYLE_PREAMBLE = (
   
    "dossier aesthetic, horizontal/landscape orientation. "
    "BACKGROUND: Off-white/cream parchment (#F2EDE0), subtle grid overlay at low "
    "opacity, technical crosshair marks (+) in corners. "
    "TYPOGRAPHY: Headlines bold dark navy (#1A2744) sans-serif, body text in "
    "monospace dark charcoal, labels in ALL-CAPS monospace letter-spaced, "
    "accent subheadings steel blue (#4A90B8). "
    "COLOR PALETTE (strict): dark navy #1A2744, burnt orange #C0622A, "
    "steel blue #4A8FB5, olive green #6B7A45, cream #F2EDE0. "
    "LAYOUT: clean ruled border, 2-4 card regions with thin borders, "
    "bold key stat or flat technical icon (large) with monospace bullet points, "
    "flat blueprint-like iconography only. "
    "MOOD:  financial research. "
    "Serious, structured, data-dense, visually clean. "
    "NO gradients. NO photos. NO photorealism. NO watermarks. "
    "Flat technical illustration ONLY. "
    "\n\n"
)


def _load_font(size=40):
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_scene_image(prompt, output_path, style="", model=None,
                         max_retries=3, visual_style="photo"):
    """Generate a scene image via Azure OpenAI.

    Args:
        prompt:       The visual_prompt text from the scene plan.
        output_path:  Where to save the generated image.
        style:        The overall_style string from the scene plan (appended).
        model:        Override image deployment name.
        max_retries:  Number of retry attempts.
        visual_style: "photo" or "infographic" — controls preamble injection.
    """
    client = get_azure_client()
    deployment = model or get_image_deployment()

    # Build the full prompt
    if visual_style == "infographic":
        full_prompt = DOSSIER_STYLE_PREAMBLE + prompt
    else:
        full_prompt = prompt

    if style:
        full_prompt = f"{full_prompt}\n\nOverall visual style: {style}"

    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.images.generate(
                model=deployment,
                prompt=full_prompt,
                n=1,
                size="1536x1024",
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
            
            import io
            img_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            
            if visual_style == "infographic":
                # Save the image natively since it matches target aspect ratio
                img_pil = img_pil.resize((1536, 1024), Image.Resampling.LANCZOS)
                img_pil.save(output_path, quality=95)
            else:
                # Direct crop from center if preserving aspect ratio is needed, but assuming full fit
                img_cropped = img_pil.resize((1536, 1024), Image.Resampling.LANCZOS)
                img_cropped.save(output_path, quality=95)

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
