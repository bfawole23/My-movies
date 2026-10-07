"""Image generation, voiceover, and video assembly."""
import asyncio
import base64
import os
import subprocess
import textwrap
import time
import shutil
from pathlib import Path

import edge_tts
import requests
from PIL import Image, ImageDraw

W, H, FPS = 1080, 1920, 30


def _ensure_tools() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            winget_pkgs = Path(local_app) / "Microsoft" / "WinGet" / "Packages"
            for b in winget_pkgs.glob("*ffmpeg*/**/bin"):
                if (b / "ffmpeg.exe").exists() or (b / "ffmpeg").exists():
                    os.environ["PATH"] = f"{b};" + os.environ.get("PATH", "")
                    break


_ensure_tools()


def _replicate(model: str, inp: dict) -> bytes:
    token = os.getenv("REPLICATE_API_TOKEN")
    r = requests.post(
        f"https://api.replicate.com/v1/models/{model}/predictions",
        headers={"Authorization": f"Bearer {token}", "Prefer": "wait"},
        json={"input": inp},
        timeout=180,
    )
    r.raise_for_status()
    data = r.json()
    while data.get("status") not in ("succeeded", "failed", "canceled"):
        time.sleep(2)
        data = requests.get(data["urls"]["get"], headers={"Authorization": f"Bearer {token}"}).json()
    if data["status"] != "succeeded":
        raise RuntimeError(f"Image generation failed: {data.get('error')}")
    url = data["output"][0] if isinstance(data["output"], list) else data["output"]
    return requests.get(url, timeout=120).content


def _has_replicate() -> bool:
    t = os.getenv("REPLICATE_API_TOKEN", "").strip()
    return bool(t and not t.startswith("your_"))


def make_character_ref(look: str, style: str, out: Path) -> None:
    """One reference portrait per character. Replace the PNG with your own image anytime."""
    if not _has_replicate():
        return _placeholder(f"CHARACTER REFERENCE: {look}", out)
    out.write_bytes(_replicate("black-forest-labs/flux-schnell", {
        "prompt": f"ultra-realistic 8k glamour shot portrait, head and upper body, natural skin texture, clear bright background, shot on high-end 85mm camera lens, {look}. {style}",
        "aspect_ratio": "2:3", "output_format": "png"}))


def make_image(prompt: str, style: str, out: Path, ref: Path | None = None) -> None:
    if not _has_replicate():
        if ref and ref.exists():
            import shutil
            shutil.copy(ref, out)
            return
        return _placeholder(prompt, out)
    if ref and ref.exists():
        # Kontext edits a reference image, which keeps the same face and costume across scenes
        uri = "data:image/png;base64," + base64.b64encode(ref.read_bytes()).decode()
        out.write_bytes(_replicate("black-forest-labs/flux-kontext-pro", {
            "prompt": f"Ultra-realistic 8k HD shot, glamour shot, natural lighting, shot on high quality camera. "
                      f"The same character as in the reference image, identical face, hair and costume. "
                      f"Clear bright background, sharp focus, natural skin texture. New scene: {prompt}. {style}",
            "input_image": uri, "aspect_ratio": "9:16", "output_format": "png"}))
    else:
        out.write_bytes(_replicate("black-forest-labs/flux-schnell", {
            "prompt": f"Ultra-realistic 8k HD shot, glamour shot, clear bright background, shot on high quality cinema camera, natural lighting, crystal clear focus, {prompt}. {style}",
            "aspect_ratio": "9:16", "output_format": "png"}))


def _placeholder(prompt: str, out: Path) -> None:
    # Clear, bright high-resolution studio backdrop
    img = Image.new("RGB", (W, H), (242, 246, 252))
    d = ImageDraw.Draw(img)
    d.rectangle([(40, 40), (W - 40, H - 40)], outline=(200, 215, 230), width=3)
    d.text((80, 580), "ULTRA-REALISTIC 8K CINEMATOGRAPHY", fill=(45, 85, 155))
    d.multiline_text((80, 680), "\n".join(textwrap.wrap(prompt, 38)[:12]), fill=(25, 30, 45), spacing=14)
    img.save(out)


def make_voice(text: str, out: Path, voice: str = "", pitch: str = "+0Hz", rate: str = "+0%") -> None:
    chosen_voice = voice or os.getenv("VOICE", "en-US-BrianNeural")
    for attempt in range(4):
        try:
            asyncio.run(edge_tts.Communicate(text, chosen_voice, pitch=pitch, rate=rate).save(str(out)))
            return
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2)


