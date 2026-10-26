# DESIGN.md — Lorenzo Dalla Rosa, Aerospace Engineer Portfolio

The design brief for the one-page portfolio of Lorenzo Dalla Rosa (CFD and FEA engineer, Pisa, Italy), published on GitHub Pages at `https://lorenzodallarosa.com`. It defines the character, look, typography, structure, motion and 3D approach. Sections 1 to 10 are the visual system and are fixed. Section 0 ties that system to this repository, and sections 11, 14 and 17 say how to build it here. The result must be original work.

---

## 0. Project context and overrides

**Where things live (repo root = site root)**

| Path | Role |
|---|---|
| `content/portfolio-input.md` | The single source of all copy and data (profile, experience, education, activities, projects, groups, software, awards, extras). Its header explains the format. Edit it only when the owner asks |
| `content/DESIGN.md` | This file |
| `tools/build_site.py` | Generator: reads the input file, writes `index.html` and the obfuscated model files (`assets/models/<slug>/<slug>.bin`). Standard library only |
| `index.html`, `assets/css/`, `assets/js/` | Generated or hand-written site output. The builder owns these |
| `assets/img/profile/`, `assets/img/projects/<slug>/` | Portrait and per-project images (`cover.*` is the poster). Figures extracted from the project PDFs live here too |
| `assets/models/<slug>/<slug>.glb` | Source 3D models (Draco + Meshopt glTF Binary). **Local only (gitignored)**; the site loads the obfuscated `.bin` copy |
| `assets/docs/` | Public downloads: the CV and project PDFs. Link only what the input file lists |
| `projects/` | **Local-only source material, gitignored. Never publish or link anything from it.** The VTOL rotor project is sensitive: no figures, numbers beyond those already written in the input file, or PDF |
| `CNAME`, `.nojekyll`, `.github/workflows/pages.yml` | Hosting. Do not modify. The workflow deploys the repo root as-is, so the site needs no build step on GitHub |

**Hosting constraints**
- Static files only, served from the domain root. No server code.
- Fonts and libraries load from Google Fonts, cdnjs or jsDelivr only. Pin versions.
- Keep the page light: images at most ~1600px on the long side, 3D loaded lazily (section 9).

**Content rules**
- Every piece of copy comes from `content/portfolio-input.md`. Never invent credentials, metrics, logos, dates **or decorative figures** (no generated line drawings, aerofoils or illustrations standing in for real work). An empty `[]` field is omitted from the page.
- Language is English (British spelling, as written in the input file). Text is used as written.
- The portrait is shown greyscale (CSS filter), never in colour.
- Markdown in the input file (bold, italic, bullet lists, `$...$` equations) must render; KaTeX loads from jsDelivr only when equations are present.
- Missing images render as labelled placeholders (see "Image placeholders"), never as invented content.

**Page structure and themes** (replaces the page anatomy table in section 5; the components and rules in section 6 still apply)

| # | Section | Theme | Source |
|---|---|---|---|
| 0 | Top bar | Cream, inverts over dark | `Name`; links: `CV`, `Contact` only. No year in the sub-line |
| 1 | Intro | Cream | `Tag line` (CFD · FEA · Composites) above the name, `Greeting` (Ciao!), `Name`, `Role`, `Location`, institutions linked to their `Link:`, greyscale portrait. No work index, no figure |
| 2 | ET-18 | Light, `--paper` family | `et-18-aero-package`: kicker "E-Team Squadra Corse" above the H1 "ET-18", the car photo as the hero image, then the 3D stage, then the numbered steps |
| 3 | Caelus Sant'Anna | Dark | Group `caelus`: group header, then the quadcopter (compact block), ONE:1 and Baff-1, each with its own hero, 3D stage and steps |
| 4 | Smaller projects | Sage pastel | `Tier: small` projects as cards that expand into a full-width panel with figures |
| 5 | CV | Cream with paper cards | About, Education (completed and in progress), Experience, Activities, Skills, Interests, CV download |
| 6 | Awards | Butter pastel | Awards and certifications |
| 7 | Software | Orange blueprint panel | `# SOFTWARE`: what each tool is for and the projects it was used in (linked) |
| 8 | Contact / footer | Dark | Email (obfuscated), LinkedIn, GitHub, CV link, mega name |

