#!/usr/bin/env python3
"""Build index.html from content/portfolio-input.md, following content/DESIGN.md.

Usage:  python tools/build_site.py

Standard library only. Writes index.html and the obfuscated 3D model files
(assets/models/<slug>/<slug>.bin). The CSS and JS in assets/ are hand-written and
never touched here. Re-run it after any edit to the input file.
"""
from __future__ import annotations

import base64
import datetime as _dt
import html
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "content" / "portfolio-input.md"
OUTPUT = ROOT / "index.html"
SITE_URL = "https://lorenzodallarosa.com/"
THREE_VERSION = "0.169.0"
KATEX_VERSION = "0.16.11"
MODEL_KEY = b"ldr-stage-7f3a91"  # XOR key shared with assets/js/stage-core.js

# 3D stage set-up per project: camera orientation, preset overrides and callouts (DESIGN.md
# section 0). Top views look straight down; the aircraft's camera sits on the nose side so the
# wings lie horizontal, and an optional 4th value scales the camera distance for that view.
# "node" matches mesh names in the .glb; "bias" moves the anchor by fractions of the
# part's half-size, "dy" offsets the label vertically in pixels.
# "hoverCallouts" shows the callouts only while the stage is hovered; "carbon" overrides the
# carbon-fibre finish (see tuneMaterial in assets/js/stage-core.js).
AIRCRAFT_TOP = {"top": [-0.002, 1, 0, 1.45]}
STAGES = {
    "et-18-aero-package": {
        "rotateY": 180, "smooth": 40, "fit": 0.75, "hoverCallouts": True,
        "carbon": {"roughness": 0.9, "clearcoat": 0.45, "clearcoatRoughness": 0.38, "envMapIntensity": 1.0},
        "callouts": [
            {"node": "L18_AE_flap", "label": "Adjustable flaps", "tone": "orange", "bias": [0, 0.5, 0.75], "dy": -90},
            {"node": "L18_AE_FW_Endplate", "label": "Footplate", "tone": "ink", "bias": [0, -0.7, 0.9], "dy": 80},
            {"node": "L18_AE_Fairing", "label": "Flow diverters", "tone": "ink", "bias": [-0.5, 0.6, 0.95], "dy": -60},
            {"node": "L18_AE_Undertray", "label": "Venturi-style undertray", "tone": "ink", "bias": [0, -0.3, 0.9], "dy": 90},
            {"node": "L18_AE_RW_Flap", "label": "Low-drag configuration", "tone": "orange", "bias": [0, 0.6, 0.5], "dy": -70}]},
    "caelus-one": {"rotateY": 180, "views": AIRCRAFT_TOP, "callouts": [
        {"node": "Alerons", "label": "Flaperons", "tone": "powder", "bias": [0, 0, 0.6], "dy": 70},
        {"node": "Fuselage", "label": "Full carbon-fibre monocoque", "tone": "bone", "bias": [-0.72, -0.5, 0], "dy": -110},
        {"node": "Payload", "label": "Payload fairing", "tone": "orange", "dy": 90}]},
    "caelus-baff-1": {"views": AIRCRAFT_TOP, "callouts": [
        {"node": "Tail_Body", "label": "A-tail pusher", "tone": "orange"},
        {"node": "R_DBox", "label": "D-box wing · leading-edge spar", "tone": "bone", "bias": [-0.6, 0.3, 0.45], "dy": 120},
        {"node": "R_flap", "label": "Split flaps · flaperons", "tone": "powder", "bias": [0.6, 0, 0.8], "dy": 40}]},
}


# --------------------------------------------------------------------------- utils

def esc(s: str) -> str:
    return html.escape(s, quote=True)


def clean(value: str) -> str:
    """Strip the [ ] wrapper; '[]' becomes ''."""
    v = value.strip()
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1].strip()
    return v


def split_top(s: str, sep: str = ",") -> list[str]:
    """Split on sep, ignoring separators inside parentheses."""
    out, depth, cur = [], 0, ""
    for ch in s:
        depth += ch == "("
        depth -= ch == ")"
        if ch == sep and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def pairs(value: str) -> list[tuple[str, str]]:
    """'a | b ; c | d' -> [(a, b), (c, d)]."""
    out = []
    for chunk in value.split(";"):
        if chunk.strip():
            left, _, right = chunk.partition("|")
            out.append((left.strip(), right.strip()))
    return out


def image_size(path: Path) -> tuple[int, int] | None:
    """Width and height of a PNG or JPEG, read from its header."""
    try:
        data = path.read_bytes()[: 256 * 1024]
    except OSError:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        length = struct.unpack(">H", data[i + 2 : i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 5 : i + 9])
            return w, h
        i += 2 + length
    return None


# ------------------------------------------------------------------------ markdown

MATH = re.compile(r"\$(.+?)\$")


