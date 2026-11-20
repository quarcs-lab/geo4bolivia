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
- ``hero``  -> ``hero.webp`` (1600 x 800), the home page, README and link-preview banner, and
  ``hero-card.webp`` (1600 x 900), the observatory website's geo4bolivia card (copied there by
  hand); on both this script draws the package name, its tagline and the SDG colour wheel
  (``HERO_TITLE``) in Inter (``tools/fonts/``, SIL Open Font License)
- articles  -> ``thumbs/<id>.webp`` (1200 x 675), one per article

Rules for the pictures: Bolivian places and themes only; no country outlines,
borders, globes or other countries; no text, logos or flags (the hero may hold abstract map-like
shapes, and its title and SDG wheel are drawn by this script). Any real map in the documentation is
drawn by the package from the official boundaries.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs" / "images"
FONTS = ROOT / "tools" / "fonts"
PREFIX = "g4b-"

RULES = (
    "Cinematic, editorial and minimal. Palette: deep teal-black (#071417, #0b1e22), glowing turquoise "
    "(#5ad6c6), flamingo pink and rose (#ff8597, #d1405a), soft salt-white and a little warm sand (#e7c27d). "
    "Strict rules: only Bolivian landscape and culture; NO maps, NO country outlines, NO borders or boundary "
    "lines, NO globe, NO other countries or continents; no people's faces; no text, letters, numbers, labels, "
    "logos, flags or watermarks."
)
# The hero shows the package's subject, so it may hold abstract map-like shapes (never a country outline)
HERO_RULES = (
    "Cinematic, editorial, luminous. Palette: deep teal-black (#071417, #0b1e22), glowing turquoise "
    "(#5ad6c6), flamingo pink and rose (#ff8597, #d1405a), soft salt-white and a little warm sand (#e7c27d). "
    "Strict rules: Bolivian landscape only; abstract map-like shapes are allowed, but NO country outline, "
    "NO borders or boundary lines, NO globe, NO other countries or continents; no people's faces; no text, "
    "letters, numbers, axis labels, legends, logos, flags or watermarks."
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
    "hero": "2:1 wide banner. " + HERO_RULES + " "
    "Bolivia's night-time lights seen from orbit: a high view of the Earth's surface at night over the Andes,"
    ' the Altiplano and the eastern lowlands, with no coastline, no borders and no visible country shape. '
    'City lights form clusters of warm gold and rose: one large dense cluster on the high plateau beside a '
    'dark lake, others in the valleys and a large one on the eastern plain, villages as faint specks, the '
    'dark snow-capped cordillera between them. A faint turquoise hexagon grid lies over part of the land, '
    'aggregating the lights into cells. In the foreground, in orbit, a detailed satellite with solar panels '
    'senses the lights below with a soft turquoise sensor glow. A slim translucent panel of three tiny '
    'unlabelled charts floats in space at right: a scatter plot with a fitted line, a Lorenz curve, a trend '
    'line. Logic of the picture: the satellite only observes the land (it images the terrain or senses its '
    'lights); every analytical graphic (points, network lines, cells, charts) is a translucent data layer or '
    'overlay derived from the land, never an object lying on the ground. Charts are tiny and unlabelled: no '
    'axis labels, no numbers, no letters. Leave the upper-left corner of the picture as calm, empty dark sky '
    'or space, with nothing in it, for a title and emblem added later. Elegant, modern, uncluttered.',
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
SIZES = {"icon": (512, 512), "hero": (1600, 800), "hero-card": (1600, 900)}

# The SDG colour wheel is drawn by this script, not by the image model (which gets its 17 segments and
# colours wrong): official colours, SDG 1 at twelve o'clock, clockwise, no text. Used for information only,
# as the UN's SDG guidelines allow.
SDG_COLOURS = ["#E5243B", "#DDA63A", "#4C9F38", "#C5192D", "#FF3A21", "#26BDE2", "#FCC30B", "#A21942", "#FD6925",
               "#DD1367", "#FD9D24", "#BF8B2E", "#3F7E44", "#0A97D9", "#56C02B", "#00689D", "#19486A"]

# The hero's title, drawn by this script (the image model misspells text). x is a fraction of the width;
# y (the top of the name) and size (the name's font size) are fractions of the height. The left of the
# picture is darkened (shade) and a soft dark spot sits behind the text (spot: centre x, y and radii as
# fractions, opacity), so the tagline reads over the city lights. The SDG wheel sits above the name.
HERO_TITLE = {
    "name": "geo4bolivia",
    "tagline": ["Spatial data science for Bolivia's", "subnational development data"],
    "x": 0.055, "y": 0.27, "size": 0.15,
    "shade": {"reach": 0.62, "vreach": 1.15, "strength": 0.95},
    "spot": (0.20, 0.42, 0.30, 0.30, 0.8),
    "wheel": {"r": 0.42, "alpha": 0.9, "glow": 0.45},       # radius as a fraction of the name's size
}
TEXT, TAGLINE_TEXT, ACCENT, NIGHT = "#f2f7f6", "#e3ecea", "#5ad6c6", (7, 20, 23)


def sdg_wheel(r: int, inner: float = 0.6, gap_deg: float = 1.2, ss: int = 4) -> Image.Image:
    """The SDG colour wheel as an RGBA ring of radius ``r`` pixels."""
    big = r * ss
    img = Image.new("RGBA", (2 * big + 2, 2 * big + 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    step = 360 / len(SDG_COLOURS)
    for k, colour in enumerate(SDG_COLOURS):
        start = -90 + k * step + gap_deg / 2
        draw.pieslice([0, 0, 2 * big, 2 * big], start, start + step - gap_deg, fill=colour)
    hole = big * inner
    draw.ellipse([big - hole, big - hole, big + hole, big + hole], fill=(0, 0, 0, 0))
    return img.resize((2 * r + 1, 2 * r + 1), Image.LANCZOS)


def add_sdg_wheel(img: Image.Image, x: float, y: float, r: float, alpha: float, glow: float) -> Image.Image:
    """Composite a softly glowing, slightly translucent SDG wheel onto ``img``."""
    base = img.convert("RGBA")
    cx, cy, radius = round(x * base.width), round(y * base.height), round(r * base.height)

    def faded(ring: Image.Image, factor: float) -> Image.Image:
        ring.putalpha(ring.getchannel("A").point(lambda v: int(v * factor)))
        return ring

    halo = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ring = faded(sdg_wheel(round(radius * 1.06)), glow)
    halo.paste(ring, (cx - ring.width // 2, cy - ring.height // 2), ring)
    base = Image.alpha_composite(base, halo.filter(ImageFilter.GaussianBlur(radius * 0.18)))
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ring = faded(sdg_wheel(radius), alpha)
    layer.paste(ring, (cx - ring.width // 2, cy - ring.height // 2), ring)
    return Image.alpha_composite(base, layer).convert("RGB")


def _darken(img: Image.Image, mask: Image.Image) -> Image.Image:
    night = Image.new("RGBA", img.size, (*NIGHT, 255))
    night.putalpha(mask)
    return Image.alpha_composite(img.convert("RGBA"), night)


def shade_left(img: Image.Image, reach: float, vreach: float, strength: float) -> Image.Image:
    """Darken the upper-left of ``img``, fading out by ``reach`` of the width and ``vreach`` of the height."""
    w, h = img.size
    across = Image.new("L", (w, 1))
    across.putdata([round(255 * max(0.0, 1 - x / (reach * w)) ** 1.4) for x in range(w)])
    down = Image.new("L", (1, h))
    down.putdata([round(255 * strength * max(0.0, 1 - y / (vreach * h)) ** 0.84) for y in range(h)])
    return _darken(img, ImageChops.multiply(across.resize((w, h)), down.resize((w, h))))


def dark_spot(img: Image.Image, cx: float, cy: float, rx: float, ry: float, opacity: float) -> Image.Image:
    """A soft dark ellipse (centre and radii as fractions of the size) behind the text."""
    w, h = img.size
    mask = Image.new("L", (w, h))
    ImageDraw.Draw(mask).ellipse([(cx - rx) * w, (cy - ry) * h, (cx + rx) * w, (cy + ry) * h], fill=round(255 * opacity))
    return _darken(img, mask.filter(ImageFilter.GaussianBlur(min(w, h) * 0.09)))


def add_title(img: Image.Image, spec: dict = HERO_TITLE) -> Image.Image:
    """Draw the package name, a turquoise bar with the tagline, and the SDG wheel above the name."""
    img = dark_spot(shade_left(img, **spec["shade"]), *spec["spot"])
    w, h = img.size
    x, y, size = round(spec["x"] * w), round(spec["y"] * h), round(spec["size"] * h)
    if spec.get("wheel"):
        wheel = spec["wheel"]
        r = round(size * wheel["r"])
        img = add_sdg_wheel(img, x=(x + r) / w, y=(y - r * 1.45) / h, r=r / h, alpha=wheel["alpha"],
                            glow=wheel["glow"]).convert("RGBA")
    name = ImageFont.truetype(str(FONTS / "Inter-ExtraBold.ttf"), size)
    tag_px = round(size * 0.33)
    tag = ImageFont.truetype(str(FONTS / "Inter-Medium.ttf"), tag_px)
    # A faint glow behind the name and a soft shadow under the tagline
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((x, y), spec["name"], font=name, fill=(242, 247, 246, 40))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(size * 0.12)))
    tx, ty = x + round(size * 0.16), y + name.getbbox(spec["name"])[3] + round(size * 0.30)
    lines = [(tx, ty + i * round(tag_px * 1.32), line) for i, line in enumerate(spec["tagline"])]
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    for lx, ly, line in lines:
        ImageDraw.Draw(shadow).text((lx, ly), line, font=tag, fill=(*NIGHT, 230))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(size * 0.06)))
    draw = ImageDraw.Draw(img)
    draw.text((x, y), spec["name"], font=name, fill=TEXT)
    bar_end = ty + round(tag_px * (1.32 * (len(lines) - 1) + 1.28))
    draw.rounded_rectangle([x, ty + 4, x + round(size * 0.04), bar_end], 3, fill=ACCENT)
    for lx, ly, line in lines:
        draw.text((lx, ly), line, font=tag, fill=TAGLINE_TEXT)
    return img.convert("RGB")


THUMB = (1200, 675)


def crop_to(img: Image.Image, size: tuple[int, int], align: float = 0.5) -> Image.Image:
    """Crop to the aspect ratio of ``size`` (``align``: 0 keeps the left or top, 1 the right or bottom), then resize."""
    w, h = img.size
    target = size[0] / size[1]
    if w / h > target:
        nw = round(h * target)
        left = round((w - nw) * align)
        img = img.crop((left, 0, left + nw, h))
    else:
        nh = round(w / target)
        top = round((h - nh) * align)
        img = img.crop((0, top, w, top + nh))
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
        # The 16:9 card keeps the right of the picture (its charts); the cut-off left lies under the title
        for name, size, align in (("hero.webp", SIZES["hero"], 0.5), ("hero-card.webp", SIZES["hero-card"], 1.0)):
            add_title(crop_to(source.convert("RGB"), size, align)).save(IMG / name, quality=86, method=6)
            out.append(IMG / name)
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
