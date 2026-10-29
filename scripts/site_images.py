"""Render the website's images from the data and from Sentinel-2 cloudless.

    uv run python scripts/site_images.py [all | hero | bands | outline | emblem | og | cards | pillars]

- hero, bands: Sentinel-2 cloudless by EOX IT Services GmbH, read as WGS84 WMTS tiles and cached
  in the system temp folder: the 2016 mosaic (CC BY 4.0), except the Laguna Verde band from the
  2024 mosaic (CC BY-NC-SA 4.0). `hero` prints the patch settings to paste into index.html
  (BOLIVIA_PATCH, HERO_CITIES): a level-11 patch around each city and a level-13 close-up of its centre.
- outline: geo/boundaries/country_outline_web.geojson, a light outline for the globe.
- emblem: images/logo/emblem-*.png, the GDO-Bolivia emblem: the nine departments shaded by
  multidimensional poverty inside a satellite's orbit, on a lagoon tile (icons) or transparent
  (emblem-dark-192.png, for the dark site header).
- og: images/og-image.jpg, the social preview.
- cards, pillars: maps and charts of the published data, in the site's colours.

Card images for the notebooks redraw one key result of each notebook in the site's colours,
recomputed from the data with the notebook's own settings (`notebook_cards`, run with `cards`).
"""

from __future__ import annotations

import io
import json
import math
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "images"
# The site's Altiplano palette (index.html, tailwind.config): the night over the Salar de Uyuni,
# Laguna Verde's turquoise, Laguna Colorada's flamingos, salt and sand
BG = "#071417"           # lagoon-950
SURFACE = "#0b1e22"      # lagoon-900
RAISED = "#122b30"       # lagoon-800
EDGE = "#1b3c42"         # lagoon-700
TEXT = "#e6efee"
MUTED = "#a9bebb"        # salt-400
SALT = "#f4f1e8"
TURQUOISE = "#5ad6c6"    # highlights, indicators
FLAMINGO = "#ff8597"     # accent text and marks
ROSE = "#e8566b"
SAND = "#e7c27d"         # packages
DEEP_TEAL = "#1f8a80"
# Diverging palette of the site's maps: deep lagoon -> turquoise -> salt -> flamingo rose
SITE_PALETTE = ["#0f3a3f", "#13605f", "#1f8a80", "#5fb7a6", "#c9e2d6", "#f3c7c1", "#ec8f99", "#d84a64"]
# Sequential palette for densities: deep lagoon -> turquoise -> salt
SEQ_PALETTE = ["#0f3a3f", "#13605f", "#1f8a80", "#5fb7a6", "#a8dccf", "#f4f1e8"]

# 2016 is CC BY 4.0; the later yearly mosaics (s2cloudless-<year>) are CC BY-NC-SA 4.0
TILE_URL = "https://tiles.maps.eox.at/wmts/1.0.0/{layer}/default/WGS84/{z}/{row}/{col}.jpg"
CACHE = Path(tempfile.gettempdir()) / "gdo_s2cloudless_2016"

CITIES = [  # hero cities: id, name, lat, lng
    ("la-paz", "La Paz", -16.4955, -68.1336),
    ("cochabamba", "Cochabamba", -17.3895, -66.1568),
    ("santa-cruz", "Santa Cruz", -17.7833, -63.1821),
    ("sucre", "Sucre", -19.0476, -65.2596),
    ("potosi", "Potosí", -19.5891, -65.7535),
]

BANDS = [  # section bands: key, place, lat, lng, tile level[, mosaic year]
    ("about", "Laguna Verde · Licancabur", -22.80, -67.87, 12, 2024),   # the 2016 mosaic has cloud over the lagoon
    ("indicators", "Lake Titicaca", -16.05, -69.05, 9),
    ("tools", "La Paz · El Alto", -16.51, -68.15, 11),
    ("insights", "Santa Cruz de la Sierra", -17.78, -63.18, 11),
    ("events", "Cochabamba valley", -17.42, -66.15, 10),
    ("footer", "Río Mamoré near Trinidad", -14.83, -64.92, 10),
]


# --- Sentinel-2 cloudless tiles ------------------------------------------------------------

def tile_deg(z: int) -> float:
    return 180 / 2 ** z


def tile_index(lat: float, lng: float, z: int) -> tuple[int, int]:
    d = tile_deg(z)
    return math.floor((90 - lat) / d), math.floor((lng + 180) / d)   # row, col


def tile(z: int, row: int, col: int, year: int = 2016) -> Image.Image:
    layer = "s2cloudless" if year == 2016 else f"s2cloudless-{year}"
    path = CACHE / (f"{z}_{row}_{col}.jpg" if year == 2016 else f"{year}_{z}_{row}_{col}.jpg")
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        for attempt in range(4):
            r = requests.get(TILE_URL.format(layer=layer, z=z, row=row, col=col), timeout=60)
            if r.ok:
                path.write_bytes(r.content)
                break
            time.sleep(2 ** attempt)
        else:
            r.raise_for_status()
    return Image.open(path).convert("RGB")


def mosaic(z: int, row0: int, col0: int, nrows: int, ncols: int, year: int = 2016) -> Image.Image:
    out = Image.new("RGB", (256 * ncols, 256 * nrows))
    for i in range(nrows):
        for j in range(ncols):
            out.paste(tile(z, row0 + i, col0 + j, year), (256 * j, 256 * i))
    return out


def block_bounds(z, row0, col0, nrows, ncols):
    d = tile_deg(z)
    lat0, lng0 = 90 - row0 * d, col0 * d - 180              # top-left corner
    return lat0, lng0, nrows * d, ncols * d


def patch_spec(z, row0, col0, nrows, ncols):
    lat0, lng0, h, w = block_bounds(z, row0, col0, nrows, ncols)
    return {"lat": round(lat0 - h / 2, 6), "lng": round(lng0 + w / 2, 6), "width": round(w, 6), "height": round(h, 6)}


def save_webp(img: Image.Image, path: Path, quality: int = 80) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "WEBP", quality=quality, method=6)
    print(f"  wrote {path.relative_to(ROOT)}  {img.size[0]}x{img.size[1]}  {path.stat().st_size / 1e3:.0f} kB")


def country():
    import geo4bolivia as geo
    return geo.boundaries("country").geometry.iloc[0]


