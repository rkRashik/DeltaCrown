(function () {
  'use strict';
  var source = document.getElementById('ownlobby-brand');
  if (!source) return;
  try { window.OWNLOBBY_BRAND = Object.freeze(JSON.parse(source.textContent)); }
  catch (error) { /* Static server-rendered branding remains the fallback. */ }
}());
