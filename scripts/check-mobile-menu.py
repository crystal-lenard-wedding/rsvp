#!/usr/bin/env python3
"""Run with python3 scripts/check-mobile-menu.py. No preview server needed."""

import base64
import json
import unittest

from browser_check import Browser, ROOT, wait_for


class MobileMenuChecks:
    width = None
    height = 844
    expects_overflow = False

    @classmethod
    def setUpClass(cls):
        cls.browser = Browser().__enter__()
        cls.addClassCleanup(cls.browser.__exit__, None, None, None)

    def setUp(self):
        self.addCleanup(self.capture_failure)
        self.browser.load(self.width, self.height)
        self.assertEqual(self.browser.js("innerWidth"), self.width)
        self.assertEqual(self.browser.js("innerHeight"), self.height)

    def capture_failure(self):
        """Leave evidence only when a check fails; keep output out of Git."""
        result = self._outcome.result
        if not any(test is self for test, _ in result.failures + result.errors):
            return
        output = ROOT / "generated-artifacts" / "mobile-menu"
        output.mkdir(parents=True, exist_ok=True)
        name = f"{self.width}x{self.height}-{self._testMethodName}"
        try:
            shot = self.browser.call("Page.captureScreenshot", {"format": "png"})["data"]
            (output / f"{name}.png").write_bytes(base64.b64decode(shot))
            state = self.browser.js("""({
                url: location.href, scrollY, width: innerWidth, height: innerHeight,
                activeElement: document.activeElement?.outerHTML,
                menu: document.querySelector('#mobileMenu')?.outerHTML,
                menuScrollTop: document.querySelector('#mobileMenu')?.scrollTop,
                menuScrollHeight: document.querySelector('#mobileMenu')?.scrollHeight,
                menuClientHeight: document.querySelector('#mobileMenu')?.clientHeight,
                overflow: getComputedStyle(document.body).overflow
            })""")
            (output / f"{name}.json").write_text(json.dumps(state, indent=2))
            print(f"\nFailure evidence: {output / name}", flush=True)
        except Exception as error:
            print(f"\nCould not capture failure evidence: {error}", flush=True)

    def check(self, expression, message):
        wait_for(lambda: self.browser.js(expression),
                 f"{self.width}x{self.height}: {message}")

    def focused(self, selector):
        self.check(f"document.activeElement === document.querySelector({json.dumps(selector)})",
                   f"Focus should be on {selector}")

    def open_menu(self):
        self.browser.tap("#menuButton")
        self.check("""document.querySelector('#mobileMenu').classList.contains('open')
            && document.querySelector('#mobileMenu').getAttribute('aria-hidden') === 'false'
            && document.querySelector('#menuButton').getAttribute('aria-expanded') === 'true'
            && getComputedStyle(document.body).overflow === 'hidden'""",
                   "Touch opening should expose the dialog and lock page scrolling")
        self.focused("#mobileMenu .mobile-close")
        self.assert_close_reachable()

    def target_visible(self, selector):
        return self.browser.js(f"""(() => {{
            const el = document.querySelector({json.dumps(selector)});
            const r = el.getBoundingClientRect();
            const menu = document.querySelector('#mobileMenu').getBoundingClientRect();
            return r.width > 0 && r.height > 0
                && r.top >= Math.max(0, menu.top) && r.bottom <= Math.min(innerHeight, menu.bottom)
                && r.left >= 0 && r.right <= innerWidth
                && el.contains(document.elementFromPoint(r.x + r.width/2, r.y + r.height/2));
        }})()""")

    def assert_close_reachable(self):
        self.assertTrue(self.target_visible("#mobileMenu .mobile-close"),
                        "Close control must remain onscreen and unobscured")

    def touch_reach(self, selector):
        """Reach a clipped menu item using input only, never scrollIntoView."""
        background = self.browser.settled_scroll()
        for _ in range(8):
            self.assert_close_reachable()
            if self.target_visible(selector):
                return
            before = self.browser.settled_scroll("#mobileMenu")
            self.browser.swipe("#mobileMenu")
            after = self.browser.settled_scroll("#mobileMenu")
            self.assertGreater(after, before + 1, "Touch must move the overflowing menu")
            self.assertAlmostEqual(self.browser.settled_scroll(), background, delta=1,
                                   msg="Menu scrolling must not move the background page")
            self.assert_close_reachable()
        self.fail(f"Touch scrolling could not reach {selector}")

    def closed(self):
        self.check("""!document.querySelector('#mobileMenu').classList.contains('open')
            && document.querySelector('#mobileMenu').getAttribute('aria-hidden') === 'true'
            && document.querySelector('#menuButton').getAttribute('aria-expanded') === 'false'
            && getComputedStyle(document.querySelector('#mobileMenu')).display === 'none'
            && !['hidden', 'clip'].includes(getComputedStyle(document.body).overflowY)""",
                   "Closing should hide the dialog, reset ARIA and release the scroll lock")

    def can_scroll(self):
        before = self.browser.settled_scroll()
        self.browser.swipe()
        after = self.browser.settled_scroll()
        self.assertGreater(after, before + 30, "A real touch swipe must scroll the page after closing")

    def test_touch_weekend_contacts(self):
        self.open_menu()
        self.touch_reach('#mobileMenu a[href="#weekend-contacts"]')
        self.browser.tap('#mobileMenu a[href="#weekend-contacts"]')
        self.closed()
        self.check("location.hash === '#weekend-contacts'", "Touch should navigate to Weekend Contacts")
        self.focused("#weekend-contacts")
        self.browser.settled_scroll()
        self.assertTrue(self.browser.js("""(() => {
            const section = document.querySelector('#weekend-contacts');
            const h = document.querySelector('#weekend-contacts-heading').getBoundingClientRect();
            const nav = document.querySelector('body > nav').getBoundingClientRect();
            return section.getAttribute('tabindex') === '-1'
                && getComputedStyle(section).opacity === '1'
                && h.top >= nav.bottom + 8 && h.bottom <= innerHeight
                && h.left >= 0 && h.right <= innerWidth;
        })()"""), "Destination heading must be visible with breathing room below the fixed header")
        self.can_scroll()

    def test_escape_returns_focus_and_unlocks(self):
        self.open_menu()
        self.browser.key("Escape")
        self.closed()
        self.focused("#menuButton")
        self.can_scroll()

    def test_close_button_returns_focus_and_unlocks(self):
        self.open_menu()
        self.touch_reach("#mobileMenu a.guide-link")
        self.assert_close_reachable()
        self.browser.tap("#mobileMenu .mobile-close")
        self.closed()
        self.focused("#menuButton")
        self.can_scroll()

    def test_tab_and_shift_tab_trap(self):
        self.open_menu()
        self.touch_reach("#mobileMenu a.guide-link")
        # Obtain the expected DOM order, but use real keyboard events to traverse it.
        selectors = self.browser.js("""Array.from(
            document.querySelectorAll('#mobileMenu button, #mobileMenu a[href]'),
            (_, i) => `#mobileMenu > :nth-child(${i + 1})`)""")
        self.assertGreater(len(selectors), 3)
        for selector in selectors[1:] + selectors[:1]:
            self.browser.key("Tab")
            self.focused(selector)
            self.assertTrue(self.browser.js(
                "document.querySelector('#mobileMenu').contains(document.activeElement)"))
            self.assert_close_reachable()
        for selector in list(reversed(selectors[1:])) + selectors[:1]:
            self.browser.key("Tab", shift=True)
            self.focused(selector)
            self.assertTrue(self.browser.js(
                "document.querySelector('#mobileMenu').contains(document.activeElement)"))
            self.assert_close_reachable()
        self.browser.key("Escape")
        self.closed()
        self.focused("#menuButton")
        self.can_scroll()

    def test_menu_locks_background_scrolling(self):
        self.browser.swipe()
        before = self.browser.settled_scroll()
        self.assertGreater(before, 30, "The page must be scrollable before opening")
        self.open_menu()
        locked_at = self.browser.settled_scroll()
        self.browser.swipe()
        self.assertAlmostEqual(self.browser.settled_scroll(), locked_at, delta=1,
                               msg="Swiping the open menu must not move the background page")
        self.browser.key("Escape")
        self.closed()
        self.focused("#menuButton")
        self.can_scroll()

    def test_highlighted_guest_guide_is_visible(self):
        self.open_menu()
        if self.expects_overflow:
            self.assertFalse(self.target_visible("#mobileMenu a.guide-link"),
                             "Short-screen case must exercise an initially clipped guide")
            self.assertTrue(self.browser.js("""(() => {
                const menu = document.querySelector('#mobileMenu');
                return menu.scrollHeight > menu.clientHeight && menu.scrollTop === 0;
            })()"""), "Short-screen menu must initially overflow")
        else:
            self.assertTrue(self.target_visible("#mobileMenu a.guide-link"),
                            "Tall-screen guide must remain visible without scrolling")
        self.touch_reach("#mobileMenu a.guide-link")
        self.assertTrue(self.browser.js("""(() => {
            const link = document.querySelector('#mobileMenu a.guide-link');
            const badge = link?.querySelector('.nav-guide-new');
            if (!link || !badge) return false;
            const r = link.getBoundingClientRect(), b = badge.getBoundingClientRect();
            const style = getComputedStyle(link);
            const menu = getComputedStyle(document.querySelector('#mobileMenu'));
            return link.textContent.includes('Mini Guest Guide') && badge.textContent.trim() === 'New'
                && link.href === 'https://crystal-lenard-guest-guide.replit.app/'
                && r.width > 0 && r.height > 0 && r.top >= 0 && r.bottom <= innerHeight
                && r.left >= 0 && r.right <= innerWidth
                && b.width > 0 && b.height > 0 && b.top >= 0 && b.bottom <= innerHeight
                && b.left >= 0 && b.right <= innerWidth
                && style.visibility === 'visible' && style.opacity === '1'
                && style.backgroundColor !== 'rgba(0, 0, 0, 0)'
                && style.backgroundColor !== menu.backgroundColor
                && style.borderTopStyle !== 'none' && parseFloat(style.borderTopWidth) > 0
                && link.contains(document.elementFromPoint(r.x + r.width/2, r.y + r.height/2));
        })()"""), "Mini Guest Guide and New badge must be onscreen, unobscured and highlighted")
        if self.expects_overflow:
            # Another swipe at the bottom must not chain through to the page.
            background = self.browser.settled_scroll()
            self.browser.swipe("#mobileMenu")
            self.browser.settled_scroll("#mobileMenu")
            self.assertAlmostEqual(self.browser.settled_scroll(), background, delta=1)
        self.assert_close_reachable()
        self.browser.key("Escape")
        self.closed()
        self.focused("#menuButton")
        self.can_scroll()


class Menu320(MobileMenuChecks, unittest.TestCase):
    width = 320


class Menu390(MobileMenuChecks, unittest.TestCase):
    width = 390


class MenuShortPortrait(MobileMenuChecks, unittest.TestCase):
    width = 320
    height = 420
    expects_overflow = True


class MenuLandscape(MobileMenuChecks, unittest.TestCase):
    width = 844
    height = 390
    expects_overflow = True


if __name__ == "__main__":
    unittest.main(verbosity=2)