def polygon_mask(geom, size, to_px, feather: int) -> Image.Image:
    """Alpha mask of a (multi)polygon in pixel space, feathered at the edges."""
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    polys = getattr(geom, "geoms", [geom])
    for p in polys:
        draw.polygon([to_px(x, y) for x, y in p.exterior.coords], fill=255)
        for hole in p.interiors:
            draw.polygon([to_px(x, y) for x, y in hole.coords], fill=0)
    if feather:
        mask = mask.filter(ImageFilter.MaxFilter(2 * (feather // 2) + 1)).filter(ImageFilter.GaussianBlur(feather))
    return mask


def hero() -> None:
    print("hero")
    geom = country()
    minx, miny, maxx, maxy = geom.bounds
    z = 7                                                    # ~600 m/px for the country
    row0, col0 = tile_index(maxy, minx, z)
    row1, col1 = tile_index(miny, maxx, z)
    nrows, ncols = row1 - row0 + 1, col1 - col0 + 1
    img = mosaic(z, row0, col0, nrows, ncols)
    lat0, lng0, _, _ = block_bounds(z, row0, col0, nrows, ncols)
    d = tile_deg(z)
    to_px = lambda x, y: ((x - lng0) / d * 256, (lat0 - y) / d * 256)
    rgba = img.convert("RGBA")
    rgba.putalpha(polygon_mask(geom.buffer(0.15), img.size, to_px, feather=10))
    save_webp(rgba, IMG / "hero-bolivia-s2.webp", quality=78)
    specs = {"country": patch_spec(z, row0, col0, nrows, ncols)}

    # static fallback behind the hero text: the same view, unmasked
    fallback = img.resize((1600, round(img.size[1] * 1600 / img.size[0])), Image.LANCZOS)
    top = (fallback.size[1] - 1422) // 2
    save_webp(fallback.crop((0, top, 1600, top + 1422)), IMG / "hero-day.webp", quality=80)

    z = 11                                                   # ~38 m/px for the cities, a 9 x 7 block
    for cid, name, lat, lng in CITIES:
        row, col = tile_index(lat, lng, z)
        img = mosaic(z, row - 3, col - 4, 7, 9).convert("RGBA")
        fade = Image.new("L", img.size, 0)
        ImageDraw.Draw(fade).rectangle([40, 40, img.size[0] - 40, img.size[1] - 40], fill=255)
        img.putalpha(fade.filter(ImageFilter.GaussianBlur(24)))
        save_webp(img, IMG / f"hero-city-{cid}.webp", quality=78)
        specs[cid] = patch_spec(z, row - 3, col - 4, 7, 9)
        # close-up of the centre: a 7 x 5 block of level-13 tiles (~10 m/px, Sentinel-2's own resolution)
        row, col = tile_index(lat, lng, 13)
        img = mosaic(13, row - 2, col - 3, 5, 7).convert("RGBA")
        fade = Image.new("L", img.size, 0)
        ImageDraw.Draw(fade).rectangle([60, 60, img.size[0] - 60, img.size[1] - 60], fill=255)
        img.putalpha(fade.filter(ImageFilter.GaussianBlur(30)))
        save_webp(img, IMG / f"hero-city-{cid}-z13.webp", quality=78)
        specs[cid + "-z13"] = patch_spec(13, row - 2, col - 3, 5, 7)
    print("\n  Patch settings for index.html:")
    c = specs.pop("country")
    print(f"  BOLIVIA_PATCH = {{ lat: {c['lat']}, lng: {c['lng']}, width: {c['width']}, height: {c['height']} }}")
    for (cid, name, lat, lng) in CITIES:
        s = specs[cid]
        t = specs[cid + "-z13"]
        print(f"  {{ id: '{cid}', name: '{name}', lat: {lat}, lng: {lng}, patch: cityPatch('{cid}', {s['lat']}, {s['lng']}), "
              f"detail: cityDetailPatch('{cid}', {t['lat']}, {t['lng']}) }},")
    print(f"  city patch width {s['width']}, height {s['height']}; detail width {t['width']}, height {t['height']}")


def bands() -> None:
    print("bands")
    for key, place, lat, lng, z, *year in BANDS:
        year = year[0] if year else 2016
        row, col = tile_index(lat, lng, z)
        img = mosaic(z, row - 1, col - 3, 3, 7, year)         # 1792 x 768
        left, top = (img.size[0] - 1600) // 2, (img.size[1] - 640) // 2
        save_webp(img.crop((left, top, left + 1600, top + 640)), IMG / "bands" / f"{slug(place)}.webp", quality=76)
        extra = f", year: {year}" if year != 2016 else ""
        print(f"    {key}: {{ image: 'images/bands/{slug(place)}.webp', place: '{place}', lat: {lat}, lng: {lng}{extra} }}")


def slug(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return "-".join(w for w in "".join(ch if ch.isalnum() else " " for ch in text).split() if w not in {"near"})


# --- outline, emblem, social preview --------------------------------------------------------

def outline() -> None:
    import geopandas as gpd
    print("outline")
    g = gpd.GeoDataFrame({"name": ["Bolivia"]}, geometry=[country().simplify(0.01)], crs="EPSG:4326")
    out = ROOT / "geo/boundaries/country_outline_web.geojson"
    out.unlink(missing_ok=True)
    g.to_file(out, driver="GeoJSON", COORDINATE_PRECISION=4)
    print(f"  wrote {out.relative_to(ROOT)}  {out.stat().st_size / 1e3:.0f} kB")


def fit_px(geoms, box: tuple[float, float, float, float]):
    """Pixel rings of (multi)polygons, fitted together in box = (x0, y0, x1, y1) at Bolivia's latitude."""
    k = math.cos(math.radians(16.5))
    minx, miny, maxx, maxy = country().bounds
    w, h = (maxx - minx) * k, maxy - miny
    x0, y0, x1, y1 = box
    s = min((x1 - x0) / w, (y1 - y0) / h)
    ox, oy = x0 + ((x1 - x0) - w * s) / 2, y0 + ((y1 - y0) - h * s) / 2
    to_px = lambda x, y: (ox + (x - minx) * k * s, oy + (maxy - y) * s)
    return [[[to_px(x, y) for x, y in p.exterior.coords] for p in getattr(g, "geoms", [g])] for g in geoms]


def hex_rgba(color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), alpha


def orbit_px(W: int, front: bool, n: int = 240):
    """One half of a tilted satellite orbit around the map: the far (upper) or the near (lower) half."""
    cx, cy, a, b, tilt = W * 0.5, W * 0.53, W * 0.45, W * 0.13, math.radians(-24)
    ts = np.linspace(0, math.pi, n) if front else np.linspace(math.pi, 2 * math.pi, n)
    return [(cx + a * math.cos(t) * math.cos(tilt) - b * math.sin(t) * math.sin(tilt),
             cy + a * math.cos(t) * math.sin(tilt) + b * math.sin(t) * math.cos(tilt)) for t in ts]


def compose_emblem(size: int, tile: bool) -> Image.Image:
    """The GDO-Bolivia emblem: Bolivia's nine departments shaded by multidimensional poverty
    (2012, population-weighted; turquoise = lower, flamingo = higher) inside a satellite's orbit.
    tile=True draws it on a rounded lagoon tile (favicons, app icons); False leaves it transparent.
    Below 64 px the country is one turquoise shape and the orbit is heavier, so the favicon stays legible."""
    import geo4bolivia as geo
    ss = 4                                                    # supersampling for smooth edges
    W = size * ss
    canvas = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    if tile:
        glow = Image.new("RGBA", (W, W), hex_rgba(BG))
        halo = Image.new("L", (W, W), 0)
        ImageDraw.Draw(halo).ellipse([W * 0.05, W * 0.0, W * 0.95, W * 0.9], fill=150)
        glow.paste(Image.new("RGBA", (W, W), hex_rgba(RAISED)), mask=halo.filter(ImageFilter.GaussianBlur(W * 0.12)))
        mask = Image.new("L", (W, W), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, W - 1], radius=int(W * 0.22), fill=255)
        canvas.paste(glow, mask=mask)
    small = size <= 64
    lw = max(2, int(W * (0.05 if small else 0.018 if tile else 0.03)))   # the header copy is shown at 40 px

    back = Image.new("RGBA", (W, W), (0, 0, 0, 0))            # the far half of the orbit, behind the map
    ImageDraw.Draw(back).line(orbit_px(W, front=False), fill=hex_rgba(SALT, 110), width=lw, joint="curve")
    canvas.alpha_composite(back)

    deps = geo.boundaries("department")
    mpi = geo.aggregate(geo.load("sdg", variables="sdg1_2_mpi", years=2012), to="department",
                        rules={"sdg1_2_mpi": "weighted_mean:pop"}, weights=geo.load("pop", years=2012))
    deps = deps.merge(mpi[["geo_id", "sdg1_2_mpi"]], on="geo_id")
    rank = deps["sdg1_2_mpi"].rank(method="first").to_numpy() - 1
    cmap = site_cmap()
    shapes = fit_px(deps.geometry.simplify(0.01), (W * 0.2, W * 0.15, W * 0.8, W * 0.87))
    draw = ImageDraw.Draw(canvas)
    if small:
        for rings in fit_px([country().simplify(0.05)], (W * 0.2, W * 0.15, W * 0.8, W * 0.87)):
            for ring in rings:
                draw.polygon(ring, fill=hex_rgba(TURQUOISE))
    else:
        for rings, r in zip(shapes, rank):
            c = tuple(int(255 * v) for v in cmap(0.12 + 0.88 * r / (len(deps) - 1))[:3]) + (255,)
            for ring in rings:
                draw.polygon(ring, fill=c)
        for rings in shapes:                                  # department borders in the background colour
            for ring in rings:
                draw.line(ring + [ring[0]], fill=hex_rgba(BG), width=max(1, int(W * 0.007)), joint="curve")

    front = Image.new("RGBA", (W, W), (0, 0, 0, 0))           # the near half, in front of the map
    ImageDraw.Draw(front).line(orbit_px(W, front=True), fill=hex_rgba(SALT, 235), width=lw, joint="curve")
    canvas.alpha_composite(front)
    sx, sy = orbit_px(W, front=True)[38]                      # the satellite, low on the near side
    halo = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    rd = W * 0.075
    ImageDraw.Draw(halo).ellipse([sx - rd, sy - rd, sx + rd, sy + rd], fill=hex_rgba(FLAMINGO, 150))
    canvas.alpha_composite(halo.filter(ImageFilter.GaussianBlur(W * 0.03)))
    rd = W * (0.085 if small else 0.042 if tile else 0.055)
    draw = ImageDraw.Draw(canvas)
    draw.ellipse([sx - rd, sy - rd, sx + rd, sy + rd], fill=hex_rgba(FLAMINGO), outline=hex_rgba(SALT), width=max(1, int(W * 0.01)))
    return canvas.resize((size, size), Image.LANCZOS)


def emblem() -> None:
    print("emblem")
    out = IMG / "logo"
    icon = compose_emblem(512, tile=True)
    for s in (180, 192, 512):
        icon.resize((s, s), Image.LANCZOS).save(out / f"emblem-{s}.png")
    compose_emblem(32, tile=True).save(out / "emblem-32.png")    # drawn at its own size, so the orbit stays crisp
    icon.resize((256, 256), Image.LANCZOS).save(out / "emblem.webp", "WEBP", quality=90)
    compose_emblem(192, tile=False).save(out / "emblem-dark-192.png")
    print("  wrote images/logo/emblem-{32,180,192,512}.png, emblem.webp, emblem-dark-192.png")


def font(size: int, bold: bool = False):
    from matplotlib import font_manager
    return ImageFont.truetype(font_manager.findfont(f"DejaVu Sans:{'bold' if bold else 'normal'}"), size)


def og() -> None:
    print("og")
    bg = Image.open(IMG / "hero-day.webp").convert("RGB")
    bg = bg.resize((1200, round(bg.size[1] * 1200 / bg.size[0])), Image.LANCZOS)
    top = (bg.size[1] - 630) // 2
    img = bg.crop((0, top, 1200, top + 630)).convert("RGBA")
    shade = Image.new("RGBA", img.size)
    px = shade.load()
    for x in range(img.size[0]):                             # dark on the left, fading to the right
        a = int(235 * max(0.0, 1 - x / 900) ** 0.8)
        for y in range(img.size[1]):
            px[x, y] = (7, 20, 23, a)
    img.alpha_composite(shade)
    img.alpha_composite(Image.open(IMG / "logo/emblem-dark-192.png").convert("RGBA").resize((120, 120), Image.LANCZOS), (70, 90))
    d = ImageDraw.Draw(img)
    d.text((70, 250), "GeoDevelopment", font=font(64, True), fill=(255, 255, 255))
    d.text((70, 325), "Observatory", font=font(64, True), fill=(255, 255, 255))
    d.text((70, 400), "of Bolivia", font=font(48, True), fill=(255, 133, 151))
    d.text((70, 490), "Open indicators, tools and insights for regional development",
           font=font(24), fill=(203, 217, 215))
    img.convert("RGB").save(IMG / "og-image.jpg", quality=88)
    print("  wrote images/og-image.jpg")


# --- data cards (matplotlib) ---------------------------------------------------------------

def mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
                         "text.color": TEXT, "axes.labelcolor": TEXT, "xtick.color": MUTED, "ytick.color": MUTED,
                         "axes.edgecolor": EDGE, "font.size": 13, "font.family": "DejaVu Sans"})
    return plt


def save_fig(fig, path: Path, size=(1600, 900)) -> None:
    buf = io.BytesIO()
    fig.savefig(buf, dpi=100, format="png")
    import matplotlib.pyplot as plt
    plt.close(fig)
    img = Image.open(buf).convert("RGB")
    if img.size != size:
        img = img.resize(size, Image.LANCZOS)
    save_webp(img, path, quality=85)


def site_cmap(n=None):
    from matplotlib.colors import LinearSegmentedColormap, ListedColormap
    if n:
        return ListedColormap(LinearSegmentedColormap.from_list("site", SITE_PALETTE)(np.linspace(0, 1, n)))
    return LinearSegmentedColormap.from_list("site", SITE_PALETTE)


def seq_cmap():
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list("seq", SEQ_PALETTE)


def quantile_map(ax, gdf, column, k, cmap, label, fmt="{:,.2f}", cax=None, reverse=False):
    import mapclassify
    q = mapclassify.Quantiles(gdf[column], k=k)
    cm = cmap if not reverse else cmap.reversed()
    gdf.assign(_c=q.yb).plot(column="_c", cmap=cm, ax=ax, edgecolor=BG, linewidth=0.25)
    ax.set_axis_off()
    if cax is not None:
        import matplotlib as mplib
        norm = mplib.colors.BoundaryNorm(np.arange(k + 1), cm.N)
        cb = mplib.colorbar.ColorbarBase(cax, cmap=cm, norm=norm, ticks=np.arange(k) + 0.5)
        cb.ax.set_yticklabels([f"≤ {fmt.format(b)}" for b in q.bins])
        cb.outline.set_edgecolor(MUTED)
        cb.set_label(label, color=TEXT)
        cb.ax.tick_params(colors=TEXT)


def cards() -> None:
    import geo4bolivia as geo
    from sklearn.decomposition import PCA
    plt = mpl()
    print("cards")
    mun = geo.boundaries("municipality")

    # SDG indicators: multidimensional poverty
    gdf = mun.merge(geo.load("sdg", variables="sdg1_2_mpi", years=2012), on="geo_id")
    fig = plt.figure(figsize=(16, 9))
    ax = fig.add_axes([0.18, 0.04, 0.6, 0.92]); cax = fig.add_axes([0.82, 0.2, 0.018, 0.6])
    quantile_map(ax, gdf, "sdg1_2_mpi", 7, site_cmap(), "Multidimensional Poverty Index 2012, quantiles", "{:.3f}", cax)
    save_fig(fig, IMG / "indicators/sdg.webp")

    # Night-time lights per capita (trend), 2020
    gdf = mun.merge(geo.load("ntl", years=2020), on="geo_id")
    fig = plt.figure(figsize=(16, 9))
    ax = fig.add_axes([0.18, 0.04, 0.6, 0.92]); cax = fig.add_axes([0.82, 0.2, 0.018, 0.6])
    quantile_map(ax, gdf, "ln_t400NTLpc", 7, plt.get_cmap("magma"), "Log night-time lights per capita (trend) 2020, quantiles", "{:.2f}", cax)
    save_fig(fig, IMG / "indicators/ntl.webp")

    # Population: density 2020 and growth 2001-2020
    pop = geo.load("pop", wide="pop")
    gdf = mun.merge(pop, on="geo_id").merge(geo.units("municipality")[["geo_id", "area_km2"]], on="geo_id")
    gdf["density"] = gdf["pop2020"] / gdf["area_km2"].astype(float)
    gdf["growth"] = 100 * ((gdf["pop2020"] / gdf["pop2001"]) ** (1 / 19) - 1)
    fig, axes = plt.subplots(1, 2, figsize=(16, 9))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.08, wspace=0.05)
    for ax, col, title, cmap in [(axes[0], "density", "People per km², 2020", seq_cmap()),
                                 (axes[1], "growth", "Annual population growth 2001–2020 (%)", site_cmap())]:
        quantile_map(ax, gdf, col, 7, cmap, title)
        ax.set_title(title, fontsize=20, color=TEXT)
    save_fig(fig, IMG / "indicators/pop.webp")

    # Satellite embeddings: the first three principal components as colours
    emb = geo.load("emb")
    X = emb.filter(regex=r"^A\d{2}$").to_numpy()
    pcs = PCA(3, random_state=0).fit_transform((X - X.mean(0)) / X.std(0))
    rgb = (pcs - np.percentile(pcs, 2, 0)) / (np.percentile(pcs, 98, 0) - np.percentile(pcs, 2, 0))
    gdf = mun.merge(emb[["geo_id"]].assign(_i=np.arange(len(emb))), on="geo_id")
    fig = plt.figure(figsize=(16, 9))
    ax = fig.add_axes([0.05, 0.04, 0.55, 0.92])
    gdf.plot(color=np.clip(rgb[gdf["_i"]], 0, 1), ax=ax, edgecolor=BG, linewidth=0.25); ax.set_axis_off()
    fig.text(0.6, 0.62, "Satellite embeddings, 2017", fontsize=27, weight="bold", color="white")
    fig.text(0.6, 0.55, "64 dimensions per municipality,\nshown as the first three principal\ncomponents in red, green and blue", fontsize=19, color=MUTED, va="top")
    fig.text(0.6, 0.3, 'geo.load("emb")   geo.load("embpw")', fontsize=17, color=TURQUOISE, family="DejaVu Sans Mono")
    save_fig(fig, IMG / "indicators/emb.webp")

    package_card(geo, plt)
    geometrics_card(geo, plt)
    expdpy_card(geo, plt)
    insight_card(geo, plt)
    notebook_cards(geo, plt)


