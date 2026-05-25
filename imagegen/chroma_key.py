from __future__ import annotations

import argparse
import io
import statistics
from pathlib import Path
from typing import Iterable, List, Literal, Optional, Sequence, Tuple

from PIL import Image, ImageFilter


RGB = Tuple[int, int, int]
AutoKeyMode = Literal["border", "corners"]

DEFAULT_GREEN: RGB = (0, 255, 0)
ALT_MAGENTA: RGB = (255, 0, 255)

GREEN_TERMS = (
    "green",
    "lime",
    "emerald",
    "jade",
    "grass",
    "leaf",
    "foliage",
    "\u7eff",
    "\u7fe1\u7fe0",
    "\u8349",
    "\u6811\u53f6",
    "\u53f6\u5b50",
)


def parse_hex_color(value: str) -> RGB:
    raw = value.strip().lstrip("#")
    if len(raw) != 6:
        raise ValueError("key color must be a 6-digit hex color, for example #00ff00")
    try:
        return tuple(int(raw[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError("key color must be a valid hex color") from exc


def hex_color(color: RGB) -> str:
    return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"


def choose_chroma_key(prompt: str, default: RGB = DEFAULT_GREEN, alternate: RGB = ALT_MAGENTA) -> RGB:
    lower_prompt = prompt.lower()
    return alternate if any(term in lower_prompt for term in GREEN_TERMS) else default


def append_chroma_key_instruction(prompt: str, key_color: RGB) -> str:
    color = hex_color(key_color)
    return (
        f"{prompt}\n\n"
        "Transparent background workflow instruction: place the complete subject on a perfectly flat, "
        f"solid chroma-key background of exactly {color}. Keep the background uniform edge-to-edge with "
        "no shadows, gradients, texture, reflections, floor line, props, or lighting falloff. Keep the "
        "subject fully separated from the chroma-key color and do not use the chroma-key color in the "
        "subject unless explicitly required."
    )


def _smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def _chebyshev_distance(pixel: RGB, key_color: RGB) -> int:
    return max(abs(pixel[index] - key_color[index]) for index in range(3))


def _dominant_key_channels(key_color: RGB) -> Tuple[List[int], List[int]]:
    peak = max(key_color)
    key_channels = [index for index, value in enumerate(key_color) if value == peak]
    non_key_channels = [index for index in range(3) if index not in key_channels]
    return key_channels, non_key_channels


def _primary_chroma_alpha(pixel: RGB, key_color: RGB, tolerance: int, soft_width: int) -> int:
    key_channels, non_key_channels = _dominant_key_channels(key_color)
    if not key_channels or not non_key_channels:
        return 255
    key_strength = min(pixel[index] for index in key_channels)
    non_key_strength = max(pixel[index] for index in non_key_channels)
    dominance = key_strength - non_key_strength
    if dominance <= 0:
        return 255
    span = max(1, tolerance + soft_width)
    return int(round(255 * (1.0 - _smoothstep(dominance / span))))


def _sample_points(image: Image.Image, mode: AutoKeyMode, sample_size: int) -> List[RGB]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    samples: List[RGB] = []

    if mode == "corners":
        patch = max(1, sample_size)
        ranges = (
            (range(0, min(patch, width)), range(0, min(patch, height))),
            (range(max(0, width - patch), width), range(0, min(patch, height))),
            (range(0, min(patch, width)), range(max(0, height - patch), height)),
            (range(max(0, width - patch), width), range(max(0, height - patch), height)),
        )
        for xs, ys in ranges:
            for y in ys:
                for x in xs:
                    samples.append(pixels[x, y])
        return samples

    stride = max(1, max(width, height) // max(1, sample_size * 8))
    for x in range(0, width, stride):
        samples.append(pixels[x, 0])
        samples.append(pixels[x, height - 1])
    for y in range(0, height, stride):
        samples.append(pixels[0, y])
        samples.append(pixels[width - 1, y])
    return samples


def auto_detect_key_color(image: Image.Image, mode: AutoKeyMode = "border", sample_size: int = 12) -> RGB:
    samples = _sample_points(image, mode, sample_size)
    if not samples:
        return DEFAULT_GREEN
    channels = zip(*samples)
    return tuple(int(round(statistics.median(channel))) for channel in channels)  # type: ignore[return-value]


def remove_chroma_key_image(
    image: Image.Image,
    *,
    key_color: RGB = DEFAULT_GREEN,
    tolerance: int = 36,
    soft_matte: bool = False,
    soft_width: int = 48,
    primary_chroma_alpha: bool = True,
    despill: bool = False,
    despill_amount: float = 0.85,
    alpha_shrink: int = 0,
    feather: float = 0.0,
    auto_key: Optional[AutoKeyMode] = None,
) -> Image.Image:
    if auto_key is not None:
        key_color = auto_detect_key_color(image, auto_key)

    rgba = image.convert("RGBA")
    output_pixels = []
    opaque_distance = tolerance + max(1, soft_width)
    key_channels, non_key_channels = _dominant_key_channels(key_color)

    for red, green, blue, original_alpha in rgba.getdata():
        rgb = (red, green, blue)
        distance = _chebyshev_distance(rgb, key_color)
        if soft_matte:
            if distance <= tolerance:
                alpha = 0
            elif distance >= opaque_distance:
                alpha = 255
            else:
                alpha = int(round(255 * _smoothstep((distance - tolerance) / max(1, soft_width))))
        else:
            alpha = 0 if distance <= tolerance else 255

        if primary_chroma_alpha and distance <= opaque_distance:
            alpha = min(alpha, _primary_chroma_alpha(rgb, key_color, tolerance, soft_width))

        alpha = min(alpha, original_alpha)
        if despill and alpha < 255 and key_channels and non_key_channels:
            channels = [red, green, blue]
            non_key_level = max(channels[index] for index in non_key_channels)
            strength = despill_amount * (1.0 - alpha / 255.0)
            for channel_index in key_channels:
                cleaned = min(channels[channel_index], non_key_level)
                channels[channel_index] = int(round(channels[channel_index] * (1.0 - strength) + cleaned * strength))
            red, green, blue = channels

        output_pixels.append((red, green, blue, alpha))

    result = Image.new("RGBA", rgba.size)
    result.putdata(output_pixels)

    if alpha_shrink > 0 or feather > 0:
        red, green, blue, alpha = result.split()
        if alpha_shrink > 0:
            alpha = alpha.filter(ImageFilter.MinFilter(alpha_shrink * 2 + 1))
        if feather > 0:
            alpha = alpha.filter(ImageFilter.GaussianBlur(radius=feather))
        result.putalpha(alpha)

    return result


def remove_chroma_key_bytes(
    image_bytes: bytes,
    *,
    key_color: RGB = DEFAULT_GREEN,
    output_format: str = "png",
    **kwargs: object,
) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as image:
        result = remove_chroma_key_image(image, key_color=key_color, **kwargs)

    buffer = io.BytesIO()
    fmt = "PNG" if output_format == "png" else "WEBP"
    result.save(buffer, format=fmt)
    return buffer.getvalue()


def remove_chroma_key_file(
    input_path: Path,
    output_path: Path,
    *,
    key_color: RGB = DEFAULT_GREEN,
    output_format: Optional[str] = None,
    **kwargs: object,
) -> None:
    image_bytes = input_path.read_bytes()
    inferred_format = output_format or output_path.suffix.lower().lstrip(".") or "png"
    result = remove_chroma_key_bytes(image_bytes, key_color=key_color, output_format=inferred_format, **kwargs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(result)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Remove a solid chroma-key background and convert it to alpha.")
    parser.add_argument("input", type=Path, help="Input image path")
    parser.add_argument("output", type=Path, help="Output PNG/WebP path")
    parser.add_argument("--key", default="#00ff00", help="Hex key color, for example #00ff00")
    parser.add_argument("--auto-key", choices=["border", "corners"], help="Sample the key color from image edges")
    parser.add_argument("--tolerance", type=int, default=36, help="Chebyshev distance for fully transparent pixels")
    parser.add_argument("--soft-matte", action="store_true", help="Use a smooth alpha transition outside tolerance")
    parser.add_argument("--soft-width", type=int, default=48, help="Soft matte transition width")
    parser.add_argument("--no-primary-chroma-alpha", action="store_true", help="Disable dominant key-channel alpha")
    parser.add_argument("--despill", action="store_true", help="Reduce key-color spill on semi-transparent edges")
    parser.add_argument("--despill-amount", type=float, default=0.85, help="Despill strength from 0 to 1")
    parser.add_argument("--alpha-shrink", type=int, default=0, help="Shrink alpha mask by N pixels before feathering")
    parser.add_argument("--feather", type=float, default=0.0, help="Gaussian blur radius for alpha feathering")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    remove_chroma_key_file(
        args.input,
        args.output,
        key_color=parse_hex_color(args.key),
        tolerance=args.tolerance,
        soft_matte=args.soft_matte,
        soft_width=args.soft_width,
        primary_chroma_alpha=not args.no_primary_chroma_alpha,
        despill=args.despill,
        despill_amount=args.despill_amount,
        alpha_shrink=args.alpha_shrink,
        feather=args.feather,
        auto_key=args.auto_key,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
