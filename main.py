"""Main orchestrator -- parses scene JSON, generates images via GPT, generates narration via TTS, builds video."""

import os
import sys
import json
import argparse
from pathlib import Path

from image_generator import generate_scene_image, add_text_overlay
from utils.tts_utils import text_to_speech
from video_builder import build_video


def main():
    parser = argparse.ArgumentParser(description="Generate video from scene descriptions using GPT image generation.")
    parser.add_argument("input_json", help="Path to input JSON file")
    parser.add_argument("--output", default="assets/outputs/final_video.mp4", help="Output video path")
    parser.add_argument("--skip-images", action="store_true", help="Skip image generation (reuse existing)")
    parser.add_argument("--skip-audio", action="store_true", help="Skip audio generation (reuse existing)")
    parser.add_argument("--model", default="gpt-image-1", help="Image generation model name")
    parser.add_argument("--voice", default="alloy", help="TTS voice (alloy, echo, fable, onyx, nova, shimmer)")
    args = parser.parse_args()

    if not os.path.exists(args.input_json):
        print(f"Error: {args.input_json} not found")
        sys.exit(1)

    with open(args.input_json) as f:
        data = json.load(f)

    scenes = data["scenes"]
    style = data.get("overall_style", "")
    total = len(scenes)

    print(f"Loaded {total} scenes from {args.input_json}")

    image_dir = "assets/images"
    audio_dir = "assets/audio"
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    # Step 1: Generate images
    if not args.skip_images:
        print(f"\n[1/3] Generating scene images ({args.model})...")
        for scene in scenes:
            num = scene["scene_number"]
            raw_path = os.path.join(image_dir, f"scene_{num}_raw.png")
            final_path = os.path.join(image_dir, f"scene_{num}.png")

            print(f"  Scene {num}/{total}: generating image...")
            generate_scene_image(scene["visual_prompt"], raw_path, style=style, model=args.model)

            text = scene.get("on_screen_text", "")
            add_text_overlay(raw_path, text, final_path)
            print(f"  Scene {num}/{total}: done")
    else:
        print("\n[1/3] Skipping image generation (using existing)")

    # Step 2: Generate narration audio
    if not args.skip_audio:
        print("\n[2/3] Generating narration audio...")
        for scene in scenes:
            num = scene["scene_number"]
            script = scene.get("audio_script", "")
            if not script:
                continue
            audio_path = os.path.join(audio_dir, f"scene_{num}.mp3")
            print(f"  Scene {num}/{total}: generating audio...")
            text_to_speech(script, audio_path, voice=args.voice)
    else:
        print("\n[2/3] Skipping audio generation (using existing)")

    # Step 3: Build video
    print("\n[3/3] Building video...")
    output = build_video(scenes, image_dir, audio_dir, args.output)
    print(f"\nDone -- {output}")


if __name__ == "__main__":
    main()