def squash(gdf, y_scale=0.42, dy=0.0):
    from shapely import affinity
    out = gdf.copy()
    out["geometry"] = gdf.geometry.map(lambda g: affinity.affine_transform(g, [1, 0, 0, y_scale, 0, dy]))
    return out


def package_card(geo, plt):
    import mapclassify
    fig = plt.figure(figsize=(16, 9))
    ax = fig.add_axes([0.02, 0.03, 0.4, 0.94]); ax.set_axis_off()
    mpi = geo.load("sdg", variables="sdg1_2_mpi", years=2012)
    pop = geo.load("pop", years=2012)
    layers = [("department", "9 departments", "pop · BO-04", site_cmap()),
              ("province", "112 provinces", "sdg · BO-04-17", seq_cmap()),
              ("municipality", "339 municipalities", "ntl · BO-04-17-04", site_cmap().reversed())]
    for i, (scale, label, sub, cmap) in enumerate(layers):
        b = geo.boundaries(scale)
        vals = geo.aggregate(mpi, to=scale, rules={"sdg1_2_mpi": "weighted_mean:pop"}, weights=pop) if scale != "municipality" else mpi
        g = b.merge(vals, on="geo_id")
        dy = -i * 9.5
        sq = squash(g, dy=dy)
        sq.assign(_c=mapclassify.Quantiles(g["sdg1_2_mpi"], k=min(6, len(g) - 1)).yb).plot(
            column="_c", cmap=cmap, ax=ax, edgecolor=BG, linewidth=0.3 if scale != "municipality" else 0.15)
        pt = geo.boundaries("municipality").set_index("geo_id").loc["BO-04-17-04", "geometry"].representative_point()
        ax.plot(pt.x, pt.y * 0.42 + dy, "o", ms=9, mfc="white", mec=ROSE, mew=2.5, zorder=5)
        fig.text(0.42, 0.84 - i * 0.33, label, fontsize=21, weight="bold", color="white")
        fig.text(0.42, 0.79 - i * 0.33, sub, fontsize=15, color=TURQUOISE, family="DejaVu Sans Mono")
    ax.plot([pt.x] * 2, [pt.y * 0.42, pt.y * 0.42 - 19], ls="--", color=ROSE, lw=1.5, zorder=4)
    ax.set_xlim(-70, -57); ax.set_ylim(-31.5, -3.5)
    fig.text(0.62, 0.84, "geo4bolivia", fontsize=46, weight="bold", color="white")
    fig.text(0.62, 0.77, "load · link · build · move across scales", fontsize=20, color=SAND)
    from matplotlib.patches import FancyBboxPatch
    panel = FancyBboxPatch((0.61, 0.17), 0.365, 0.55, boxstyle="round,pad=0.005,rounding_size=0.015",
                           transform=fig.transFigure, facecolor=SURFACE, edgecolor=EDGE, lw=1.5)
    fig.patches.append(panel)
    for k, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
        fig.patches.append(plt.Circle((0.63 + k * 0.013, 0.68), 0.0055, transform=fig.transFigure, color=c))
    lines = ['import geo4bolivia as geo', '', 'geo.load("ntl", geometry=True)', 'geo.link(df, "municipality", on="mun_id")',
             'geo.aggregate(df, to="department")', 'geo.combine(["ntl", "pop"], "municipality")', 'geo.for_geometrics("ntl")']
    for k, t in enumerate(lines):
        fig.text(0.625, 0.61 - k * 0.055, t, fontsize=15, family="DejaVu Sans Mono", color="white" if k == 0 else "#bfe9e2")
    fig.text(0.62, 0.08, "pip install geo4bolivia", fontsize=21, weight="bold", family="DejaVu Sans Mono", color=SAND)
    save_fig(fig, IMG / "tools/geo4bolivia-package.webp")


