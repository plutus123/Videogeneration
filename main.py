"""Main orchestrator -- loads input, generates content via GPT, renders HTML slides, and builds the final video."""

import os
import sys
import re
import json
import argparse
from pathlib import Path

from gpt_formatter import load_structured_input, generate_all_scenes
from slide_renderer import render_slides_to_images, build_video_from_slides


def main():
    parser = argparse.ArgumentParser(description="Generate a presentation video from structured JSON input.")
    parser.add_argument("input_json", help="Path to the input JSON file")
    parser.add_argument("--skip-generation", action="store_true", help="Reuse previously generated slide data")
    parser.add_argument("--output-dir", default="assets/outputs", help="Directory for the final video")
    parser.add_argument("--scenes-dir", default="generated_scenes", help="Directory for generated scene data")
    parser.add_argument("--no-tts", action="store_true", help="Disable text-to-speech narration")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    if not input_path.exists():
        print(f"Error: file not found -- {args.input_json}")
        sys.exit(1)

    print("=" * 70)
    print("Presentation Video Generator")
    print("=" * 70)

    # 1. Load input
    print("\n[1/4] Loading input...")
    structured_input = load_structured_input(args.input_json)
    title = structured_input.get("title", "Untitled")
    scenes_raw = structured_input.get("scenes", [])
    num_sections = len(scenes_raw) if scenes_raw else len(structured_input.get("full_text", {}))
    total_with_closing = num_sections + 1
    print(f"  Title: {title}  |  Slides: {total_with_closing} (including closing)")

    # 2. Generate slide content + narration
    enable_tts = not args.no_tts
    if not args.skip_generation:
        print("\n[2/4] Generating slide content via GPT...")
        generate_all_scenes(structured_input, args.scenes_dir, enable_tts=enable_tts)
    else:
        print("\n[2/4] Using existing slide data...")

    # 3. Load slide JSONs, append closing slide, render to images
    print("\n[3/4] Rendering slides...")
    scenes_dir = Path(args.scenes_dir)
    slides_data = []
    slide_ids = []

    for scene in scenes_raw:
        safe_name = re.sub(r"[^a-z0-9_]", "", scene["title"].lower().replace(" ", "_").replace("'", ""))
        json_path = scenes_dir / f"{safe_name}_slide.json"
        if json_path.exists():
            with open(json_path) as f:
                data = json.load(f)
            data["total_slides"] = total_with_closing
            slides_data.append(data)
        else:
            slides_data.append({
                "title": scene.get("title", ""), "text": scene.get("text", ""),
                "equation": scene.get("equation", ""), "animation": scene.get("animation", ""),
                "slide_index": len(slides_data), "total_slides": total_with_closing,
                "presentation_title": title,
            })
        slide_ids.append(safe_name)

    # Closing slide
    slides_data.append({
        "slide_type": "closing", "slide_index": num_sections,
        "total_slides": total_with_closing, "presentation_title": title,
    })
    slide_ids.append("_closing")

    if len(slides_data) < 2:
        print("Error: not enough slide data.")
        sys.exit(1)

    image_paths = render_slides_to_images(slides_data, output_dir="assets/slide_images")
    print(f"  Captured {len(image_paths)} slides")

    # 4. Build video
    print("\n[4/4] Building video...")
    output_path = os.path.join(args.output_dir, "final_video.mp4")
    final_video = build_video_from_slides(
        image_paths=image_paths,
        narration_dir="assets/narration",
        slide_ids=slide_ids if enable_tts else None,
        output_path=output_path,
        transition_duration=0.8,
        min_slide_duration=6.0,
        padding=1.5,
    )

    print(f"\nDone -- {final_video}")


if __name__ == "__main__":
    main()

