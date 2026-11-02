/* Decorative motion preference. Read only this preference, never account data. */
(function () {
  'use strict';
  if (window.muumeiMotion) return;
  var key = 'muumei-motion-choice-v1';
  var root = document.documentElement;
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  var connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  var choice = 'system';
  var snapshot = '';
  function normalize(value) { return value === 'on' || value === 'off' ? value : 'system'; }
  try { choice = normalize(window.localStorage.getItem(key)); } catch (_) {}
  function paint() {
    var reason = document.hidden ? 'hidden' : choice === 'off' ? 'user' : choice === 'on' ? 'ready' : reduced.matches ? 'reduced' : connection && connection.saveData ? 'data' : 'ready';
    var state = reason === 'ready' ? 'playing' : 'paused';
    root.dataset.motion = state;
    root.dataset.motionChoice = choice;
    root.dataset.motionReason = reason;
    var next = choice + ':' + state + ':' + reason;
    if (next === snapshot) return;
    snapshot = next;
    window.dispatchEvent(new CustomEvent('muumei:motion-change'));
  }
  window.muumeiMotion = {
    getSnapshot: function () { return snapshot; },
    setChoice: function (value) {
      if (value !== 'system' && value !== 'on' && value !== 'off') return false;
      choice = value;
      try {
        if (choice === 'system') window.localStorage.removeItem(key);
        else window.localStorage.setItem(key, choice);
      } catch (_) {}
      paint();
      return true;
    }
  };
  if (reduced.addEventListener) reduced.addEventListener('change', paint);
  else if (reduced.addListener) reduced.addListener(paint);
  if (connection && connection.addEventListener) connection.addEventListener('change', paint);
  document.addEventListener('visibilitychange', paint);
  window.addEventListener('storage', function (event) {
    if (event.key !== key && event.key !== null) return;
    if (event.storageArea && event.storageArea !== window.localStorage) return;
    choice = normalize(event.newValue);
    paint();
  });
  paint();
})();
