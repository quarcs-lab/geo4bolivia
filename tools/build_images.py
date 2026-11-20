"""Generate and prepare the documentation's images.

    uv run python tools/build_images.py --generate     # draw the missing pictures with the Codex CLI
    uv run python tools/build_images.py [<folder>]     # process the pictures (default: docs/images/originals)
    uv run python tools/build_images.py --prompts      # print the prompts
    uv run python tools/build_images.py --placeholders # stand-ins for missing pictures

The pictures are AI-generated with OpenAI's image model from the prompts in PROMPTS,
through the maintainer's ChatGPT subscription: either with the Codex CLI
(``--generate`` runs ``codex exec`` once per picture and collects the result from
``~/.codex/generated_images``) or by hand in ChatGPT. They are kept as
``docs/images/originals/g4b-<id>.png`` (not committed). This script crops and resizes
them into ``docs/images/``:

- ``icon``  -> ``icon.png`` (512 px), ``favicon.png`` (64 px), ``logo-navbar.png`` (72 px)
- ``hero``  -> ``hero.webp`` (1600 x 800), the home page and README banner
- articles  -> ``thumbs/<id>.webp`` (1200 x 675), one per article

Rules for the pictures: Bolivian places and themes only; no maps, country outlines,
borders, globes or other countries; no text, logos or flags. Any map in the
documentation is drawn by the package from the official boundaries.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs" / "images"
PREFIX = "g4b-"

RULES = (
    "Cinematic, editorial and minimal. Palette: deep teal-black (#071417, #0b1e22), glowing turquoise "
    "(#5ad6c6), flamingo pink and rose (#ff8597, #d1405a), soft salt-white and a little warm sand (#e7c27d). "
    "Strict rules: only Bolivian landscape and culture; NO maps, NO country outlines, NO borders or boundary "
    "lines, NO globe, NO other countries or continents; no people's faces; no text, letters, numbers, labels, "
    "logos, flags or watermarks."
)
ICON_RULES = (
    "A flat, minimal vector-style app icon, perfectly centred on a deep teal-black (#0b1e22) rounded square, "
    "bold simple shapes that stay legible at 32 pixels, generous margins, no gradients on the background, "
    "no text, letters, numbers, maps, country outlines, flags or watermarks."
)
PROMPTS = {
    "icon": "1:1. " + ICON_RULES + " The emblem: one hexagonal tile of the Salar de Uyuni's salt crust, drawn as "
    "seven nested hexagon cells (one in the middle, six around it) in turquoise (#5ad6c6) outlines, the middle cell "
    "filled flamingo rose (#d1405a), two of the outer cells filled soft salt-white; a single thin turquoise orbit "
    "arc with a small dot (a satellite) curving around the upper right of the hexagon.",
    "hero": "2:1 wide banner. " + RULES + " Bolivia's landscapes in one sweep at blue hour, from a high oblique "
    "aerial angle: in the foreground the Salar de Uyuni, its hexagonal salt polygons glowing softly in a gradient "
    "from rose to turquoise like the cells of a data mosaic; in the middle distance the lights of Altiplano towns "
    "joined by thin luminous threads; on the horizon the snow peaks of the Cordillera Real and, beyond them, the "
    "dark green lowlands under a starry sky crossed by one thin satellite trail. Leave the composition calm and "
    "uncluttered.",
    "data-model": "16:9. " + RULES + " The Inca agricultural terraces of Isla del Sol on Lake Titicaca at dusk, "
    "seen from above: the terraces nest inside one another in clear levels, each level edged with a faint "
    "turquoise glow, the smallest plots inside larger ones, the lake dark and still beyond.",
    "exploring": "16:9. " + RULES + " A close view of traditional Bolivian aguayo textiles from Tarabuco laid side "
    "by side on dark stone: their woven stripes in rose, turquoise, sand and salt-white have different heights, "
    "like the bars of a chart, lit by warm low light.",
    "spatial-dependence": "16:9. " + RULES + " The Altiplano at night from a high oblique angle: the lights of "
    "towns and villages gather in clusters, one group of neighbours glowing warm rose and another glowing "
    "turquoise, with a few lone lights of the other colour among them; neighbouring lights are joined by very "
    "thin luminous threads; Sajama volcano in silhouette.",
    "convergence": "16:9. " + RULES + " The Bolivian Amazon lowlands near Rurrenabaque at dawn, aerial view: "
    "several meandering rivers, some rose-tinted and some turquoise, flow from the Andean foothills and come "
    "together into one wide calm river that runs to the horizon through dark forest.",
    "transitions": "16:9. " + RULES + " La Paz at dusk seen from El Alto: the cabins of the Mi Teleférico cable "
    "cars glide along their lines between stations at different heights of the city, a few cabins lit rose and "
    "the others turquoise, the bowl of city lights below and Illimani behind.",
    "inequality": "16:9. " + RULES + " The bowl of La Paz at night from the rim of El Alto: the city lights are "
    "uneven, a small dense core of bright rose and white lights at the bottom and wide slopes of sparse, dim "
    "turquoise lights climbing the hillsides, under a dark teal sky with Illimani faint in the distance.",
    "models": "16:9. " + RULES + " The night sky over the Cordillera Real seen from the Chacaltaya observatory: "
    "a scatter of bright stars above the snow peaks, and one straight, thin, luminous turquoise line drawn "
    "through the middle of the stars like a fitted trend, a small observatory dome in silhouette.",
    "heterogeneity": "16:9. " + RULES + " A panorama across Bolivia's Yungas, where the high Andes fall to the "
    "Amazon: from left to right the same ridged landscape changes gradually, the light over the highlands rose "
    "and salt-white, shifting smoothly through sand tones to turquoise over the cloud forest and lowlands.",
    "case-study-sdg": "16:9. " + RULES + " A small town on the Bolivian Altiplano at dawn, seen from a low hill: "
    "adobe houses, a school with a solar roof, a water tower and street lamps whose lights are coming on in rose "
    "and turquoise, quinoa fields in red and gold around it, Andean peaks behind.",
    "own-indicators": "16:9. " + RULES + " A traditional Andean backstrap loom in a Bolivian workshop, close "
    "view without people: threads in turquoise, rose, sand and salt-white run from separate spools and join into "
    "one aguayo pattern taking shape on the loom, warm light on dark adobe walls.",
}
SIZES = {"icon": (512, 512), "hero": (1600, 800)}
THUMB = (1200, 675)


def crop_to(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Centre-crop to the aspect ratio of ``size``, then resize."""
    w, h = img.size
    target = size[0] / size[1]
    if w / h > target:
        nw = round(h * target)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = round(w / target)
        img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return img.resize(size, Image.LANCZOS)


