/* Helpers: qs, trapFocus, copyToClipboard, simple share handlers */
export function qs(sel, ctx=document){ return ctx.querySelector(sel); }
export function qsa(sel, ctx=document){ return Array.from(ctx.querySelectorAll(sel)); }

export function trapFocus(container) {
  const focusable = qsa('a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])', container)
    .filter(el => !el.hasAttribute('disabled'));
  if (!focusable.length) return;
  let first = focusable[0], last = focusable[focusable.length - 1];
  function onKey(e){
    if (e.key !== 'Tab') return;
    if (e.shiftKey && document.activeElement === first){ e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last){ e.preventDefault(); first.focus(); }
  }
  container.addEventListener('keydown', onKey);
  first.focus();
  return () => container.removeEventListener('keydown', onKey);
}

export async function copyToClipboard(text){
  try { await navigator.clipboard.writeText(text); window.toast && window.toast("Link copied"); }
  catch { /* noop */ }
}

function wireShare(){
  const wrap = qs("[data-share]");
  if (!wrap) return;
  const url = window.location.href;
  const fb = qs("[data-share-fb]", wrap);
  const ig = qs("[data-share-ig]", wrap);
  const dc = qs("[data-share-discord]", wrap);
  const wa = qs("[data-share-wa]", wrap);
  const cp = qs("[data-copy-url]", wrap);

  if (fb) fb.href = "https://www.facebook.com/sharer/sharer.php?u="+encodeURIComponent(url);
  if (ig) ig.href = "https://www.instagram.com/?url="+encodeURIComponent(url); // IG has no official share; opens app
  if (dc) dc.href = "https://discord.com/channels/@me"; // user pastes link
  if (wa) wa.href = "https://wa.me/?text="+encodeURIComponent(url);
  if (cp) cp.addEventListener("click", () => copyToClipboard(url));
}

function wireModal(){
  document.addEventListener("click", (e) => {
    const opener = e.target.closest("[data-modal-open]");
    if (opener){
      const id = opener.getAttribute("data-modal-open");
      const modal = typeof id === "string" ? document.querySelector(id) : opener;
      if (!modal) return;
      modal.hidden = false;
      const panel = modal.querySelector("[data-modal-panel]");
      trapFocus(panel||modal);
    }
    const closer = e.target.closest("[data-modal-close]");
    if (closer){
      const modal = closer.closest(".modal");
      if (modal) modal.hidden = true;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  wireShare();
  wireModal();
});
