import os
import sys
import json
import argparse
from image_generator import generate_scene_image, add_text_overlay
from utils.tts_utils import text_to_speech
from video_builder import build_video, build_video_pair


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


def _auto_pipeline(args):
    """Automated pipeline: Tavily search -> Curation -> 3-slide briefing -> Video pair."""
    from tavily_search import search_aviation_news, load_whitelist_from_config
    from curation_agent import curate_articles, generate_briefing_summary

    run_dir = args.output_dir
    os.makedirs(run_dir, exist_ok=True)

    # Step 1: Tavily search
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

    # Step 2: Curate articles
    print("\n" + "=" * 60)
    print("STEP 2: Curating and ranking articles")
    print("=" * 60)
    curated = curate_articles(
        search_results,
        save_path=os.path.join(run_dir, "curated_articles.json"),
    )

    # Step 3: Generate 3-slide briefing
    print("\n" + "=" * 60)
    print("STEP 3: Generating 3-slide briefing summary")
    print("=" * 60)
    scene_plan_path = os.path.join(run_dir, "generated_scene_plan.json")
    plan = generate_briefing_summary(curated, save_path=scene_plan_path)

    if args.plan_only:
        print(f"\nScene plan saved to {scene_plan_path}")
        return

    # Step 4: Generate images + audio + video pair
    _generate_video_pair(plan, args)


def _generate_video_pair(data, args):
    """Generate images, audio, and TWO videos (with/without voiceover)."""
    scenes = data["scenes"]
    style = data.get("overall_style", "")
    visual_style = args.style
    total = len(scenes)
    total_dur = sum(s.get("duration_seconds", 0) for s in scenes)

    run_dir = args.output_dir
    image_dir = os.path.join(run_dir, "images")
    audio_dir = os.path.join(run_dir, "audio")
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    # Generate images
    if not args.skip_images:
        print(f"\nSTEP 4a: Generating {total} scene images...")
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

    # Generate audio
    if not args.skip_audio:
        print(f"\nSTEP 4b: Generating {total} narration clips...")
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

    # Build both videos
    print(f"\nSTEP 5: Assembling 2 videos ({total} scenes, {total_dur:.1f}s)...")
    output_dir = os.path.join(run_dir, "outputs")
    path_with, path_without = build_video_pair(scenes, image_dir, audio_dir, output_dir)
    print(f"\nDone!")
    print(f"  With voiceover:    {path_with}")
    print(f"  Without voiceover: {path_without}")


def _generate_video(data, args):
    """Legacy single-video pipeline (from --from-urls or scene JSON)."""
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

    # Build both videos (with and without voiceover)
    print("Assembling final videos...")
    output_dir = os.path.dirname(args.output) or "assets/outputs"
    path_with, path_without = build_video_pair(scenes, image_dir, audio_dir, output_dir)
    print(f"\nDone!")
    print(f"  With voiceover:    {path_with}")
    print(f"  Without voiceover: {path_without}")