No two neighbouring sections share a theme. The section counter reads `0X / 08`, computed from the sections actually rendered.

**Project rendering**
- `Tier: big`: full section (or full sub-section inside a group) with kicker, H1 short title (`Short:`), H2 statement (`Statement:` or `Summary`), the 3D stage (when `assets/models/<slug>/<slug>.glb` exists) and the cover photo, the spec row from `Facts:`, and the steps.
- `Tier: compact`: a shorter block inside its group: title, summary, facts, cover image, details.
- `Tier: small`: a card (index, cover, title, summary, spec row) in the Smaller projects section; clicking it opens a full-width panel with the steps and figures.
- **Steps**: each `#### Title` block in `Details:` is one numbered row. Rows show the title and expand on click to show the full text, bullets and figures (`Image:` lines). No boxed "project notes" panels.
- 3D callouts are limited to what the input states: Baff-1 (A-tail pusher, D-box wing with leading-edge spar, split flaps and flaperons), ONE:1 (flaperons, full carbon-fibre monocoque, payload fairing). No legends, no generic captions under the stage, nothing on the ET-18 stage.
- 3D materials: carbon fibre renders as a dielectric weave under a glossy clear coat (metalness 0, low clear-coat roughness), not as metal. The ET-18 mesh gets smooth (creased) normals. Dark-stage floor light stays subtle so the stage blends into `--ink`.
- Mobile: the 3D model loads directly when the device and connection look capable (no Save-Data, 4G-class connection, at least 4 GB memory where reported); otherwise it waits for a tap.

**Image placeholders**
- Wherever an image named in the input file is missing on disk, render a placeholder in the exact slot, with the final aspect ratio, so adding the file later needs no layout change.
- Look: `--cream-deep` fill (or `--ink-soft` on dark), a 1px dashed rule, corner ticks, a faint diagonal hatch at ~6% opacity, and a centred mono label `IMAGE PENDING · <file name>`. `role="img"` and an honest `aria-label`.

**Protection (basic, not security)**
- Email: never written in plain text in the HTML; it is stored encoded and assembled by JS, with a `name [at] domain [dot] com` fallback. (The CV PDF still contains it.)
- 3D models: published only as XOR-obfuscated `.bin` files decoded in the browser; the raw `.glb` is not deployed and the canvas has no context menu. Anyone determined can still extract a model from a running page.

**Awards section**
- Source: `# AWARDS AND CERTIFICATIONS`, one entry per line `Title | Issuer | Date | Description | Image`. Keep the input order. Never invent a missing date or description.
- Butter pastel, H1 `Awards`, mono tag `RECOGNITION · CERTIFICATIONS`, a hairline spec table (index, title, issuer and date in mono, description underneath). An entry with an image shows it as a small figure with corner ticks. The first row has the orange square marker.

**Software section (orange blueprint panel)**
- Source: `# SOFTWARE`, one line per tool: `Name | What it is for | where it was used`. Project slugs become anchor links to those projects; free text (e.g. coursework) is shown as written. Tools with no stated use are listed in a final "Also" row without links. Never guess which project a tool was used in.

---

## 1. The soul in one paragraph

A portfolio that feels like a well-made instrument or a field manual. It is warm, precise and a little playful. Cream paper, black ink and one hot orange. Mono labels like silkscreen printing on hardware. Hairline rules and measurement marks like an engineering drawing. The page moves between light "paper" sections and dark "stage" sections, the way a product catalogue cuts from a spec sheet to a spotlit product shot. Nothing shouts for attention. The work is the hero, and the design behaves like good packaging: confident, quiet, obsessive about detail.

**Three words:** *tactile, technical, calm.*

