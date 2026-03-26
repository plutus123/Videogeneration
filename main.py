import os
import sys
import json
import argparse
from image_generator import generate_scene_image, add_text_overlay
from utils.tts_utils import text_to_speech
from video_builder import build_video_pair


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


def _generate_assets_and_video(data, image_dir, audio_dir, output_dir, args):
    """Generate images, audio, and TWO videos (with/without voiceover).

    Shared by all modes (auto, urls, scene).
    """
    scenes = data["scenes"]
    style = data.get("overall_style", "")
    visual_style = args.style
    total = len(scenes)
    total_dur = sum(s.get("duration_seconds", 0) for s in scenes)

    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    if not args.skip_images:
        print(f"\nGenerating {total} scene images...")
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
            if visual_style == "infographic":
                os.replace(raw_path, final_path)
            else:
                text = scene.get("on_screen_text", "")
                add_text_overlay(raw_path, text, final_path)

    if not args.skip_audio:
        print(f"\nGenerating {total} narration clips...")
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

    print(f"\nAssembling 2 videos ({total} scenes, {total_dur:.1f}s)...")
    path_with, path_without = build_video_pair(scenes, image_dir, audio_dir, output_dir)
    print(f"\nDone!")
    print(f"  With voiceover:    {path_with}")
    print(f"  Without voiceover: {path_without}")


def _auto_pipeline(args):
    """Automated pipeline: Tavily search -> Curation -> 3-slide briefing -> Video pair."""
    from tavily_search import search_aviation_news, load_whitelist_from_config
    from curation_agent import curate_articles, generate_briefing_summary

    run_dir = args.output_dir
    os.makedirs(run_dir, exist_ok=True)

    print("=" * 60)
    print("STEP 1: Searching aviation news via Tavily")
    print("=" * 60)
    whitelist = load_whitelist_from_config("urls_config.json")
    search_results = search_aviation_news(
        whitelist=whitelist,
        days_back=args.days_back,
        save_path=os.path.join(run_dir, "tavily_results.json"),
    )
    if not search_results:
        print("ERROR: No search results found. Check TAVILY_API_KEY and internet.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("STEP 2: Curating and ranking articles")
    print("=" * 60)
    curated = curate_articles(
        search_results,
        save_path=os.path.join(run_dir, "curated_articles.json"),
    )

    print("\n" + "=" * 60)
    print("STEP 3: Generating 3-slide briefing summary")
    print("=" * 60)
    scene_plan_path = os.path.join(run_dir, "generated_scene_plan.json")
    plan = generate_briefing_summary(curated, save_path=scene_plan_path)

    if args.plan_only:
        print(f"\nScene plan saved to {scene_plan_path}")
        return

    _generate_assets_and_video(
        plan,
        image_dir=os.path.join(run_dir, "images"),
        audio_dir=os.path.join(run_dir, "audio"),
        output_dir=os.path.join(run_dir, "outputs"),
        args=args,
    )


def _resolve_dirs(args):
    """Set image_dir, audio_dir, output_dir from --version flag."""
    if args.version:
        run_dir = os.path.join("assets", "runs", args.version)
        os.makedirs(run_dir, exist_ok=True)
        args.image_dir = os.path.join(run_dir, "images")
        args.audio_dir = os.path.join(run_dir, "audio")
        args.output_dir = os.path.join(run_dir, "outputs")
    else:
        args.image_dir = "assets/images"
        args.audio_dir = "assets/audio"
        args.output_dir = "assets/outputs"


def _add_common_args(parser):
    """Add flags shared by urls and scene sub-parsers."""
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--skip-audio", action="store_true")
    parser.add_argument("--model", default=None)
    parser.add_argument("--voice", default="alloy")
    parser.add_argument("--style", choices=["photo", "infographic"], default="infographic")
    parser.add_argument("--version", default=None)


def main():
    parser = argparse.ArgumentParser(description="Aviation news video generator")
    sub = parser.add_subparsers(dest="command")

    # ------ AUTO mode ------
    auto_p = sub.add_parser("auto", help="Auto-search, curate, and generate 3-slide briefing video")
    auto_p.add_argument("--output-dir", default="assets/runs/auto")
    auto_p.add_argument("--days-back", type=int, default=7)
    auto_p.add_argument("--plan-only", action="store_true")
    auto_p.add_argument("--skip-images", action="store_true")
    auto_p.add_argument("--skip-audio", action="store_true")
    auto_p.add_argument("--model", default=None)
    auto_p.add_argument("--voice", default="alloy")
    auto_p.add_argument("--style", choices=["photo", "infographic"], default="infographic")

    # ------ URLS mode ------
    urls_p = sub.add_parser("urls", help="Generate video from URLs config")
    urls_p.add_argument("input", help="Path to URLs config JSON")
    urls_p.add_argument("--plan-only", action="store_true")
    urls_p.add_argument("--extracted-json", default="extracted_content.json")
    urls_p.add_argument("--scene-json", default="generated_scene_plan.json")
    _add_common_args(urls_p)

    # ------ SCENE mode ------
    scene_p = sub.add_parser("scene", help="Generate video from existing scene plan JSON")
    scene_p.add_argument("input", help="Path to scene plan JSON")
    _add_common_args(scene_p)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "auto":
        _auto_pipeline(args)
        return

    # --- URLS / SCENE modes ---
    _resolve_dirs(args)

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found")
        sys.exit(1)

    with open(args.input) as f:
        data = json.load(f)

    if args.command == "urls":
        if args.version:
            run_dir = os.path.join("assets", "runs", args.version)
            if args.extracted_json == "extracted_content.json":
                args.extracted_json = os.path.join(run_dir, "extracted_content.json")
            if args.scene_json == "generated_scene_plan.json":
                args.scene_json = os.path.join(run_dir, "generated_scene_plan.json")

        fetched, section_mapping = _extract(args.input, args.extracted_json)
        data = _plan(fetched, section_mapping, args.scene_json, style=args.style)
        if args.plan_only:
            print(f"\nScene plan saved to {args.scene_json}")
            return

    if "scenes" not in data:
        print("Error: Invalid scene plan JSON (missing 'scenes' key)")
        sys.exit(1)

    _generate_assets_and_video(data, args.image_dir, args.audio_dir, args.output_dir, args)


if __name__ == "__main__":
    main()
