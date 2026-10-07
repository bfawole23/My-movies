"""Writes the series bible and each episode script using Claude."""
import json
import os
import re

import anthropic

MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest")


def _ask(system: str, prompt: str, max_tokens: int = 4000) -> dict:
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    match = re.search(r"\{.*\}", text, re.S)
    return json.loads(match.group(0))


def make_bible(idea: str, episodes: int, style_key: str = "realistic") -> dict:
    from styles import STYLES

    style = STYLES.get(style_key, STYLES["realistic"])
    system = "You are a showrunner for short vertical-video AI series. Reply with JSON only."
    prompt = f"""Idea: {idea}
Visual world: {style['prompt']}
Create a series bible for {episodes} episodes of 4 minutes each.
All characters, places and costumes must be original (no existing show or film characters).
Assign each character an appropriate voice from this list:
- en-GB-RyanNeural (mature/commanding male, British)
- en-US-BrianNeural (gritty, heroic captain/knight male, American)
- en-US-ChristopherNeural (dark/sinister supernatural male)
- en-US-RogerNeural (wise, calculating older counselor male)
- en-GB-SoniaNeural (regal, sharp queen/noblewoman female)
- en-GB-MaisieNeural (witty, sharp scholar/consort female)
- en-GB-ThomasNeural (curious, energetic young prince boy)
- en-US-AvaNeural (mystic/younger woman female)
- en-US-JennyNeural (versatile natural female)

JSON shape:
{"title": str, "logline": str,
"characters": [{"name": str, "look": str (fixed visual description: face, build, hair, costume, colors), "voice": str, "pitch": str (e.g. "+0Hz" or "-15Hz"), "rate": str (e.g. "+0%" or "-5%")}],
"episode_outline": [{"number": int, "title": str, "summary": str}]}"""
    bible = _ask(system, prompt)
    bible["style_key"] = style_key
    bible["visual_style"] = style["prompt"]
    return bible


def write_episode(bible: dict, number: int, previous: list[str]) -> dict:
    system = "You write cinematic, full-length character-driven dialogues for 4-minute video episodes blending comic wit, educational science, and dramatic mystery. Reply with JSON only."
    outline = next(e for e in bible["episode_outline"] if e["number"] == number)
    prompt = f"""Series: {bible['title']} - {bible['logline']}
Visual style: {bible['visual_style']}
Characters: {json.dumps(bible['characters'])}
Previously: {' | '.join(previous) or 'nothing, this is episode 1'}
Write episode {number}: {outline['title']} - {outline['summary']}

Rules for 4-Minute Episode:
- TARGET EPISODE DURATION: 4 MINUTES (approximately 230 to 250 seconds total).
- Write 15 to 18 substantial, dramatic scenes.
- THE CAST MUST DO ALL THE TALKING. Absolutely NO third-person narrator descriptions.
- COMIC & EDUCATIONAL TONE: Seamlessly blend witty humor and real educational science/logic into the mystery:
  * Lady Rosalind applies empirical science (optics, acoustics, chemistry, mechanics, botany) with dry wit and sharp intellectual charm.
  * Prince Leo asks curious questions, invents humorous contraptions, and provides charming comic relief.
  * King Maelor, Queen Iselde, Captain Doran, and Chancellor Pell react with royal exasperation, banter, and dramatic mystery.
  * The Shadow itself trades witty banter while remaining an enigmatic supernatural presence.
- In each scene, characters engage in lively, realistic, multi-turn dialogue.
- 'dialogue' must be a multi-turn conversation between the characters present (2-3 spoken lines):
  [
    {{"speaker": "Exact Character Name", "line": "Spoken line..."}},
    {{"speaker": "Exact Character Name", "line": "Response line..."}}
  ]
  If only one character is present, provide a 2-3 sentence speech/soliloquy in the same list format.
- Every visual_prompt must describe an ultra-realistic, natural, 8k high-resolution shot with a clear bright background and high-quality cinema camera cinematography.
- "characters" lists the visible character names (main one first).

JSON shape:
{{"title": str, "scenes": [{{"dialogue": [{{"speaker": str, "line": str}}], "visual_prompt": str, "characters": [str]}}],
"summary": str (2 sentences, for continuity),
"caption": str (social caption with 3-5 hashtags)}}"""
    return _ask(system, prompt, max_tokens=10000)
