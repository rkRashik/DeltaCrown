// Mobile drawer + focus trap + scroll-shrink header
(function(){
  const header = document.getElementById("dc-header");
  const btn = document.getElementById("dc-menu-btn");
  const drawer = document.getElementById("dc-mobile-drawer");
  const panel = drawer ? drawer.querySelector('[role="dialog"]') : null;

  if (!btn || !drawer || !panel) return;

  let open = false;
  let lastFocus = null;

  function openDrawer(){
    lastFocus = document.activeElement;
    drawer.classList.remove("hidden");
    drawer.removeAttribute("aria-hidden");
    btn.setAttribute("aria-expanded", "true");

    // focus first link
    const first = panel.querySelector("a, button, [tabindex]:not([tabindex='-1'])");
    if (first) first.focus();

    // trap
    document.addEventListener("keydown", trap, true);
  }
  function closeDrawer(){
    drawer.classList.add("hidden");
    drawer.setAttribute("aria-hidden", "true");
    btn.setAttribute("aria-expanded", "false");
    document.removeEventListener("keydown", trap, true);
    if (lastFocus) lastFocus.focus();
  }
  function trap(e){
    if (e.key === "Escape") { e.preventDefault(); closeDrawer(); return; }
    if (e.key !== "Tab") return;
    const focusables = panel.querySelectorAll("a, button, input, select, textarea, [tabindex]:not([tabindex='-1'])");
    const list = Array.from(focusables).filter(el => !el.hasAttribute("disabled"));
    if (!list.length) return;
    const first = list[0], last = list[list.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  btn.addEventListener("click", () => {
    open ? closeDrawer() : openDrawer();
    open = !open;
  });

  drawer.addEventListener("click", (e) => {
    if (e.target && e.target.getAttribute("data-close") === "drawer") {
      open = false; closeDrawer();
    }
  });

  // Scroll shrink
  let last = 0;
  window.addEventListener("scroll", () => {
    const y = window.scrollY || 0;
    const goingDown = y > last;
    last = y;
    if (y > 8 && goingDown) header.classList.add("is-shrunk");
    else if (y < 8) header.classList.remove("is-shrunk");
  }, { passive: true });
})();