def placeholder(key: str, size: tuple[int, int]) -> Image.Image:
    """A stand-in in the site's colours, so the documentation builds before the pictures exist."""
    img = Image.new("RGB", size, "#0b1e22")
    draw = ImageDraw.Draw(img)
    w, h = size
    for i, colour in enumerate(("#122b30", "#1b3c42", "#29545b")):
        draw.polygon([(0, h), (w * (0.25 + 0.2 * i), h * (0.45 + 0.12 * i)), (w, h * (0.7 + 0.08 * i)), (w, h)], fill=colour)
    draw.ellipse([w * 0.78, h * 0.14, w * 0.78 + h * 0.12, h * 0.26], fill="#5ad6c6" if hash(key) % 2 else "#d1405a")
    return img


def write(key: str, source: Image.Image) -> list[Path]:
    """Write every file derived from one picture."""
    out = []
    if key == "icon":
        icon = crop_to(source.convert("RGBA"), SIZES["icon"])
        for name, px in (("icon.png", 512), ("favicon.png", 64), ("logo-navbar.png", 72)):
            icon.resize((px, px), Image.LANCZOS).save(IMG / name)
            out.append(IMG / name)
    elif key == "hero":
        crop_to(source.convert("RGB"), SIZES["hero"]).save(IMG / "hero.webp", quality=86, method=6)
        out.append(IMG / "hero.webp")
    else:
        (IMG / "thumbs").mkdir(parents=True, exist_ok=True)
        path = IMG / "thumbs" / f"{key}.webp"
        crop_to(source.convert("RGB"), THUMB).save(path, quality=84, method=6)
        out.append(path)
    return out


ORIGINALS = IMG / "originals"
CODEX_IMAGES = Path.home() / ".codex" / "generated_images"
ASK = ("Use your image generation tool to create exactly one image from this description, then stop. "
       "Do not write any code or files yourself. Description: ")


def generate(only_missing: bool = True) -> None:
    """Draw the pictures with the Codex CLI's image tool (needs ``codex`` signed in to ChatGPT)."""
    ORIGINALS.mkdir(parents=True, exist_ok=True)
    for key, prompt in PROMPTS.items():
        target = ORIGINALS / f"{PREFIX}{key}.png"
        if only_missing and target.exists():
            continue
        started = time.time()
        subprocess.run(["codex", "exec", "--skip-git-repo-check", ASK + prompt], stdin=subprocess.DEVNULL,
                       capture_output=True, cwd=ORIGINALS, check=False)
        new = [p for p in CODEX_IMAGES.glob("*/*.png") if p.stat().st_mtime >= started]
        if not new:
            print(f"{key}: no picture was generated")
            continue
        target.write_bytes(max(new, key=lambda p: p.stat().st_mtime).read_bytes())
        print(f"{target.relative_to(ROOT)}  ({time.time() - started:.0f} s)")


def main(argv: list[str]) -> int:
    if "--prompts" in argv:
        for key, prompt in PROMPTS.items():
            print(f"\n### {PREFIX}{key}.png\n{prompt}")
        return 0
    if "--generate" in argv:
        generate(only_missing="--all" not in argv)
    stand_ins = "--placeholders" in argv
    folders = [a for a in argv if not a.startswith("--")]
    folder = Path(folders[0]).expanduser() if folders else ORIGINALS
    IMG.mkdir(parents=True, exist_ok=True)
    missing = []
    for key in PROMPTS:
        source = folder / f"{PREFIX}{key}.png"
        if source.exists():
            for path in write(key, Image.open(source)):
                print(f"{path.relative_to(ROOT)}  <- {source.name}")
        elif stand_ins:
            for path in write(key, placeholder(key, SIZES.get(key, THUMB))):
                print(f"{path.relative_to(ROOT)}  (placeholder)")
        else:
            missing.append(source.name)
    if missing:
        print(f"\nNot found in {folder}: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