def make_scene_audio(dialogue_data, out: Path, cast_voices: dict, default_voice: str = "en-US-BrianNeural") -> None:
    """Renders single or multi-turn character dialogue into a combined scene audio track."""
    if isinstance(dialogue_data, list):
        temp_dir = out.parent / f"_temp_{out.stem}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        part_files = []
        for idx, turn in enumerate(dialogue_data):
            speaker = turn.get("speaker", "")
            line = turn.get("line") or turn.get("text") or str(turn)
            cfg = cast_voices.get(speaker.lower(), {}) if speaker else {}
            v = cfg.get("voice", default_voice)
            p = cfg.get("pitch", "+0Hz")
            r = cfg.get("rate", "+0%")
            part_path = temp_dir / f"turn_{idx:03d}.mp3"
            make_voice(line, part_path, voice=v, pitch=p, rate=r)
            part_files.append(part_path)
        listfile = temp_dir / "list.txt"
        listfile.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in part_files))
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", str(out)],
            check=True, capture_output=True,
        )
        for p in part_files:
            p.unlink(missing_ok=True)
        listfile.unlink(missing_ok=True)
        try:
            temp_dir.rmdir()
        except OSError:
            pass
    else:
        make_voice(str(dialogue_data), out, voice=default_voice)



def _duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def make_cinematic_shot(image: Path, audio: Path, out: Path, speaker: str = "", grade: str = "") -> None:
    """Renders an individual speaking shot with character-tailored camera motion and atmospheric lighting."""
    dur = _duration(audio) + 0.35
    frames = int(dur * FPS)
    spk = (speaker or "").lower()

    if "shadow" in spk:
        # Faded spectral replica: shimmering ethereal wave, cold silver luminescence, floating ghost mist
        vf = (
            f"scale=2160:3840,"
            f"zoompan=z='1.09 + 0.04*sin(on*0.3)':"
            f"x='(iw-iw/zoom)/2 + (iw/zoom)*0.03*sin(on*0.15)':"
            f"y='(ih-ih/zoom)/2 + (ih/zoom)*0.025*cos(on*0.12)':"
            f"d={frames}:s={W}x{H}:fps={FPS},"
            f"colorchannelmixer=rr=0.88:gg=0.92:bb=1.14,"
            f"eq=brightness='0.025*sin(2*PI*t*1.6)':contrast='1.12 + 0.04*cos(2*PI*t*1.2)',"
            f"unsharp=5:5:0.6:5:5:0.0"
        )
    elif "leo" in spk:
        # Energetic young prince: bouncy dynamic tracking camera
        vf = (
            f"scale=2160:3840,"
            f"zoompan=z='1.07 + 0.05*(on/{frames}) + 0.007*sin(on*0.9)':"
            f"x='(iw-iw/zoom)/2 + (iw/zoom)*0.022*sin(on*0.2)':"
            f"y='(ih-ih/zoom)/2 + (ih/zoom)*0.016*cos(on*0.25)':"
            f"d={frames}:s={W}x{H}:fps={FPS},"
            f"eq=contrast='1.08 + 0.03*sin(2*PI*t*3.0)':gamma='1.03 + 0.03*cos(2*PI*t*3.5)',"
            f"unsharp=5:5:0.5:5:5:0.0"
        )
    elif "rosalind" in spk:
        # Scholar noblewoman: smooth horizontal slider dolly pan
        vf = (
            f"scale=2160:3840,"
            f"zoompan=z='1.08 + 0.02*(on/{frames})':"
            f"x='(iw-iw/zoom)*0.35 + (iw-iw/zoom)*0.3*(on/{frames}) + (iw/zoom)*0.008*sin(on*0.3)':"
            f"y='(ih-ih/zoom)/2 + (ih/zoom)*0.01*cos(on*0.08)':"
            f"d={frames}:s={W}x{H}:fps={FPS},"
            f"eq=contrast='1.05 + 0.02*sin(2*PI*t*2.0)':gamma='1.02 + 0.02*cos(2*PI*t*2.8)',"
            f"unsharp=5:5:0.5:5:5:0.0"
        )
    elif "iselde" in spk:
        # Commanding Queen: regal pull-back shot with subtle head sway
        vf = (
            f"scale=2160:3840,"
            f"zoompan=z='1.14 - 0.06*(on/{frames}) + 0.004*cos(on*0.4)':"
            f"x='(iw-iw/zoom)/2 + (iw/zoom)*0.01*cos(on*0.06)':"
            f"y='(ih-ih/zoom)/2 + (ih/zoom)*0.008*sin(on*0.05)':"
            f"d={frames}:s={W}x{H}:fps={FPS},"
            f"eq=contrast='1.07 + 0.02*cos(2*PI*t*1.5)':gamma='1.03 + 0.025*sin(2*PI*t*2.5)',"
            f"unsharp=5:5:0.5:5:5:0.0"
        )
    elif "doran" in spk:
        # Veteran knight: gritty Steadicam with subtle handheld micro-drift
        vf = (
            f"scale=2160:3840,"
            f"zoompan=z='1.08 + 0.04*(on/{frames}) + 0.005*sin(on*0.7)':"
            f"x='(iw-iw/zoom)/2 + (iw/zoom)*0.018*cos(on*0.3)':"
            f"y='(ih-ih/zoom)/2 + (ih/zoom)*0.014*sin(on*0.28)':"
            f"d={frames}:s={W}x{H}:fps={FPS},"
            f"eq=contrast='1.08 + 0.025*sin(2*PI*t*1.6)':gamma='1.01 + 0.03*sin(2*PI*t*2.7)',"
            f"unsharp=5:5:0.6:5:5:0.0"
        )
    elif "pell" in spk:
        # Anxious chancellor: nervous micro-jitter and fussy tilt
        vf = (
            f"scale=2160:3840,"
            f"zoompan=z='1.10 - 0.03*(on/{frames}) + 0.006*sin(on*0.8)':"
            f"x='(iw-iw/zoom)/2 + (iw/zoom)*0.015*sin(on*0.4)':"
            f"y='(ih-ih/zoom)/2 + (ih/zoom)*0.012*cos(on*0.35)':"
            f"d={frames}:s={W}x{H}:fps={FPS},"
            f"eq=contrast='1.06 + 0.02*sin(2*PI*t*2.2)':gamma='1.02 + 0.025*cos(2*PI*t*3.0)',"
            f"unsharp=5:5:0.5:5:5:0.0"
        )
    else:
        # King Maelor / Dramatic lead push-in with candlelight flicker
        vf = (
            f"scale=2160:3840,"
            f"zoompan=z='1.06 + 0.08*(on/{frames}) + 0.005*sin(on*0.5)':"
            f"x='(iw-iw/zoom)/2 + (iw/zoom)*0.015*sin(on*0.08)':"
            f"y='(ih-ih/zoom)/2 + (ih/zoom)*0.01*cos(on*0.06)':"
            f"d={frames}:s={W}x{H}:fps={FPS},"
            f"eq=contrast='1.06 + 0.025*sin(2*PI*t*1.8)':gamma='1.02 + 0.03*sin(2*PI*t*2.9 + 0.8)',"
            f"unsharp=5:5:0.5:5:5:0.0"
        )

    if grade:
        vf += f",{grade}"
    vf += ",format=yuv420p"

    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", str(image), "-i", str(audio),
         "-vf", vf, "-t", f"{dur}", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)],
        check=True, capture_output=True,
    )


