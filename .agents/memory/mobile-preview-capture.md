---
name: Mobile preview capture
description: Avoid false blank-image reports when capturing anchored mobile pages with Chromium.
---

Chromium's one-shot headless screenshot of an anchored page can capture during smooth scrolling, before the intended section reaches the viewport. A dark area seen in that capture may be a different section, not a failed image.

**Why:** The wedding homepage's mobile photo looked blank in a headless screenshot at a story anchor, but inspection showed its image fully loaded. An instant scroll to the carousel followed by a capture showed the photo correctly.

**How to apply:** For visual QA of an anchored section, explicitly scroll to the element with instant behavior and capture after it settles. Check the image's natural width and element position before changing production code.