def _emphasis(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<em>\1</em>", s)


def inline(s: str) -> str:
    """Escape, render **bold** / *italic*, and mark $tex$ for KaTeX."""
    out, pos = [], 0
    for m in MATH.finditer(s):
        out.append(_emphasis(esc(s[pos : m.start()])))
        out.append(f'<span class="math">{esc(m.group(1))}</span>')
        pos = m.end()
    out.append(_emphasis(esc(s[pos:])))
    return "".join(out)


def md(text: str) -> str:
    """Paragraphs and '- ' bullet lists, which is all the input file uses."""
    blocks, para, items = [], [], []

    def flush():
        if para:
            blocks.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()
        if items:
            blocks.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")
            items.clear()

    for line in text.splitlines():
        s = line.strip()
        if not s:
            flush()
        elif s.startswith("- "):
            if para:
                flush()
            items.append(s[2:])
        else:
            if items:
                flush()
            para.append(s)
    flush()
    return "\n".join(blocks)


# -------------------------------------------------------------------------- parser

KEY = re.compile(r"^([A-Z][A-Za-z ]*):\s*(.*)$")


def parse(path: Path) -> dict:
    raw = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    d: dict = {
        "site": {}, "profile": {}, "about": [], "skills": {}, "experience": [], "education": [],
        "activities": [], "projects": [], "groups": [], "software": [], "publications": [],
        "awards": [], "extras": {},
    }
    h1 = h2 = None
    cur = None
    in_details = False

    for line in raw.splitlines():
        if line.startswith("# "):
            h1, h2, cur, in_details = line[2:].strip().upper(), None, None, False
            continue
        if line.startswith("## "):
            h2, cur, in_details = line[3:].strip(), None, False
            if h1 == "EXTRAS":
                d["extras"][h2] = []
            continue
        if line.startswith("### "):
            title, in_details = line[4:].strip(), False
            if h1 in ("EXPERIENCE", "EDUCATION", "ACTIVITIES"):
                role, _, org = title.partition("|")
                cur = {"title": role.strip(), "org": org.strip(), "bullets": []}
                d[h1.lower()].append(cur)
            elif h1 in ("PROJECTS", "GROUPS"):
                cur = {"title": title, "details": []}
                d[h1.lower()].append(cur)
            continue

        s = line.strip()
        key = KEY.match(s)

        if h1 in ("SITE", "PROFILE") and h2 is None and key:
            d[h1.lower()][key.group(1)] = clean(key.group(2))
        elif h1 == "PROFILE" and h2 == "About":
            d["about"].append(line)
        elif h1 == "PROFILE" and h2 == "Skills" and s.startswith("- "):
            k, _, v = s[2:].partition(":")
            d["skills"][k.strip()] = split_top(clean(v))
        elif h1 in ("EXPERIENCE", "EDUCATION", "ACTIVITIES") and cur is not None:
            if s.startswith("- "):
                cur["bullets"].append(s[2:])
            elif key:
                cur[key.group(1).lower()] = clean(key.group(2))
        elif h1 in ("PROJECTS", "GROUPS") and cur is not None:
            if in_details:
                cur["details"].append(line)
            elif s == "Details:":
                in_details = True
            elif key:
                cur[key.group(1).lower().replace(" ", "_")] = clean(key.group(2))
        elif h1 == "SOFTWARE" and s.startswith("- "):
            f = [p.strip() for p in s[2:].split("|")] + ["", ""]
            uses = [u.strip() for u in f[2].split(",") if u.strip()]
            d["software"].append({"name": f[0], "what": f[1], "uses": uses})
        elif h1 == "PUBLICATIONS" and s.startswith("- "):
            v = clean(s[2:])
            if v and not v.startswith("Authors,"):
                d["publications"].append(v)
        elif h1 == "AWARDS AND CERTIFICATIONS" and s.startswith("- "):
            f = [p.strip() for p in s[2:].split("|")] + [""] * 5
            d["awards"].append(dict(zip(("title", "issuer", "date", "desc", "image"), f)))
        elif h1 == "EXTRAS" and h2:
            d["extras"][h2].append(line)

    d["about"] = "\n".join(d["about"]).strip()
    for p in d["projects"]:
        p["details"] = "\n".join(p["details"]).strip()
    d["extras"] = {k: "\n".join(v).strip() for k, v in d["extras"].items() if "\n".join(v).strip()}
    return d


def split_details(details: str) -> tuple[str, list[dict]]:
    """Intro text and '#### Title' steps, each with its body text and Image: lines."""
    parts = re.split(r"^#### +(.+)$", details, flags=re.M)
    intro, steps = parts[0].strip(), []
    for title, body in zip(parts[1::2], parts[2::2]):
        images, lines = [], []
        for line in body.splitlines():
            m = re.match(r"^\s*Image:\s*(.+)$", line)
            if m:
                file, _, cap = m.group(1).partition("|")
                images.append((file.strip(), cap.strip()))
            else:
                lines.append(line)
        steps.append({"title": title.strip(), "body": "\n".join(lines).strip(), "images": images})
    return intro, steps


# ------------------------------------------------------------------------ helpers

def corner_ticks() -> str:
    return '<span class="tick tl"></span><span class="tick tr"></span><span class="tick bl"></span><span class="tick br"></span>'


def mask(text: str, i: int = 0) -> str:
    return f'<span class="mask"><span class="mask-in" style="--i:{i}">{text}</span></span>'


def img_path(slug: str, file: str) -> str:
    return f"assets/img/projects/{file}" if "/" in file else f"assets/img/projects/{slug}/{file}"


def img_tag(rel: str, alt: str, cls: str = "", lazy: bool = True) -> str:
    size = image_size(ROOT / rel)
    wh = f' width="{size[0]}" height="{size[1]}"' if size else ""
    lz = ' loading="lazy" decoding="async"' if lazy else ""
    c = f' class="{cls}"' if cls else ""
    return f'<img src="{esc(rel)}" alt="{esc(alt)}"{wh}{lz}{c}>'


PENDING: list[str] = []  # image files named in the input but missing on disk (for the report)


def placeholder(file: str, title: str, ratio: str = "4 / 3") -> str:
    PENDING.append(file)
    return (f'<div class="ph" role="img" aria-label="Image pending for {esc(title)}" style="aspect-ratio:{ratio}">'
            f'{corner_ticks()}<span class="t-label">Image pending · {esc(file.split("/")[-1])}</span></div>')


def figure(slug: str, file: str, caption: str, title: str, cls: str = "fig") -> str:
    rel = img_path(slug, file)
    if (ROOT / rel).is_file():
        body = img_tag(rel, caption or title)
        size = image_size(ROOT / rel)
        if size and size[0] >= 1.9 * size[1]:
            cls += " fig--wide"  # wide plots and strips take the full row
    else:
        body = placeholder(rel.replace("assets/img/projects/", ""), f"{title}: {caption}" if caption else title)
    cap = f'<figcaption class="t-cap">{esc(caption)}</figcaption>' if caption else ""
    return f'<figure class="{cls}"><div class="fig-frame">{body}{corner_ticks()}</div>{cap}</figure>'


def spec_row(facts: list[tuple[str, str]], cls: str = "") -> str:
    cells = "".join(f'<div class="spec"><dt class="t-label">{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k, v in facts if v)
    return f'<dl class="specs {cls}">{cells}</dl>' if cells else ""


def project_facts(p: dict) -> list[tuple[str, str]]:
    return [("Role", p.get("role", "")), ("Year", p.get("year", ""))] + pairs(p.get("facts", ""))


def links_html(p: dict) -> str:
    """Project links. A PDF becomes a card with a preview of its first page, when
    assets/img/projects/<slug>/<pdf name>.jpg exists (rendered once, title area only)."""
    links = pairs(p.get("links", ""))
    if not links:
        return ""
    items = []
    for label, url in links:
        if url.lower().endswith(".pdf"):
            thumb = f"assets/img/projects/{p['slug']}/{Path(url).stem}.jpg"
            prev = f'<span class="doc-thumb">{img_tag(thumb, "")}</span>' if (ROOT / thumb).is_file() else ""
            items.append(f'<a class="doc-card" href="{esc(url)}" target="_blank" rel="noopener">{prev}'
                         f'<span class="doc-meta"><span class="doc-label">{esc(label)}</span>'
                         f'<span class="doc-open t-label">Open PDF ↗</span></span></a>')
        else:
            items.append(f'<a class="t-label" href="{esc(url)}">{esc(label)}</a>')
    return f'<div class="proj-links">{"".join(items)}</div>'


def tags_of(p: dict) -> list[str]:
    return [t.strip() for t in p.get("tags", "").split(",") if t.strip()]


def has_model(slug: str) -> bool:
    return (ROOT / f"assets/models/{slug}/{slug}.glb").is_file() or (ROOT / f"assets/models/{slug}/{slug}.bin").is_file()


def obfuscate_models() -> None:
    """Write assets/models/<slug>/<slug>.bin, the XOR-obfuscated copy the site loads."""
    for glb in sorted((ROOT / "assets/models").glob("*/*.glb")):
        out = glb.with_suffix(".bin")
        if out.is_file() and out.stat().st_mtime >= glb.stat().st_mtime:
            continue
        data = bytearray(glb.read_bytes())
        k = MODEL_KEY
        for i in range(len(data)):
            data[i] ^= k[i % len(k)]
        out.write_bytes(bytes(data))
        print(f"obfuscated {glb.relative_to(ROOT)} -> {out.name}")


def b64r(s: str) -> str:
    return base64.b64encode(s[::-1].encode()).decode()


# ----------------------------------------------------------------------- sections

class Page:
    def __init__(self, data: dict):
        self.d = data
        self.year = _dt.date.today().year
        self.by_slug = {p.get("slug"): p for p in data["projects"]}
        self.groups = {g.get("slug"): g for g in data["groups"]}
        self.sections: list[tuple[str, str]] = []  # (id, counter name), filled in build()
        self.needs_math = "$" in "".join(p["details"] + p.get("summary", "") for p in data["projects"])

    def no(self, sid: str) -> str:
        return f"{[i for i, _ in self.sections].index(sid) + 1:02d}"

    # ---- steps: numbered, expandable rows (DESIGN.md section 0, "Steps")
    def steps(self, p: dict, open_all: bool = False) -> str:
        intro, steps = split_details(p["details"])
        rows = []
        for i, st in enumerate(steps, 1):
            figs = "".join(figure(p["slug"], f, c, p["title"]) for f, c in st["images"])
            figs_html = f'<div class="step-figs">{figs}</div>' if figs else ""
            body = f'<div class="step-body"><div class="prose">{md(st["body"])}</div>{figs_html}</div>'
            if open_all:
                rows.append(f'<section class="step step--flat"><h4 class="step-head"><span class="t-index">{i:02d}</span>'
                            f'<span class="step-t">{inline(st["title"])}</span></h4>{body}</section>')
            else:
                rows.append(f'<details class="step"><summary class="step-head"><span class="t-index">{i:02d}</span>'
                            f'<span class="step-t">{inline(st["title"])}</span><span class="step-plus" aria-hidden="true"></span>'
                            f'</summary>{body}</details>')
        intro_html = f'<div class="prose proj-intro t-lead">{md(intro)}</div>' if intro else ""
        list_html = f'<div class="steps">{"".join(rows)}</div>' if rows else ""
        return intro_html + list_html

    # ---- photo gallery from "Images:", collapsed until opened
    def gallery(self, p: dict) -> str:
        shots = pairs(p.get("images", ""))
        if not shots:
            return ""
        figs = "".join(figure(p["slug"], f, c, p["title"], "fig gallery-fig") for f, c in shots)
        return (f'<details class="step gallery"><summary class="step-head"><span class="t-index">+</span>'
                f'<span class="step-t">Gallery <span class="t-label gallery-n">{len(shots)} photos</span></span>'
                f'<span class="step-plus" aria-hidden="true"></span></summary><div class="gallery-grid">{figs}</div></details>')

    # ---- 3D stage
    def stage(self, p: dict, theme: str, micro: str = "") -> str:
        slug = p["slug"]
        cfg = {"theme": theme, "models": [{
            "key": slug, "src": f"assets/models/{slug}/{slug}.bin",
            "poster": img_path(slug, p.get("cover_image", "")), **STAGES.get(slug, {})}]}
        poster_rel = img_path(slug, p.get("cover_image", ""))
        poster = img_tag(poster_rel, f"{p['title']}", "stage-poster", lazy=False) if (ROOT / poster_rel).is_file() else ""
        return f"""
      <figure class="stage stage--{theme}" data-stage aria-label="{esc(p['title'])}: interactive 3D model, drag to rotate">
        <div class="stage-box">
          {poster}
          <div class="stage-gl" aria-hidden="true"></div>
          <div class="stage-callouts" aria-hidden="true"></div>
          {corner_ticks()}
          <span class="stage-micro t-label">{esc(micro)}</span>
          <p class="stage-hint t-label" aria-hidden="true">Drag to rotate · Ctrl + scroll to zoom</p>
          <button class="stage-tap t-label" type="button">Tap to load 3D</button>
          <div class="stage-ui">
            <div class="presets" role="group" aria-label="Camera views">
              <button type="button" class="t-label" data-view="three">3/4</button>
              <button type="button" class="t-label" data-view="side">Side</button>
              <button type="button" class="t-label" data-view="front">Front</button>
              <button type="button" class="t-label" data-view="top">Top</button>
            </div>
          </div>
        </div>
        <script type="application/json" class="stage-cfg">{json.dumps(cfg)}</script>
      </figure>"""

    def head(self, p: dict, crumb: str, number: str, level: int = 2) -> str:
        short = p.get("short") or p["title"]
        kicker = f'<p class="proj-kicker">{esc(p["kicker"])}</p>' if p.get("kicker") else ""
        statement = p.get("statement") or p.get("summary", "")
        tag = f"h{level}"
        return f"""
      <div class="proj-head">
        <p class="t-label crumb">{esc(crumb)}</p>
        <p class="t-label proj-no"><span class="sq"></span> No.{number} <span class="proj-tags">{esc(' / '.join(tags_of(p)[:3]))}</span></p>
        {kicker}
        <{tag} class="t-h1 proj-title" aria-label="{esc(p['title'])}">{mask(esc(short))}</{tag}>
        <p class="t-h2 proj-statement rise">{inline(statement)}</p>
      </div>"""

    # ---- 1. intro
    def intro(self) -> str:
        pr, site = self.d["profile"], self.d["site"]
        first, _, last = pr["Name"].partition(" ")
        insts = []
        for e in self.d["education"]:
            if e["org"] not in [i[0] for i in insts]:
                insts.append((e["org"], e.get("link", "")))
        inst_html = " / ".join(f'<a href="{esc(u)}" rel="noopener">{esc(o)}</a>' if u else esc(o) for o, u in insts)
        photo = f"assets/img/profile/{pr.get('Photo', '')}"
        portrait = (f'<figure class="intro-portrait rise"><div class="fig-frame">{img_tag(photo, "Portrait of " + pr["Name"], "portrait", lazy=False)}'
                    f'{corner_ticks()}</div></figure>') if (ROOT / photo).is_file() else ""
        greet = f'<p class="intro-greet">{mask(esc(site["Greeting"]))}</p>' if site.get("Greeting") else ""
        return f"""
<section id="top" class="intro" data-theme="light" data-name="Intro">
  <div class="wrap intro-grid">
    <div class="intro-text">
      <p class="t-label intro-tag mask"><span class="mask-in">{esc(site.get('Tag line', ''))}</span></p>
      {greet}
      <h1 class="t-h1 intro-name">{mask(esc(first))}{mask(esc(last), 1)}</h1>
      <p class="t-h2 intro-role rise">{esc(pr.get('Role', ''))}</p>
      <p class="t-label intro-loc rise"><span class="sq"></span> {esc(pr.get('Location', ''))}<br>{inst_html}</p>
    </div>
    {portrait}
  </div>
</section>"""

    # ---- big project body (used standalone and inside groups)
    def big(self, p: dict, theme: str, crumb: str, number: str, flip: bool = False, level: int = 2) -> str:
        cover_rel = img_path(p["slug"], p.get("cover_image", ""))
        model = has_model(p["slug"])
        if theme == "paper":
            # Photo is the hero image; the 3D model follows as its own band.
            hero_img = figure(p["slug"], p.get("cover_image", ""), "", p["title"], "fig hero-photo") if p.get("cover_image") else ""
            stage_band = f'<div class="stage-band">{self.stage(p, theme, micro=p.get("short", ""))}</div>' if model else ""
            hero = f'<div class="hero">{self.head(p, crumb, number, level)}{hero_img}</div>{stage_band}'
        else:
            visual = self.stage(p, theme, micro=p.get("short", "")) if model else (
                figure(p["slug"], p.get("cover_image", ""), "", p["title"], "fig hero-photo") if (ROOT / cover_rel).is_file() else "")
            hero = f'<div class="hero{" hero--flip" if flip else ""}">{self.head(p, crumb, number, level)}{visual}</div>'
        return f"""
    {hero}
    <div class="proj-body">
      {spec_row(project_facts(p), "rise")}
      <div class="proj-steps">{self.steps(p)}{self.gallery(p)}{links_html(p)}</div>
    </div>"""

    # ---- 2. ET-18
    def et18(self) -> str:
        p = self.by_slug["et-18-aero-package"]
        sid = p["slug"]
        return f"""
<section id="{sid}" class="proj proj--big" data-theme="paper" data-name="{esc(p.get('short', ''))}">
  <div class="wrap">{self.big(p, "paper", f"Projects › {p.get('short', '')}", self.no(sid))}
  </div>
</section>"""

    # ---- 3. Caelus group
    def caelus(self) -> str:
        g = self.groups["caelus"]
        members = [p for p in self.d["projects"] if p.get("group") == "caelus" and p.get("tier")]
        n = self.no("caelus")
        blocks, flip = [], False
        for i, p in enumerate(members, 1):
            num = f"{n}.{i}"
            if p["tier"] == "compact":
                cover = figure(p["slug"], p["cover_image"], "", p["title"], "fig compact-fig") if p.get("cover_image") else ""
                blocks.append(f"""
    <article id="{p['slug']}" class="compact rise">
      <div class="compact-text">
        <p class="t-label proj-no"><span class="sq"></span> No.{num} <span class="proj-tags">{esc(' / '.join(tags_of(p)[:3]))}</span></p>
        <h3 class="compact-title">{esc(p.get('short') or p['title'])}<span class="compact-year t-label">{esc(p.get('year', ''))}</span></h3>
        <p class="t-lead">{inline(p.get('summary', ''))}</p>
        {spec_row(project_facts(p))}
        <div class="prose">{md(p['details'])}</div>
      </div>
      {cover}
    </article>""")
            else:
                blocks.append(f"""
    <article id="{p['slug']}" class="sub-proj">
      {self.big(p, "dark", f"Projects › Caelus › {p.get('short', '')}", num, flip, level=3)}
    </article>""")
                flip = not flip
        return f"""
<section id="caelus" class="proj proj--group" data-theme="dark" data-name="Caelus">
  <div class="wrap">
    <header class="group-head">
      <p class="t-label crumb">Projects › Caelus</p>
      <p class="t-label proj-no"><span class="sq"></span> No.{n} <span class="proj-tags">{esc(' / '.join(tags_of(g)[:3]))}</span></p>
      <h2 class="t-h1 proj-title" aria-label="{esc(g['title'])}">{mask('Caelus')}</h2>
      <p class="t-h2 proj-statement rise">{inline(g.get('summary', ''))}</p>
    </header>
    {''.join(blocks)}
  </div>
</section>"""

    # ---- 4. Smaller projects
    def smaller(self) -> str:
        small = [p for p in self.d["projects"] if p.get("tier") == "small"]
        sid = "more-projects"
        title = self.d["site"].get("Projects title") or "Projects"
        cards, panels = [], []
        for i, p in enumerate(small, 1):
            slug = p["slug"]
            cover = figure(slug, p["cover_image"], "", p["title"], "fig card-fig") if p.get("cover_image") else placeholder(f"{slug}/cover", p["title"])
            facts = [("Type", p.get("type", "")), ("Year", p.get("year", ""))] + pairs(p.get("facts", ""))[:1]
            cards.append(f"""
      <li class="card rise">
        <button class="card-btn" type="button" aria-expanded="false" aria-controls="panel-{slug}" data-panel="{slug}">
          {cover}
          <span class="t-index">{i:02d}</span>
          <span class="card-title">{esc(p['title'])}</span>
          {f'<span class="card-course t-label">{esc(p["course"])}</span>' if p.get("course") else ""}
          <span class="card-sum">{inline(p.get('summary', ''))}</span>
          <span class="card-more t-label">Open project</span>
        </button>
        {spec_row(facts, "card-specs")}
      </li>""")
            panels.append(f"""
    <article class="panel" id="panel-{slug}" data-slug="{slug}" aria-labelledby="h-{slug}">
      <span id="{slug}" class="anchor"></span>
      <div class="panel-head">
        <p class="t-label proj-no"><span class="sq"></span> {i:02d} <span class="proj-tags">{esc(' / '.join(tags_of(p)[:4]))}</span></p>
        <h3 class="panel-title" id="h-{slug}">{esc(p['title'])}</h3>
        {f'<p class="panel-course">{esc(p["course"])}</p>' if p.get("course") else ""}
        <p class="t-lead">{inline(p.get('summary', ''))}</p>
        {spec_row(project_facts(p))}
        {links_html(p)}
        <button class="panel-close t-label" type="button" data-close>Close</button>
      </div>
      <div class="panel-body">{self.steps(p)}</div>
    </article>""")
        return f"""
<section id="{sid}" class="smaller" data-theme="sage" data-name="{esc(title)}">
  <div class="wrap">
    <p class="t-label crumb">Projects › {esc(title)}</p>
    <p class="t-label proj-no"><span class="sq"></span> No.{self.no(sid)} <span class="proj-tags">Academic · Thesis · Industry · Competition</span></p>
    <h2 class="t-h1 proj-title">{"".join(mask(esc(w), i) for i, w in enumerate(title.split()))}</h2>
    <ul class="cards">{''.join(cards)}</ul>
    <div class="panels">{''.join(panels)}</div>
  </div>
</section>"""

    # ---- 5. CV
    def cv(self) -> str:
        d, pr = self.d, self.d["profile"]
        sid = "cv"

        def entry(e: dict, kind: str) -> str:
            org = esc(e["org"])
            if e.get("link"):
                org = f'<a href="{esc(e["link"])}" rel="noopener">{org}</a>'
            meta = " · ".join(esc(x) for x in (e.get("dates", ""), e.get("location", "")) if x)
            rows = []
            if e.get("grade"):
                rows.append(("Grade", e["grade"]))
            if e.get("thesis"):
                rows.append(("Thesis", e["thesis"]))
            facts = spec_row(rows)
            hl = f'<p>{inline(e["highlights"])}</p>' if e.get("highlights") else ""
            # "Coursework: ..." gets its own highlighted line; other bullets stay a list.
            course = "".join(f'<p class="cv-course"><span class="t-label">Coursework</span><span>{inline(b.split(":", 1)[1].strip())}</span></p>'
                             for b in e["bullets"] if b.startswith("Coursework:"))
            rest = [b for b in e["bullets"] if not b.startswith("Coursework:")]
            bullets = ("<ul>" + "".join(f"<li>{inline(b)}</li>" for b in rest) + "</ul>" if rest else "") + course
            return f"""
        <li class="cv-row rise">
          <p class="cv-dates t-label">{meta}</p>
          <div class="cv-main">
            <h4 class="cv-title">{esc(e['title'])}</h4>
            <p class="cv-org">{org}</p>
            {facts}
            <div class="prose">{hl}{bullets}</div>
          </div>
        </li>"""

        edu_now = [e for e in d["education"] if e.get("status", "").lower().startswith("in progress")]
        edu_done = [e for e in d["education"] if e not in edu_now]
        about = md(d["about"])
        cv_file = pr.get("CV file", "")
        cv_link = (f'<a class="btn" href="assets/docs/{esc(cv_file)}" download>Download CV · PDF</a>'
                   if cv_file and (ROOT / "assets/docs" / cv_file).is_file() else "")
        def skill(k: str, vals: list[str]) -> str:
            if k == "Languages":
                rows = ""
                for v in vals:
                    m = re.match(r"(.+?)\s*\((.+)\)$", v)
                    name, level = (m.group(1), m.group(2)) if m else (v, "")
                    rows += f'<div class="lang"><dt>{esc(name)}</dt><dd class="t-label">{esc(level)}</dd></div>'
                return f'<div class="skill skill--lang"><h4 class="t-label">{esc(k)}</h4><dl>{rows}</dl></div>'
            return f'<div class="skill"><h4 class="t-label">{esc(k)}</h4><ul>{"".join(f"<li>{esc(v)}</li>" for v in vals)}</ul></div>'

        skills = "".join(skill(k, vals) for k, vals in d["skills"].items() if vals)
        extras = "".join(f'<div class="skill"><h4 class="t-label">{esc(k)}</h4><div class="prose">{md(v)}</div></div>'
                         for k, v in d["extras"].items())

        def block(title: str, items: list[dict], kind: str) -> str:
            if not items:
                return ""
            return (f'<div class="cv-block"><h3 class="cv-h t-label"><span class="sq"></span> {esc(title)}</h3>'
                    f'<ol class="cv-list">{"".join(entry(e, kind) for e in items)}</ol></div>')

        return f"""
<section id="{sid}" class="cv" data-theme="light" data-name="CV">
  <div class="wrap">
    <p class="t-label crumb">CV</p>
    <p class="t-label proj-no"><span class="sq"></span> No.{self.no(sid)} <span class="proj-tags">Curriculum vitae</span></p>
    <h2 class="t-h1 proj-title">{mask('About')}</h2>
    <div class="cv-top">
      <div class="prose cv-about rise">{about}</div>
      <div class="cv-actions rise">{cv_link}</div>
    </div>
    <div class="cv-card">
      {block('Education · in progress', edu_now, 'edu')}
      {block('Education · completed', edu_done, 'edu')}
      {block('Experience', d['experience'], 'exp')}
      {block('Activities', d['activities'], 'act')}
      {self.awards()}
      <div class="cv-block"><h3 class="cv-h t-label"><span class="sq"></span> Skills</h3><div class="skills rise">{skills}{extras}</div></div>
    </div>
  </div>
</section>"""

    # ---- awards, a block of the CV section
    def awards(self) -> str:
        rows = []
        for i, a in enumerate(self.d["awards"], 1):
            meta = " · ".join(esc(x) for x in (a["issuer"], a["date"]) if x)
            fig = ""
            if a.get("image"):
                rel = f"assets/img/projects/{a['image']}"
                if (ROOT / rel).is_file():
                    fig = (f'<figure class="aw-fig"><div class="fig-frame">{img_tag(rel, a["title"])}{corner_ticks()}</div>'
                           f'<figcaption class="t-cap">{esc(a["title"])}</figcaption></figure>')
            marker = ""
            desc = f'<p class="aw-desc">{inline(a["desc"])}</p>' if a.get("desc") else ""
            rows.append(f"""
      <li class="aw-row rise">
        <span class="t-index">{marker}{i:02d}</span>
        <div class="aw-main"><h4 class="aw-title">{esc(a["title"])}</h4><p class="t-label aw-meta">{meta}</p>{desc}</div>
        {fig}
      </li>""")
        if not rows:
            return ""
        return (f'<div class="cv-block" id="awards"><h3 class="cv-h t-label"><span class="sq"></span> Awards and certifications</h3>'
                f'<ol class="aw-list">{"".join(rows)}</ol></div>')

    # ---- 6. Software (orange blueprint panel)
    def software(self) -> str:
        sid = "software"
        known = {p["slug"]: p for p in self.d["projects"] if p.get("tier")}
        used, also = [], []
        for t in self.d["software"]:
            (used if t["uses"] else also).append(t)

        def use_html(u: str) -> str:
            if u in known:
                p = known[u]
                return f'<a href="#{u}">{esc(p.get("short") or p["title"])}</a>'
            if re.fullmatch(r"[a-z0-9-]+", u):
                raise SystemExit(f"build_site: software use {u!r} is not a project slug")
            return f'<span>{esc(u)}</span>'

        trs = "".join(
            f'<tr><td class="bp-n">{i:02d}</td><th scope="row">{esc(t["name"])}</th><td>{esc(t["what"])}</td>'
            f'<td><div class="bp-uses">{"".join(use_html(u) for u in t["uses"])}</div></td></tr>'
            for i, t in enumerate(used, 1))
        if also:
            trs += (f'<tr class="bp-also"><td class="bp-n">+</td><th scope="row">Also</th>'
                    f'<td colspan="2">{" · ".join(esc(t["name"]) for t in also)}</td></tr>')
        return f"""
<section id="{sid}" class="bp" data-theme="orange" data-name="Software">
  <div class="bp-sheet">
    <div class="wrap">
      <div class="bp-top t-label"><span>Software</span><span>Sheet {self.no(sid)}/{len(self.sections):02d}</span></div>
      <h2 class="bp-title">{mask('Software')}</h2>
      <table class="bp-table rise">
        <caption class="sr-only">Software, what it is for, and the projects it was used in</caption>
        <thead><tr><th scope="col">No.</th><th scope="col">Tool</th><th scope="col">What it is for</th><th scope="col">Used in</th></tr></thead>
        <tbody>{trs}</tbody>
      </table>
      <div class="bp-bar t-label"><span>{esc(self.d['profile']['Name'])}</span><span>{self.year}</span></div>
    </div>
  </div>
</section>"""

    # ---- 7. Contact / footer
    def contact(self) -> str:
        pr = self.d["profile"]
        user, _, domain = pr.get("Email", "").partition("@")
        name, _, tld = domain.rpartition(".")
        fallback = f"{user} [at] {name} [dot] {tld}"
        mail = (f'<a class="btn btn--primary js-mail" data-u="{b64r(user)}" data-d="{b64r(domain)}" href="#contact">'
                f'<span class="js-mail-t">{esc(fallback)}</span></a>') if user else ""
        links = [("LinkedIn", pr.get("LinkedIn", "")), ("GitHub", pr.get("GitHub", ""))] + pairs(pr.get("Other links", ""))
        if pr.get("CV file"):
            links.append(("CV · PDF", f"assets/docs/{pr['CV file']}"))
        link_html = "".join(f'<li><a href="{esc(u)}" rel="noopener">{esc(l)}</a></li>' for l, u in links if u)
        last = pr["Name"].partition(" ")[2]
        return f"""
<section id="contact" class="contact" data-theme="dark" data-name="Contact">
  <div class="wrap">
    <p class="t-label proj-no"><span class="sq"></span> No.{self.no('contact')} <span class="proj-tags">Contact</span></p>
    <div class="contact-grid">
      <div>
        <h2 class="t-h1 contact-title">{mask("Let's talk.")}</h2>
        <p class="contact-mail rise">{mail}</p>
      </div>
      <ul class="contact-links rise">{link_html}</ul>
    </div>
  </div>
  <div class="mega-wrap"><p class="t-mega contact-mega" aria-hidden="true">{esc(last)}</p></div>
  <div class="contact-legal t-label"><div class="wrap"><span>© {self.year} {esc(pr['Name'])}</span><span>{esc(pr.get('Location', ''))}</span></div></div>
</section>"""

    # ---- page shell
    def build(self) -> str:
        order = [("intro", "top", "Intro"), ("et18", "et-18-aero-package", "ET-18"), ("caelus", "caelus", "Caelus"),
                 ("smaller", "more-projects", self.d["site"].get("Projects title") or "Projects"), ("cv", "cv", "CV"),
                 ("software", "software", "Software"), ("contact", "contact", "Contact")]
        self.sections = [(sid, name) for _, sid, name in order]
        body = "\n".join(getattr(self, fn)() for fn, _, _ in order)
        nav_html = '<li><a href="#cv">CV</a></li><li><a href="#contact">Contact</a></li>'
        pr = self.d["profile"]
        title = self.d["site"].get("Site title") or pr["Name"]
        desc = re.match(r"(.+?\.)(\s|$)", self.d["about"]).group(1)
        katex = ""
        if self.needs_math:
            katex = (f'<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist/katex.min.css">\n'
                     f'<script defer src="https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist/katex.min.js"></script>\n'
                     f'<script defer src="assets/js/math.js"></script>')
        importmap = json.dumps({"imports": {
            "three": f"https://cdn.jsdelivr.net/npm/three@{THREE_VERSION}/build/three.module.js",
            "three/addons/": f"https://cdn.jsdelivr.net/npm/three@{THREE_VERSION}/examples/jsm/"}})
        return f"""<!doctype html>
<!-- Generated by tools/build_site.py from content/portfolio-input.md. Do not edit by hand. -->
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE_URL}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{SITE_URL}">
<meta name="theme-color" content="#EAE4D3">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' fill='%23EAE4D3'/%3E%3Crect x='5' y='5' width='6' height='6' fill='%23F0541E'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wdth,wght@12..96,75..100,200..800&amp;family=IBM+Plex+Mono:wght@400;500&amp;display=swap">
<link rel="stylesheet" href="assets/css/tokens.css">
<link rel="stylesheet" href="assets/css/base.css">
<link rel="stylesheet" href="assets/css/components.css">
{katex}
<script type="importmap">{importmap}</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="bar" data-on="light">
  <div class="wrap bar-in">
    <a class="wm" href="#top"><span class="wm-name">{esc(pr['Name'])}</span><span class="wm-sub t-label">{esc(pr.get('Role', ''))}</span></a>
    <nav class="bar-nav" aria-label="Primary"><ul>{nav_html}</ul></nav>
    <button class="bar-menu" type="button" aria-expanded="false" aria-controls="menu">Menu</button>
  </div>
</header>
<div class="menu" id="menu" data-theme="light" hidden>
  <nav aria-label="Mobile"><ul>{nav_html}</ul></nav>
</div>
<main id="main">
{body}
</main>
<div class="counter t-label" aria-hidden="true" data-on="light"><span class="sq"></span><span class="c-num">01</span><span>/ {len(self.sections):02d} —</span><span class="c-name">Intro</span></div>
<script src="assets/js/reveal.js" defer></script>
<script src="assets/js/theme-nav.js" defer></script>
<script src="assets/js/site.js" defer></script>
<script src="assets/js/tunnel.js" defer></script>
<script type="module" src="assets/js/stage-projects.js"></script>
</body>
</html>
"""


def main() -> int:
    data = parse(INPUT)
    obfuscate_models()
    page = Page(data).build()
    OUTPUT.write_text(page, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(page) // 1024} KB)")
    if PENDING:
        print("image placeholders (drop these files in assets/img/projects/):")
        for f in dict.fromkeys(PENDING):
            print("  -", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
