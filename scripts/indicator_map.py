"""Render a dataset's headline map for its indicator page on the website.

    uv run python scripts/indicator_map.py <dataset> [--variable V] [--year Y] [--scale S] [--name N] [--log]

Maps one variable in one year (by default the dataset's ``geo:map`` in its datapackage) in three
natural-break classes (Fisher-Jenks: Low, Middle, High) plus "No data", over a keyless basemap
whose labels are drawn above the units. Title, legend with the class ranges, data source and
basemap attribution are part of the image. Writes two WebP images:

- ``images/indicators/<name>-map.webp``: the indicator page's map (1600 x 1000)
- ``images/indicators/<name>.webp``: the indicator card (1600 x 900)

``<name>`` defaults to the dataset id. Basemap tiles and colours come from the ``site`` block
of project.yaml (defaults below). Tiles are downloaded once per run, never by the website.
"""

from __future__ import annotations

import argparse
import io
import math
from pathlib import Path

import numpy as np
from PIL import Image

import geo4bolivia as geo
from geo4bolivia import metadata

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "images/indicators"
DEFAULTS = {
    "basemap": {
        "base": "https://services.arcgisonline.com/arcgis/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        "labels": "https://services.arcgisonline.com/arcgis/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Basemap: Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community",
    },
    "colors": {"background": "#071417", "text": "#e6efee", "muted": "#a9bebb", "accent": "#5ad6c6",
               "no_data": "#5c6b6a", "classes": ["#1f8a80", "#ec8f99", "#ffd9de"]},
}
CLASSES = ["Low", "Middle", "High"]


def settings() -> dict:
    site = geo.config().get("site", {})
    return {key: {**DEFAULTS[key], **site.get(key, {})} for key in DEFAULTS}


def number(lo: float, hi: float):
    """A formatter with as many decimals as the range of the data needs."""
    span = max(abs(lo), abs(hi))
    decimals = 0 if span >= 1000 else 1 if span >= 10 else 2 if span >= 1 else 3
    return lambda v: f"{v:,.{decimals}f}".replace("-", "−")


def headline(dataset: str, variable: str | None, year: int | None, scale: str | None, log: bool | None = None):
    """The units of the scale with the variable in that year, its classes, and its metadata."""
    import mapclassify
    spec = metadata.package(dataset).get("geo:map", {})
    variable, year = variable or spec.get("variable"), year or spec.get("year")
    if not (variable and year):
        raise SystemExit(f"{dataset}: give --variable and --year, or set geo:map in its datapackage")
    res = metadata.resource(dataset, scale or spec.get("scale"))
    sid = res["geo:scale"]
    field = next(f for f in res["schema"]["fields"] if f["name"] == variable)
    data = geo.load(dataset, scale=sid, years=int(year), variables=[variable])
    gdf = geo.boundaries(sid).merge(data[["geo_id", variable]], on="geo_id", how="left")
    values = gdf[variable].dropna()
    if values.nunique() < 3:
        raise SystemExit(f"{dataset}: {variable} has fewer than 3 distinct values in {year}")
    # "classify": "log" finds the breaks on the logarithm of a skewed, positive variable
    log = spec.get("classify") == "log" if log is None else log
    if log and (values <= 0).any():
        raise SystemExit(f"{dataset}: {variable} has values <= 0, so it cannot be classified on a log scale")
    fj = mapclassify.FisherJenks(np.log(values.to_numpy()) if log else values.to_numpy(), k=3)
    gdf["_class"] = -1
    gdf.loc[values.index, "_class"] = fj.yb
    edges = [values.min(), *(np.exp(fj.bins) if log else fj.bins)]
    fmt = number(values.min(), values.max())
    legend = [(CLASSES[k], f"{fmt(edges[k])} – {fmt(edges[k + 1])}", int((fj.yb == k).sum())) for k in range(3)]
    missing = int(gdf[variable].isna().sum())
    return gdf.to_crs(3857), field, sid, int(year), legend[::-1], missing, log