def geometrics_card(geo, plt):
    import libpysal
    from esda.moran import Moran, Moran_Local
    ntl = geo.load("ntl", years=2012, variables="ln_t400NTLpc")
    g = geo.boundaries("municipality").merge(ntl, on="geo_id")
    w = libpysal.weights.Queen.from_dataframe(g, use_index=False, silence_warnings=True)
    w.transform = "r"
    y = g["ln_t400NTLpc"].to_numpy()
    lisa = Moran_Local(y, w, seed=0, permutations=999)
    mi = Moran(y, w, permutations=0)
    quad = np.where(lisa.p_sim < 0.05, lisa.q, 0)
    colors = {0: "#1d3a3f", 1: ROSE, 2: "#8fd3c5", 3: DEEP_TEAL, 4: "#f3b0b6"}
    fig = plt.figure(figsize=(16, 9))
    ax = fig.add_axes([0.02, 0.06, 0.42, 0.84])
    g.plot(color=[colors[q] for q in quad], ax=ax, edgecolor=BG, linewidth=0.2); ax.set_axis_off()
    ax.set_title("LISA clusters of night-time lights per capita, 2012", fontsize=17, color=TEXT)
    for q, lab in [(1, "High-High"), (3, "Low-Low"), (2, "Low-High"), (4, "High-Low"), (0, "Not significant")]:
        ax.scatter([], [], color=colors[q], label=lab, s=120)
    ax.legend(loc="lower left", frameon=False, labelcolor=TEXT, fontsize=12)
    ax2 = fig.add_axes([0.52, 0.14, 0.42, 0.68])
    z = (y - y.mean()) / y.std()
    lag = libpysal.weights.lag_spatial(w, z)
    ax2.scatter(z, lag, s=18, color=[colors[q] if q else "#5b7774" for q in quad], alpha=0.85)
    b = np.polyfit(z, lag, 1)
    xs = np.linspace(z.min(), z.max(), 10); ax2.plot(xs, b[0] * xs + b[1], color=SAND, lw=2.5)
    ax2.axhline(0, color="#2c4a4e", lw=1); ax2.axvline(0, color="#2c4a4e", lw=1)
    ax2.set_xlabel("Lights per capita (standardized)"); ax2.set_ylabel("Spatial lag")
    ax2.set_title(f"Moran's I = {mi.I:.2f}", fontsize=17, color=TEXT)
    for s in ax2.spines.values(): s.set_color(EDGE)
    fig.text(0.52, 0.9, "geometrics", fontsize=30, weight="bold", color="white")
    save_fig(fig, IMG / "tools/geometrics-package.webp")