def main():
    parser = argparse.ArgumentParser(description="Aviation news video generator")
    sub = parser.add_subparsers(dest="command")

    # ------ AUTO mode: Tavily search -> Curation -> Video ------
    auto_parser = sub.add_parser("auto", help="Auto-search, curate, and generate 3-slide briefing video")
    auto_parser.add_argument("--output-dir", default="assets/runs/auto",
                             help="Directory for all outputs (default: assets/runs/auto)")
    auto_parser.add_argument("--days-back", type=int, default=7,
                             help="Search articles from past N days (default: 7)")
    auto_parser.add_argument("--plan-only", action="store_true",
                             help="Stop after generating scene plan")
    auto_parser.add_argument("--skip-images", action="store_true")
    auto_parser.add_argument("--skip-audio", action="store_true")
    auto_parser.add_argument("--model", default=None)
    auto_parser.add_argument("--voice", default="alloy")
    auto_parser.add_argument("--style", choices=["photo", "infographic"],
                             default="infographic")

    # ------ URLS mode: existing pipeline ------
    urls_parser = sub.add_parser("urls", help="Generate video from URLs config")
    urls_parser.add_argument("input", help="Path to URLs config JSON")
    urls_parser.add_argument("--plan-only", action="store_true")
    urls_parser.add_argument("--extracted-json", default="extracted_content.json")
    urls_parser.add_argument("--scene-json", default="generated_scene_plan.json")
    urls_parser.add_argument("--output", default="assets/outputs/final_video.mp4")
    urls_parser.add_argument("--skip-images", action="store_true")
    urls_parser.add_argument("--skip-audio", action="store_true")
    urls_parser.add_argument("--model", default=None)
    urls_parser.add_argument("--voice", default="alloy")
    urls_parser.add_argument("--style", choices=["photo", "infographic"],
                             default="infographic")
    urls_parser.add_argument("--version", default=None)

    # ------ SCENE mode: from existing scene plan JSON ------
    scene_parser = sub.add_parser("scene", help="Generate video from existing scene plan JSON")
    scene_parser.add_argument("input", help="Path to scene plan JSON")
    scene_parser.add_argument("--output", default="assets/outputs/final_video.mp4")
    scene_parser.add_argument("--skip-images", action="store_true")
    scene_parser.add_argument("--skip-audio", action="store_true")
    scene_parser.add_argument("--model", default=None)
    scene_parser.add_argument("--voice", default="alloy")
    scene_parser.add_argument("--style", choices=["photo", "infographic"],
                             default="infographic")
    scene_parser.add_argument("--version", default=None)

    args = parser.parse_args()

    # Backward compatibility: if no subcommand, try legacy mode
    if args.command is None:
        # Check if first positional arg looks like old-style usage
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            legacy_parser = argparse.ArgumentParser()
            legacy_parser.add_argument("input")
            legacy_parser.add_argument("--from-urls", action="store_true")
            legacy_parser.add_argument("--plan-only", action="store_true")
            legacy_parser.add_argument("--extracted-json", default="extracted_content.json")
            legacy_parser.add_argument("--scene-json", default="generated_scene_plan.json")
            legacy_parser.add_argument("--output", default="assets/outputs/final_video.mp4")
            legacy_parser.add_argument("--skip-images", action="store_true")
            legacy_parser.add_argument("--skip-audio", action="store_true")
            legacy_parser.add_argument("--model", default=None)
            legacy_parser.add_argument("--voice", default="alloy")
            legacy_parser.add_argument("--style", choices=["photo", "infographic"], default="infographic")
            legacy_parser.add_argument("--version", default=None)
            args = legacy_parser.parse_args()
            args.command = "legacy"
        else:
            parser.print_help()
            sys.exit(1)

    # ---- AUTO mode ----
    if args.command == "auto":
        _auto_pipeline(args)
        return

    # ---- URLS / SCENE / LEGACY mode ----
    if args.command in ("urls", "legacy"):
        if hasattr(args, "version") and args.version:
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

        from_urls = getattr(args, "from_urls", False) or args.command == "urls"
        if "categories" in data or from_urls:
            fetched, section_mapping = _extract(args.input, args.extracted_json)
            data = _plan(fetched, section_mapping, args.scene_json, style=args.style)
            if args.plan_only:
                print(f"\nScene plan saved to {args.scene_json}")
                return

        if "scenes" not in data:
            print("Error: Invalid scene plan JSON (missing 'scenes' key)")
            sys.exit(1)

        _generate_video(data, args)

    elif args.command == "scene":
        if hasattr(args, "version") and args.version:
            run_dir = os.path.join("assets", "runs", args.version)
            os.makedirs(run_dir, exist_ok=True)
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

        if "scenes" not in data:
            print("Error: Invalid scene plan JSON (missing 'scenes' key)")
            sys.exit(1)

        _generate_video(data, args)


if __name__ == "__main__":
    main()
