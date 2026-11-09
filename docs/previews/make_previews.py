# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10"]
# ///
"""Regenerate the README previews in this folder.

    uv run docs/previews/make_previews.py

Draws a few illustrated scenes, labels them with the skill's own label_tool
(as the skill runs it), and screenshots a labelled article and the site
label component with headless Chrome. Needs ffmpeg and Google Chrome.
"""

from __future__ import annotations

import json
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SKILL = REPO / "skills" / "eu-ai-labelling"
TOOL = SKILL / "scripts" / "label_tool.py"
ICONS = SKILL / "assets" / "icons"
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

SS = 2  # supersampling for smooth edges


def tool(*args: str, cwd: Path) -> dict:
    out = subprocess.run(["uv", "run", "--quiet", str(TOOL), *args], cwd=cwd, capture_output=True, text=True)
    report = json.loads(out.stdout)
    if out.returncode:
        sys.exit(f"label_tool {' '.join(args)} failed: {report}")
    return report


# --- Scenes ---------------------------------------------------------------------


def gradient(size, top, bottom) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        c = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
        for x in range(w):
            px[x, y] = c
    return img


def ridge(rng, w, base, amp, roughness=6):
    """A mountain ridge as polygon points, from a few summed sines."""
    waves = [(rng.uniform(0.5, 1) * amp / (i + 1), rng.uniform(1, 3) * (i + 1), rng.uniform(0, 6.3)) for i in range(roughness)]
    pts = []
    for x in range(0, w + 8, 8):
        y = base - sum(a * math.sin(f * x / w * math.pi + p) for a, f, p in waves)
        pts.append((x, y))
    return pts


def lake_sunset(size=(1200, 800), seed=3) -> Image.Image:
    rng = random.Random(seed)
    w, h = size[0] * SS, size[1] * SS
    img = gradient((w, h), (196, 222, 240), (250, 214, 170))
    d = ImageDraw.Draw(img)
    sun = (int(w * 0.3), int(h * 0.5))
    # A soft glow: alpha falling off smoothly from the sun's centre.
    glow = Image.radial_gradient("L").resize((360 * SS, 360 * SS), Image.BICUBIC)
    glow = glow.point(lambda v: round(255 * max(0.0, 1 - v / 255) ** 2.2))
    img.paste((255, 236, 196), (sun[0] - 180 * SS, sun[1] - 180 * SS), glow)
    d.ellipse([sun[0] - 54 * SS, sun[1] - 54 * SS, sun[0] + 54 * SS, sun[1] + 54 * SS], fill=(255, 240, 200))
    horizon = int(h * 0.62)
    layers = [((150, 160, 190), 0.50, 90), ((110, 120, 160), 0.56, 70), ((70, 82, 120), 0.62, 50)]
    for colour, base, amp in layers:
        pts = ridge(rng, w, h * base, amp * SS)
        d.polygon(pts + [(w, horizon), (0, horizon)], fill=colour)
    # Lake: the scene above, mirrored and tinted.
    above = img.crop((0, horizon - (h - horizon), w, horizon)).transpose(Image.FLIP_TOP_BOTTOM)
    water = Image.blend(above, Image.new("RGB", above.size, (80, 110, 150)), 0.45)
    img.paste(water, (0, horizon))
    for _ in range(60):
        y = rng.randint(horizon + 4, h)
        x = rng.randint(0, w)
        d.line([(x, y), (x + rng.randint(30, 160) * SS, y)], fill=(230, 220, 210), width=SS)
    # Reeds in the foreground, bottom-left.
    for i in range(40):
        x = rng.randint(0, int(w * 0.25))
        d.line([(x, h), (x + rng.randint(-20, 20) * SS, h - rng.randint(60, 220) * SS)], fill=(40, 52, 40), width=3 * SS)
    return img.resize(size, Image.LANCZOS)


