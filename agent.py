"""AI movie series agent.

  python agent.py new "your series idea" --name myshow --episodes 5
  python agent.py episode myshow 1
  python agent.py episode myshow 2
"""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import media  # noqa: E402
import story  # noqa: E402
from styles import DEFAULT_STYLE, STYLES  # noqa: E402

ROOT = Path("series")


def _slug(name: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in name.lower()).strip("_")


def new_series(args):
    folder = ROOT / args.name
    folder.mkdir(parents=True, exist_ok=True)
    bible = story.make_bible(args.idea, args.episodes, args.style)
    (folder / "bible.json").write_text(json.dumps(bible, indent=2))
    print(f"Series: {bible['title']}\n{bible['logline']}\n")
    for e in bible["episode_outline"]:
        print(f"  Ep {e['number']}: {e['title']}")
    print(f"\nEdit {folder / 'bible.json'} if you want to change anything, then run:")
    print(f"  python agent.py episode {args.name} 1")


def make_episode(args):
    folder = ROOT / args.name
    bible = json.loads((folder / "bible.json").read_text())
    ep_dir = folder / f"ep{args.number:02d}"
    (ep_dir / "work").mkdir(parents=True, exist_ok=True)

    previous = []
    for n in range(1, args.number):
        s = folder / f"ep{n:02d}" / "script.json"
        if s.exists():
            previous.append(json.loads(s.read_text())["summary"])

    script_path = ep_dir / "script.json"
    if script_path.exists() and not args.rewrite:
        script = json.loads(script_path.read_text())
    else:
        script = story.write_episode(bible, args.number, previous)
        script_path.write_text(json.dumps(script, indent=2))
    print(f"Episode {args.number}: {script['title']} ({len(script['scenes'])} scenes)")

    # One reference portrait per character, made once and reused by every episode
    refs = {}
    cast_voices = {}
    (folder / "characters").mkdir(exist_ok=True)
    for c in bible["characters"]:
        ref = folder / "characters" / f"{_slug(c['name'])}.png"
        if not ref.exists():
            print(f"  making reference for {c['name']}")
            media.make_character_ref(c["look"], bible["visual_style"], ref)
        refs[c["name"].lower()] = ref
        cast_voices[c["name"].lower()] = {
            "voice": c.get("voice", "en-US-BrianNeural"),
            "pitch": c.get("pitch", "+0Hz"),
            "rate": c.get("rate", "+0%"),
        }

    clips = []
    for i, scene in enumerate(script["scenes"], 1):
        work = ep_dir / "work"
        img, aud, clip = work / f"{i:02d}.png", work / f"{i:02d}.mp3", work / f"{i:02d}.mp4"
        if not img.exists():
            lead = next((refs[n.lower()] for n in scene.get("characters", []) if n.lower() in refs), None)
            media.make_image(scene["visual_prompt"], bible["visual_style"], img, lead)
        dialogue_data = scene.get("dialogue") or scene.get("narration", "")
        speaker = scene.get("speaker")
        if not speaker and scene.get("characters"):
            speaker = scene["characters"][0]
        speaker_info = cast_voices.get(speaker.lower(), {}) if speaker else {}
        v = speaker_info.get("voice", os.getenv("VOICE", "en-US-BrianNeural"))

        if not aud.exists() or aud.stat().st_size == 0:
            media.make_scene_audio(dialogue_data, aud, cast_voices, default_voice=v)
        if not clip.exists():
            media.make_scene_video(
                dialogue_data, img, aud, clip,
                refs=refs, cast_voices=cast_voices, default_voice=v,
                grade=STYLES[bible.get("style_key", DEFAULT_STYLE)]["grade"]
            )
        clips.append(clip)
        print(f"  scene {i}/{len(script['scenes'])} done")

    final = ep_dir / f"{args.name}_ep{args.number:02d}.mp4"
    media.concat(clips, final)
    (ep_dir / "caption.txt").write_text(f"{bible['title']} - Ep {args.number}: {script['title']}\n\n{script['caption']}\n")
    print(f"\nReady to upload: {final}\nCaption: {ep_dir / 'caption.txt'}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(required=True)

    a = sub.add_parser("new")
    a.add_argument("idea")
    a.add_argument("--name", required=True)
    a.add_argument("--episodes", type=int, default=5)
    a.add_argument("--style", choices=list(STYLES), default=DEFAULT_STYLE,
                   help="realistic = ultra-realistic 8k glamour cinema, arena = gritty historical epic, legend = medieval fantasy")
    a.set_defaults(fn=new_series)

    b = sub.add_parser("episode")
    b.add_argument("name")
    b.add_argument("number", type=int)
    b.add_argument("--rewrite", action="store_true", help="regenerate the script")
    b.set_defaults(fn=make_episode)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
