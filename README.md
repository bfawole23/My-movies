# AI Movie Series Agent

Turns an idea into a serialized short-form series. Claude writes the series bible and each episode script, an image model draws every scene, a text-to-speech voice narrates, and ffmpeg assembles a vertical 1080x1920 MP4 with a slow camera zoom and a film-style color grade. You get one video and one caption per episode, ready to upload to TikTok, Instagram Reels, YouTube Shorts or Facebook.

It makes **narrated image-sequence episodes** (stills with motion), not full video-generation clips.

## What's included

```
movie_agent/
  agent.py          command-line entry point (new, episode)
  story.py          Claude: series bible and episode scripts
  media.py          images, character references, voiceover, video assembly
  styles.py         visual style presets (prompt wording + color grade)
  requirements.txt  Python packages
  .env.example      copy to .env and add your keys
  series/
    kings_shadow/
      bible.json    ready-made series: The King's Second Shadow (6 episodes)
```

## Requirements

- Python 3.10 or newer
- ffmpeg and ffprobe on your PATH (`ffmpeg -version` should work)
  - Windows: `winget install ffmpeg`, Mac: `brew install ffmpeg`, Linux: `sudo apt install ffmpeg`
- An Anthropic API key (writes the scripts)
- A Replicate API token (draws the images). Optional for testing: without it you get plain text placeholder cards.
- Internet access (the voice uses Microsoft Edge text-to-speech, no key needed)

## Setup

1. Unzip the project and open a terminal inside the `movie_agent` folder. Always run commands from this folder, because `series/` is created relative to where you run them.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in:

| Variable | Needed | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | yes | Script writing |
| `REPLICATE_API_TOKEN` | for real images | Scene images and character portraits |
| `VOICE` | no | Narration voice, default `en-NG-AbeoNeural`. List voices with `edge-tts --list-voices` |
| `CLAUDE_MODEL` | no | Override the Claude model used for writing |

On some systems the command is `python3` instead of `python`.

## Quick start: The King's Second Shadow

The series is already set up. Make and post one episode at a time:

```
python agent.py episode kings_shadow 1
python agent.py episode kings_shadow 2
...
python agent.py episode kings_shadow 6
```

Episodes must be made in order, because each script is written with the summaries of the earlier ones for continuity.

## Starting a new series

```
python agent.py new "your idea in a sentence or two" --name myshow --episodes 6 --style arena
```

- `--name` is the folder name under `series/`
- `--episodes` is how many episodes to outline (default 5)
- `--style` is `arena` (default) or `legend`

This writes `series/myshow/bible.json` and prints the outline. Then run `python agent.py episode myshow 1`.

## Visual styles

| Style | Look |
|---|---|
| `arena` | Gritty, stylized historical epic: dust, hard contrast, crimson and gold, desaturated skin, heavy grain |
| `legend` | Medieval fantasy adventure: castles, misty forests, soft golden light, warmer colors |

Each style has image-prompt wording and an ffmpeg color grade (contrast, saturation, vignette, grain) in `styles.py`. Add your own by copying an entry there. To change the style of an existing series, edit `style_key` and `visual_style` in its `bible.json` and delete the cached files in each episode's `work/` folder.

Prompts use generic style descriptions, not the names of existing shows. All characters and places should be original.

## The series bible (`bible.json`)

You can edit this by hand before making episodes.

- `title`, `logline`: used in captions and for script writing
- `characters`: each has a `name` and a fixed `look`. The look is repeated in prompts and used for the reference portrait, so be specific (age, build, hair, face, clothing, colors)
- `episode_outline`: `number`, `title`, `summary` for each episode. Episode scripts follow these.
- `style_key`, `visual_style`: the look of the series

## What an episode produces

Everything lands in `series/<name>/epNN/`:

- `<name>_epNN.mp4`: the finished video. Upload this.
- `caption.txt`: title line plus a caption with hashtags
- `script.json`: narration, image prompts, characters per scene, summary, caption
- `work/`: per-scene files (`01.png`, `01.mp3`, `01.mp4`, ...)

## Consistent characters

The first time you make an episode, every character in the bible gets a reference portrait in `series/<name>/characters/`. Scenes that feature a character are generated from that portrait using an image-editing model, which keeps the same face and costume across scenes and episodes.

- Not happy with a face? Replace the PNG with any image you like, or delete it to regenerate.
- A scene with several characters follows the first-listed one. The others can still drift.
- This uses a pricier image model than plain text-to-image. Check Replicate's current pricing and run one episode before planning a whole series.

## Fixing and redoing scenes

Each step is cached, so reruns skip finished work. A scene is only rebuilt if its files are missing. **The video clip is built from the image and audio, so delete the clip too.**

| You want to change | Delete these in `epNN/work/` (scene 03 as example) |
|---|---|
| The picture | `03.png` and `03.mp4` |
| The narration or voice | `03.mp3` and `03.mp4` |
| Both | `03.png`, `03.mp3`, `03.mp4` |

Then run the same `episode` command again. To change what a scene says or shows, edit `narration` or `visual_prompt` in `script.json` first.

To rewrite the whole script: `python agent.py episode myshow 3 --rewrite`. This does not delete old scene files, so clear `work/` if the scenes changed.

## Posting workflow

1. Make the episode and watch it fully. Check faces, odd hands and any text artifacts.
2. Fix any weak scenes (see above).
3. Upload the MP4, paste the caption, and post. Release episodes on a regular schedule so viewers return.
4. Check each platform's rules for labeling AI-generated content and turn that label on where required.

## Troubleshooting

- **`ffmpeg` or `ffprobe` not found**: install ffmpeg and restart the terminal.
- **`ModuleNotFoundError`**: run `pip install -r requirements.txt`.
- **Authentication or 401 errors**: check the keys in `.env`; there should be no quotes or spaces around them.
- **JSON parse error while writing a script or bible**: rare, caused by a malformed reply. Run the command again.
- **Image generation failed**: usually a Replicate billing or rate-limit issue. Rerun; finished scenes are kept.
- **Scenes look like text cards**: no `REPLICATE_API_TOKEN` is set, so placeholders were used. Add the token, then delete the PNGs and clips in `work/`.
- **No such file `bible.json`**: you are in the wrong folder, or the series name is misspelled.
- **Voice errors**: edge-tts needs internet. Check the `VOICE` name with `edge-tts --list-voices`.

## Limits

- Stills with a slow zoom, not animated video.
- One narrator voice, no separate character voices and no music or sound effects. Add those in an editor such as CapCut if you want them.
- No burned-in subtitles yet.
- Faces can drift between scenes, especially with several characters in one image.
- Quality depends on the image model; some scenes will need a redo.
