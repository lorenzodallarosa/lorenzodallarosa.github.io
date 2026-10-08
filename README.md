# Aerospace Engineering Portfolio

Static site hosted on GitHub Pages.

## How it works
1. Edit **`content/portfolio-input.md`** (the only file you need to touch).
2. Ask Claude to "build the portfolio from the input file" - it generates the one-page `index.html` and the CSS/JS, following `content/DESIGN.md`.
3. Commit and push; GitHub Pages publishes automatically.

## Structure
```
content/portfolio-input.md   <- YOUR INPUT (profile, CV, education, projects)
content/DESIGN.md            <- design brief (look, layout, motion, 3D) the site is built from
assets/img/profile/          <- your photo
assets/img/projects/         <- one sub-folder per project (images, renders, plots)
assets/docs/                 <- CV PDF, reports, theses
assets/css, assets/js        <- generated styles and scripts
assets/models/               <- 3D models (.glb) for the interactive viewers
projects/                    <- LOCAL source PDFs and extractions (gitignored, never published)
tools/                       <- site generator script (input .md -> index.html)
index.html                   <- generated one-page site
CNAME                        <- custom domain (added at the domain step)
.nojekyll                    <- tells GitHub Pages to serve files as-is
```