def expdpy_card(geo, plt):
    ntl = geo.load("ntl")
    u = geo.units("municipality")[["geo_id", "department_id"]]
    deps = geo.units("department").set_index("geo_id")["name"]
    d = ntl.merge(u, on="geo_id")
    fig = plt.figure(figsize=(16, 9))
    ax = fig.add_axes([0.06, 0.12, 0.56, 0.7])
    for _, s in d.groupby("geo_id"):
        ax.plot(s["year"], s["ln_t400NTLpc"], color="#5fb7a6", alpha=0.12, lw=1)
    means = d.groupby(["department_id", "year"])["ln_t400NTLpc"].mean().unstack(0)
    cm = site_cmap()                                         # skip the darkest teals, unreadable on the background
    for k, col in enumerate(means.columns):
        ax.plot(means.index, means[col], color=cm(0.25 + 0.75 * k / 8), lw=3, label=deps[col])
    ax.legend(ncol=3, fontsize=10, frameon=False, labelcolor=TEXT, loc="lower right")
    ax.set_xlabel("Year"); ax.set_ylabel("Log lights per capita (trend)")
    ax.set_title("339 municipal trajectories and department means, 2012–2020", fontsize=16, color=TEXT)
    for s in ax.spines.values(): s.set_color(EDGE)
    x = d["ln_t400NTLpc"]
    between = d.groupby("geo_id")["ln_t400NTLpc"].transform("mean")
    sd_b, sd_w = between.std(), (x - between).std()
    ax2 = fig.add_axes([0.7, 0.12, 0.26, 0.5])
    ax2.bar(["between", "within"], [sd_b, sd_w], color=[ROSE, TURQUOISE], width=0.6)
    ax2.set_title("Standard deviation", fontsize=15, color=TEXT)
    for s in ax2.spines.values(): s.set_color(EDGE)
    fig.text(0.7, 0.86, "expdpy", fontsize=30, weight="bold", color="white")
    fig.text(0.7, 0.8, "panel exploration and econometrics", fontsize=15, color=MUTED)
    save_fig(fig, IMG / "tools/expdpy-package.webp")


def insight_card(geo, plt):
    sdg = geo.load("sdg").groupby("geo_id").first().reset_index()
    g = geo.boundaries("municipality").merge(sdg, on="geo_id")
    panels = [("sdg2_2_cmc", "Chronic child\nmalnutrition (2016)"), ("sdg10_2_nssp", "Non-Spanish\nspeakers (2012)"),
              ("sdg4_1_ssdrm", "Secondary dropout,\nmales (2017)"), ("sdg4_1_ssdrf", "Secondary dropout,\nfemales (2017)"),
              ("sdg10_2_gcye", "Inequality in years\nof education (2012)")]
    fig, axes = plt.subplots(1, 5, figsize=(16, 9))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.72, bottom=0.08, wspace=0.02)
    for ax, (col, title) in zip(axes, panels):
        quantile_map(ax, g.dropna(subset=[col]), col, 5, site_cmap(), title)
        ax.set_title(title, fontsize=15, color=TEXT)
    fig.text(0.02, 0.9, "Human capital constraints across Bolivia's 339 municipalities", fontsize=28, weight="bold", color="white")
    fig.text(0.02, 0.84, "The five indicators studied by Mendez & Gonzales (2021), mapped from the observatory's sdg dataset (quintiles)",
             fontsize=15, color=MUTED)
    save_fig(fig, IMG / "insights/human-capital-paper.webp")


LISA_COLORS = {"High-high": FLAMINGO, "Low-low": TURQUOISE, "High-low": "#f3c7c1", "Low-high": "#a8dccf",
               "Not significant": EDGE}


def card_text(fig, title, subtitle, code=None, x=0.6):
    fig.text(x, 0.66, title, fontsize=27, weight="bold", color="white", va="bottom")
    fig.text(x, 0.63, subtitle, fontsize=18, color=MUTED, va="top", linespacing=1.4)
    if code:
        fig.text(x, 0.2, code, fontsize=15, color=TURQUOISE, family="DejaVu Sans Mono")


def map_axes(fig):
    return fig.add_axes([0.04, 0.04, 0.52, 0.92])


