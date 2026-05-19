---
name: imagegen
description: "Generate or edit images via CLI using any OpenAI-compatible API. Use when the user wants to create new images, edit existing ones, make transparent backgrounds, generate batch assets, produce mockups, illustrations, concept art, product photos, or UI wireframes. This skill supports custom API base URLs and models — use it whenever image generation is needed. Do NOT use for SVG/vector editing, simple diagrams better done as code, or tasks where the user clearly wants deterministic code-native output instead of a bitmap."
---

# Image Generation Skill

Generate or edit images via any OpenAI-compatible API. Pre-configured with custom API endpoint and model.

## Streamlit App

This project also includes a local Streamlit app for direct user operation, so image generation does not need to be driven by an agent.

Run from the skill root:

```bash
C:\Users\HP\anaconda3\envs\imagegen\python.exe -m streamlit run scripts\streamlit_app.py
```

The app supports:
- Custom Base URL, API Key, and model
- Preset aspect ratios plus custom width/height
- Quality, output format, background, moderation, and image count
- Structured prompt fields and prompt augmentation preview
- Generate and edit modes
- In-browser preview and download

Install dependencies if needed:

```bash
C:\Users\HP\anaconda3\envs\imagegen\python.exe -m pip install -r requirements.txt
```

## ⚡ Skill installation path (critical for AI Agent)

This skill is installed at:

```
C:\Users\HP\AppData\Roaming\tokeny\skills\imagegen
```

**All relative paths in this file (scripts/, references/, assets/) are relative to this root.**

When running commands via bash, the working directory is **the workspace root** (NOT the skill root), so you MUST use absolute paths or copy_skill_resources first.

---

## 🧠 AI Agent usage guide

### How to reference skill files

