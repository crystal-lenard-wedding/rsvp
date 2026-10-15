# Local mobile menu regression checks

Run from the repository root:

```sh
python3 scripts/check-mobile-menu.py
```

Requires Python 3 and Chrome/Chromium. The check uses only Python's standard
library, with no pip packages, Node, build system, or running preview required.
It discovers `chromium`, `chromium-browser`, or `google-chrome` on PATH.
For another installation, set `CHROMIUM` to the browser executable:

```sh
CHROMIUM=/path/to/chrome python3 scripts/check-mobile-menu.py
```

The command starts a temporary loopback-only static server and headless browser
with an isolated profile, then cleans both up. It tests the working copy, never
production. Plausible requests are blocked before loading the page, and external
links are inspected without following them. Fonts may load from Google Fonts.
The `--no-sandbox` browser flag supports the Replit environment; only run this
against this trusted local site.

The 12 checks cover **320 × 844** and **390 × 844** touch-enabled viewports:

- Touch opening and Weekend Contacts activation, URL hash and destination focus.
- A visible destination heading with clearance beneath the fixed header,
  after smooth scrolling settles.
- Escape and touch close-button dismissal, focus return and actual touch
  scrolling after each dismissal or destination jump.
- Forward and backward keyboard traversal, including both focus-trap boundaries.
- Background scroll locking while the menu is open, starting partway down the page.
- A fully visible, unobscured, highlighted Mini Guest Guide link and New badge.

Checks use browser input events, not calls to the site's menu functions or
synthetic DOM clicks. Failed assertions or setup errors return a nonzero exit
code. Failures save a screenshot and diagnostic state under the ignored
`generated-artifacts/mobile-menu/` directory. For a focused rerun:

```sh
python3 scripts/check-mobile-menu.py Menu320.test_touch_weekend_contacts
```

These are Chromium regression checks, not a substitute for occasional testing
on real iOS Safari and Android devices.
