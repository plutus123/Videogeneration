import os
import sys
import json
import argparse
from image_generator import generate_scene_image, add_text_overlay
from utils.tts_utils import text_to_speech
from video_builder import build_video


def _extract(urls_config_path, extracted_path):
    from content_extractor import extract_content
    print("STEP 1: Extracting content from URLs")
    fetched, section_mapping = extract_content(urls_config_path, save_path=extracted_path)
    return fetched, section_mapping


def _plan(fetched, section_mapping, scene_json_path, style="infographic"):
    from content_extractor import build_context
    from scene_planner import generate_scene_plan, save_scene_plan
    print("\nSTEP 2: Generating scene plan via GPT")
    context = build_context(fetched, section_mapping)
    plan = generate_scene_plan(context, style=style)
    save_scene_plan(plan, scene_json_path)
    num_scenes = len(plan.get("scenes", []))
    total_dur = sum(s.get("duration_seconds", 0) for s in plan.get("scenes", []))
    print(f"Generated {num_scenes} scenes, {total_dur}s total")
    return plan


def _generate_video(data, args):
    scenes = data["scenes"]
    style = data.get("overall_style", "")
    visual_style = args.style
    total = len(scenes)
    total_dur = sum(s.get("duration_seconds", 0) for s in scenes)
    print(f"\nSTEP 3: Generating video ({total} scenes, {total_dur}s, style={visual_style})")
    image_dir = getattr(args, "image_dir", "assets/images")
    audio_dir = getattr(args, "audio_dir", "assets/audio")
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    if not args.skip_images:
        print("Generating scene images...")
        for scene in scenes:
            num = scene["scene_number"]
            raw_path = os.path.join(image_dir, f"scene_{num}_raw.png")
            final_path = os.path.join(image_dir, f"scene_{num}.png")
            if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
                print(f"  Scene {num}/{total} (cached)")
                continue
            print(f"  Scene {num}/{total}")
            generate_scene_image(
                scene["visual_prompt"], raw_path,
                style=style, model=args.model,
                visual_style=visual_style,
            )
            # In infographic mode the dossier card already contains
            # all text — skip the Pillow overlay to keep it clean.
            if visual_style == "infographic":
                os.replace(raw_path, final_path)
            else:
                text = scene.get("on_screen_text", "")
                add_text_overlay(raw_path, text, final_path)

    if not args.skip_audio:
        print("Generating narration audio...")
        for scene in scenes:
            num = scene["scene_number"]
            script = scene.get("audio_script", "")
            if script:
                audio_path = os.path.join(audio_dir, f"scene_{num}.mp3")
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    print(f"  Scene {num}/{total} (cached)")
                    continue
                print(f"  Scene {num}/{total}")
                text_to_speech(script, audio_path, voice=args.voice)

    print("Assembling final video...")
    output = build_video(scenes, image_dir, audio_dir, args.output)
    print(f"Done: {output}")


def main():
    parser = argparse.ArgumentParser(description="Aviation news video generator")
    parser.add_argument("input", help="Path to scene JSON or URLs config JSON")
    parser.add_argument("--from-urls", action="store_true",
                        help="Treat input as URLs config")
    parser.add_argument("--plan-only", action="store_true",
                        help="Stop after generating scene plan")
    parser.add_argument("--extracted-json", default="extracted_content.json")
    parser.add_argument("--scene-json", default="generated_scene_plan.json")
    parser.add_argument("--output", default="assets/outputs/final_video.mp4")
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--skip-audio", action="store_true")
    parser.add_argument("--model", default=None,
                        help="Azure image deployment (default: from .env)")
    parser.add_argument("--voice", default="alloy")
    parser.add_argument("--style", choices=["photo", "infographic"],
                        default="infographic",
                        help="Visual style: 'photo' for corporate photography, "
                             "'infographic' for classified dossier (default)")
    parser.add_argument("--version", default=None,
                        help="Folder version name (e.g. v2). If set, creates a "
                             "dedicated folder assets/runs/<version>/ for all outputs.")
    args = parser.parse_args()

    if args.version:
        run_dir = os.path.join("assets", "runs", args.version)
        os.makedirs(run_dir, exist_ok=True)
        if args.extracted_json == "extracted_content.json":
            args.extracted_json = os.path.join(run_dir, "extracted_content.json")
        if args.scene_json == "generated_scene_plan.json":
            args.scene_json = os.path.join(run_dir, "generated_scene_plan.json")
        if args.output == "assets/outputs/final_video.mp4":
            args.output = os.path.join(run_dir, f"final_video_{args.version}.mp4")
        args.image_dir = os.path.join(run_dir, "images")
        args.audio_dir = os.path.join(run_dir, "audio")
    else:
        args.image_dir = "assets/images"
        args.audio_dir = "assets/audio"

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found")
        sys.exit(1)

    with open(args.input) as f:
        data = json.load(f)

    if "categories" in data or args.from_urls:
        fetched, section_mapping = _extract(args.input, args.extracted_json)
        data = _plan(fetched, section_mapping, args.scene_json, style=args.style)
        if args.plan_only:
            print(f"\nScene plan saved to {args.scene_json}")
            return

    if "scenes" not in data:
        print("Error: Invalid scene plan JSON (missing 'scenes' key)")
        sys.exit(1)

    _generate_video(data, args)


if __name__ == "__main__":
    main()