def swatches(fig, items, x=0.6, y=0.38, dy=0.045):
    """A legend of coloured squares: [(label, colour)]."""
    for i, (label, color) in enumerate(items):
        fig.patches.append(__import__("matplotlib").patches.Rectangle(
            (x, y - i * dy), 0.016, 0.028, transform=fig.transFigure, facecolor=color, edgecolor=MUTED, linewidth=0.5))
        fig.text(x + 0.026, y - i * dy + 0.014, label, fontsize=15, color=TEXT, va="center")


def lisa_map(ax, gdf, column, deps):
    for label, color in LISA_COLORS.items():
        part = gdf[gdf[column] == label]
        if len(part):
            part.plot(ax=ax, color=color, edgecolor=BG, linewidth=0.25)
    deps.boundary.plot(ax=ax, color=SALT, linewidth=0.8, alpha=0.7)
    ax.set_axis_off()


def scatter_axes(fig, rect=(0.08, 0.13, 0.86, 0.72)):
    ax = fig.add_axes(rect)
    ax.grid(color=EDGE, linewidth=0.8); ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return ax


def notebook_cards(geo, plt) -> None:
    """One dark panel per notebook, recomputed from the data with each notebook's own settings."""
    import pandas as pd
    from esda.moran import Moran_Local, Moran_Local_BV
    from libpysal import weights
    from mgwr.gwr import GWR
    from mgwr.sel_bw import Sel_BW

    crs = geo.config()["equal_area_crs"]
    units = geo.units("municipality")
    deps = geo.boundaries("department").to_crs(crs)
    mpi = geo.load("sdg", variables="sdg1_2_mpi", years=2012, geometry=True)
    ntl = geo.load("ntl", variables="ln_t400NTLpc", years=2012)
    gdf = (mpi.merge(ntl[["geo_id", "ln_t400NTLpc"]], on="geo_id")
              .merge(units[["geo_id", "department_id"]], on="geo_id").to_crs(crs))
    W = weights.KNN.from_dataframe(gdf, k=6)
    W.transform = "r"
    quad = {1: "High-high", 2: "Low-high", 3: "Low-low", 4: "High-low"}
    tools = IMG / "tools"

    # quickstart: population-weighted poverty by department
    dep_mpi = geo.aggregate(geo.load("sdg", variables="sdg1_2_mpi", years=2012), to="department",
                            rules={"sdg1_2_mpi": "weighted_mean:pop"}, weights=geo.load("pop"))
    d = deps.merge(dep_mpi[["geo_id", "sdg1_2_mpi"]], on="geo_id")
    fig = plt.figure(figsize=(16, 9)); ax = map_axes(fig)
    d.plot(column="sdg1_2_mpi", cmap=site_cmap(), ax=ax, edgecolor=BG, linewidth=1.5); ax.set_axis_off()
    for _, r in d.iterrows():
        p = r.geometry.representative_point()
        ax.annotate(r["name"], (p.x, p.y), ha="center", va="center", fontsize=12, color="white",
                    path_effects=[__import__("matplotlib.patheffects", fromlist=["x"]).withStroke(linewidth=3, foreground=BG)])
    cax = fig.add_axes([0.6, 0.3, 0.3, 0.025])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(d["sdg1_2_mpi"].min(), d["sdg1_2_mpi"].max()), cmap=site_cmap()),
                      cax=cax, orientation="horizontal")
    cb.outline.set_edgecolor(MUTED); cb.ax.tick_params(colors=TEXT, labelsize=13)
    card_text(fig, "Poverty by department, 2012", "Multidimensional Poverty Index,\npopulation-weighted from 339 municipalities",
              'geo.aggregate(mpi, to="department")')
    save_fig(fig, tools / "geo4bolivia-quickstart.webp")

    # eda: lights and poverty
    x, y = gdf["ln_t400NTLpc"].to_numpy(), gdf["sdg1_2_mpi"].to_numpy()
    fig = plt.figure(figsize=(16, 9)); ax = scatter_axes(fig, (0.08, 0.13, 0.5, 0.72))
    ax.scatter(x, y, s=46, color=TURQUOISE, alpha=0.6, edgecolor="none")
    b, a = np.polyfit(x, y, 1); xs = np.linspace(x.min(), x.max(), 50)
    ax.plot(xs, a + b * xs, color=FLAMINGO, linewidth=3)
    ax.set_xlabel("Log night-time lights per capita (trend)", fontsize=16)
    ax.set_ylabel("Multidimensional Poverty Index", fontsize=16)
    card_text(fig, "Lights and poverty, 2012", f"Brighter municipalities are less poor:\n339 municipalities, r = {np.corrcoef(x, y)[0, 1]:.2f}",
              x=0.64)
    save_fig(fig, tools / "eda.webp")

    # esda: LISA clusters of poverty (p < 0.05)
    lisa = Moran_Local(gdf["sdg1_2_mpi"], W, permutations=999, seed=12345)
    gdf["lisa"] = np.where(lisa.p_sim < 0.05, pd.Series(lisa.q).map(quad), "Not significant")
    fig = plt.figure(figsize=(16, 9)); ax = map_axes(fig)
    lisa_map(ax, gdf, "lisa", deps)
    card_text(fig, "Poverty clusters, 2012", "Local Moran's I of multidimensional\npoverty, 6 nearest neighbours, p < 0.05")
    swatches(fig, [(f"{k} ({(gdf['lisa'] == k).sum()})", c) for k, c in LISA_COLORS.items()])
    save_fig(fig, tools / "esda.webp")

    # esda_dependence: box-plot breaks
    import mapclassify
    bp = mapclassify.BoxPlot(gdf["sdg1_2_mpi"])
    colors = site_cmap(6).colors
    fig = plt.figure(figsize=(16, 9)); ax = map_axes(fig)
    gdf.assign(_c=bp.yb).plot(column="_c", cmap=site_cmap(6), vmin=0, vmax=5, ax=ax, edgecolor=BG, linewidth=0.25)
    deps.boundary.plot(ax=ax, color=SALT, linewidth=0.8, alpha=0.7); ax.set_axis_off()
    lo = [gdf["sdg1_2_mpi"].min(), *bp.bins[:-1]]
    names = ["Low outliers", "Below Q1", "Q1 to median", "Median to Q3", "Above Q3", "High outliers"]
    card_text(fig, "Poverty, box-plot breaks", "Multidimensional Poverty Index, 2012:\nquartiles and outliers")
    swatches(fig, [(f"{n} ({(bp.yb == i).sum()})", colors[i]) for i, n in enumerate(names)], y=0.42)
    save_fig(fig, tools / "esda-dependence.webp")

    # esda_inequality: quintiles within departments
    q = mapclassify.Quantiles(gdf["sdg1_2_mpi"], k=5)
    fig = plt.figure(figsize=(16, 9)); ax = map_axes(fig)
    gdf.assign(_c=q.yb).plot(column="_c", cmap=site_cmap(5), ax=ax, edgecolor=BG, linewidth=0.25)
    deps.boundary.plot(ax=ax, color=SALT, linewidth=1.4); ax.set_axis_off()
    card_text(fig, "Inequality within and\nbetween departments", "Poverty quintiles, 2012, with the nine\ndepartments of the Theil decomposition")
    lo = [gdf["sdg1_2_mpi"].min(), *q.bins[:-1]]
    swatches(fig, [(f"{a:.2f} – {b:.2f}", c) for a, b, c in zip(lo, q.bins, site_cmap(5).colors)], y=0.38)
    save_fig(fig, tools / "esda-inequality.webp")

    # esda_heterogeneity: significant GWR slopes
    cent = gdf.geometry.centroid
    coords = np.column_stack([cent.x, cent.y]) / 1000
    yv, Xv = gdf[["sdg1_2_mpi"]].values, gdf[["ln_t400NTLpc"]].values
    bw = Sel_BW(coords, yv, Xv).search(criterion="AICc")
    res = GWR(coords, yv, Xv, bw).fit()
    sig = res.filter_tvals(alpha=0.05)[:, 1] != 0
    gdf["slope"] = res.params[:, 1]
    fj = mapclassify.FisherJenks(gdf.loc[sig, "slope"], k=5)
    cm = site_cmap(5).reversed()
    fig = plt.figure(figsize=(16, 9)); ax = map_axes(fig)
    gdf[~sig].plot(ax=ax, color=EDGE, edgecolor=BG, linewidth=0.25)
    gdf[sig].assign(_c=fj.yb).plot(column="_c", cmap=cm, ax=ax, edgecolor=BG, linewidth=0.25)
    deps.boundary.plot(ax=ax, color=SALT, linewidth=0.8, alpha=0.7); ax.set_axis_off()
    card_text(fig, "Where lights track poverty", f"Local GWR slope of poverty on night-time\nlights, 2012 (bandwidth {int(bw)}, significant at 5%)")
    lo = [gdf.loc[sig, "slope"].min(), *fj.bins[:-1]]
    swatches(fig, [(f"{a:.3f} to {b:.3f}", c) for a, b, c in zip(lo, fj.bins, cm.colors)] + [("Not significant", EDGE)], y=0.4)
    save_fig(fig, tools / "esda-heterogeneity.webp")

    # eda_esda: bivariate LISA, own poverty vs neighbours' lights (p < 0.10)
    bv = Moran_Local_BV(gdf["sdg1_2_mpi"].values, gdf["ln_t400NTLpc"].values, W, permutations=999, seed=12345)
    gdf["lisa_bv"] = np.where(bv.p_sim < 0.10, pd.Series(bv.q).map(quad), "Not significant")
    fig = plt.figure(figsize=(16, 9)); ax = map_axes(fig)
    lisa_map(ax, gdf, "lisa_bv", deps)
    card_text(fig, "Poverty and the lights\nnext door", "Bivariate LISA: own poverty against\nneighbours' night-time lights, p < 0.10")
    swatches(fig, [(f"{k} ({(gdf['lisa_bv'] == k).sum()})", c) for k, c in LISA_COLORS.items()])
    save_fig(fig, tools / "eda-esda.webp")

    # embeddings_mpi_ml: out-of-fold predictions, random 5-fold CV, XGBoost on embeddings + lights
    from sklearn.metrics import r2_score
    from sklearn.model_selection import KFold, cross_val_predict
    from xgboost import XGBRegressor
    df = (gdf[["geo_id", "sdg1_2_mpi", "ln_t400NTLpc"]]
          .merge(geo.load("pop", years=2012)[["geo_id", "pop"]], on="geo_id"))
    embpw = geo.load("embpw", years=2017).set_index("geo_id")
    dims = [f"A{i:02d}" for i in range(64)]
    X = np.column_stack([embpw.loc[df["geo_id"], dims].to_numpy(), df["ln_t400NTLpc"], np.log(df["pop"])])
    yv = df["sdg1_2_mpi"].to_numpy()
    model = XGBRegressor(n_estimators=400, learning_rate=0.03, max_depth=4, min_child_weight=3, subsample=0.8,
                         colsample_bytree=0.8, reg_lambda=1.0, random_state=42, n_jobs=4, verbosity=0)
    pred = cross_val_predict(model, X, yv, cv=KFold(n_splits=5, shuffle=True, random_state=42))
    fig = plt.figure(figsize=(16, 9)); ax = scatter_axes(fig, (0.08, 0.13, 0.5, 0.72))
    lim = (0, max(yv.max(), pred.max()) * 1.05)
    ax.plot(lim, lim, color=MUTED, linestyle="--", linewidth=1.2)
    ax.scatter(yv, pred, s=46, color=TURQUOISE, alpha=0.6, edgecolor="none")
    ax.set(xlim=lim, ylim=lim)
    ax.set_xlabel("Observed MPI (2012)", fontsize=16); ax.set_ylabel("Out-of-fold predicted MPI", fontsize=16)
    card_text(fig, "Poverty seen from space", f"XGBoost on 64 satellite embedding\ndimensions plus lights and population\n\nRandom 5-fold CV: R² = {r2_score(yv, pred):.2f}",
              'geo.load("embpw")', x=0.64)
    save_fig(fig, tools / "embeddings-mpi-ml.webp")


