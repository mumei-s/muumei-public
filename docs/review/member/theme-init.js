/* Read the saved appearance before the first paint. No account or network access. */
(function () {
  'use strict';
  if (window.muumeiTheme) return;
  var key = 'muumei-color-mode-v1';
  var root = document.documentElement;
  var media = window.matchMedia('(prefers-color-scheme: dark)');
  var choice = 'system';
  var normalize = function (value) { return value === 'light' || value === 'dark' ? value : 'system'; };
  try { choice = normalize(window.localStorage.getItem(key)); } catch (_) {}
  function paint() {
    var mode = choice === 'system' ? (media.matches ? 'dark' : 'light') : choice;
    root.dataset.colorMode = mode;
    root.classList.toggle('dark', mode === 'dark');
    root.dataset.themeChoice = choice;
    root.style.colorScheme = mode;
    var color = mode === 'dark' ? '#19191d' : '#fbfaf6';
    document.querySelectorAll('meta[name="theme-color"]').forEach(function (meta) {
      meta.removeAttribute('media');
      meta.setAttribute('content', color);
    });
    window.dispatchEvent(new CustomEvent('muumei:theme-change'));
  }
  window.muumeiTheme = {
    getChoice: function () { return choice; },
    getMode: function () { return root.dataset.colorMode; },
    setChoice: function (value) {
      if (value !== 'system' && value !== 'light' && value !== 'dark') return false;
      choice = value;
      try {
        if (choice === 'system') window.localStorage.removeItem(key);
        else window.localStorage.setItem(key, choice);
      } catch (_) {}
      paint();
      return true;
    }
  };
  var onSystemChange = function () { if (choice === 'system') paint(); };
  if (typeof media.addEventListener === 'function') media.addEventListener('change', onSystemChange);
  else if (typeof media.addListener === 'function') media.addListener(onSystemChange);
  window.addEventListener('storage', function (event) {
    if (event.key !== key && event.key !== null) return;
    if (event.storageArea) {
      try { if (event.storageArea !== window.localStorage) return; } catch (_) { return; }
    }
    choice = normalize(event.newValue);
    paint();
  });
  paint();
})();