def night_city(size=(1200, 800), seed=7) -> Image.Image:
    rng = random.Random(seed)
    w, h = size[0] * SS, size[1] * SS
    img = gradient((w, h), (12, 16, 38), (48, 40, 82))
    d = ImageDraw.Draw(img)
    for _ in range(220):
        x, y, r = rng.randint(0, w), rng.randint(0, int(h * 0.6)), rng.choice((1, 1, 2)) * SS
        d.ellipse([x - r, y - r, x + r, y + r], fill=(235, 235, 255))
    moon = (int(w * 0.22), int(h * 0.22))
    d.ellipse([moon[0] - 50 * SS, moon[1] - 50 * SS, moon[0] + 50 * SS, moon[1] + 50 * SS], fill=(246, 240, 214))
    x = 0
    while x < w:
        bw = rng.randint(50, 140) * SS
        top = h - rng.randint(180, 480) * SS
        d.rectangle([x, top, x + bw, h], fill=(22, 24, 44))
        for wy in range(top + 14 * SS, h - 10 * SS, 22 * SS):
            for wx in range(x + 10 * SS, x + bw - 14 * SS, 18 * SS):
                if rng.random() < 0.35:
                    d.rectangle([wx, wy, wx + 8 * SS, wy + 10 * SS], fill=(250, 210, 120))
        x += bw + rng.randint(4, 20) * SS
    return img.resize(size, Image.LANCZOS)


def forest_light(size=(1200, 800), seed=11) -> Image.Image:
    """Dappled canopy: dark leaves and bright sky gaps everywhere, so neither
    a black nor a white icon reaches 3:1 and the label gets a backing plate."""
    rng = random.Random(seed)
    w, h = size[0] * SS, size[1] * SS
    img = gradient((w, h), (250, 252, 240), (214, 236, 200))
    d = ImageDraw.Draw(img)
    for _ in range(650):
        x, y = rng.randint(0, w), rng.randint(0, int(h * 0.75))
        r = rng.randint(8, 30) * SS
        g = rng.randint(24, 70)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(g // 3, g, g // 2))
    for i in range(7):
        x = int(w * (0.08 + i * 0.14)) + rng.randint(-30, 30) * SS
        d.rectangle([x, int(h * 0.35), x + rng.randint(18, 34) * SS, h], fill=(60, 44, 30))
    d.rectangle([0, int(h * 0.85), w, h], fill=(70, 100, 50))
    return img.resize(size, Image.LANCZOS)


# --- Composites -------------------------------------------------------------------


def font(px: int) -> ImageFont.FreeTypeFont:
    for name in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(name).exists():
            return ImageFont.truetype(name, px)
    return ImageFont.load_default()


def side_by_side(panels: list[tuple[Image.Image, str]], width: int, gap=24, caption=40) -> Image.Image:
    """Panels in a row on white, each with a caption underneath."""
    pw = (width - gap * (len(panels) + 1)) // len(panels)
    scaled = [(img.resize((pw, round(img.height * pw / img.width)), Image.LANCZOS), text) for img, text in panels]
    ph = max(s.height for s, _ in scaled)
    sheet = Image.new("RGB", (width, ph + caption + gap * 2), "white")
    d = ImageDraw.Draw(sheet)
    f = font(22)
    for i, (img, text) in enumerate(scaled):
        x = gap + i * (pw + gap)
        sheet.paste(img, (x, gap))
        tw = d.textlength(text, font=f)
        d.text((x + (pw - tw) / 2, gap + ph + 10), text, fill=(60, 60, 60), font=f)
    return sheet


# --- Pages ----------------------------------------------------------------------


def screenshot(html: Path, out: Path, size: tuple[int, int]) -> None:
    subprocess.run([CHROME, "--headless=new", "--hide-scrollbars", "--force-device-scale-factor=2",
                    f"--window-size={size[0]},{size[1]}", f"--screenshot={out}", html.as_uri()],
                   check=True, capture_output=True)


PAGE = """<!doctype html><html lang="{lang}"><meta charset="utf-8">
<style>
  body {{ margin: 0; background: #fff; color: #1d1d1b; font: 17px/1.55 -apple-system, "Helvetica Neue", Arial, sans-serif; }}
  main {{ max-width: 640px; margin: 36px auto; padding: 0 24px; }}
  h1 {{ font: 700 32px/1.2 Georgia, serif; margin: 0 0 14px; }}
  .meta {{ color: #6b6b6b; font-size: 14px; margin: 0 0 18px; }}
  img.hero {{ width: 100%; border-radius: 6px; display: block; margin: 8px 0 4px; }}
  {extra}
</style>
<main>{body}</main></html>"""


def article(work: Path, out: Path) -> None:
    doc = work / "article.html"
    doc.write_text('<html lang="it"><body><h1>x</h1></body></html>')
    label = tool("snippet", "--format", "html", "--wording", "generated", "--document", str(doc), cwd=work)["snippet"]
    body = f"""<h1>Cinque laghi alpini da vedere in autunno</h1>
{label}
<p class="meta">Viaggi · 6 minuti di lettura</p>
<p>Quando le prime nevi imbiancano le cime e i larici si accendono di arancio, i laghi alpini cambiano volto.
L'acqua si fa più ferma, i rifugi si svuotano e i sentieri tornano silenziosi.</p>
<p>Ecco cinque mete, dalla Valle d'Aosta al Trentino, raggiungibili in giornata e adatte anche a chi cammina con i bambini.</p>"""
    page = work / "article-page.html"
    page.write_text(PAGE.format(lang="it", extra="", body=body))
    screenshot(page, out, (720, 420))


# The reference implementation's own CSS, from the first html block of site.md.
SITE_CSS = ((SKILL / "references" / "site.md").read_text().split("```html", 1)[1].split("```", 1)[0]
            .split("<style>", 1)[1].split("</style>", 1)[0])


def site_component(work: Path, scene: Path, out: Path) -> None:
    shutil.copy(ICONS / "ai-basic-black.svg", work / "ai-basic-black.svg")
    shutil.copy(scene, work / "scene.png")
    body = """<h1>Alpine lakes in autumn</h1>
<img class="hero" src="scene.png" alt="An illustration of a mountain lake at sunset, generated with AI">
<span class="eu-ai-label">
  <button type="button" class="eu-ai-label__toggle" aria-expanded="true" aria-controls="eu-ai-label-details-1">
    <img class="eu-ai-label__icon" src="ai-basic-black.svg" alt="" width="32" height="32">
    <span class="eu-ai-label__text">Generated with AI</span>
  </button>
  <span class="eu-ai-label__details" id="eu-ai-label-details-1">The illustration in this article was generated with AI.</span>
</span>
<p style="margin-top:48px">When the first snow whitens the peaks, the lakes change their face.</p>"""
    page = work / "site-page.html"
    page.write_text(PAGE.format(lang="en", extra=SITE_CSS + "main { max-width: 480px; }", body=body))
    screenshot(page, out, (560, 560))


# --- Video ----------------------------------------------------------------------


def video(work: Path, out: Path) -> None:
    """A slow pan over a wide scene, labelled continuously, as an animated GIF."""
    wide = lake_sunset((1800, 600), seed=5)
    frames = work / "frames"
    frames.mkdir()
    fps, seconds = 12, 4
    for i in range(fps * seconds):
        x = round(i / (fps * seconds - 1) * (wide.width - 900))
        wide.crop((x, 0, x + 900, 600)).save(frames / f"{i:03d}.png")
    clip = work / "clip.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(fps), "-i", str(frames / "%03d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip)], check=True)
    report = tool("video-apply", "clip.mp4", "--variant", "generated", "--corner", "tr", "--visibility", "continuous", cwd=work)
    labelled = work / Path(report["labelled_copy"]).name
    palette = work / "palette.png"
    scale = "fps=12,scale=600:-1:flags=lanczos"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(labelled), "-vf", f"{scale},palettegen=max_colors=96:stats_mode=diff", str(palette)], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(labelled), "-i", str(palette),
                    "-lavfi", f"{scale}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle", str(out)], check=True)


