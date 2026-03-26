"""Assembles scene images and narration audio into a final video using MoviePy."""

import os
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, vfx
from mutagen.mp3 import MP3

VIDEO_WIDTH = 1536
VIDEO_HEIGHT = 1024
FPS = 30


def _audio_duration(path):
    try:
        return MP3(path).info.length
    except Exception:
        return 0


def build_video(scenes, image_dir, audio_dir, output_path, include_audio=True):
    """Build a single video from scenes.

    Args:
        scenes:        List of scene dicts.
        image_dir:     Directory containing scene_N.png files.
        audio_dir:     Directory containing scene_N.mp3 files.
        output_path:   Where to write the .mp4.
        include_audio: If False, build a silent video (no voiceover).
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    clips = []

    for scene in scenes:
        num = scene["scene_number"]
        target_dur = scene.get("duration_seconds", 8)

        img_path = os.path.join(image_dir, f"scene_{num}.png")
        audio_path = os.path.join(audio_dir, f"scene_{num}.mp3")

        if not os.path.exists(img_path):
            print(f"  Warning: {img_path} not found, skipping scene {num}")
            continue

        duration = target_dur
        has_audio = include_audio and os.path.exists(audio_path)
        if has_audio:
            audio_dur = _audio_duration(audio_path)
            if audio_dur > 0:
                duration = max(target_dur, audio_dur + 0.3)

        clip = (
            ImageClip(img_path)
            .with_duration(duration)
            .resized((VIDEO_WIDTH, VIDEO_HEIGHT))
        )

        if has_audio:
            audio_clip = AudioFileClip(audio_path)
            clip = clip.with_audio(audio_clip)

        clips.append(clip)

    if not clips:
        raise ValueError("No clips to assemble")

    clips[0] = clips[0].with_effects([vfx.FadeIn(0.5)])
    clips[-1] = clips[-1].with_effects([vfx.FadeOut(1.0)])
    final = concatenate_videoclips(clips, method="compose")

    final.write_videofile(
        output_path, fps=FPS, codec="libx264",
        audio_codec="aac", bitrate="5000k",
        preset="medium", threads=4,
    )

    for c in clips:
        c.close()
    final.close()

    return output_path


def build_video_pair(scenes, image_dir, audio_dir, output_dir):
    """Build TWO videos: one with voiceover, one without.

    Args:
        scenes:     List of scene dicts.
        image_dir:  Directory containing scene images.
        audio_dir:  Directory containing scene audio.
        output_dir: Directory to write both videos into.

    Returns:
        Tuple of (path_with_voice, path_without_voice).
    """
    os.makedirs(output_dir, exist_ok=True)

    path_with = os.path.join(output_dir, "final_with_voiceover.mp4")
    path_without = os.path.join(output_dir, "final_without_voiceover.mp4")

    print("  Building video WITH voiceover...")
    build_video(scenes, image_dir, audio_dir, path_with, include_audio=True)
    print(f"  -> {path_with}")

    print("  Building video WITHOUT voiceover...")
    build_video(scenes, image_dir, audio_dir, path_without, include_audio=False)
    print(f"  -> {path_without}")

    return path_with, path_without
