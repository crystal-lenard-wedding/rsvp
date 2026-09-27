(() => {
  const nav = document.querySelector('body > nav');
  if (!nav) return;

  const syncNavHeight = () => {
    document.documentElement.style.setProperty('--sticky-nav-height', `${nav.offsetHeight}px`);
  };

  syncNavHeight();
  if ('ResizeObserver' in window) {
    new ResizeObserver(syncNavHeight).observe(nav);
  } else {
    window.addEventListener('resize', syncNavHeight);
  }
})();