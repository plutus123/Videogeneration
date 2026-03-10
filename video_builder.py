"""Assembles scene images and narration audio into a final video using MoviePy."""

import os
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, vfx
from mutagen.mp3 import MP3

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30


def _audio_duration(path):
    try:
        return MP3(path).info.length
    except Exception:
        return 0


def build_video(scenes, image_dir, audio_dir, output_path, transition=0.8):
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
        has_audio = os.path.exists(audio_path)
        if has_audio:
            audio_dur = _audio_duration(audio_path)
            if audio_dur > 0:
                duration = max(target_dur, audio_dur + 0.5)

        clip = (
            ImageClip(img_path)
            .with_duration(duration)
            .resized((VIDEO_WIDTH, VIDEO_HEIGHT))
        )

        if has_audio:
            clip = clip.with_audio(AudioFileClip(audio_path))

        clips.append(clip)

    if not clips:
        raise ValueError("No clips to assemble")

    clips[0] = clips[0].with_effects([vfx.FadeIn(1.0)])
    clips[-1] = clips[-1].with_effects([vfx.FadeOut(1.5)])

    if len(clips) > 1 and transition > 0:
        for i in range(1, len(clips)):
            clips[i] = clips[i].with_effects([vfx.CrossFadeIn(transition)])
        final = concatenate_videoclips(clips, method="compose", padding=-transition)
    else:
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