**The tension to preserve:** playful warmth (cream, pastel, orange) against rigorous precision (grid, mono, hairlines, numbers). Lose either side and it turns into a generic template or a cold developer page.

---

## 2. Design principles

1. **Light ↔ dark rhythm.** Sections alternate between cream "paper" and warm near-black "stage". Dark sections are where the work is shown like an object on display. Light sections carry explanation, lists and specs.
2. **Small and quiet around big and bold.** Enormous, tight, heavy display type sits against tiny mono labels and light body text. The scale contrast is the main design device.
3. **Blueprint structure.** Numbered rows, hairline rules, bordered spec tables, breadcrumbs, dimension lines and corner ticks. Technical sections speak in mono.
4. **One loud colour.** Orange is a punctuation mark, with one full-bleed orange "blueprint" panel as the page's single saturated moment.
5. **Proof over decoration.** Real work is shown in real, interactive form: 3D models, live data views, honest diagrams. Nothing exists just to look busy.
6. **Calm motion.** Motion explains or rewards. It never decorates.
7. **One page, anchors only.** No sub-pages. Navigation is a handful of anchor links.
8. **No theatre at the door.** No intro, loader or splash. No animated or randomly generated hero. The hero is static typography.

---

## 3. Colour

Warm and slightly desaturated except for the orange. Never pure `#000` or pure `#FFF` as a page background.

```css
:root {
  /* Paper (light sections) */
  --cream:        #EAE4D3;  /* primary light background */
  --cream-deep:   #DDD5BF;  /* hover, rules on cream, secondary panels */
  --paper:        #F6F2E8;  /* cards/panels sitting on cream */

  /* Ink (dark sections + text) */
  --ink:          #1B1B19;  /* text on light, dark section background */
  --ink-soft:     #2A2A27;  /* raised surfaces on dark */
  --ink-mute:     #6E6A5F;  /* secondary text on light */
  --bone:         #EDE7D6;  /* text on dark (same family as cream) */
  --bone-mute:    #9B968A;  /* secondary text on dark */

  /* The one loud colour */
  --orange:       #F0541E;  /* accents, markers, the bold panel */
  --orange-deep:  #D8430F;  /* hover/pressed */

  /* Pastels: use sparingly, one per section at most, as backgrounds or chart tints */
  --sage:         #C7D1B6;
  --powder:       #BCD0D6;
  --butter:       #EBD98F;
  --blush:        #E8C6B8;

  /* Lines */
  --rule-light:   rgba(27,27,25,.18);
  --rule-dark:    rgba(237,231,214,.18);
}
```

**Usage rules**
- Ratio per full scroll: ~55% cream/paper, ~30% ink, ~10% pastel, ~5% orange.
- Orange on cream is only ~3:1 contrast. Use it for large shapes, markers, rules, big numerals and focus rings, **never for body text**. Text stays ink or bone.
- Pastels behave like paper stock colours. Fill a whole section or a diagram with one; never put two pastels side by side.
- Dark sections are warm near-black (`--ink`), not blue-black or neutral grey.
- Optional: a very subtle paper grain (2–3% opacity noise) on cream sections only.

---

## 4. Typography

Two voices that never blur together: a **heavy, tight display grotesk** and a **mono for everything technical**. Body is a light, clean grotesk.

**Recommended (free, Google Fonts):**
- **Display + body:** `Bricolage Grotesque` (variable, weights 200–800, optical-size and width axes). Extra-bold with tight tracking for display; light/regular for body, letting the optical-size axis adapt it to small sizes. It has a warm, slightly quirky grotesk character that suits the playful-but-precise tone.
- **Mono:** `IBM Plex Mono` (alternatives: `JetBrains Mono`, `Geist Mono`).
- If Bricolage doesn't feel right: `Schibsted Grotesk`, `Hanken Grotesk` or `Instrument Sans`.

```css
:root {
  --font-display: "Bricolage Grotesque", "Helvetica Neue", Arial, sans-serif;
  --font-body:    "Bricolage Grotesque", "Helvetica Neue", Arial, sans-serif;
  --font-mono:    "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
```

