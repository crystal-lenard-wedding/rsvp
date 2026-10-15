#!/usr/bin/env python3
"""Navigation analytics contract checks. Run directly with Python and Chromium."""

import json
import unittest

from browser_check import Browser


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
# The detail pages intentionally have no tracked Home, area, hotel or attraction
# reports. Keep this inventory explicit rather than deriving it from the handler.
DETAIL_LOCATIONS = {
    "body > nav": ["travel.html", "accommodations.html", "explore.html", GUIDE],
    ".mobile-menu": [],
    ".guest-guide-banner": [GUIDE],
    ".hero-cta": [],
    ".guide-grid": [],
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


class AnalyticsContract:
    page = "index.html"
    locations = LOCATIONS

    @classmethod
    def setUpClass(cls):
        cls.browser = Browser().__enter__()
        cls.addClassCleanup(cls.browser.__exit__, None, None, None)
        # No third-party scripts, fonts or guest-guide requests during this suite.
        cls.browser.call("Network.setBlockedURLs", {"urls": ["https://*"]})

    def setUp(self):
        self.browser.load(1280, path=self.page)
        self.browser.js("""
            window.analyticsCalls = [];
            window.analyticsErrors = [];
            window.addEventListener('error', e => analyticsErrors.push(e.message));
        """)

    def test_supported_locations_and_script_wiring(self):
        self.assertEqual(self.browser.js("""Array.from(document.scripts)
            .filter(s => s.getAttribute('src')?.split('?')[0] === 'analytics-events.js')
            .length"""), 1, f"{self.page} must load the analytics handler exactly once")
        for location, hrefs in self.locations.items():
            with self.subTest(location=location):
                actual = self.browser.js(f"""Array.from(
                    document.querySelectorAll({json.dumps(location + ' a[href]')}),
                    a => a.getAttribute('href')).filter(href => {json.dumps(list(EVENTS))}.includes(href))
                """)
                self.assertCountEqual(actual, hrefs, "Supported navigation links changed")
        if self.page == "index.html":
            self.assertEqual(self.browser.js(
                """document.querySelectorAll('.mobile-menu a[href="#weekend-contacts"]').length"""
            ), 1, "Weekend Contacts must remain an explicit untracked menu destination")
        else:
            self.assertEqual(self.browser.js(
                """document.querySelectorAll('body > nav a[href="index.html"]').length"""
            ), 2, "Both the logo and Back to Home must remain untracked")

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
            for location, hrefs in self.locations.items():
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
                                const results = [];
                                for (let repeat = 0; repeat < 2; repeat++) {{
                                    analyticsCalls.length = analyticsErrors.length = 0;
                                    target.dispatchEvent(new MouseEvent('click', {{
                                        bubbles: true, cancelable: true
                                    }}));
                                    results.push({{calls: [...analyticsCalls],
                                        errors: [...analyticsErrors], prevented: wasPrevented}});
                                }}
                                child.remove();
                                return results;
                            }})()""")
                            expected = [EVENTS[href]] if mode in ("available", "throwing") else []
                            for repeat, click in enumerate(result):
                                with self.subTest(repeat=repeat):
                                    self.assertEqual(click["calls"], expected, "Wrong report or duplicate dispatch")
                                    self.assertEqual(click["errors"], [], "Analytics error escaped the handler")
                                    self.assertFalse(click["prevented"], "Site code canceled navigation")

    def test_untracked_links_and_non_link_targets_stay_untracked(self):
        self.browser.js(MODES["available"])
        result = self.browser.js(f"""(() => {{
            window.addEventListener('click', e => e.preventDefault());
            const supported = {json.dumps(list(self.locations))}.join(', ');
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
        if self.page == "index.html":
            self.assertGreaterEqual(result["contacts"], 2, "Keep both Weekend Contacts controls covered")
        self.assertEqual(result["calls"], [], "An untracked link silently acquired an event")
        self.assertEqual(result["errors"], [], "Non-link clicks must be harmless")

    def test_unavailable_analytics_allows_real_local_navigation(self):
        # Unlike the dispatch matrix, these clicks have NO preventDefault guard.
        # Exercise every local supported link and Weekend Contacts in the real DOM.
        for mode in ("missing", "throwing", "non-callable"):
            for location, hrefs in self.locations.items():
                local_links = [(href, 0) for href in hrefs if not href.startswith("https:")]
                if location == ".mobile-menu" and self.page == "index.html":
                    local_links.append(("#weekend-contacts", 0))
                if location == "body > nav" and self.page != "index.html":
                    # Cover both untracked Home controls as well as tracked links.
                    local_links.extend([("index.html", 0), ("index.html", 1)])
                for href, occurrence in local_links:
                    with self.subTest(mode=mode, location=location, href=href, occurrence=occurrence):
                        self.browser.load(390 if location == ".mobile-menu" else 1280,
                                          path=self.page)
                        self.browser.js("window.analyticsCalls = [];" + MODES[mode])
                        if location == ".mobile-menu":
                            self.browser.js("toggleMenu()")
                        self.browser.js(
                            f"document.querySelectorAll({json.dumps(selector(location, href))})"
                            f"[{occurrence}].click()"
                        )
                        base = self.browser.url.rsplit("/", 1)[0] + "/"
                        expected = base + self.page + href if href.startswith("#") else base + href
                        self.browser.wait_js(f"location.href === {json.dumps(expected)}",
                                             f"{mode}: {location} must navigate to {href}")
                        if not href.startswith("#"):
                            self.browser.wait_js("document.readyState === 'complete'",
                                                 f"{href} must finish loading")


class AnalyticsChecks(AnalyticsContract, unittest.TestCase):
    """Homepage: all seven existing reports."""


class TravelAnalyticsChecks(AnalyticsContract, unittest.TestCase):
    page = "travel.html"
    locations = DETAIL_LOCATIONS


class AccommodationsAnalyticsChecks(AnalyticsContract, unittest.TestCase):
    page = "accommodations.html"
    locations = DETAIL_LOCATIONS


class ExploreAnalyticsChecks(AnalyticsContract, unittest.TestCase):
    page = "explore.html"
    locations = DETAIL_LOCATIONS


if __name__ == "__main__":
    unittest.main(verbosity=2)
