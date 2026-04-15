"""AMCA Defence Intelligence Video Generator.

End-to-end pipeline:
  1. Tavily Search  → Find AMCA/defence news articles (quarterly by default)
  2. Curation       → AlphaSense-grade filtering & structuring with GPT-5-nano
  3. Excel Export   → Structured report with Executive Summary, Citations
  4. Scene Planning → Generate video scene plan via GPT
  5. Image Gen      → Generate infographic images via Azure OpenAI
  6. TTS            → Generate narration audio
  7. Video Assembly → Compose final MP4 (with and without voiceover)

Usage:
    python main.py --curation-only               # Stop after curation + Excel (testing)
    python main.py --plan-only                    # Stop after scene plan
    python main.py                                # Full pipeline
    python main.py --date-mode week               # Weekly instead of quarterly
    python main.py --output-dir assets/runs/q1_2026
"""

import os
import sys
import json
import argparse

from image_generator import generate_scene_image, add_text_overlay
from utils.tts_utils import text_to_speech
from video_builder import build_video_pair


def run_pipeline(args):
    """Full end-to-end pipeline: Search → Curate → Excel → Plan → Images → TTS → Video."""
    from tavily_search import search_aviation_news
    from curation_agent import curate_articles
    from utils.excel_export import export_to_excel

    run_dir = args.output_dir
    os.makedirs(run_dir, exist_ok=True)
    image_dir = os.path.join(run_dir, "images")
    audio_dir = os.path.join(run_dir, "audio")
    output_dir = os.path.join(run_dir, "outputs")

    # ─── STEP 1: Search ──────────────────────────────────────────────
    print("=" * 60)
    print("STEP 1: Searching AMCA & defence news")
    print("=" * 60)

    days_back = args.days_back if args.days_back else None
    search_results = search_aviation_news(
        days_back=days_back,
        save_path=os.path.join(run_dir, "tavily_results.json"),
        date_mode=args.date_mode,
    )
    if not search_results:
        print("❌ No search results found. Check TAVILY_API_KEY and internet.")
        sys.exit(1)
    print(f"✅ Found {len(search_results)} articles")

    # ─── STEP 2: Curate ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 2: Curating articles (GPT-5-nano, AlphaSense-style)")
    print("=" * 60)

    curated = curate_articles(
        search_results,
        save_path=os.path.join(run_dir, "curated_articles.json"),
    )
    selected = curated.get("selected_articles", [])
    if not selected:
        print("❌ No relevant articles found after curation.")
        sys.exit(1)
    print(f"✅ Curated {len(selected)} articles")

    # ─── Export to Excel ─────────────────────────────────────────────
    excel_path = os.path.join(run_dir, "articles_report.xlsx")
    export_to_excel(search_results, curated, excel_path)

    if args.curation_only:
        print(f"\n🛑 Curation-only mode. Results saved to:")
        print(f"   JSON:  {os.path.join(run_dir, 'curated_articles.json')}")
        print(f"   Excel: {excel_path}")
        return

    # ─── STEP 3: Scene Plan ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 3: Generating video scene plan")
    print("=" * 60)

    from scene_planner import generate_scene_plan, save_scene_plan, build_context_from_curated
    context = build_context_from_curated(curated)
    scene_plan_path = os.path.join(run_dir, "generated_scene_plan.json")
    plan = generate_scene_plan(context, style=args.style, slides=args.slides)
    save_scene_plan(plan, scene_plan_path)

    scenes = plan.get("scenes", [])
    total_dur = sum(s.get("duration_seconds", 0) for s in scenes)
    print(f"✅ Generated {len(scenes)} scenes, {total_dur:.1f}s total -> {scene_plan_path}")

    if args.plan_only:
        print(f"\n🛑 Plan-only mode. Scene plan saved to: {scene_plan_path}")
        return

    # ─── STEP 4: Image Generation ────────────────────────────────────
    if not args.skip_images:
        print("\n" + "=" * 60)
        print(f"STEP 4: Generating {len(scenes)} scene images")
        print("=" * 60)
        os.makedirs(image_dir, exist_ok=True)

        overall_style = plan.get("overall_style", "")
        for scene in scenes:
            num = scene["scene_number"]
            raw_path = os.path.join(image_dir, f"scene_{num}_raw.png")
            final_path = os.path.join(image_dir, f"scene_{num}.png")

            if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
                print(f"  Scene {num}/{len(scenes)} (cached)")
                continue

            print(f"  Scene {num}/{len(scenes)}...")
            generate_scene_image(
                scene["visual_prompt"], raw_path,
                style=overall_style, model=args.model,
                visual_style=args.style,
            )

            if args.style == "infographic":
                os.replace(raw_path, final_path)
            else:
                text = scene.get("on_screen_text", "")
                add_text_overlay(raw_path, text, final_path)
    else:
        print("\n⏭️  Skipping image generation (--skip-images)")

    # ─── STEP 5: TTS Audio ───────────────────────────────────────────
    if not args.skip_audio:
        print("\n" + "=" * 60)
        print(f"STEP 5: Generating {len(scenes)} narration clips")
        print("=" * 60)
        os.makedirs(audio_dir, exist_ok=True)

        for scene in scenes:
            num = scene["scene_number"]
            script = scene.get("audio_script", "")
            if not script:
                continue

            audio_path = os.path.join(audio_dir, f"scene_{num}.mp3")
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                print(f"  Scene {num}/{len(scenes)} (cached)")
                continue

            print(f"  Scene {num}/{len(scenes)}...")
            text_to_speech(script, audio_path, voice=args.voice)
    else:
        print("\n⏭️  Skipping audio generation (--skip-audio)")

    # ─── STEP 6: Video Assembly ──────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"STEP 6: Assembling video ({len(scenes)} scenes, {total_dur:.1f}s)")
    print("=" * 60)

    path_with, path_without = build_video_pair(scenes, image_dir, audio_dir, output_dir)

    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  With voiceover:    {path_with}")
    print(f"  Without voiceover: {path_without}")
    print(f"  Output directory:  {run_dir}")


def main():
    parser = argparse.ArgumentParser(description="AMCA Defence Intelligence Video Generator")
    parser.add_argument("--output-dir", default="assets/runs/auto", help="Output directory")
    parser.add_argument("--days-back", type=int, default=None, help="Override days back (default: auto)")
    parser.add_argument("--date-mode", choices=["quarter", "week"], default="quarter",
                        help="Date range mode (default: quarter = 90 days)")
    parser.add_argument("--curation-only", action="store_true",
                        help="Stop after curation + Excel export (no video)")
    parser.add_argument("--plan-only", action="store_true", help="Stop after generating scene plan")
    parser.add_argument("--skip-images", action="store_true", help="Skip image generation")
    parser.add_argument("--skip-audio", action="store_true", help="Skip TTS audio generation")
    parser.add_argument("--model", default=None, help="Override Azure OpenAI model deployment")
    parser.add_argument("--voice", default="alloy", help="TTS voice (default: alloy)")
    parser.add_argument("--style", choices=["photo", "infographic"], default="infographic",
                        help="Visual style (default: infographic)")
    parser.add_argument("--slides", type=int, default=3,
                        help="Number of slides: 3 for Q&A briefing (default), 0 for full multi-scene")
    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