| What | Path |
|---|---|
| Skill root | C:\Users\HP\AppData\Roaming\tokeny\skills\imagegen |
| Python env | /c/Users/HP/anaconda3/envs/imagegen/python |
| Main script | C:\Users\HP\AppData\Roaming\tokeny\skills\imagegen\scripts\image_gen.py |
| Config | C:\Users\HP\AppData\Roaming\tokeny\skills\imagegen\scripts\config.json |
| Chroma-key removal | C:\Users\HP\AppData\Roaming\tokeny\skills\imagegen\scripts\remove_chroma_key.py |
| Reference docs | C:\Users\HP\AppData\Roaming\tokeny\skills\imagegen\references/*.md |

### Two ways to run scripts

**Option A — Use absolute paths (recommended for bash commands):**

```bash
PYTHON=/c/Users/HP/anaconda3/envs/imagegen/python
SCRIPT=/c/Users/HP/AppData/Roaming/tokeny/skills/imagegen/scripts/image_gen.py

$PYTHON "$SCRIPT" generate --prompt "your prompt" --out output/image.png
```

**Option B — Use copy_skill_resources to bring scripts into workspace (for read/modify):**

Agent tool: `copy_skill_resources` with `skillPath="imagegen"` copies scripts/references/assets to workspace.

### Accessing reference files

Read reference files from the absolute path:
```bash
cat /c/Users/HP/AppData/Roaming/tokeny/skills/imagegen/references/prompting.md
```
Or use `read_file` with the absolute path.

---

## Python Environment

This skill requires a dedicated Conda environment at:
```
C:\Users\HP\anaconda3\envs\imagegen
```

**Always use the full Python path:**
```bash
PYTHON=/c/Users/HP/anaconda3/envs/imagegen/python
SCRIPT=/c/Users/HP/AppData/Roaming/tokeny/skills/imagegen/scripts/image_gen.py

$PYTHON "$SCRIPT" generate --prompt "..." --out output/image.png
```

> ⚠️ Do NOT rely on bare `python`
> ⚠️ Do NOT use relative `scripts/image_gen.py` (only works from skill root)
> ⚠️ Always use `background=true` for generate/edit (API can take >60s)

## Quick Start

```bash
PYTHON=/c/Users/HP/anaconda3/envs/imagegen/python
SCRIPT=/c/Users/HP/AppData/Roaming/tokeny/skills/imagegen/scripts/image_gen.py

# Generate (use background=true)
$PYTHON "$SCRIPT" generate --prompt "your prompt" --out output/image.png

# Edit an image
$PYTHON "$SCRIPT" edit --image input.png --prompt "change background" --out output/edited.png
```

No need to pass --base-url, --api-key, or --model — pre-configured in config.json.

## Configuration

Pre-configured via scripts/config.json:
- **Base URL:** https://aigc.x-see.cn/v1
- **Model:** gpt-image-2-reverse
- **API Key:** set via OPENAI_API_KEY env var
- **Size:** 1024x1024
- **Quality:** medium

Always use these defaults unless the user explicitly requests otherwise.

## Structured prompt via CLI flags

Script supports structured fields as CLI flags for better results:
```bash
PYTHON=/c/Users/HP/anaconda3/envs/imagegen/python
SCRIPT=/c/Users/HP/AppData/Roaming/tokeny/skills/imagegen/scripts/image_gen.py

$PYTHON "$SCRIPT" generate \
  --prompt "Abaqus UEL subroutine mechanism" \
  --use-case infographic-diagram \
  --style "clean technical infographic, flat vector" \
  --composition "vertical flowchart, top-to-bottom" \
  --out output/diagram.png
```

Available flags: --use-case, --scene, --subject, --style, --composition, --lighting, --palette, --materials, --text, --constraints, --negative. Use --no-augment to disable augmentation.

## Transparent image workflow

### Chroma-key + local removal (default)
```bash
PYTHON=/c/Users/HP/anaconda3/envs/imagegen/python
SCRIPT=/c/Users/HP/AppData/Roaming/tokeny/skills/imagegen/scripts/image_gen.py
REMOVE=/c/Users/HP/AppData/Roaming/tokeny/skills/imagegen/scripts/remove_chroma_key.py

$PYTHON "$SCRIPT" generate \
  --prompt "Subject on flat solid #00ff00 chroma-key background" \
  --out tmp/subject.png

$PYTHON "$REMOVE" --input tmp/subject.png --out output/final.png \
  --auto-key border --soft-matte --despill
```

Key color: default #00ff00 (green), use #ff00ff for green subjects.

## Prompt structure
```
Use case: <taxonomy slug>
Primary request: <main prompt>
Style/medium: <photo/illustration/3D/etc>
Composition/framing: <wide/close/top-down>
Lighting/mood: <lighting + mood>
Constraints: <must keep / must avoid>
```

## Use-case taxonomy

### Generate

| Slug | Description |
| ---- | ----------- |
| photorealistic-natural | Candid/editorial scenes with real texture |
| product-mockup | Product/packaging shots, catalog imagery |
| ui-mockup | App/web interface mockups and wireframes |
| infographic-diagram | Diagrams/infographics with structured layout |
| scientific-educational | Classroom explainers and learning visuals |
| ads-marketing | Campaign concepts and ad creatives |
| productivity-visual | Slides, charts, data-heavy business visuals |
| logo-brand | Logo/mark exploration, vector-friendly |
| illustration-story | Comics, children's book art, narrative scenes |
| stylized-concept | Style-driven concept art, 3D renders |
| historical-scene | Period-accurate/world-knowledge scenes |

### Edit

| Slug | Description |
| ---- | ----------- |
| text-localization | Translate/replace in-image text, preserve layout |
| identity-preserve | Try-on, person-in-scene; lock face/body/pose |
| precise-object-edit | Remove/replace a specific element |
| lighting-weather | Time-of-day/season/atmosphere changes only |
| background-extraction | Transparent background / clean cutout |
| style-transfer | Apply reference style while changing subject |
| compositing | Multi-image insert/merge with matched lighting |
| sketch-to-render | Drawing/line art to photoreal render |

## Prompt augmentation rules

- If the user prompt is already detailed: normalize without adding creative requirements.
- If the user prompt is generic: add tasteful augmentation only when it improves quality.
- **Allowed:** composition hints, polish level, layout guidance, scene concreteness.
- **Not allowed:** extra characters/objects, brand names, arbitrary placement.

## Prompting best practices

- Structure: scene/backdrop -> subject -> details -> constraints
- Include intended use to set polish level
- Quote exact text and require verbatim rendering
- For edits, repeat invariants every iteration

## Dependencies

Requires openai and pillow in dedicated Conda environment:
```bash
conda create -n imagegen python=3.11 -y
conda activate imagegen
pip install openai pillow
```
Verify: `C:\Users\HP\anaconda3\envs\imagegen\python.exe -c "import openai; from PIL import Image; print('OK')"`

## Reference files

- references/prompting.md — Prompting principles and tactics
- references/sample-prompts.md — Copy/paste prompt recipes
- references/cli.md — Full CLI reference
- references/image-api.md — API parameter reference
- scripts/remove_chroma_key.py — Chroma-key background removal

Read them via absolute path: `cat /c/Users/HP/AppData/Roaming/tokeny/skills/imagegen/references/prompting.md`

## Lessons Learned

### Python environment path mismatch
**Symptom:** openai SDK not installed error despite being installed.
**Fix:** Always use full Conda path: `/c/Users/HP/anaconda3/envs/imagegen/python`
Do NOT use bare python or base Anaconda python.

### Relative script path fails from workspace
**Symptom:** `$PYTHON scripts/image_gen.py` fails because workspace cwd != skill root.
**Fix:** Use absolute script path:
```bash
SCRIPT=/c/Users/HP/AppData/Roaming/tokeny/skills/imagegen/scripts/image_gen.py
$PYTHON "$SCRIPT" generate --prompt "..." --out output/image.png
```

### Long API call timeouts
**Symptom:** bash command times out before API returns (60-120s).
**Fix:** Always use background=true for generate/edit. Check output file asynchronously.

### Model-specific constraints
- gpt-image-2 / gpt-image-2-reverse: NO --background transparent (use chroma-key). NO --input-fidelity.
- gpt-image-1.5: legacy sizes only, supports --background transparent.
**Check:** Effective model in scripts/config.json, not code default.

### Agent looked in wrong skill directory
**Symptom:** Agent searched .claude/skills/, .cc-switch/skills/ instead of actual path.
**Fix:** The canonical path is always C:\Users\HP\AppData\Roaming\tokeny\skills\imagegen.
