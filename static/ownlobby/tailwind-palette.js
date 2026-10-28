/* Shared by the local Tailwind build and the existing browser Tailwind setup. */
(function () {
  'use strict';
  function palette(c, previous) {
    previous = previous || {};
    return Object.assign({}, previous, {
      primary: {50: c.offwhite, 100: c.offwhite, 200: c.ivory, 300: c.gold,
        400: c.gold, 500: c.gold, 600: c.gold_light, 700: c.gold_light,
        800: c.hairline, 900: c.raised, 950: c.deep},
      delta: Object.assign({}, previous.delta, {base: c.deep, surface: c.surface,
        highlight: c.raised, gold: c.gold, violet: c.gold, electric: c.gold}),
      dc: Object.assign({}, previous.dc, {bg: c.deep, surface: c.surface, panel: c.raised,
        border: c.hairline, borderLight: c.hairline, text: c.muted, textBright: c.ivory,
        cyan: c.gold, purple: c.gold, gold: c.gold, dark: c.deep, card: c.surface,
        'card-hover': c.raised, cardhover: c.raised, accent: c.gold}),
      'dc-cyan': c.gold, 'dc-purple': c.gold, 'dc-gold': c.gold,
      'dc-dark': c.deep, 'dc-bg': c.deep, 'dc-surface': c.surface,
      'dc-card': c.surface, 'dc-card-hover': c.raised, 'dc-cardhover': c.raised,
      'dc-border': c.hairline, 'dc-accent': c.gold
    });
  }
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = palette;
    return;
  }
  var data = document.getElementById('ownlobby-palette');
  if (!data || typeof tailwind === 'undefined') return;
  try {
    var config = tailwind.config || {};
    config.theme = config.theme || {};
    config.theme.extend = config.theme.extend || {};
    config.theme.extend.colors = palette(JSON.parse(data.textContent), config.theme.extend.colors);
    tailwind.config = config;
  } catch (error) {
    // Compiled CSS and the server-rendered page remain usable without the CDN.
  }
}());
