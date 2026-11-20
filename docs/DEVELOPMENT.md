# Portfolio development

Buildless HTML, CSS and JavaScript. GitHub Pages serves this directory from `main` → `/docs`.

## Local preview

From the repository root, run `python -m http.server 8000 --directory docs` and open http://localhost:8000.

## Editing

- `index.html`: page content, navigation, dialogs, SEO metadata.
- `style.css`: responsive design, themes, motion preferences.
- `app.js`: curated project data, filters, case studies, command palette, BFS lab.
- `../assets/header.svg`: GitHub profile banner.
- `../README.md`: GitHub profile.

Project descriptions intentionally distinguish implemented public features from future scope. No API keys or backend services are required. Fonts use Google Fonts with local system fallbacks.

## Accessibility

Native dialogs support Escape and focus containment. Navigation and controls support keyboard input. The grid uses one Tab stop with arrow-key navigation and Space/Enter wall toggling. Reduced-motion settings skip search animation; an explicit motion toggle and persistent light/dark theme are also provided.

## Checks

`node --check docs/app.js`

Browser checks: category filtering; each case study; command search and empty state; theme switch; grid wall toggles; shortest path; blocked goal; reset; dialog Escape; keyboard navigation. BFS runs locally and is a separate demonstration, not a hosted endpoint of the featured projects.