def tiles(url: str, extent, zoom: int):
    import contextily as cx
    img, ext = cx.bounds2img(*extent, zoom=zoom, source=url, ll=False)
    return img, ext


def readable(labels: np.ndarray, halo: str) -> np.ndarray:
    """Basemap labels in light text on a soft dark halo, so they read on top of any class colour."""
    from PIL import ImageFilter
    im = Image.fromarray(labels).convert("RGBA")
    alpha = im.getchannel("A")
    glow = alpha.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
    out = Image.new("RGBA", im.size, halo)
    out.putalpha(glow.point(lambda v: int(v * 0.8)))
    text = Image.new("RGBA", im.size, "#f4f1e8")
    text.putalpha(alpha.point(lambda v: min(255, int(v * 1.4))))
    out.alpha_composite(text)
    return np.asarray(out)


def lines(text: str, size: float, width_px: float) -> str:
    """Wrap text to the panel width (DejaVu Sans averages about 0.6 em per character)."""
    import textwrap
    return textwrap.fill(text, max(12, int(width_px / (0.6 * size * 100 / 72))), break_on_hyphens=False)


def basemap_zoom(width_m: float) -> int:
    """The zoom at which the units span about 600 tile pixels: country-scale labels (cities,
    regions), drawn large enough to read once the image is scaled down on a page."""
    return max(1, min(16, round(math.log2(600 * 156543.03 / width_m))))


def fit_extent(gdf, box_aspect: float, pad: float = 0.08):
    """The units' bounds plus a margin, widened or heightened to the map box's shape."""
    x0, y0, x1, y1 = gdf.total_bounds
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    half_w, half_h = (x1 - x0) * (0.5 + pad), (y1 - y0) * (0.5 + pad)
    if half_w / half_h < box_aspect:
        half_w = half_h * box_aspect
    else:
        half_h = half_w / box_aspect
    return cx - half_w, cy - half_h, cx + half_w, cy + half_h


def draw_map(ax, gdf, extent, cfg) -> None:
    """Basemap, the classes, and the basemap's labels on top."""
    col = cfg["colors"]
    ax.set_axis_off()
    x0, _, x1, _ = gdf.total_bounds
    zoom = basemap_zoom(x1 - x0)
    base, ext = tiles(cfg["basemap"]["base"], extent, zoom)
    ax.imshow(base, extent=ext, interpolation="lanczos", zorder=0)
    nodata = gdf[gdf["_class"] < 0]
    if len(nodata):
        nodata.plot(ax=ax, facecolor="none", edgecolor=col["no_data"], hatch="////", linewidth=0.3, zorder=1)
    for k in range(3):
        gdf[gdf["_class"] == k].plot(ax=ax, color=col["classes"][k], alpha=0.8, edgecolor=col["background"],
                                     linewidth=0.25, zorder=2)
    labels, ext = tiles(cfg["basemap"]["labels"], extent, zoom)
    ax.imshow(readable(labels, col["background"]), extent=ext, interpolation="lanczos", zorder=3)
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])


def legend_handles(legend, missing, cfg):
    from matplotlib.patches import Patch
    col = cfg["colors"]
    handles = [Patch(facecolor=col["classes"][2 - i], edgecolor="none", label=f"{name}   {rng}   (n = {n})")
               for i, (name, rng, n) in enumerate(legend)]
    if missing:
        handles.append(Patch(facecolor="none", edgecolor=col["no_data"], hatch="////",
                             label=f"No data   (n = {missing})"))
    return handles


def style_legend(leg, cfg, has_title: bool) -> None:
    for t in leg.get_texts():
        t.set_color(cfg["colors"]["text"])
    if has_title:
        leg.get_title().set_color(cfg["colors"]["muted"])


