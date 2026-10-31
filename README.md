# Aerospace Engineering Portfolio

Static site hosted on GitHub Pages.

## How it works
1. Edit **`content/portfolio-input.md`** (the only file you need to touch).
2. Run `python tools/build_site.py` (Python 3, standard library only). It regenerates the one-page `index.html` from the input file, following `content/DESIGN.md`, rebuilds the obfuscated 3D models, writes the crawler files (`robots.txt`, `sitemap.xml`, `llms.txt`), and lists any image placeholders still waiting for a file.
   - New image: drop it in `assets/img/projects/<slug>/` with the name used in the input file, then rebuild.
   - New CV: replace `assets/docs/Lorenzo Dalla Rosa.pdf` and update the CV sections of the input file.
3. Preview locally with `python -m http.server` from the repo root, then open http://localhost:8000.
4. Commit and push; GitHub Pages publishes automatically.

## Structure
```
content/portfolio-input.md   <- YOUR INPUT (profile, CV, education, projects)
content/DESIGN.md            <- design brief (look, layout, motion, 3D) the site is built from
tools/build_site.py          <- generator: input .md -> index.html
index.html                   <- generated one-page site (do not edit by hand)
robots.txt, sitemap.xml, llms.txt <- generated crawler files (search engines and AI assistants)
<key>.txt                     <- IndexNow key; the deploy workflow pings Bing when content changes
assets/css/                  <- tokens.css, base.css, components.css (hand-written)
assets/js/                   <- reveal.js, theme-nav.js, site.js, math.js, tunnel.js (footer easter egg), stage-core.js + stage-projects.js (3D viewers)
assets/img/profile/          <- your photo
assets/img/projects/         <- one sub-folder per project (cover.* is the poster and index preview)
assets/models/               <- source .glb models (local only, gitignored) + obfuscated .bin copies the site loads
assets/docs/                 <- CV PDF, reports, theses
projects/                    <- LOCAL source PDFs and extractions (gitignored, never published)
CNAME                        <- custom domain
.nojekyll                    <- tells GitHub Pages to serve files as-is
```
