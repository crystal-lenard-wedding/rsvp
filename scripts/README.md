# Local regression checks

## Gift dialog

Run from the repository root:

```sh
python3 scripts/check-gift-dialog.py
```

Requires Python 3 and Chrome/Chromium, with the same executable discovery and
optional `CHROMIUM` override as the mobile-menu checks below. No packages,
build step or running preview server are needed. The shared `browser_check.py`
helper starts a loopback-only server and isolated browser, then cleans both up.

The suite covers 36 scenarios across desktop **1280 × 900** (mouse and wheel)
and mobile **390 × 844** (touch):

- All three gift buttons open the real `gratitudeModal` using Enter and Space.
- The selected fund, visible labelled dialog, initial close-button focus and
  background scroll lock are checked.
- Tab and Shift+Tab traverse every control in order and wrap at both boundaries,
  twice in each direction.
- Escape from inside the dialog, keyboard close-button activation, and mouse or
  touch close-button activation dismiss the dialog.
- Each dismissal hides the dialog, restores focus to the exact initiating gift
  button, releases the scroll lock and permits actual wheel or touch scrolling.
  The same input must also scroll the unlocked page before opening.

Payment links are only focused, never activated. External HTTPS requests
(including payment sites, analytics and fonts) are blocked before loading;
link activation and form submission are also prevented by test-only guards.
No money is sent, clipboard actions are not activated, and no real responses
are submitted. The suite tests only the local working copy and never publishes.

Failures return a nonzero exit code and save a PNG screenshot plus JSON state
(scenario, focused element, dialog markup and scroll/overflow state) under
the ignored `generated-artifacts/gift-dialog/` directory. Evidence is captured
per failing scenario; successful runs do not remove earlier evidence.

These are repeatable Chromium checks, not real-device Safari/Android coverage.

## Navigation analytics

```sh
python3 scripts/check-analytics-events.py
```

Uses the same dependency-free Python/Chromium helper described below. No Node,
packages, build step, or preview server is needed. All HTTPS requests are blocked,
including Plausible and the external Mini Guest Guide. No live reports are sent.

The analytics suite checks the real `index.html` and `analytics-events.js`:

- The seven exact existing report names across all 20 supported links in the
  desktop nav, mobile menu, guest-guide banner, hero buttons and guide cards.
- Exactly one dispatch per click, including nested targets and repeat clicks.
- Missing, throwing and non-callable analytics cannot cancel navigation or leak
  errors. Every local supported link also follows its real destination without
  a test cancellation handler in each unavailable-analytics mode.
- External guide links are not followed; the suite checks their href and that
  site code has not canceled their default navigation.
- Untracked links, including both Weekend Contacts shortcuts, emit no custom
  event. Recognized hrefs outside supported locations and non-link targets are
  ignored.

Failures print the mode, location, href and target variant and return a nonzero
exit code. This suite uses DOM click activation, not physical touch input; menu
accessibility and layout are covered separately below.

## Mobile menu

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

The 24 checks cover **320 × 844**, **390 × 844**, short portrait **320 × 420**
and landscape **844 × 390** touch-enabled viewports:

The short portrait size represents the usable page area with browser controls
taking up screen space. Both compact sizes must initially clip the guide itself,
not merely overflow the menu's bottom padding.

- Touch opening and Weekend Contacts activation, URL hash and destination focus.
- A visible destination heading with clearance beneath the fixed header,
  after smooth scrolling settles.
- Escape and touch close-button dismissal, focus return and actual touch
  scrolling after each dismissal or destination jump.
- Forward and backward keyboard traversal, including both focus-trap boundaries.
- Background scroll locking while the menu is open, starting partway down the page.
- A fully visible, unobscured, highlighted Mini Guest Guide link and New badge.
- On short and landscape screens, the guide starts clipped and must be reached
  with real touch scrolling inside the menu. Checks assert menu scroll movement,
  a stationary background (including at the bottom), and a reachable close control.
- Keyboard focus remains trapped after scrolling the menu, and both Escape and
  touch dismissal restore focus and actual page scrolling.

Checks use browser input events, not calls to the site's menu functions or
synthetic DOM clicks. Failed assertions or setup errors return a nonzero exit
code. Failures save a screenshot and diagnostic state under the ignored
`generated-artifacts/mobile-menu/` directory. For a focused rerun:

```sh
python3 scripts/check-mobile-menu.py Menu320.test_touch_weekend_contacts
python3 scripts/check-mobile-menu.py MenuLandscape
```

These are Chromium regression checks, not a substitute for occasional testing
on real iOS Safari and Android devices.