def texts(field, dataset, sid, year, cfg):
    scale_label = geo.scales().loc[sid, "label"]
    source = field.get("geo:source")
    return {
        "code": f'geo.load("{dataset}")',
        "title": f"{field.get('title', field['name'])}, {year}",
        "subtitle": metadata.package(dataset)["title"],
        "units": f"units: {scale_label}",
        "method": "Fisher–Jenks natural breaks" + (", log scale" if cfg.get("log") else ""),
        "source": f"Data: {source}" if source else "",
        "credit": cfg["basemap"]["attribution"],
        "site": f"{geo.config()['short_name']} · {geo.config().get('website', '')}",
        "unit": field.get("geo:unit") or None,
    }


def draw(gdf, field, dataset, sid, year, legend, missing, cfg, w=1600, h=900):
    """The map on the left, title and legend on the right: 1600 x 1000 for the indicator
    page (shown across the page), 1600 x 900 for the card."""
    import matplotlib.pyplot as plt
    col, t = cfg["colors"], texts(field, dataset, sid, year, cfg)
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100, facecolor=col["background"])
    map_w = 0.58
    ax = fig.add_axes([0, 0, map_w, 1])
    draw_map(ax, gdf, fit_extent(gdf, map_w * w / h), cfg)
    x, panel, y = map_w + 0.035, (1 - map_w - 0.07) * w, 1 - 90 / h

    def block(text, size, gap=0.5, **kw):
        nonlocal y
        text = lines(text, size, panel)
        fig.text(x, y, text, fontsize=size, va="top", linespacing=1.25, **kw)
        y -= (text.count("\n") + 1) * 1.25 * size * (100 / 72) / h + gap * size * (100 / 72) / h

    block(t["code"], 15, 0.9, color=col["accent"], family="DejaVu Sans Mono")
    block(t["title"], 29, 0.45, color="white", weight="bold")
    block(t["subtitle"], 18, 0.7, color=col["muted"])
    block(f"{len(gdf)} {t['units']}", 14, 0.2, color=col["muted"])
    block(f"Three classes: {t['method']}", 14, 1.4, color=col["muted"])
    leg = fig.legend(handles=legend_handles(legend, missing, cfg), loc="upper left",
                     bbox_to_anchor=(x - 0.008, y + 0.01), frameon=False, fontsize=17, handlelength=1.6,
                     handleheight=1.3, labelspacing=0.8, title=lines(t["unit"], 14, panel) if t["unit"] else None,
                     title_fontsize=14, alignment="left")
    style_legend(leg, cfg, bool(t["unit"]))
    foot = [lines(s, 11.5, panel) for s in (t["source"], t["credit"]) if s] + [t["site"]]
    fig.text(x, 0.045, "\n".join(foot), fontsize=11.5, color=col["muted"], va="bottom", linespacing=1.5)
    return fig


def render(fig) -> Image.Image:
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    fig.savefig(buf, dpi=100, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    return Image.open(buf).convert("RGB")


def save_webp(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "WEBP", quality=86, method=6)
    print(f"  wrote {path.relative_to(ROOT)}  {img.size[0]}x{img.size[1]}  {path.stat().st_size / 1e3:.0f} kB")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dataset")
    ap.add_argument("--variable")
    ap.add_argument("--year", type=int)
    ap.add_argument("--scale")
    ap.add_argument("--name", help="image file name (default: the dataset id)")
    ap.add_argument("--log", action="store_true", help="find the breaks on a log scale (skewed variables)")
    args = ap.parse_args()
    cfg = settings()
    gdf, field, sid, year, legend, missing, log = headline(args.dataset, args.variable, args.year, args.scale,
                                                           True if args.log else None)
    cfg["log"] = log
    name = args.name or args.dataset
    import matplotlib
    matplotlib.use("Agg")
    for (w, h), path in [((1600, 1000), OUT / f"{name}-map.webp"), ((1600, 900), OUT / f"{name}.webp")]:
        save_webp(render(draw(gdf, field, args.dataset, sid, year, legend, missing, cfg, w, h)), path)
    # facts for the image's alt text
    top = gdf.dropna(subset=[field["name"]]).nlargest(3, field["name"])["name"].tolist()
    print(f"  classes (High→Low): {legend}; no data: {missing}; highest: {', '.join(top)}")


if __name__ == "__main__":
    main()