# --- pillars -------------------------------------------------------------------------------

def glow_line(ax, xs, ys, color, width=1.2, layers=6, alpha=0.08, z=3):
    for k in range(layers, 0, -1):
        ax.plot(xs, ys, color=color, lw=width + k * 2.2, alpha=alpha, solid_capstyle="round", zorder=z)
    ax.plot(xs, ys, color=color, lw=width, alpha=0.95, zorder=z + 0.1)


def backdrop(fig):
    ax = fig.add_axes([0, 0, 1, 1], zorder=-2); ax.set_axis_off()
    yy, xx = np.mgrid[0:1:400j, 0:1:600j]
    r = np.hypot((xx - 0.5) * 1.3, yy - 0.55)
    ax.imshow(np.clip(1 - r * 1.4, 0, 1), cmap=site_cmap().from_list("bg", [BG, RAISED]), extent=[0, 1, 0, 1],
              aspect="auto", zorder=0)
    return ax


def pillars() -> None:
    import geo4bolivia as geo
    import libpysal
    from matplotlib.transforms import Affine2D
    from shapely import affinity
    plt = mpl()
    print("pillars")
    mun = geo.boundaries("municipality")
    outline_geom = country()
    mpi = mun.merge(geo.load("sdg", variables="sdg1_2_mpi", years=2012), on="geo_id")
    ntl = mun.merge(geo.load("ntl", years=2020), on="geo_id")

    # Indicators: three stacked layers (imagery, a choropleth, night lights)
    fig = plt.figure(figsize=(12, 8)); backdrop(fig)
    ax = fig.add_axes([0.05, 0.02, 0.9, 0.96]); ax.set_axis_off(); ax.set_aspect("equal")
    SK, SY, GAP = -0.55, 0.42, 7.5                       # shear, vertical squash, distance between layers
    skew = lambda g, dy: affinity.affine_transform(g, [1, SK, 0, SY, 0, dy])
    sat = Image.open(IMG / "hero-bolivia-s2.webp").convert("RGBA")
    minx, miny, maxx, maxy = outline_geom.bounds
    z = 7
    row0, col0 = tile_index(maxy, minx, z)
    lat0, lng0, h, w = block_bounds(z, row0, col0, sat.size[1] // 256, sat.size[0] // 256)
    import mapclassify
    cls = mapclassify.Quantiles(mpi["sdg1_2_mpi"], k=8).yb
    cm = site_cmap(8)
    pts = ntl.geometry.representative_point()
    v = ntl["ln_t400NTLpc"].to_numpy(); s = np.clip((v - np.percentile(v, 5)) / (np.ptp(v) + 1e-9), 0.02, 1)
    layers = [("lights", -2 * GAP), ("choropleth", -GAP), ("imagery", 0.0)]
    for layer, dy in layers:
        edge = skew(outline_geom, dy)
        for p in getattr(edge, "geoms", [edge]):
            xs, ys = p.exterior.xy
            ax.fill(np.array(xs) + 0.15, np.array(ys) - 0.5, color="#020a0c", alpha=0.8, zorder=1)
            ax.fill(xs, ys, color="#0a1a1d", zorder=1.5)
            glow_line(ax, xs, ys, TURQUOISE, width=1.0, layers=5, alpha=0.08, z=4)
        if layer == "imagery":
            tr = Affine2D([[1, SK, 0], [0, SY, dy], [0, 0, 1]]) + ax.transData
            ax.imshow(np.array(sat), extent=[lng0, lng0 + w, lat0 - h, lat0], transform=tr, zorder=3, interpolation="bilinear")
        elif layer == "choropleth":
            for geom_, c in zip(mpi.geometry, cls):
                gg = skew(geom_, dy)
                for p in getattr(gg, "geoms", [gg]):
                    ax.fill(*p.exterior.xy, color=cm(c), ec=SURFACE, lw=0.25, zorder=3)
        else:
            px, py = pts.x + SK * pts.y, SY * pts.y + dy
            for k, a in [(420, 0.05), (160, 0.12), (36, 0.7)]:
                ax.scatter(px, py, s=k * s ** 2, color="#ffb547", alpha=a, lw=0, zorder=3.5)
    for _, _, lat, lng in CITIES[:3]:                       # vertical links between the layers
        x = lng + SK * lat
        ax.plot([x, x], [SY * lat - 2 * GAP, SY * lat], color=FLAMINGO, lw=1.2, alpha=0.8, zorder=5)
        ax.scatter([x] * 3, [SY * lat - 2 * GAP, SY * lat - GAP, SY * lat], s=28, color="white", zorder=6)
    allb = [skew(outline_geom, dy).bounds for _, dy in layers]
    x0, y0 = min(b[0] for b in allb), min(b[1] for b in allb)
    x1, y1 = max(b[2] for b in allb), max(b[3] for b in allb)
    cx, cy, half_w = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, (y1 - y0) * 1.5 * 0.96 / 0.9) / 2 * 1.08
    ax.set_xlim(cx - half_w, cx + half_w); ax.set_ylim(cy - half_w / 1.5 * 0.96 / 0.9, cy + half_w / 1.5 * 0.96 / 0.9)
    save_fig(fig, IMG / "pillar-indicators.webp", size=(1200, 800))

    # Tools: a choropleth on a screen, with three charts
    fig = plt.figure(figsize=(12, 8)); backdrop(fig)
    from matplotlib.patches import FancyBboxPatch
    for k in range(6, 0, -1):
        fig.patches.append(FancyBboxPatch((0.07, 0.12), 0.86, 0.78, boxstyle="round,pad=0,rounding_size=0.03", zorder=-1,
                                          transform=fig.transFigure, facecolor="none", edgecolor=SAND, lw=k * 2.5, alpha=0.05))
    fig.patches.append(FancyBboxPatch((0.07, 0.12), 0.86, 0.78, boxstyle="round,pad=0,rounding_size=0.03", zorder=-1,
                                      transform=fig.transFigure, facecolor=SURFACE, edgecolor=SAND, lw=1.6, alpha=0.92))
    ax = fig.add_axes([0.1, 0.15, 0.48, 0.72]); ax.set_axis_off()
    import mapclassify
    mpi.assign(_c=mapclassify.Quantiles(mpi["sdg1_2_mpi"], k=8).yb).plot(column="_c", cmap=site_cmap(8).reversed(),
                                                                       ax=ax, edgecolor=SURFACE, linewidth=0.2)
    d = geo.load("ntl").merge(geo.units("municipality")[["geo_id", "department_id"]], on="geo_id")
    series = d.groupby(["year"])["ln_t400NTLpc"].quantile([0.25, 0.5, 0.75]).unstack()
    for k, (y0, title) in enumerate([(0.66, "lines"), (0.43, "bars"), (0.2, "density")]):
        a = fig.add_axes([0.62, y0, 0.28, 0.18]); a.set_facecolor(RAISED)
        for s in a.spines.values(): s.set_color(EDGE)
        a.set_xticks([]); a.set_yticks([])
        if title == "lines":
            for q, c in zip(series.columns, [TURQUOISE, FLAMINGO, TURQUOISE]):
                a.plot(series.index, series[q], color=c, lw=2.2, marker="o", ms=4)
        elif title == "bars":
            pop = geo.aggregate(geo.load("pop", years=2020), to="department", dataset="pop").sort_values("pop")
            a.bar(range(9), pop["pop"], color=[ROSE if i % 3 == 2 else DEEP_TEAL for i in range(9)])
        else:
            vals = np.sort(mpi["sdg1_2_mpi"].to_numpy())
            hist, edges = np.histogram(vals, bins=30, density=True)
            a.fill_between(edges[:-1], hist, color=DEEP_TEAL, alpha=0.6); a.plot(edges[:-1], hist, color=FLAMINGO, lw=2)
    save_fig(fig, IMG / "pillar-tools.webp", size=(1200, 800))

    # Insights: a network of municipalities, glowing where lights are brightest
    fig = plt.figure(figsize=(12, 8)); backdrop(fig)
    ax = fig.add_axes([0.12, 0.04, 0.76, 0.92]); ax.set_axis_off()
    for p in getattr(outline_geom, "geoms", [outline_geom]):
        xs, ys = p.exterior.xy
        glow_line(ax, xs, ys, FLAMINGO, width=1.6, layers=8, alpha=0.06)
    pts = ntl.geometry.representative_point()
    coords = np.column_stack([pts.x, pts.y])
    knn = libpysal.weights.KNN.from_array(coords, k=4)
    for i, nbrs in knn.neighbors.items():
        for j in nbrs:
            if i < j:
                ax.plot(*zip(coords[i], coords[j]), color="#2f8f86", lw=0.6, alpha=0.5, zorder=2)
    v = ntl["ln_t400NTLpc"].to_numpy(); s = (v - v.min()) / np.ptp(v)
    for k, a in [(500, 0.04), (160, 0.12), (24, 0.9)]:
        ax.scatter(coords[:, 0], coords[:, 1], s=k * s ** 3 + 4, color="#f4d08a", alpha=a, lw=0, zorder=3)
    ax.set_aspect(1 / math.cos(math.radians(16.5)))
    save_fig(fig, IMG / "pillar-insights.webp", size=(1200, 800))


STEPS = {"hero": hero, "bands": bands, "outline": outline, "emblem": emblem, "og": og, "cards": cards, "pillars": pillars}

if __name__ == "__main__":
    targets = sys.argv[1:] or ["all"]
    for name in (list(STEPS) if targets == ["all"] else targets):
        STEPS[name]()