**Scale (fluid, using clamp)**

| Role | Font | Weight | Size | Tracking | Line-height | Notes |
|---|---|---|---|---|---|---|
| Mega (name in footer, one use) | Display | 800 | `clamp(8rem, 24vw, 26rem)` | -0.05em | 0.8 | Cropped by the viewport edge is fine |
| H1 section title | Display | 800 | `clamp(4rem, 11vw, 11rem)` | -0.045em | 0.88 | Sentence case, one or two words max |
| H2 statement | Body | 300 | `clamp(1.75rem, 3vw, 2.75rem)` | -0.015em | 1.15 | Short, 2–3 lines |
| Lead | Body | 300 | 1.25rem | 0 | 1.45 | |
| Body | Body | 300–400 | 1rem / 1.0625rem | 0 | 1.55 | Max 62ch |
| Label | Mono | 500 | 0.72rem | 0.12em, UPPERCASE | 1.3 | Section tags, categories |
| Caption | Body | 300 | 0.75rem | 0 | 1.4 | Under figures, 45ch max, right-aligned allowed |
| Index / number | Mono | 400 | 0.7rem | 0.05em | 1 | `01`, `02`... |

**Typographic rules**
- Giant display words are tight and heavy, and they carry the page. Everything around them is small and quiet.
- Mono labels are always uppercase with wide tracking. Mono body or table text is sentence case.
- In **blueprint sections**, switch the entire section, headings included, to mono (uppercase headings at ~2rem). That's the "spec sheet" voice.
- Never bold body text. Use weight contrast between display and light body.
- Underlined links are a 1px underline offset 4px, not a colour change.

---

## 5. Layout, grid and structure

**Grid:** 12 columns, 24px gutters, outer margin `clamp(20px, 4vw, 72px)`. Content max-width 1440px. Sections use generous vertical padding, `clamp(96px, 14vh, 200px)`.

**Signature layout moves**
1. **Asymmetric split.** Title block in the left ~40%, visual or interactive stage in the right ~60%, with overlap allowed. Flip sides between projects.
2. **Tinted panel + paper card.** The About section splits: a cream/pastel half with portrait and a giant greeting word, and a `--paper` card containing the dense detail.
3. **Hairline everything.** 1px rules separate list rows, table rows, header and footer. No boxes with shadows. No rounded cards (radius 0–2px max).
4. **Corner ticks and registration marks.** Small `+` marks or L-shaped corner brackets at the corners of figures and panels. They signal "drawn with care".
5. **Running section counter.** A fixed mono indicator in a bottom corner: `03 / 09 — WORK`. It updates on scroll.

**Page anatomy (top to bottom)**

| # | Section | Theme | Purpose |
|---|---|---|---|
| 0 | Top bar | Cream, translucent, 1px bottom rule | Wordmark left, anchor links right (`Work`, `About`, `Capabilities`, `Contact`). Inverts colours automatically over dark sections |
| 1 | Intro | Cream | Mono tag line, one huge display word or phrase, one short statement, one text link ("See selected work"), small location line. A single quiet static figure (line drawing or still image), **no animated hero** |
| 2 | Work index | Cream | A numbered list of projects as hairline rows: `01  Title — category — year`. Hover shifts the row and reveals a tiny preview |
| 3…n | Project sections | Alternate **dark** (`--ink`), **pastel**, **cream** | One section per project. See Project section |
| n+1 | About | Split cream + paper card | Portrait (greyscale), greeting, short bio, Education / Experience in two columns, then three narrow columns for Focus / Tools / Languages |
| n+2 | Capabilities | **Orange blueprint panel** | Spec-sheet table of what the owner does, bordered, mono. The page's single saturated orange moment |
| n+3 | Contact / footer | Dark | Short invitation, 2–4 links, a mega-size name cropped at the bottom, hairline, small legal line |

