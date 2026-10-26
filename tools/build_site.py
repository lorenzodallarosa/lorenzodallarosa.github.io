#!/usr/bin/env python3
"""Build index.html from content/portfolio-input.md, following content/DESIGN.md.

Usage:  python tools/build_site.py

Standard library only. The script writes index.html and nothing else; the CSS and
JS in assets/ are hand-written and never touched here. Re-run it after any edit to
the input file.
"""
from __future__ import annotations

import cmath
import datetime as _dt
import html
import json
import math
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

# Sections rendered, in page order (DESIGN.md section 0, "Section order and themes").
# First checkpoint (DESIGN.md section 17): intro, one light project, one dark 3D
# project and the orange blueprint panel. The rest are added after review.
SECTIONS = ["intro", "et18", "caelus", "capabilities"]

# Template text left over from the input file's instructions counts as empty.
TEMPLATE_VALUES = {"label | url ; label | url", "dark | light", "#hex, e.g. #1e6fff"}


# --------------------------------------------------------------------------- utils

def esc(s: str) -> str:
    return html.escape(s, quote=True)


def clean(value: str) -> str:
    """Strip the [ ] wrapper; template or empty values become ''."""
    v = value.strip()
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1].strip()
    if v in TEMPLATE_VALUES or v.startswith("Authors,"):
        return ""
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


def has_math(text: str) -> bool:
    return bool(MATH.search(text))


# -------------------------------------------------------------------------- parser

KEY = re.compile(r"^([A-Z][A-Za-z ]*):\s*(.*)$")


