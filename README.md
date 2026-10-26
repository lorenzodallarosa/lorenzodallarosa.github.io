# Aerospace Engineering Portfolio

Static site hosted on GitHub Pages.

## How it works
1. Edit **`content/portfolio-input.md`** (the only file you need to touch).
2. Run `python tools/build_site.py` (Python 3, standard library only). It regenerates the one-page `index.html` from the input file, following `content/DESIGN.md`.
3. Preview locally with `python -m http.server` from the repo root, then open http://localhost:8000.
4. Commit and push; GitHub Pages publishes automatically.

## Structure
```
content/portfolio-input.md   <- YOUR INPUT (profile, CV, education, projects)
content/DESIGN.md            <- design brief (look, layout, motion, 3D) the site is built from
tools/build_site.py          <- generator: input .md -> index.html
index.html                   <- generated one-page site (do not edit by hand)
assets/css/                  <- tokens.css, base.css, components.css (hand-written)
assets/js/                   <- reveal.js, theme-nav.js, stage-core.js + stage-*.js (3D viewers)
assets/img/profile/          <- your photo
assets/img/projects/         <- one sub-folder per project (cover.* is the poster and index preview)
assets/models/               <- 3D models (.glb) for the interactive viewers
assets/docs/                 <- CV PDF, reports, theses
projects/                    <- LOCAL source PDFs and extractions (gitignored, never published)
CNAME                        <- custom domain
.nojekyll                    <- tells GitHub Pages to serve files as-is
```
