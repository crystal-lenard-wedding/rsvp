---
name: Chromium touch checks
description: Avoid false scroll failures from headless Chromium's synthetic touch gestures.
---

Treat a successful DevTools gesture response as input delivery, not proof that
the page actually scrolled. In this workspace's headless Chromium, a synthesized
scroll with a touch source returned successfully without moving a normally
scrollable page, while a sequence of touch-start, touch-move and touch-end
events did scroll it.

**Why:** An input-driver limitation can otherwise look like a site scroll-lock
regression. Do not change guest-facing navigation to fix that false failure.

**How to apply:** For touch scroll checks, establish that the same input scrolls
the unlocked page before checking a locked state. Assert actual scroll position,
not just inline overflow styles or successful browser protocol responses.

Do not assume a menu's positive scroll range means its last link is clipped.
Bottom padding can overflow even while every link is fully visible.

**Why:** A short-phone test initially exercised only padding overflow, not
the required touch access to an offscreen destination.

**How to apply:** Check the target's actual viewport bounds before scrolling
and require it to start clipped in overflow-specific cases. Choose compact
viewport dimensions from measured content geometry, not device labels alone.
