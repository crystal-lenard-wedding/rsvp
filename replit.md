# Local preview

This repository is a static website hosted in production by GitHub Pages at
https://crystal-lenard-wedding.github.io/rsvp/. Keep the existing HTML and asset
structure compatible with GitHub Pages. Replit is for editing and previewing,
not production hosting.

This site remains current and should be updated alongside the linked Mini Guest
Guide. Neither site supersedes the other. Keep the guide easy to find without
repeating its link throughout the site's content or implying this site's
schedule and travel information are outdated.

Run the `Preview static site` workflow to serve the repository root with
`python3 -m http.server 5000 --bind 0.0.0.0`. Open the Replit web preview
to view `index.html`; the other pages are linked from it. There are no
dependencies to install or build steps. Changes to tracked files should be
committed and pushed to the GitHub repository when approved for publication.

The RSVP and contact links use external services. Avoid submitting real
responses while testing the local preview.

Before each production update, run `python3 scripts/bump-version.py` after
editing the site. It increments `version.json` and the version embedded in all
four HTML pages, including the `version-check.js` cache-busting URL. Commit and
push those files together with the update to the existing GitHub Pages repo.
Styles and page-specific JavaScript are inline in the HTML, so they always
arrive with the page. Do not add a service worker or offline cache.