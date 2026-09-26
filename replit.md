# Local preview

This repository is a static website hosted in production by GitHub Pages at
https://crystal-lenard-wedding.github.io/rsvp/. Keep the existing HTML and asset
structure compatible with GitHub Pages. Replit is for editing and previewing,
not production hosting.

Run the `Preview static site` workflow to serve the repository root with
`python3 -m http.server 5000 --bind 0.0.0.0`. Open the Replit web preview
to view `index.html`; the other pages are linked from it. There are no
dependencies to install or build steps. Changes to tracked files should be
committed and pushed to the GitHub repository when approved for publication.

The RSVP and contact links use external services. Avoid submitting real
responses while testing the local preview.