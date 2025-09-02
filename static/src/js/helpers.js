// static/src/js/helpers.js
export function qs(sel, root = document) { return root.querySelector(sel); }
export function qsa(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }
export function on(el, ev, fn, opts) { el && el.addEventListener(ev, fn, opts); }
