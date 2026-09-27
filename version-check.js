(function () {
  'use strict';

  const script = document.currentScript;
  const pageVersion = document.querySelector('meta[name="site-version"]')?.content;
  if (!script || !pageVersion) return;

  const versionUrl = new URL('version.json', script.src);
  versionUrl.searchParams.set('t', String(Date.now()));

  fetch(versionUrl, { cache: 'no-store' })
    .then(function (response) {
      if (!response.ok) throw new Error('Version check returned HTTP ' + response.status);
      return response.json();
    })
    .then(function (release) {
      if (!release || typeof release.version !== 'string' || !release.version) {
        throw new Error('Invalid version.json');
      }

      const currentUrl = new URL(window.location.href);
      const requestedVersion = currentUrl.searchParams.get('v');

      if (release.version === pageVersion) {
        // The versioned request succeeded. Restore the guest's original URL
        // without triggering another navigation or losing other query/hash data.
        if (requestedVersion !== null) {
          currentUrl.searchParams.delete('v');
          window.history.replaceState(window.history.state, '', currentUrl.href);
        }
        return;
      }

      // If GitHub Pages is still serving old HTML at the versioned URL, do not
      // loop. A later navigation will check the current deployment again.
      if (requestedVersion === release.version) return;

      currentUrl.searchParams.set('v', release.version);
      window.location.replace(currentUrl.href);
    })
    .catch(function (error) {
      // A temporary network or deployment error must not make the page unusable.
      console.warn('Could not check the site version:', error);
    });
}());