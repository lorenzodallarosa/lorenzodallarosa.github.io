# Aerospace Engineering Portfolio

Static site hosted on GitHub Pages.

## How it works
1. Edit **`content/portfolio-input.md`** (the only file you need to touch).
2. Ask Claude to "build the portfolio from the input file" - it generates `index.html`, `projects/*.html` and the CSS/JS.
3. Commit and push; GitHub Pages publishes automatically.

## Structure
```
content/portfolio-input.md   <- YOUR INPUT (profile, CV, education, projects)
assets/img/profile/          <- your photo
assets/img/projects/         <- one sub-folder per project (images, renders, plots)
assets/docs/                 <- CV PDF, reports, theses
assets/css, assets/js        <- generated styles and scripts
projects/                    <- generated project detail pages
index.html                   <- generated home page
CNAME                        <- custom domain (added at the domain step)
.nojekyll                    <- tells GitHub Pages to serve files as-is
```
