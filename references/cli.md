# CLI reference (`scripts/image_gen.py`)

## What this CLI does

- `generate` — create a new image from a prompt
- `edit` — edit one or more existing images
- `generate-batch` — run many generation jobs from a JSONL file

Real API calls require **network access** + an API key. `--dry-run` does not.

## Python Environment

This skill requires the dedicated `imagegen` Conda environment:

```bash
C:\Users\HP\anaconda3\envs\imagegen\python.exe scripts/image_gen.py ...
```

Set a shorthand for Git Bash:

```bash
PYTHON=/c/Users/HP/anaconda3/envs/imagegen/python
```

> ⚠️ Do NOT use bare `python` — it may resolve to a different environment without the required packages.

## Dependencies

```bash
conda activate imagegen  # or: C:\Users\HP\anaconda3\envs\imagegen\python.exe -m pip
pip install openai pillow
```

## Quick start

Dry-run (no API call):

```bash
$PYTHON scripts/image_gen.py generate \
  --prompt "A cozy alpine cabin at dawn" \
  --out output/imagegen/test.png \
  --dry-run
```

Generate:

```bash
$PYTHON scripts/image_gen.py generate \
  --prompt "A cozy alpine cabin at dawn" \
  --size 1024x1024 \
  --out output/imagegen/alpine-cabin.png
```

Edit:

```bash
$PYTHON scripts/image_gen.py edit \
  --image input.png \
  --prompt "Replace only the background with a warm sunset" \
  --out output/imagegen/sunset-edit.png
```

## API connection options

| Argument | Env var | Description |
|---|---|---|
| `--base-url` | `OPENAI_BASE_URL` | Custom API base URL (default: OpenAI) |
| `--api-key` | `OPENAI_API_KEY` | API key for authentication |
| `--model` | `IMAGE_GEN_MODEL` | Model name (default: `gpt-image-2`) |

```bash
$PYTHON scripts/image_gen.py generate \
  --base-url "https://your-api-endpoint.com/v1" \
  --api-key "sk-..." \
  --model "your-model" \
  --prompt "A cat wearing a hat" \
  --size "1024x1024" \
  --out output/cat.png
```

## Defaults

- Model: `gpt-image-2`
- Size: `auto`
- Quality: `medium`
- Output format: `png`
- Default output path: `output/imagegen/output.png`

## gpt-image-2 size constraints

- Max edge `<= 3840px`
- Both edges multiples of `16px`
- Long/short edge ratio `<= 3:1`
- Total pixels between `655,360` and `8,294,400`

Popular sizes: `1024x1024`, `1536x1024`, `1024x1536`, `2048x2048`, `2048x1152`, `3840x2160`, `2160x3840`, `auto`

## Quality levels

- `low` — fast drafts, thumbnails
- `medium` — default, balanced quality/speed
- `high` — final assets, dense text, diagrams
- `auto` — let the model decide

## Transparent images

Two approaches:

1. **Chroma-key + local removal** (universal): generate on flat `#00ff00` background, then run `scripts/remove_chroma_key.py`
2. **Native transparency** (API-dependent): use `--background transparent --output-format png` if your endpoint supports it

## Batch generation

```bash
cat > tmp/imagegen/prompts.jsonl << 'EOF'
{"prompt":"Cavernous hangar interior with a compact shuttle","use_case":"stylized-concept","size":"1536x1024"}
{"prompt":"Gray wolf in profile in a snowy forest","use_case":"photorealistic-natural","size":"1024x1024"}
EOF

$PYTHON scripts/image_gen.py generate-batch \
  --input tmp/imagegen/prompts.jsonl \
  --out-dir output/imagegen/batch \
  --concurrency 5
```

### Batch JSONL format

Each line can be:
- A plain string (just the prompt)
- A JSON object with `prompt` plus optional overrides: `model`, `size`, `quality`, `background`, `output_format`, `n`, `out`, `use_case`, `scene`, `subject`, `style`, `composition`, `lighting`, `palette`, `constraints`, `negative`

## Prompt augmentation

Structured fields supported as CLI flags: `--use-case`, `--scene`, `--subject`, `--style`, `--composition`, `--lighting`, `--palette`, `--materials`, `--text`, `--constraints`, `--negative`

Use `--no-augment` to disable structured augmentation.

## Output handling

- `tmp/imagegen/` for intermediate files (JSONL, scratch)
- `output/imagegen/` for final outputs
- `--out` for single output path
- `--out-dir` for numbered outputs (`image_1.png`, `image_2.png`, ...)
- `--force` to overwrite existing files
- `--downscale-max-dim N` to also generate a downscaled copy (e.g., for web)
- `--downscale-suffix` to customize the downscaled file suffix (default: `-web`)

## All flags

| Flag | Description |
|---|---|
| `--model` | Model name (default: `gpt-image-2`) |
| `--base-url` | Custom API base URL |
| `--api-key` | API key |
| `--prompt` | Text prompt |
| `--prompt-file` | Read prompt from file |
| `--n` | Number of images (1-10) |
| `--size` | Image size (`auto` or `WIDTHxHEIGHT`) |
| `--quality` | `low`, `medium`, `high`, `auto` |
| `--background` | `transparent`, `opaque`, `auto` |
| `--output-format` | `png`, `jpeg`, `webp` |
| `--output-compression` | 0-100 (jpeg/webp only) |
| `--moderation` | `auto` or `low` |
| `--out` | Output path |
| `--out-dir` | Output directory |
| `--force` | Overwrite existing files |
| `--dry-run` | Print request without calling API |
| `--augment` / `--no-augment` | Enable/disable prompt augmentation |
| `--downscale-max-dim` | Generate downscaled copy (max dimension) |
| `--downscale-suffix` | Suffix for downscaled copy |

Edit-specific:

| Flag | Description |
|---|---|
| `--image` | Input image(s) (repeat for multiple) |
| `--mask` | Optional mask PNG |
| `--input-fidelity` | `low` or `high` |

Batch-specific:

| Flag | Description |
|---|---|
| `--input` | Path to JSONL input file |
| `--concurrency` | Max concurrent jobs (1-25, default 5) |
| `--max-attempts` | Retry limit (1-10, default 3) |
| `--fail-fast` | Stop on first failure |
