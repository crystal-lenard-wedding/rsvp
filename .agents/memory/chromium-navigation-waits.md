---
name: Chromium navigation waits
description: Distinguish transient DevTools execution-context errors from real navigation failures.
---

Browser checks that poll JavaScript during real page navigation must tolerate only transient execution-context lifetime errors, within a bounded deadline. Do not broadly suppress evaluation errors.

**Why:** In this environment, a normal detail-page navigation raced a DevTools evaluation and returned “Inspected target navigated or closed” even though the navigation succeeded. A URL poll without this distinction can intermittently fail valid navigation.

**How to apply:** Use navigation-aware polling when waiting across document changes. Keep ordinary script exceptions fatal and ensure a genuinely closed browser or stalled destination still fails within the timeout.