# --- Main -----------------------------------------------------------------------


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        scenes = {"lake.png": lake_sunset(), "city.png": night_city(), "forest.png": forest_light()}
        for name, img in scenes.items():
            img.save(work / name)

        lake = tool("apply", "lake.png", "--variant", "generated", "--corner", "tr", cwd=work)
        city = tool("apply", "city.png", "--variant", "generated", "--corner", "tr", cwd=work)
        forest = tool("apply", "forest.png", "--variant", "modified", "--corner", "tr", cwd=work)
        print(json.dumps({k: {f: r[f] for f in ("colour", "plate")} for k, r in
                          (("lake", lake), ("city", city), ("forest", forest))}))

        def labelled(report):
            return Image.open(work / Path(report["labelled_copy"]).name)

        def corner(report):
            """The labelled copy's top-right corner, where the icon sits."""
            img = labelled(report)
            return img.crop((img.width // 2, 0, img.width, img.height * 3 // 8))

        side_by_side([(scenes["lake.png"], "photo.png"), (labelled(lake), "photo.ai-label.png")], 1200).save(
            HERE / "image-before-after.png", optimize=True)
        side_by_side([(corner(lake), "light sky: black icon"), (corner(city), "night sky: white icon"),
                      (corner(forest), "mixed light: backing plate")], 1200).save(HERE / "image-contrast.png", optimize=True)

        video(work, HERE / "video.gif")
        article(work, HERE / "text-article.png")
        site_component(work, work / "lake.png", HERE / "site-component.png")


if __name__ == "__main__":
    main()
