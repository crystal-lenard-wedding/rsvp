---
name: Site cache versioning
description: Keep the static site's browser cache invalidation consistent across all pages.
---

When updating the site for release, change the version marker on every HTML page and the version manifest together. The script URL's version parameter should change in the same pass.

**Why:** Browsers can keep serving an older homepage even after the local static server has the new file. The version check can request a fresh URL, but inconsistent page markers leave some pages on stale or permanently versioned URLs.

**How to apply:** Treat the HTML markers and manifest as one release-wide value. A content change in one page still requires a coordinated bump across the static pages so navigation does not alternate between versions.