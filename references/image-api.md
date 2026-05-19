# Image API quick reference

## Scope

This reference describes the CLI parameters for `scripts/image_gen.py`. Supports any OpenAI-compatible API endpoint.

## Model summary

| Model | Quality | Input fidelity | Resolutions | Notes |
|---|---|---|---|---|
| `gpt-image-2` | low/medium/high/auto | Always high (do not set) | Flexible: max edge ≤3840px, multiples of 16, ratio ≤3:1, pixels 655K-8.3M | Default for OpenAI, high-quality generation and editing |
| `gpt-image-1.5` | low/medium/high/auto | low/high | 1024x1024, 1536x1024, 1024x1536, auto | Supports `background=transparent` |
| `gpt-image-1` | low/medium/high/auto | low/high | 1024x1024, 1536x1024, 1024x1536, auto | Legacy compatibility |
| `gpt-image-1-mini` | low/medium/high/auto | low/high | 1024x1024, 1536x1024, 1024x1536, auto | Cost-sensitive drafts |
| *any model* | *as supported* | *as supported* | `auto` or `WIDTHxHEIGHT` | Custom endpoints accept any model name |

## API connection

| Parameter | CLI flag | Env var | Description |
|---|---|---|---|
| Base URL | `--base-url` | `OPENAI_BASE_URL` | API endpoint (default: OpenAI) |
| API key | `--api-key` | `OPENAI_API_KEY` | Authentication |
| Model | `--model` | `IMAGE_GEN_MODEL` | Model name (default: `gpt-image-2`) |

## Endpoints

- Generate: `POST /v1/images/generations` (`client.images.generate(...)`)
- Edit: `POST /v1/images/edits` (`client.images.edit(...)`)

## Core parameters

- `prompt`: text prompt
- `model`: model name
- `n`: number of images (1-10)
- `size`: `auto` or `WIDTHxHEIGHT`
- `quality`: `low`, `medium`, `high`, or `auto`
- `background`: output transparency behavior (`transparent`, `opaque`, `auto`)
- `output_format`: `png` (default), `jpeg`, `webp`
- `output_compression`: 0-100 (jpeg/webp only)
- `moderation`: `auto` (default) or `low`

## Edit-specific parameters

- `image`: one or more input images (repeat `--image` flag)
- `mask`: optional mask image (PNG with alpha channel)
- `input_fidelity`: `low` or `high` (not supported by `gpt-image-2`)

## Transparent backgrounds

- `gpt-image-2` does NOT support `background=transparent`. Use chroma-key workflow instead.
- Use `gpt-image-1.5` for true transparency: `--model gpt-image-1.5 --background transparent --output-format png`
- Custom endpoints: depends on your API's capabilities.

## gpt-image-2 popular sizes

| Label | Size | Notes |
|---|---|---|
| Square | 1024x1024 | Fast default |
| Landscape | 1536x1024 | Standard landscape |
| Portrait | 1024x1536 | Standard portrait |
| 2K square | 2048x2048 | Larger output |
| 2K landscape | 2048x1152 | Widescreen |
| 4K landscape | 3840x2160 | Widescreen 4K |
| 4K portrait | 2160x3840 | Vertical 4K |
| Auto | auto | Default |

## Limits

- Input images and masks: under 50MB
- Large sizes and high quality increase latency/cost
- `quality=low` for fast drafts; `medium`/`high` for final assets