def make_clip(image: Path, audio: Path, out: Path, grade: str = "") -> None:
    make_cinematic_shot(image, audio, out, speaker="", grade=grade)


def make_scene_video(dialogue_data, scene_img: Path, scene_aud: Path, out_clip: Path,
                     refs: dict, cast_voices: dict, default_voice: str, grade: str = "") -> None:
    """Renders a scene as a sequence of dynamic cinematic shots cutting between speaking actors."""
    if isinstance(dialogue_data, list) and len(dialogue_data) > 1:
        temp_dir = out_clip.parent / f"_shots_{out_clip.stem}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        shot_clips = []
        for idx, turn in enumerate(dialogue_data):
            spk = turn.get("speaker", "")
            line = turn.get("line") or turn.get("text") or str(turn)
            cfg = cast_voices.get(spk.lower(), {}) if spk else {}
            v = cfg.get("voice", default_voice)
            p = cfg.get("pitch", "+0Hz")
            r = cfg.get("rate", "+0%")
            turn_aud = temp_dir / f"turn_{idx:03d}.mp3"
            turn_clip = temp_dir / f"shot_{idx:03d}.mp4"
            make_voice(line, turn_aud, voice=v, pitch=p, rate=r)

            # Cut to the speaking actor's portrait, or fallback to scene image
            img = refs.get(spk.lower(), scene_img)
            if not img.exists():
                img = scene_img

            make_cinematic_shot(img, turn_aud, turn_clip, speaker=spk, grade=grade)
            shot_clips.append(turn_clip)

        concat(shot_clips, out_clip)
        for c in shot_clips:
            c.unlink(missing_ok=True)
            turn_a = c.with_suffix(".mp3")
            turn_a.unlink(missing_ok=True)
        try:
            temp_dir.rmdir()
        except OSError:
            pass
    else:
        spk = dialogue_data[0].get("speaker", "") if isinstance(dialogue_data, list) and dialogue_data else ""
        make_cinematic_shot(scene_img, scene_aud, out_clip, speaker=spk, grade=grade)


def concat(clips: list[Path], out: Path) -> None:
    listfile = out.with_suffix(".txt")
    listfile.write_text("".join(f"file '{c.resolve().as_posix()}'\n" for c in clips))
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", str(out)],
        check=True, capture_output=True,
    )