Alternation rule: never two sections of the same theme back to back, and never two dark sections in a row. Cuts between sections are **hard edges**, not gradients, so it reads like turning to a new page.

*Optional refinement (adopt only if it feels right in the browser):* a light → dark boundary can be a single flat shape that grows with scroll (a `clip-path` rectangle expanding from the orange marker, over about one third of a viewport of scrolling) instead of a pure hard cut. One shape, no fade, no blur. Default to the hard cut and add this only for the boundary into the first dark project.

---

## 6. Components

### Top bar
- Height 64–72px. Cream at 85% with `backdrop-filter: blur(8px)`. 1px bottom rule.
- Left: the owner's wordmark as text, not a logo mark (`[YOUR NAME]` in display 800, 1.1rem) plus a mono sub-line such as `SELECTED WORK / 2026`.
- Right: 3–4 anchor links, body 300, 0.95rem. Active link gets a 1px underline. No hamburger on desktop. On mobile, a plain text "Menu" that opens a full-screen cream overlay with big display links.
- Over dark sections the bar switches to ink with bone text (toggle with IntersectionObserver, 250ms colour transition).

### Mono label ("tag")
`FIELD · FIELD · FIELD` style. Uppercase, tracked, 0.72rem, `--ink`. Use a middle dot `·` or slash `/` as separator. These sit above big titles and under lead sentences.

### Section counter / index
Format `No.03` above the title. Mono, with an orange 6×6px square before it.

### Numbered step list (for explaining a process or pipeline)
- Rows separated by 1px rules. Each row: mono number (muted), then body-300 text at 1.125rem.
- The active row, driven by scroll or hover, gets an orange rule on its bottom edge and a one-line description that expands beneath. Inactive rows drop to 45% opacity.
- Max 5 rows.

### Project section (the repeating unit)
```
[No.03]  [mono tag: CATEGORY / SUBCATEGORY]
[H1 title, 1–2 words]
[H2 statement, one sentence]
[numbered step list or 3 bullet "facts"]                  [ STAGE: 3D / diagram / still ]
[caption bottom-right, 3 lines max]
```
- Left column ~38%, stage ~62%, flipped on alternate projects.
- Below the stage or step list: a row of 3–4 **spec facts** in mono (`DATASET  [N] items`, `STACK  [A] · [B]`, `ROLE  [Role]`, `YEAR  [Year]`).
- Links at the end: two text links (`Read the write-up`, `Code`) with underlines.
- Dark sections: the stage sits in a spotlight (see 3D section). Pastel sections: the stage is a flat diagram or image on the pastel with ink linework. Cream sections: either.

