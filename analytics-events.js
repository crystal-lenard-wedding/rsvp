(() => {
  const eventsByHref = {
    '#schedule': 'Schedule Click',
    '#dresscode': 'Dress Code Click',
    '#registry': 'Registry Click',
    'travel.html': 'Travel Click',
    'accommodations.html': 'Accommodations Click',
    'explore.html': 'Explore Click',
    'https://crystal-lenard-guest-guide.replit.app/': 'Mini Guest Guide Click'
  };

  document.addEventListener('click', (event) => {
    if (!(event.target instanceof Element)) return;
    const link = event.target.closest('a[href]');
    if (!link || !link.closest('body > nav, .mobile-menu, .guest-guide-banner, .hero-cta, .guide-grid')) return;

    const eventName = eventsByHref[link.getAttribute('href')];
    if (!eventName) return;

    try {
      window.plausible?.(eventName);
    } catch {
      // Analytics must never interfere with navigation.
    }
  });
})();