def parse(path: Path) -> dict:
    raw = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    d: dict = {
        "site": {}, "profile": {}, "about": [], "skills": {}, "experience": [],
        "education": [], "projects": [], "publications": [], "awards": [], "extras": {},
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
            if h1 in ("EXPERIENCE", "EDUCATION"):
                role, _, org = title.partition("|")
                cur = {"title": role.strip(), "org": org.strip(), "bullets": []}
                d[h1.lower()].append(cur)
            elif h1 == "PROJECTS":
                cur = {"title": title, "details": []}
                d["projects"].append(cur)
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
        elif h1 in ("EXPERIENCE", "EDUCATION") and cur is not None:
            if s.startswith("- "):
                cur["bullets"].append(s[2:])
            elif key:
                cur[key.group(1).lower()] = clean(key.group(2))
        elif h1 == "PROJECTS" and cur is not None:
            if in_details:
                cur["details"].append(line)
            elif s == "Details:":
                in_details = True
            elif key:
                cur[key.group(1).lower().replace(" ", "_")] = clean(key.group(2))
        elif h1 == "PUBLICATIONS" and s.startswith("- "):
            v = clean(s[2:])
            if v:
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


# ------------------------------------------------------------------ figure drawing

def _joukowski(mu=complex(-0.08, 0.08), alpha_deg=6.0):
    """Joukowski aerofoil and potential-flow streamlines (Kutta condition)."""
    a = abs(1 - mu)
    alpha = math.radians(alpha_deg)
    beta = -cmath.phase(1 - mu)
    gamma = 4 * math.pi * a * math.sin(alpha + beta)  # U = 1

    def dwdz(zeta, g):
        zp = zeta - mu
        return cmath.exp(-1j * alpha) - a * a * cmath.exp(1j * alpha) / zp**2 - 1j * g / (2 * math.pi * zp)

    # Pick the circulation sign that puts the rear stagnation point on the trailing edge.
    if abs(dwdz(1 + 1e-6, -gamma)) < abs(dwdz(1 + 1e-6, gamma)):
        gamma = -gamma

    def vel(zeta):
        w = dwdz(zeta, gamma)
        v = w.conjugate()
        n = abs(v)
        return v / n if n > 1e-9 else 0

    outline = [mu + a * cmath.exp(1j * t) for t in [i * 2 * math.pi / 240 for i in range(241)]]
    foil = [z + 1 / z for z in outline]

    lines = []
    for k in range(-7, 8):
        y0 = k * 0.42 + 0.02
        z = complex(-7.0, y0)
        pts = [z]
        h = 0.03
        for _ in range(900):
            k1 = vel(z)
            k2 = vel(z + h / 2 * k1)
            k3 = vel(z + h / 2 * k2)
            k4 = vel(z + h * k3)
            z = z + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            if abs(z - mu) < a * 1.002 or z.real > 7.5:
                break
            pts.append(z)
        lines.append([p + 1 / p for p in pts if abs(p) > 1e-6])
    return foil, lines


def _path(points, fx, fy) -> str:
    return "M" + " L".join(f"{fx(p):.1f} {fy(p):.1f}" for p in points)


def intro_figure() -> str:
    """Quiet line drawing for the intro: a Joukowski section with dimension lines."""
    foil, _ = _joukowski()
    xs = [p.real for p in foil]
    x0, x1 = min(xs), max(xs)
    W, H, pad = 640, 300, 60
    s = (W - 2 * pad) / (x1 - x0)
    fx = lambda p: pad + (p.real - x0) * s
    fy = lambda p: 150 - p.imag * s
    chord_y = 150
    qx = pad + 0.25 * (x1 - x0) * s
    return f"""<svg viewBox="0 0 {W} {H}" class="fig-svg" role="img" aria-labelledby="fig0-t">
  <title id="fig0-t">Line drawing of a Joukowski aerofoil section with its chord and quarter-chord point marked</title>
  <path d="{_path(foil, fx, fy)} Z" class="ln-ink"/>
  <line x1="{pad}" y1="{chord_y}" x2="{W - pad}" y2="{chord_y}" class="ln-dash"/>
  <g class="ln-dim">
    <line x1="{pad}" y1="236" x2="{W - pad}" y2="236"/>
    <line x1="{pad}" y1="228" x2="{pad}" y2="244"/><line x1="{W - pad}" y1="228" x2="{W - pad}" y2="244"/>
    <line x1="{pad}" y1="{chord_y + 8}" x2="{pad}" y2="226"/><line x1="{W - pad}" y1="{chord_y + 8}" x2="{W - pad}" y2="226"/>
  </g>
  <text x="{W / 2}" y="258" class="fig-txt" text-anchor="middle">c</text>
  <rect x="{qx - 4:.1f}" y="{chord_y - 4}" width="8" height="8" class="fill-orange"/>
  <line x1="{qx:.1f}" y1="{chord_y - 6}" x2="{qx:.1f}" y2="70" class="ln-dim"/>
  <text x="{qx + 8:.1f}" y="76" class="fig-txt">c/4</text>
  <text x="{pad}" y="24" class="fig-txt">FIG. 00</text>
  <text x="{W - pad}" y="24" class="fig-txt" text-anchor="end">&#956; = &#8722;0.08 + 0.08i</text>
</svg>"""


def blueprint_figure() -> str:
    """Streamlines of potential flow past the same aerofoil, for the orange panel."""
    foil, lines = _joukowski()
    W, H = 560, 380
    s = W / 9.0
    fx = lambda p: W / 2 + p.real * s
    fy = lambda p: H / 2 - p.imag * s
    inside = lambda p: -4.5 <= p.real <= 4.5 and abs(p.imag) <= H / 2 / s - 0.05
    paths = []
    for ln in lines:
        seg = [p for p in ln if inside(p)]
        if len(seg) > 2 and fx(seg[-1]) - fx(seg[0]) > W * 0.8:
            paths.append(f'<path d="{_path(seg, fx, fy)}"/>')
    return f"""<svg viewBox="0 0 {W} {H}" class="fig-svg" role="img" aria-labelledby="fig1-t">
  <title id="fig1-t">Streamlines of inviscid potential flow past a Joukowski aerofoil at 6 degrees angle of attack</title>
  <g class="ln-cream">{''.join(paths)}</g>
  <path d="{_path(foil, fx, fy)} Z" class="ln-ink fill-ink"/>
</svg>"""


# ------------------------------------------------------------------------ helpers

def first_sentence(text: str) -> str:
    m = re.match(r"(.+?\.)(\s|$)", text.strip())
    return m.group(1) if m else text.strip()


def bullets_of(details: str) -> list[str]:
    return [l.strip()[2:] for l in details.splitlines() if l.strip().startswith("- ")]


def find_bullet(details: str, prefix: str) -> str:
    for b in bullets_of(details):
        if b.startswith(prefix):
            return b
    raise SystemExit(f"build_site: no Details bullet starts with {prefix!r}")


def quote(text: str, fragment: str) -> str:
    """Return fragment as written in text (case-insensitive), or fail: facts are never invented."""
    i = text.lower().find(fragment.lower())
    if i < 0:
        raise SystemExit(f"build_site: {fragment!r} is not in the input file")
    found = text[i : i + len(fragment)]
    return found[0].upper() + found[1:]


def statement_of(summary: str) -> str:
    """Trim a long Summary to its first clause for the H2 statement (DESIGN.md section 0).
    The dropped part is restated in the step list, spec row or comparison table."""
    m = re.match(r"(.+?)(, with |: )", summary)
    return (m.group(1) + ".") if m and len(summary) > 110 else summary


def corner_ticks() -> str:
    return '<span class="tick tl"></span><span class="tick tr"></span><span class="tick bl"></span><span class="tick br"></span>'


def mask(text: str, i: int = 0) -> str:
    return f'<span class="mask"><span class="mask-in" style="--i:{i}">{text}</span></span>'


def img_tag(rel: str, alt: str, cls: str = "", lazy: bool = True, sizes: str = "") -> str:
    size = image_size(ROOT / rel)
    wh = f' width="{size[0]}" height="{size[1]}"' if size else ""
    lz = ' loading="lazy" decoding="async"' if lazy else ""
    c = f' class="{cls}"' if cls else ""
    return f'<img src="{esc(rel)}" alt="{esc(alt)}"{wh}{lz}{c}>'


def placeholder(slug: str, title: str, ratio: str = "4 / 3") -> str:
    return (f'<div class="ph" role="img" aria-label="Image pending for {esc(title)}" style="aspect-ratio:{ratio}">'
            f'{corner_ticks()}<span class="t-label">Image pending · {esc(slug)}</span></div>')


def project_image(p: dict, alt: str) -> str:
    rel = f"assets/img/projects/{p['slug']}/{p.get('cover_image', '')}"
    if p.get("cover_image") and (ROOT / rel).is_file():
        return img_tag(rel, alt)
    return placeholder(p["slug"], p["title"])


def spec_row(facts: list[tuple[str, str]]) -> str:
    cells = "".join(f'<div class="spec"><dt class="t-label">{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k, v in facts if v)
    return f'<dl class="specs rise">{cells}</dl>'


# ----------------------------------------------------------------------- sections

class Page:
    def __init__(self, data: dict):
        self.d = data
        self.year = _dt.date.today().year
        self.by_slug = {p.get("slug"): p for p in data["projects"]}
        self.rendered: list[tuple[str, str]] = []  # (id, counter name)
        self.needs_math = False

    # ---- index rows (one per tiered project; Compare-with partners share a row)
    def work_rows(self) -> list[dict]:
        partners = {p.get("compare_with") for p in self.d["projects"] if p.get("compare_with")}
        rows = []
        for p in self.d["projects"]:
            if not p.get("tier") or p.get("slug") in partners:
                continue
            row = {"slug": p["slug"], "title": p["title"].split(" - ")[0], "type": p.get("type", ""),
                   "year": p.get("year", ""), "cover": p.get("cover_image", "")}
            if p.get("compare_with") in self.by_slug:
                other = self.by_slug[p["compare_with"]]
                a = other["title"].split(" - ")[0]
                b = p["title"].split(" - ")[0].replace("Caelus ", "")
                row["title"] = f"{a} → {b}"
                years = sorted({other.get("year", ""), p.get("year", "")} - {""})
                row["year"] = "–".join(years)
            rows.append(row)
        return rows

    def section_no(self, sid: str) -> str:
        ids = [i for i, _ in self.rendered]
        return f"{ids.index(sid) + 1:02d}"

    # ---- 1. intro + work index
    def intro(self) -> str:
        pr = self.d["profile"]
        first, _, last = pr["Name"].partition(" ")
        insts = []
        for e in self.d["education"]:
            if e["org"] not in insts:
                insts.append(e["org"])
        rows = []
        rendered_ids = {i for i, _ in self.rendered}
        for n, r in enumerate(self.work_rows(), 1):
            sid = r["slug"]
            target = sid if sid in rendered_ids else ("smaller-projects" if "smaller-projects" in rendered_ids else "")
            meta = " — ".join(x for x in (r["type"], r["year"]) if x)
            cover = f"assets/img/projects/{sid}/{r['cover']}"
            prev = img_tag(cover, "", "ix-prev") if r["cover"] and (ROOT / cover).is_file() else ""
            inner = (f'<span class="t-index">{n:02d}</span><span class="ix-title">{esc(r["title"])}</span>'
                     f'<span class="ix-meta t-label">{esc(meta)}</span>{prev}')
            tag = f'<a class="ix-row" href="#{target}">{inner}</a>' if target else f'<div class="ix-row is-off">{inner}</div>'
            rows.append(f'<li class="rise">{tag}<span class="ix-rule draw"></span></li>')
        return f"""
<section id="top" class="intro" data-theme="light" data-name="Intro">
  <div class="wrap">
    <p class="t-label intro-tag mask"><span class="mask-in">CFD · FEA · Aerospace</span></p>
    <h1 class="t-h1 intro-name">{mask(esc(first))}{mask(esc(last), 1)}</h1>
    <div class="intro-grid">
      <div class="intro-copy">
        <p class="t-h2 rise">{esc(self.d['site'].get('Tagline', '').strip())}.</p>
        <p class="t-label intro-role rise">{esc(pr.get('Role', ''))}</p>
        <p class="rise"><a href="#work">See selected work</a></p>
        <p class="t-label intro-loc rise"><span class="sq"></span> {esc(pr.get('Location', ''))}<br>{' / '.join(esc(i) for i in insts)}</p>
      </div>
      <figure class="intro-fig rise">
        {intro_figure()}
      </figure>
    </div>
    <div class="index" id="work">
      <div class="index-head t-label"><span>Index</span><span>{len(rows):02d} projects</span></div>
      <ol class="ix">{''.join(rows)}</ol>
    </div>
  </div>
</section>"""

    # ---- big project helpers
    def stage(self, sid: str, title: str, theme: str, models: list[dict], caption: str, legend: list[tuple[str, str]],
              toggle: str = "", micro: str = "") -> str:
        cfg = {"theme": theme, "models": models}
        first = models[0]
        poster = img_tag(first["poster"], first["alt"], "stage-poster", lazy=False)
        legend_html = "".join(f'<li><span class="chip chip--{tone}"></span>{esc(t)}</li>' for t, tone in legend)
        return f"""
      <figure class="stage stage--{theme}" data-stage aria-label="{esc(title)}: interactive 3D model">
        <div class="stage-box">
          {poster}
          <div class="stage-gl" aria-hidden="true"></div>
          <div class="stage-callouts" aria-hidden="true"></div>
          {corner_ticks()}
          <span class="stage-micro t-label">{micro}</span>
          <p class="stage-hint t-label" aria-hidden="true">Drag to rotate</p>
          <button class="stage-tap t-label" type="button">Tap to interact</button>
          <div class="stage-ui">
            {toggle}
            <div class="presets" role="group" aria-label="Camera views">
              <button type="button" class="t-label" data-view="three">3/4</button>
              <button type="button" class="t-label" data-view="side">Side</button>
              <button type="button" class="t-label" data-view="front">Front</button>
              <button type="button" class="t-label" data-view="top">Top</button>
            </div>
          </div>
        </div>
        <figcaption class="stage-cap">
          <ul class="legend t-label">{legend_html}</ul>
          <span class="t-cap">{caption}</span>
        </figcaption>
        <script type="application/json" class="stage-cfg">{json.dumps(cfg)}</script>
      </figure>"""

    def head(self, sid: str, short: str, title: str, tags: list[str], statement: str) -> str:
        return f"""
      <div class="proj-head">
        <p class="t-label crumb">Home › Work › {esc(short)}</p>
        <p class="t-label proj-no"><span class="sq"></span> No.{self.section_no(sid)} <span class="proj-tags">{esc(' / '.join(tags[:3]))}</span></p>
        <h2 class="t-h1 proj-title" aria-label="{esc(title)}">{mask(esc(short))}</h2>
        <p class="t-h2 proj-statement rise">{inline(statement)}</p>
      </div>"""

    # ---- 2. ET-18 (light, paper)
    def et18(self) -> str:
        p = self.by_slug["et-18-aero-package"]
        det = p["details"]
        steps = [find_bullet(det, k) for k in (
            "Cornering simulations", "CFD validation", "First CFD/CHT", "Reduced Order Model", "Composite manufacturing")]
        facts = [("Role", p.get("role", "")), ("Year", p.get("year", "")),
                 ("Downforce", quote(det, "+13.5%")), ("Efficiency", quote(det, "+16%")), ("Track score", quote(det, "+7.3%"))]
        cover = f"assets/img/projects/{p['slug']}/{p['cover_image']}"
        stage = self.stage(
            p["slug"], p["title"], "paper",
            [{"key": "et18", "src": f"assets/models/{p['slug']}/{p['slug']}.glb", "poster": cover, "rotateY": 180,
              "alt": "The ET-18 Formula Student car, black carbon fibre with orange accents",
              "callouts": [{"node": "RW_Main", "label": "Composite package", "tone": "orange", "dy": 40}]}],
            "Interactive model of the ET-18, loaded from the team's exported CAD. The photo stands in until it loads.",
            [("Cornering · rotating domain", "orange"), ("Battery cooling · CFD/CHT", "ink")],
            micro="ET-18 · FS 2025")
        step_rows = "".join(f'<li class="step"><span class="t-index">{i:02d}</span><span class="step-t">{inline(s)}</span></li>'
                            for i, s in enumerate(steps, 1))
        return f"""
<section id="{p['slug']}" class="proj proj--big" data-theme="paper" data-name="ET-18">
  <div class="wrap">
    <div class="hero">
      {self.head(p['slug'], 'ET-18', p['title'], [t.strip() for t in p['tags'].split(',')], statement_of(p['summary']))}
      {stage}
    </div>
    <div class="proj-body">
      <ol class="steps rise">{step_rows}</ol>
      {spec_row(facts)}
      <details class="more rise">
        <summary class="t-label">Full project notes</summary>
        <div class="prose">{md(det)}</div>
      </details>
    </div>
  </div>
</section>"""

    # ---- 3. Caelus Baff-1 vs ONE:1 (dark)
    def caelus(self) -> str:
        b = self.by_slug["caelus-baff-1"]
        o = self.by_slug[b["compare_with"]]
        bd, od = b["details"], o["details"]
        dash = "—"
        rows = [
            ("Role", o.get("role", dash), b.get("role", dash)),
            ("Layout", dash, quote(bd, "A-tail pusher configuration for better weight distribution and dynamics")),
            ("Payload", quote(od, "the payload sits outside the main fuselage, with a moving fairing that retracts after the drop"),
             quote(bd, "Internal payload storage for improved aerodynamics")),
            ("Structure", quote(od, "Full carbon-fibre monocoque airframe"),
             quote(bd, "Carbon-fibre and glass-fibre prepreg structure with internal antennas")),
            ("Wing", dash, quote(bd, "D-box wing with a leading-edge spar")),
            ("Control surfaces", dash, quote(bd, "split flaps and flaperons")),
            ("Autopilot", quote(od, "Fully autonomous flight with a PX4 autopilot"),
             quote(bd, "Fully autonomous flight with ArduPilot, a pitot tube and a lidar ground-height rangefinder")),
            ("Thrust-to-weight", quote(od, "1:1 thrust-to-weight ratio for STOL operations"), dash),
            ("Endurance", dash, quote(bd, "30 minutes of continuous operation")),
        ]
        def td(label, v):
            nil = ' class="nil"' if v == dash else ""
            return f'<td data-label="{label}"{nil}>{esc(v)}</td>'

        trs = "".join(
            f'<tr><th scope="row" class="t-label"><span class="t-index">{i:02d}</span> {esc(k)}</th>'
            f'{td("ONE:1", v1)}{td("Baff-1", v2)}</tr>'
            for i, (k, v1, v2) in enumerate(rows, 1))
        team = quote(bd, "4 people")
        toggle = """<div class="toggle" role="group" aria-label="Aircraft">
              <button type="button" class="t-label" data-model="one" aria-pressed="false">ONE:1 · Earlier</button>
              <button type="button" class="t-label" data-model="baff" aria-pressed="true">Baff-1 · Newer</button>
            </div>"""
        stage = self.stage(
            b["slug"], "Caelus Baff-1 and ONE:1", "dark",
            [{"key": "baff", "src": f"assets/models/{b['slug']}/{b['slug']}.glb",
              "poster": f"assets/img/projects/{b['slug']}/{b['cover_image']}",
              "alt": "Render of Caelus Baff-1, a fixed-wing UAV with an A-tail and a pusher propeller",
              "callouts": [{"node": "Tail_Body", "label": "A-tail pusher", "tone": "orange"},
                           {"node": "R_DBox", "label": "D-box wing · leading-edge spar", "tone": "bone", "bias": [-0.6, 0.3, 0.45], "dy": 120},
                           {"node": "R_flap", "label": "Split flaps · flaperons", "tone": "powder", "bias": [0.6, 0, 0.8], "dy": 40}]},
             {"key": "one", "src": f"assets/models/{o['slug']}/{o['slug']}.glb",
              "poster": f"assets/img/projects/{o['slug']}/{o['cover_image']}", "rotateY": 180,
              "alt": "Render of Caelus ONE:1, a carbon-fibre fixed-wing UAV with a tractor propeller and an external payload",
              "callouts": []}],
            "Both aircraft are loaded from their exported CAD and shown at the same scale, so switching keeps the camera and the size difference is real.",
            [("Structure", "bone"), ("Configuration", "orange"), ("Control surfaces", "powder")],
            toggle=toggle, micro="IMechE UAS Challenge")
        return f"""
<section id="{b['slug']}" class="proj proj--big proj--flip" data-theme="dark" data-name="Caelus">
  <div class="wrap">
    <div class="hero">
      {self.head(b['slug'], 'Caelus', 'Caelus Baff-1 compared with Caelus ONE:1', [t.strip() for t in b['tags'].split(',')], statement_of(b['summary']))}
      {stage}
    </div>
    <div class="proj-body">
      <div class="cmp rise">
        <table class="spec-table">
          <caption class="sr-only">Caelus ONE:1 compared with Caelus Baff-1</caption>
          <thead><tr><th scope="col" class="t-label">Aircraft</th><th scope="col" class="t-label">ONE:1 · {esc(o.get('year', ''))}</th><th scope="col" class="t-label">Baff-1 · {esc(b.get('year', ''))}</th></tr></thead>
          <tbody>{trs}</tbody>
        </table>
      </div>
      {spec_row([("Team", team), ("Competition", quote(bd, "IMechE UAS Challenge")), ("Role", b.get("role", "")), ("Year", b.get("year", ""))])}
      <details class="more rise">
        <summary class="t-label">Full project notes</summary>
        <div class="more-cols">
          <div class="prose"><h3 class="t-label">Baff-1 · {esc(b.get('year', ''))}</h3>{md(bd)}</div>
          <div class="prose"><h3 class="t-label">ONE:1 · {esc(o.get('year', ''))}</h3><p class="t-label">{esc(o.get('role', ''))}</p>{md(od)}</div>
        </div>
      </details>
    </div>
  </div>
</section>"""

    # ---- 7. Capabilities (orange blueprint panel)
    def capabilities(self) -> str:
        sk = self.d["skills"]
        tools = sk.get("Tools", [])
        about = self.d["about"]

        def pick(*names):
            out = []
            for n in names:
                hit = next((t for t in tools if t.startswith(n)), None)
                if hit is None:
                    raise SystemExit(f"build_site: tool {n!r} not in Skills > Tools")
                out.append(hit)
            return " · ".join(out)

        ansys = next(t for t in tools if t.startswith("ANSYS"))
        rows = [
            ("Computational fluid dynamics", pick("Star-CCM+", "OpenFOAM") + " · ANSYS Fluent",
             "Conjugate heat transfer, rotating cornering domains, automated meshing and aerodynamic maps",
             "ET-18: +13.5% downforce, +16% efficiency"),
            ("Finite element analysis", "ANSYS MAPDL, Mechanical, Workbench · " + pick("BetaCAE"),
             "Transient dynamics, nonlinear contact, modal analysis, Python post-processing",
             "Rail joint: failure detected from a 360 to 330 Hz shift"),
            ("Composites and UAV design", pick("Fibersim", "Siemens NX") + " · ANSYS ACP · " + pick("PX4", "ROS2"),
             "Mould tooling, carbon-fibre layup and curing; autonomous fixed-wing and quadcopter platforms",
             "1st place worldwide, IEEE UAV Chase Challenge 2023"),
        ]
        assert "ACP" in ansys and "MAPDL" in ansys and "Fluent" in ansys
        # Results must be stated in the input file.
        src = INPUT.read_text(encoding="utf-8")
        for r in ("+13.5% downforce", "+16% efficiency", "360 Hz to 330 Hz", "IEEE UAV Chase Challenge"):
            if r not in src:
                raise SystemExit(f"build_site: capability result {r!r} not in input")
        statement = quote(about, "I enjoy turning a complex physical problem into a fast, reproducible workflow and a design decision someone can trust.")
        trs = "".join(
            f'<tr><td class="bp-n">{i:02d}</td><th scope="row">{esc(a)}</th><td>{esc(b)}<span class="bp-sub">{esc(c)}</span></td><td>{esc(d)}</td></tr>'
            for i, (a, b, c, d) in enumerate(rows, 1))
        sid = "capabilities"
        return f"""
<section id="{sid}" class="bp" data-theme="orange" data-name="Capabilities">
  <div class="bp-sheet">
    <div class="wrap">
      <div class="bp-top t-label"><span>Home › Capabilities</span><span>Sheet {self.section_no(sid)}/{len(self.rendered):02d}</span></div>
      <h2 class="bp-title">{mask('Capabilities')}</h2>
      <div class="bp-grid">
        <figure class="bp-fig rise">
          {blueprint_figure()}
          <figcaption class="t-label">Fig. 01 · Potential flow past a Joukowski aerofoil, <span class="nocase">α</span> = 6°, Kutta condition</figcaption>
        </figure>
        <table class="bp-table rise">
          <caption class="sr-only">What I do: capability, tools and results</caption>
          <thead><tr><th scope="col">No.</th><th scope="col">Capability</th><th scope="col">Tools and methods</th><th scope="col">Result</th></tr></thead>
          <tbody>{trs}</tbody>
        </table>
      </div>
      <p class="bp-statement rise">{esc(statement)}</p>
      <div class="bp-bar t-label"><span>{esc(self.d['profile']['Name'])}</span><span>{self.year}</span></div>
    </div>
  </div>
</section>"""

    # ---- page shell
    def build(self) -> str:
        names = {"intro": ("top", "Intro"), "et18": ("et-18-aero-package", "ET-18"),
                 "caelus": ("caelus-baff-1", "Caelus"), "capabilities": ("capabilities", "Capabilities")}
        self.rendered = [names[s] for s in SECTIONS]
        body = "\n".join(getattr(self, s)() for s in SECTIONS)
        ids = {i for i, _ in self.rendered}
        nav = [(l, h) for l, h in (("Work", "work"), ("About", "about"), ("Capabilities", "capabilities"), ("Contact", "contact"))
               if h in ids or h == "work"]
        nav_html = "".join(f'<li><a href="#{h}">{l}</a></li>' for l, h in nav)
        menu_html = "".join(f'<li><a href="#{h}">{l}</a></li>' for l, h in nav)
        pr = self.d["profile"]
        title = self.d["site"].get("Site title") or pr["Name"]
        desc = first_sentence(self.d["about"])
        katex = ""
        if self.needs_math:
            katex = (f'<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist/katex.min.css">\n'
                     f'<script defer src="https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist/katex.min.js"></script>')
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
    <a class="wm" href="#top"><span class="wm-name">{esc(pr['Name'])}</span><span class="wm-sub t-label">Selected work / {self.year}</span></a>
    <nav class="bar-nav" aria-label="Primary"><ul>{nav_html}</ul></nav>
    <button class="bar-menu" type="button" aria-expanded="false" aria-controls="menu">Menu</button>
  </div>
</header>
<div class="menu" id="menu" data-theme="light" hidden>
  <nav aria-label="Mobile"><ul>{menu_html}</ul></nav>
</div>
<main id="main">
{body}
</main>
<div class="counter t-label" aria-hidden="true" data-on="light"><span class="sq"></span><span class="c-num">01</span><span>/ {len(self.rendered):02d} —</span><span class="c-name">Intro</span></div>
<script src="assets/js/reveal.js" defer></script>
<script src="assets/js/theme-nav.js" defer></script>
<script type="module" src="assets/js/stage-et18.js"></script>
<script type="module" src="assets/js/stage-caelus.js"></script>
</body>
</html>
"""


def main() -> int:
    data = parse(INPUT)
    page = Page(data).build()
    OUTPUT.write_text(page, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(page) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