### Blueprint panel (the orange moment, used once or twice)
- Full-bleed `--orange` rectangle with ~24px inset margin showing cream around it, like a framed sheet.
- Left: an isometric or line-drawn technical figure in cream/ink linework. Right: a bordered table in mono: three rows `01 / 02 / 03`, each with a label, 1px cream borders, no fill.
- Bottom: a heavy mono statement in ink (the owner's own words about standards or approach), with a thin bar below carrying `[NAME OR STUDIO]` left and the year right.
- A breadcrumb in mono at the top of any technical section: `HOME › WORK › [PROJECT]`.

### Spec table (reusable)
Mono, 0.8rem, rows separated by 1px lines, first column a two-digit index. No zebra striping. On orange: cream lines and ink text. On cream: ink lines at 18% opacity.

### Link and button styles
- Text link: underline, no colour change. Hover: underline thickens to 2px.
- Primary action (one per page, in Contact): a rectangle with no pill shape, 1px ink border, mono uppercase label, hover fills `--orange` and text turns ink. No shadows.
- Focus ring: 2px `--orange` outline, 3px offset.

### Figure caption
Small, light, 0.75rem, muted, right-aligned under the stage, 2–3 lines. Be honest and specific ("Rendered live from the exported mesh"). Captions are where trust is built.

### Footer
Dark. Mono label with the owner's name, a statement in display 800 (`Let's talk.` or their own line), links stacked at the right

---

## 7. Signature details (what makes it feel special)

Use 4–6 of these, consistently, never all at once:
- **An orange square marker** used as bullet, active state and section marker.
- **Dimension lines:** thin lines with end ticks and a mono measurement label (`Ø 24 mm`, `n = 1,000`) around figures.
- **Callout leaders:** a short line from a point on the 3D model to a mono label, colour-coded by meaning.
- **Hardware-style micro text:** tiny mono strings in corners (`REV. B`, `SHEET 03/09`, coordinates). Keep them truthful or lightly witty.
- **Greyscale portrait** on a cream panel. No colour photos of the owner.
- **Legend chips** under figures: small colour squares with mono labels.
- **A tiny human moment** per page, in a caption or footer. Warmth keeps precision from going sterile.

---

## 8. Motion (dialled down)

Principle: **motion explains or rewards. It never decorates.** Roughly one noticeable animation per viewport at a time.

| What | Behaviour |
|---|---|
| Easing | `cubic-bezier(.2,.7,.2,1)` for everything. No bounce, no overshoot |
| Durations | 250ms for colour/hover, 500–700ms for reveals |
| Headline and label reveals | **Mask-line rise.** Text slides up from behind a clipped edge (`overflow: hidden` wrapper, `translateY(105%) → 0`), staggered by 60ms, once, triggered at ~20% visibility. No opacity-only fades for headlines |
| Body blocks | Fade in and rise 8px, once |
| Rules and bars | Draw from left to right (`scaleX`) over 600ms when they enter |
| Shape continuity | Prefer elements that change shape over elements that fade: a marker grows into a panel, a list row expands into its description. Small doses only |
| Nav theme change | Colours cross-fade at 250ms when passing a light/dark boundary |
| Active step list | Opacity and orange rule transition at 300ms, driven by scroll position within the project |
| Work index hover | Row nudges 8px right; a tiny preview fades in. No cursor-follow effects |
| Section counter | Digits swap with a 150ms vertical slide |
| Small pops (markers, chips, numerals) | Optional closed-form damped spring, overshoot ≤ 4%. Never for layout, sections or the 3D camera |
| Scrolling | Native scroll. **No scroll-jacking, no smooth-scroll libraries, no parallax** |
| Page load | Content is simply there. No intro, loader or entrance sequence |

**Implementation rules**
- Scroll-linked values are **pure functions of scroll progress** (0 → 1 per section), with no timers and no state carried between frames. Scrolling back reverses them exactly. Prefer CSS `animation-timeline: view()/scroll()` where supported, with an IntersectionObserver or tiny `requestAnimationFrame` fallback.
- `prefers-reduced-motion: reduce` disables all reveals, line draws and 3D auto-rotation. Content shows immediately.
- Banned: crossfades between sections, blur-ins, glows, particles, 3D flips, long holds, anything that looks like a template.

---

## 9. 3D and interactive stages (proof of work)

These are the showpieces: the one place the page is allowed to be spectacular. Every project that has a model, point cloud, dataset or pipeline gets a real, interactive view built from the actual output, not a decorative stand-in.

**Look: "product on black"**
- Dark section, a single soft spotlight pool from above, a very slow falloff to `--ink`. The object appears to sit in a pool of light, like a catalogue product shot.
- Matte, slightly warm material (bone/cream), not glossy chrome. Soft shadows. No bloom, no neon.
- Annotations: thin 1px leader lines plus mono labels in orange / powder-blue / bone. 

**Interaction**
- Orbit controls with damping, restricted polar angle, zoom limited. Drag to rotate, with a mono hint (`DRAG TO ROTATE`) that fades after first interaction.
- Optional gentle idle rotation (≤ 2°/s) that stops on interaction and respects reduced motion.
- Scroll can step the camera between 2–4 preset views tied to the step list, so the object appears to move as you scroll through that project. This is the *only* scroll-linked animation of a 3D object on the page, and it is confined to that project's stage.

**Data and diagram stages** (light sections)
- Schematic 3D plots (point clouds on a sphere, embedding spaces, trajectories) in ink linework with orange for the "query" or "result" and a muted teal/powder for the field.
- Legends use small colour squares. Counts and labels in mono.

**Technical guidance**
- Stack: `three.js` (or `<model-viewer>` for simple cases). One canvas visible at a time. Lazy-initialise when the section is within 1 viewport of the screen, and pause rendering when it leaves.
- Assets: compressed glTF (Draco/Meshopt), If the source is `.obj`, convert it to `.glb`. Provide a static poster image so the section looks right before the canvas is ready, and as the no-WebGL fallback.
- Cap pixel ratio at 2. Target 60fps on a mid-range laptop. Touch: one-finger rotate, two-finger zoom, and don't trap vertical page scroll.

---

## 10. Imagery

- Real work only: renders, screenshots, plots, hardware photos. No stock photography, no gradient blobs, no AI-generated decoration.
- Photos of objects: dark seamless background, dramatic single light, centred, lots of negative space. Tiny caption below left.
- Portrait: greyscale, square or 4:5, flat cream panel behind.
- Illustration (optional, one per page): a single black-ink hand-drawn or technical line illustration with one orange accent. It acts as a visual joke or divider, never a hero.

---

## 11. Content scaffold (placeholders)

All placeholders below are filled from `content/portfolio-input.md` (see section 0).

```
NAV:        Work · About · Capabilities · Contact
INTRO:      [TAG: FIELD · FIELD · FIELD]
            [BIG WORD]
            [NAME]
            [ONE-LINE STATEMENT, ≤ 10 words]
            [Text link: See selected work]
            [CITY, COUNTRY] / [INSTITUTION OR STUDIO]
WORK INDEX: 01 [Project] — [category] — [year]   (one row per project, 8 today)
PROJECTS:   per project → No., tag, title, one-sentence statement,
            3–5 step list OR 3 facts, spec row, stage, caption, links
ABOUT:      [Greeting word] + portrait + 2 short paragraphs
            Education / Experience (2 columns)
            Focus / Tools / Languages (3 columns)
CAPABILITIES: 3 numbered capability rows in the orange blueprint panel
CONTACT:    [Invitation] + links + mega name
```

Writing voice: first person, plain, specific, short sentences. State results and limits honestly ("what it shows and where it falls short"). No buzzword stacks.

---

## 12. Responsive behaviour

- ≥1200px: full split layouts as described.
- 768–1199px: splits stack (title above, stage below), still alternating themes. Mega type scales via `clamp`.
- <768px: single column, 20px margins. Nav collapses to a text "Menu". Stage becomes full-bleed with a poster image first, and the 3D loads on tap (`TAP TO INTERACT`). Step lists stay visible. The section counter is hidden.
- Tables scroll horizontally only as a last resort. Prefer stacking label/value pairs.

---

## 13. Accessibility and quality bar

- Body text ≥ 16px, contrast ≥ 4.5:1. Orange never carries essential text.
- Real semantic HTML: one `<h1>`, `<section>` with ids matching the nav anchors, `<nav>`, `<figure>`/`<figcaption>`.
- 3D stages have a text alternative describing what's shown and keyboard-accessible controls for the view presets.
- Keyboard focus is always visible. Skip link at the top.
- Lighthouse targets: Performance ≥ 90 on desktop, with 3D initialised lazily. No layout shift from fonts (use `font-display: swap` and preload the two display weights).

---

## 14. Build notes

- **Stack:** a static site. Plain HTML + CSS + a small amount of vanilla JS, with `three.js` (plus `GLTFLoader`, `DRACOLoader` and `OrbitControls`, loaded from a pinned CDN version) only where a 3D stage needs it. No SPA framework, no animation library beyond what's needed (CSS transitions, scroll-driven CSS and IntersectionObserver cover almost everything).
- **Generation:** the page is generated from `content/portfolio-input.md` by a small dependency-light script, `tools/build_site.py` (Python 3 is installed on the owner's machine; the optional `markdown` package may be listed in `tools/requirements.txt`). It writes `index.html` only. The generated `index.html` is committed, so GitHub Pages serves it with no build step. Re-running the script after any edit to the input file must reproduce the page. Hand-written CSS and JS live in `assets/` and are never overwritten by the script.
- **Structure:** `index.html`, `assets/css/tokens.css` (the variables above), `assets/css/base.css`, `assets/css/components.css`, `assets/js/theme-nav.js` (nav inversion + section counter), `assets/js/reveal.js`, `assets/js/stage-*.js` (one per 3D stage), `assets/models`, `assets/img`. The site is one page, so the old `projects/*.html` pages mentioned in `README.md` are not generated. Update `README.md`'s structure section to match.
- **Theming:** each `<section>` carries `data-theme="light|dark|pastel|orange"`; CSS variables switch per theme so components don't need per-theme rules.
- **Build order:** tokens and type → top bar → intro → work index → one project section (light) → one project section (dark) → about → blueprint panel → footer → motion polish → 3D stages → responsive pass → accessibility pass.
- **Placeholder rule:** use obviously fake content (`[Project name]`) until real copy and assets are supplied. Never invent credentials, metrics or logos.

---

## 15. Do-not list

- Don't imitate any existing site's logo, wordmark treatment, copy, layout composition, animation or imagery. The result must be original.
- No loader, intro animation, animated or generated hero, particle fields, cursor effects, scroll-jacking, parallax or marquee text.
- No video, trailer, soundtrack or sound effects. No cursor-driven showpieces.
- No liquid glass, iris/aperture transitions, goo/metaball effects, or page-wide "everything morphs" choreography.
- No animated logo or letter-mark as the hero.
- No gradients as decoration, glassmorphism, drop shadows, rounded pill cards, emoji, or stock photos.
- No pure black/white backgrounds, no neon, no blue-black dark mode.
- No orange body text. No more than one saturated orange panel per screen.
- No multi-page navigation. Everything lives on one page with anchor links.
- Don't use more than two font families.

---

## 16. Final gut-check

Before calling any section done, it should pass these:
1. Squint test: can the light-to-dark rhythm and the orange be read at a glance?
2. Remove the colour: is the hierarchy still clear from size and weight alone?
3. Is there at least one tiny detail (a tick, a caption, a spec row) that shows someone cared?
4. Is every moving thing either explaining the work or responding to the visitor's input?
5. Does it feel original, like it could only belong to its owner?

---

## 17. Working agreement for the builder

- Work only inside `C:\Users\loren\Documents\Projects\Porfolio`. Do not read or write elsewhere.
- **You may create or overwrite:** `index.html`, `assets/css/`, `assets/js/`, `tools/`, the generated `assets/models/*/*.bin`, extracted figures in `assets/img/projects/`, and the `README.md` structure section. Edit `content/portfolio-input.md` and this file only when the owner asks. **Never modify** anything under `assets/docs/`, the source `.glb` models, `CNAME`, `.nojekyll` or `.github/`, and never open anything under `projects/`.
- **The content already exists** in `content/portfolio-input.md`. Do not ask the owner for it again. Ask only when a genuine choice is open (the display word in the intro, the order of projects) or a field a section needs is empty (for example no cover image for the connecting rod). Use the image placeholders described above for missing images, clearly marked text placeholders for anything else genuinely missing, and list them in your report.
- Build a static first pass of four sections only (intro, one light project, one dark 3D project, the orange blueprint panel) and show screenshots before continuing. Serve the site locally (`python -m http.server` from the repo root) to check it. Verify with the browser tools if available.
- Follow the build order in Section 14 and the motion limits in Section 8.
- When done, check desktop and mobile widths, check that the 3D models load, that every link and download resolves, and that no file from `projects/` is referenced. Report what was verified and what was not.
- Commit and push when the owner asks (they have allowed publishing the site live). A push publishes to `lorenzodallarosa.com` immediately.
