from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps


def load_rgb(path: Path) -> np.ndarray:
    if not path.is_file():
        raise ValueError(f"Image does not exist: {path}")
    with Image.open(path) as source:
        oriented = ImageOps.exif_transpose(source)
        # Transparent pixels have no unique visible color: composite on white.
        rgba = oriented.convert("RGBA")
        background = Image.new("RGBA", rgba.size, "white")
        rgb = np.asarray(Image.alpha_composite(background, rgba).convert("RGB"))
    if min(rgb.shape[:2]) < 4:
        raise ValueError("Image must be at least 4×4 pixels for 16 nonempty cells")
    return rgb


def grid_regions(rgb: np.ndarray):
    height, width = rgb.shape[:2]
    if min(height, width) < 4:
        raise ValueError("Image must be at least 4×4 pixels")
    for row in range(4):
        for column in range(4):
            # Integer boundaries partition every pixel, including odd dimensions.
            y0, y1 = row * height // 4, (row + 1) * height // 4
            x0, x1 = column * width // 4, (column + 1) * width // 4
            yield row, column, rgb[y0:y1, x0:x1]


def grid_overlay(rgb: np.ndarray, path: Path) -> None:
    image = Image.fromarray(rgb)
    # Keep labels legible even for tiny test images; this affects the overlay only.
    if min(image.size) < 256:
        scale = 256 / min(image.size)
        image = image.resize(tuple(round(s * scale) for s in image.size), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for i in range(1, 4):
        draw.line((i * width // 4, 0, i * width // 4, height), fill="white", width=2)
        draw.line((0, i * height // 4, width, i * height // 4), fill="white", width=2)
    for row in range(4):
        for col in range(4):
            x, y = col * width // 4 + 5, row * height // 4 + 5
            text = f"{row},{col}"
            bounds = draw.textbbox((x, y), text)
            draw.rectangle((bounds[0]-3, bounds[1]-3, bounds[2]+3, bounds[3]+3), fill="black")
            draw.text((x, y), text, fill="white")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)

