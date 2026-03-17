import os
import sys
import json
import argparse
from datetime import datetime
from slide_renderer import render_scene, composite_icon
from image_generator import generate_icon
from utils.tts_utils import text_to_speech
from video_builder import build_video

OUTPUTS_DIR = "outputs"


def _next_version():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    existing = [
        d for d in os.listdir(OUTPUTS_DIR)
        if os.path.isdir(os.path.join(OUTPUTS_DIR, d)) and d.startswith("v")
    ]
    nums = []
    for d in existing:
        try:
            nums.append(int(d.split("_")[0][1:]))
        except ValueError:
            pass
    return max(nums) + 1 if nums else 1


def _create_version_dir():
    ver = _next_version()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"v{ver}_{ts}"
    base = os.path.join(OUTPUTS_DIR, name)
    img_dir = os.path.join(base, "images")
    aud_dir = os.path.join(base, "audio")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(aud_dir, exist_ok=True)
    print(f"Version: {name}")
    return base, img_dir, aud_dir, ver


def _extract(urls_config_path, extracted_path):
    from content_extractor import extract_content
    print("STEP 1: Extracting content from URLs")
    fetched, section_mapping = extract_content(urls_config_path, save_path=extracted_path)
    return fetched, section_mapping


def _plan(fetched, section_mapping, scene_json_path):
    from content_extractor import build_context
    from scene_planner import generate_scene_plan, save_scene_plan
    print("\nSTEP 2: Generating scene plan via GPT")
    context = build_context(fetched, section_mapping)
    plan = generate_scene_plan(context)
    save_scene_plan(plan, scene_json_path)
    num_scenes = len(plan.get("scenes", []))
    total_dur = sum(s.get("duration_seconds", 0) for s in plan.get("scenes", []))
    total_words = sum(len(s.get("audio_script", "").split()) for s in plan.get("scenes", []))
    print(f"Generated {num_scenes} scenes, {total_dur}s planned, {total_words} words")
    types_used = set(s.get("scene_type", "?") for s in plan.get("scenes", []))
    print(f"Scene types: {', '.join(sorted(types_used))}")
    return plan


def _generate_video(data, args):
    scenes = data["scenes"]
    total = len(scenes)
    total_dur = sum(s.get("duration_seconds", 0) for s in scenes)
    total_words = sum(len(s.get("audio_script", "").split()) for s in scenes)

    ver_dir, img_dir, aud_dir, ver_num = _create_version_dir()
    output_path = os.path.join(ver_dir, "final_video.mp4")

    plan_copy = os.path.join(ver_dir, "scene_plan.json")
    with open(plan_copy, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    est_secs = int(total_words / 2.5)
    print(f"\nSTEP 3: Generating video ({total} scenes, ~{total_words} words, ~{est_secs}s est)")

    print("Rendering slides...")
    for scene in scenes:
        num = scene["scene_number"]
        img_path = os.path.join(img_dir, f"scene_{num}.png")
        print(f"  Slide {num}/{total} [{scene.get('scene_type', '?')}]")
        render_scene(scene, img_path)

    icon_dir = os.path.join(ver_dir, "icons")
    os.makedirs(icon_dir, exist_ok=True)
    print("Generating decorative icons (gpt-image-1.5)...")
    for scene in scenes:
        num = scene["scene_number"]
        scene_type = scene.get("scene_type", "")
        hint = scene.get("icon_hint", "")
        if not hint or scene_type in ("comparison", "steps"):
            continue
        icon_path = os.path.join(icon_dir, f"icon_{num}.png")
        print(f"  Icon {num}/{total} [{hint}]")
        result = generate_icon(hint, icon_path)
        if result:
            slide_path = os.path.join(img_dir, f"scene_{num}.png")
            composite_icon(slide_path, icon_path, scene_type)

    print("Generating narration audio...")
    for scene in scenes:
        num = scene["scene_number"]
        script = scene.get("audio_script", "")
        if script:
            audio_path = os.path.join(aud_dir, f"scene_{num}.mp3")
            print(f"  Audio {num}/{total}")
            text_to_speech(script, audio_path, voice=args.voice)

    print("Assembling final video...")
    output = build_video(scenes, img_dir, aud_dir, output_path)
    print(f"\nDone: {output}")
    print(f"Version directory: {ver_dir}")
    return output


def main():
    parser = argparse.ArgumentParser(description="Aviation news video generator")
    parser.add_argument("input", help="Path to scene JSON or URLs config JSON")
    parser.add_argument("--from-urls", action="store_true",
                        help="Treat input as URLs config")
    parser.add_argument("--plan-only", action="store_true",
                        help="Stop after generating scene plan")
    parser.add_argument("--extracted-json", default="extracted_content.json")
    parser.add_argument("--scene-json", default="generated_scene_plan.json")
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--skip-audio", action="store_true")
    parser.add_argument("--voice", default="alloy")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found")
        sys.exit(1)

    with open(args.input) as f:
        data = json.load(f)

    if "categories" in data or args.from_urls:
        fetched, section_mapping = _extract(args.input, args.extracted_json)
        data = _plan(fetched, section_mapping, args.scene_json)
        if args.plan_only:
            print(f"\nScene plan saved to {args.scene_json}")
            return

    if "scenes" not in data:
        print("Error: Invalid scene plan JSON (missing 'scenes' key)")
        sys.exit(1)

    _generate_video(data, args)


if __name__ == "__main__":
    main()
