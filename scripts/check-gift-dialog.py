#!/usr/bin/env python3
"""Local gift-dialog regression checks using only Python and Chromium."""

import base64
import json
import unittest

from browser_check import Browser, ROOT, wait_for


MODAL = "#gratitudeModal"
CLOSE = f"{MODAL} .gratitude-close"
FOCUS_ORDER = [
    CLOSE,
    f"{MODAL} .gratitude-option:nth-child(1) a",
    f"{MODAL} .gratitude-option:nth-child(1) summary",
    f"{MODAL} .gratitude-option:nth-child(2) button",
    f"{MODAL} .gratitude-option:nth-child(2) summary",
    f"{MODAL} .gratitude-option:nth-child(3) a",
    f"{MODAL} .gratitude-option:nth-child(3) summary",
]


class GiftDialogChecks:
    @classmethod
    def setUpClass(cls):
        cls.browser = Browser().__enter__()
        cls.addClassCleanup(cls.browser.__exit__, None, None, None)
        # Block third-party HTTPS, including fonts, analytics and payment sites.
        cls.browser.call("Network.setBlockedURLs", {"urls": ["https://*"]})
        cls.browser.call("Page.addScriptToEvaluateOnNewDocument", {"source": """
            // Defense in depth: never activate payment links or submit responses.
            window.addEventListener('click', event => {
                if (event.target.closest?.('a[href]')) event.preventDefault();
            }, true);
            window.addEventListener('submit', event => event.preventDefault(), true);
            window.open = () => { throw new Error('External windows forbidden in gift checks'); };
        """})

    def check(self, expression, message):
        wait_for(lambda: self.browser.js(expression),
                 f"{self.width}x{self.height}: {message}")

    def focused(self, selector):
        self.check(f"document.activeElement === document.querySelector({json.dumps(selector)})",
                   f"Expected focus on {selector}")

    def scroll_input(self):
        if self.mobile:
            self.browser.swipe()
        else:
            self.browser.call("Input.dispatchMouseEvent", {
                "type": "mouseWheel", "x": self.width - 8, "y": self.height / 2,
                "deltaX": 0, "deltaY": 220,
            })

    def can_scroll(self):
        before = self.browser.settled_scroll()
        self.scroll_input()
        self.assertGreater(self.browser.settled_scroll(), before + 30,
                           "Actual page scrolling must work, not just overflow styles")

    def open_dialog(self, trigger, key):
        self.browser.load(self.width, self.height, mobile=self.mobile)
        self.assertEqual(self.browser.js("[innerWidth, innerHeight]"), [self.width, self.height])
        self.assertEqual(self.browser.js("matchMedia('(pointer: coarse)').matches"), self.mobile)
        self.check("typeof openGratitudeModal === 'function'", "Gift dialog code must load")
        # Position/focus the initiating button, but never call the site's open function.
        self.browser.js(f"""document.querySelector({json.dumps(trigger)}).scrollIntoView({{
            block: 'center', behavior: 'instant'
        }})""")
        self.browser.settled_scroll()
        self.can_scroll()  # Prove the input driver scrolls before asserting a lock.
        self.browser.js(f"document.querySelector({json.dumps(trigger)}).focus()")
        self.focused(trigger)
        self.browser.settled_scroll()
        self.browser.target_point(trigger)
        self.browser.key(key)
        self.check("""(() => {
            const modal = document.querySelector('#gratitudeModal');
            return modal.classList.contains('open')
                && modal.getAttribute('aria-hidden') === 'false'
                && modal.getAttribute('role') === 'dialog'
                && modal.getAttribute('aria-modal') === 'true'
                && document.getElementById(modal.getAttribute('aria-labelledby'))?.textContent.trim()
                && getComputedStyle(modal).display !== 'none'
                && getComputedStyle(document.body).overflowY === 'hidden';
        })()""", "Keyboard activation must expose a labelled modal and lock page scrolling")
        self.focused(CLOSE)
        self.browser.target_point(CLOSE)
        self.assertEqual(self.browser.js("document.querySelector('#gratitudeFund').textContent"),
                         self.browser.js(f"""document.querySelector({json.dumps(trigger)})
                             .closest('.registry-card').querySelector('.registry-name')
                             .textContent.replaceAll("'", "’")"""),
                         "The dialog must belong to the initiating gift button")
        before = self.browser.settled_scroll()
        self.scroll_input()
        self.assertAlmostEqual(self.browser.settled_scroll(), before, delta=1,
                               msg="Opening the dialog must lock background scrolling")

    def traverse_dialog(self):
        self.assertEqual(self.browser.js("""document.querySelectorAll(
            '#gratitudeModal a[href], #gratitudeModal button:not([disabled]), '
            + '#gratitudeModal summary').length"""), len(FOCUS_ORDER))
        # Traverse every control and both boundaries twice. Payment links are
        # focused only, never activated; the copy-email button is not activated.
        for _ in range(2):
            for selector in FOCUS_ORDER[1:] + FOCUS_ORDER[:1]:
                self.browser.key("Tab")
                self.focused(selector)
            for selector in list(reversed(FOCUS_ORDER[1:])) + FOCUS_ORDER[:1]:
                self.browser.key("Tab", shift=True)
                self.focused(selector)

    def closed(self, trigger):
        self.check("""(() => {
            const modal = document.querySelector('#gratitudeModal');
            return !modal.classList.contains('open')
                && modal.getAttribute('aria-hidden') === 'true'
                && getComputedStyle(modal).display === 'none'
                && !['hidden', 'clip'].includes(getComputedStyle(document.body).overflowY);
        })()""", "Dismissal must hide the dialog and release the scroll lock")
        self.focused(trigger)
        self.assertEqual(self.browser.js("location.href"), self.browser.url,
                         "Checks must stay on the local homepage")
        self.can_scroll()

    def capture_failure(self, scenario):
        output = ROOT / "generated-artifacts" / "gift-dialog"
        output.mkdir(parents=True, exist_ok=True)
        name = f"{self.width}x{self.height}-{self._testMethodName}-{scenario['gift']}-{scenario['key']}"
        try:
            shot = self.browser.call("Page.captureScreenshot", {"format": "png"})["data"]
            (output / f"{name}.png").write_bytes(base64.b64decode(shot))
            state = self.browser.js("""({
                url: location.href, scrollY, width: innerWidth, height: innerHeight,
                activeElement: document.activeElement?.outerHTML,
                modal: document.querySelector('#gratitudeModal')?.outerHTML,
                bodyOverflow: getComputedStyle(document.body).overflow,
                htmlOverflow: getComputedStyle(document.documentElement).overflow,
                dialogScrollTop: document.querySelector('.gratitude-dialog')?.scrollTop
            })""")
            state["scenario"] = scenario
            (output / f"{name}.json").write_text(json.dumps(state, indent=2))
            print(f"\nFailure evidence: {output / name}", flush=True)
        except Exception as error:
            print(f"\nCould not capture failure evidence: {error}", flush=True)

    def run_scenarios(self, dismissal):
        for gift in ("cat", "africa", "puppy"):
            for key in ("Enter", " "):
                scenario = {"gift": gift, "key": "Space" if key == " " else key,
                            "dismissal": dismissal}
                with self.subTest(**scenario):
                    try:
                        trigger = f"#registry .{gift}-btn"
                        self.open_dialog(trigger, key)
                        self.traverse_dialog()
                        if dismissal == "escape":
                            # Escape works from inside the dialog, not only its close button.
                            self.browser.key("Tab")
                            self.focused(FOCUS_ORDER[1])
                            self.browser.key("Escape")
                        elif dismissal == "keyboard-close":
                            self.browser.key(key)
                        elif self.mobile:
                            self.browser.tap(CLOSE)
                        else:
                            self.browser.click(CLOSE)
                        self.closed(trigger)
                    except Exception:
                        self.capture_failure(scenario)
                        raise

    def test_escape(self):
        self.run_scenarios("escape")

    def test_keyboard_close_button(self):
        self.run_scenarios("keyboard-close")

    def test_pointer_close_button(self):
        self.run_scenarios("pointer-close")


class Desktop(GiftDialogChecks, unittest.TestCase):
    width, height, mobile = 1280, 900, False


class Mobile(GiftDialogChecks, unittest.TestCase):
    width, height, mobile = 390, 844, True


if __name__ == "__main__":
    unittest.main(verbosity=2)
