"""Interactive launcher for AI Movie Series Agent."""
import os
import sys
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path("series")


def check_env():
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    replicate_token = os.getenv("REPLICATE_API_TOKEN", "").strip()
    has_anthropic = bool(anthropic_key and not anthropic_key.startswith("your_"))
    has_replicate = bool(replicate_token and not replicate_token.startswith("your_"))
    return has_anthropic, has_replicate


def list_series():
    if not ROOT.exists():
        return []
    return [d for d in ROOT.iterdir() if d.is_dir() and (d / "bible.json").exists()]


def show_banner():
    has_claude, has_replicate = check_env()
    print("=" * 60)
    print("           🎬 AI MOVIE SERIES AGENT - CONTROL PANEL")
    print("=" * 60)
    print(f" Anthropic API Key : {'[READY] ✅' if has_claude else '[NOT SET - needed for script writing] ⚠️'}")
    print(f" Replicate API Key : {'[READY] ✅' if has_replicate else '[NOT SET - using placeholder cards] ℹ️'}")
    print("=" * 60)


def main():
    while True:
        show_banner()
        all_series = list_series()
        print("\nAvailable Options:")
        print("  1. Make / Render an Episode")
        print("  2. Create a New Series Bible")
        print("  3. View Existing Series & Generated Episodes")
        print("  4. Play a Rendered Video")
        print("  5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            if not all_series:
                print("\n[!] No series found in 'series/' folder. Create one first!")
                input("\nPress Enter to return...")
                continue
            
            print("\nSelect a Series:")
            for idx, s in enumerate(all_series, 1):
                bible = json.loads((s / "bible.json").read_text())
                print(f"  {idx}. {s.name} - \"{bible.get('title', s.name)}\"")
            
            s_choice = input(f"Choose series (1-{len(all_series)}): ").strip()
            if not s_choice.isdigit() or not (1 <= int(s_choice) <= len(all_series)):
                print("Invalid choice.")
                continue
            selected_series = all_series[int(s_choice) - 1]
            
            ep_num = input("Enter Episode number to generate (e.g. 1, 2, 3...): ").strip()
            if not ep_num.isdigit():
                print("Invalid episode number.")
                continue
                
            rewrite = input("Force rewrite script with Claude? (y/N): ").strip().lower() == "y"
            
            cmd = [sys.executable, "agent.py", "episode", selected_series.name, ep_num]
            if rewrite:
                cmd.append("--rewrite")
                
            print(f"\n🚀 Running: {' '.join(cmd)}\n")
            subprocess.run(cmd)
            input("\nPress Enter to return to main menu...")

        elif choice == "2":
            has_claude, _ = check_env()
            if not has_claude:
                print("\n[!] Claude API key is required to write a new series bible.")
                print("    Please add your ANTHROPIC_API_KEY into .env first.")
                input("\nPress Enter to return...")
                continue
                
            idea = input("\nEnter series logline / idea: ").strip()
            if not idea:
                print("Idea cannot be empty.")
                continue
            name = input("Folder name for series (e.g. lagos_shadows): ").strip()
            episodes = input("Number of episodes [default: 5]: ").strip() or "5"
            style = input("Visual style [realistic / arena / legend, default: realistic]: ").strip() or "realistic"
            
            cmd = [sys.executable, "agent.py", "new", idea, "--name", name, "--episodes", episodes, "--style", style]
            print(f"\n🚀 Running: {' '.join(cmd)}\n")
            subprocess.run(cmd)
            input("\nPress Enter to return to main menu...")

        elif choice == "3":
            print("\n--- Series Library ---")
            for idx, s in enumerate(all_series, 1):
                bible = json.loads((s / "bible.json").read_text(encoding="utf-8"))
                print(f"\n📁 [{idx}] {s.name.upper()} : {bible.get('title')}")
                print(f"   Logline: {bible.get('logline')}")
                print(f"   Style: {bible.get('style_key')}")
                print(f"   Total Episodes in Bible: {len(bible.get('episode_outline', []))}")
                chars = [c['name'] for c in bible.get('characters', [])]
                print(f"   Cast ({len(chars)} members): {', '.join(chars)}")
                ep_dirs = sorted([d for d in s.iterdir() if d.is_dir() and d.name.startswith("ep")])
                if ep_dirs:
                    print("   Generated Episodes on disk:")
                    for ep in ep_dirs:
                        video = ep / f"{s.name}_{ep.name}.mp4"
                        status = "✅ Rendered MP4" if video.exists() else "📝 Script only"
                        print(f"     - {ep.name}: {status}")
            
            sub = input("\nEnter series number to view full episode outline list, or press Enter to return: ").strip()
            if sub.isdigit() and 1 <= int(sub) <= len(all_series):
                s = all_series[int(sub) - 1]
                bible = json.loads((s / "bible.json").read_text(encoding="utf-8"))
                print(f"\n=== Episode Outlines for {bible.get('title')} ({len(bible.get('episode_outline', []))} Episodes) ===")
                for ep in bible.get("episode_outline", []):
                    print(f"\n[Episode {ep['number']}] {ep['title']}")
                    print(f"  {ep['summary']}")
                input("\nPress Enter to return...")
            continue

        elif choice == "4":
            videos = list(ROOT.glob("*/*/*.mp4"))
            if not videos:
                print("\n[!] No rendered MP4 videos found yet.")
                input("\nPress Enter to return...")
                continue
            print("\nRendered Videos:")
            for idx, v in enumerate(videos, 1):
                size_mb = v.stat().st_size / (1024 * 1024)
                print(f"  {idx}. {v.parent.parent.name}/{v.name} ({size_mb:.1f} MB)")
            v_choice = input(f"Choose video to play (1-{len(videos)}): ").strip()
            if v_choice.isdigit() and 1 <= int(v_choice) <= len(videos):
                selected_v = videos[int(v_choice) - 1]
                print(f"Opening {selected_v.name}...")
                os.startfile(str(selected_v.resolve()))
            input("\nPress Enter to return...")

        elif choice == "5":
            print("\nExiting AI Movie Series Agent. Goodbye!\n")
            break
        else:
            print("Invalid choice, please select 1-5.")


if __name__ == "__main__":
    main()

