#!/usr/bin/env python3
"""Navigation analytics contract checks. Run directly with Python and Chromium."""

import json
import unittest

from browser_check import Browser, wait_for


# Deliberately independent of analytics-events.js: these are existing report names.
EVENTS = {
    "#schedule": "Schedule Click",
    "#dresscode": "Dress Code Click",
    "#registry": "Registry Click",
    "travel.html": "Travel Click",
    "accommodations.html": "Accommodations Click",
    "explore.html": "Explore Click",
    "https://crystal-lenard-guest-guide.replit.app/": "Mini Guest Guide Click",
}
GUIDE = "https://crystal-lenard-guest-guide.replit.app/"
LOCATIONS = {
    "body > nav": list(EVENTS),
    ".mobile-menu": list(EVENTS),
    ".guest-guide-banner": [GUIDE],
    ".hero-cta": [GUIDE, "#schedule"],
    ".guide-grid": ["travel.html", "accommodations.html", "explore.html"],
}
MODES = {
    "available": "window.plausible = name => window.analyticsCalls.push(name)",
    "missing": "delete window.plausible",
    "throwing": """window.plausible = name => {
        window.analyticsCalls.push(name); throw new Error('Analytics unavailable');
    }""",
    "non-callable": "window.plausible = {}",
}


def selector(location, href):
    return f"{location} a[href={json.dumps(href)}]"


class AnalyticsChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser = Browser().__enter__()
        cls.addClassCleanup(cls.browser.__exit__, None, None, None)
        # No third-party scripts, fonts or guest-guide requests during this suite.
        cls.browser.call("Network.setBlockedURLs", {"urls": ["https://*"]})

    def setUp(self):
        self.browser.load(1280)
        self.browser.js("""
            window.analyticsCalls = [];
            window.analyticsErrors = [];
            window.addEventListener('error', e => analyticsErrors.push(e.message));
        """)

    def test_supported_locations_and_script_wiring(self):
        self.assertEqual(self.browser.js("""Array.from(document.scripts)
            .filter(s => s.getAttribute('src')?.split('?')[0] === 'analytics-events.js')
            .length"""), 1, "Homepage must load the analytics handler exactly once")
        for location, hrefs in LOCATIONS.items():
            with self.subTest(location=location):
                actual = self.browser.js(f"""Array.from(
                    document.querySelectorAll({json.dumps(location + ' a[href]')}),
                    a => a.getAttribute('href')).filter(href => {json.dumps(list(EVENTS))}.includes(href))
                """)
                self.assertCountEqual(actual, hrefs, "Supported navigation links changed")
        self.assertEqual(self.browser.js(
            """document.querySelectorAll('.mobile-menu a[href="#weekend-contacts"]').length"""
        ), 1, "Weekend Contacts must remain an explicit untracked menu destination")

    def test_exactly_once_for_every_link_and_nested_target(self):
        # Observe at window, AFTER document's delegated listener. Only this test
        # cancels default navigation, so no external links or forms are followed.
        self.browser.js("""
            window.addEventListener('click', event => {
                window.wasPrevented = event.defaultPrevented;
                event.preventDefault();
            });
        """)
        for mode, setup in MODES.items():
            self.browser.js(setup)
            for location, hrefs in LOCATIONS.items():
                for href in hrefs:
                    for nested in (False, True):
                        with self.subTest(mode=mode, location=location, href=href, nested=nested):
                            result = self.browser.js(f"""(() => {{
                                const link = document.querySelector({json.dumps(selector(location, href))});
                                if (!link) throw new Error('Missing supported link');
                                analyticsCalls.length = analyticsErrors.length = 0;
                                const child = document.createElement('span');
                                child.textContent = 'Nested click target';
                                if ({json.dumps(nested)}) link.append(child);
                                const target = {json.dumps(nested)} ? child : link;
                                target.dispatchEvent(new MouseEvent('click', {{
                                    bubbles: true, cancelable: true
                                }}));
                                child.remove();
                                return {{calls: analyticsCalls, errors: analyticsErrors,
                                    prevented: wasPrevented}};
                            }})()""")
                            expected = [EVENTS[href]] if mode in ("available", "throwing") else []
                            self.assertEqual(result["calls"], expected, "Wrong report or duplicate dispatch")
                            self.assertEqual(result["errors"], [], "Analytics error escaped the handler")
                            self.assertFalse(result["prevented"], "Site code canceled navigation")

    def test_untracked_links_and_non_link_targets_stay_untracked(self):
        self.browser.js(MODES["available"])
        result = self.browser.js(f"""(() => {{
            window.addEventListener('click', e => e.preventDefault());
            const supported = {json.dumps(list(LOCATIONS))}.join(', ');
            const events = {json.dumps(EVENTS)};
            // Include every current untracked anchor, especially BOTH Weekend
            // Contacts shortcuts and Story, not just a manufactured fixture.
            const links = [...document.querySelectorAll('a[href]')].filter(a =>
                !a.closest(supported) || !events[a.getAttribute('href')]);
            const contacts = links.filter(a => a.getAttribute('href') === '#weekend-contacts');
            for (const link of links) link.click();
            // Recognized hrefs outside supported locations must not count.
            for (const href of Object.keys(events)) {{
                const link = document.createElement('a');
                link.href = href;
                document.body.append(link);
                link.click();
                link.remove();
            }}
            document.body.dispatchEvent(new MouseEvent('click', {{bubbles: true}}));
            document.createTextNode('not an Element').dispatchEvent(
                new MouseEvent('click', {{bubbles: true}}));
            document.dispatchEvent(new MouseEvent('click', {{bubbles: true}}));
            return {{calls: analyticsCalls, errors: analyticsErrors, contacts: contacts.length}};
        }})()""")
        self.assertGreaterEqual(result["contacts"], 2, "Keep both Weekend Contacts controls covered")
        self.assertEqual(result["calls"], [], "An untracked link silently acquired an event")
        self.assertEqual(result["errors"], [], "Non-link clicks must be harmless")

    def test_unavailable_analytics_allows_real_local_navigation(self):
        # Unlike the dispatch matrix, these clicks have NO preventDefault guard.
        # Exercise every local supported link and Weekend Contacts in the real DOM.
        for mode in ("missing", "throwing", "non-callable"):
            for location, hrefs in LOCATIONS.items():
                local_hrefs = [href for href in hrefs if not href.startswith("https:")]
                if location == ".mobile-menu":
                    local_hrefs.append("#weekend-contacts")
                for href in local_hrefs:
                    with self.subTest(mode=mode, location=location, href=href):
                        self.browser.load(390 if location == ".mobile-menu" else 1280)
                        self.browser.js("window.analyticsCalls = [];" + MODES[mode])
                        if location == ".mobile-menu":
                            self.browser.js("toggleMenu()")
                        self.browser.js(
                            f"document.querySelector({json.dumps(selector(location, href))}).click()"
                        )
                        expected = self.browser.url + href if href.startswith("#") else (
                            self.browser.url.rsplit("/", 1)[0] + "/" + href
                        )
                        wait_for(lambda: self.browser.js("location.href") == expected,
                                 f"{mode}: {location} must navigate to {href}")
                        if not href.startswith("#"):
                            wait_for(lambda: self.browser.js("document.readyState === 'complete'"),
                                     f"{href} must finish loading")


if __name__ == "__main__":
    unittest.main(verbosity=2)
